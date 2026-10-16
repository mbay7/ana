"""Limits that keep one chat, one visitor or one brand from running up the bill.

Three checks, all cheap and in-process:
- messages per chat (a whole conversation) and messages per minute,
- messages per minute per visitor (across chats, when the visitor's address is known),
- a monthly spend ceiling per brand, estimated from token counts and kept in a
  small JSON file next to the brand's log.

Settings come from the brand's config.yaml (`limits:` block) or environment
variables; the environment wins so the live server can tighten them without a
code change. A limit of 0 switches that limit off.

This is the minimal, in-app version. A limit at the proxy (Cloudflare) is still
needed to stop floods before they reach the app.
"""
import json
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

DEFAULTS = {
    "max_messages_per_chat": 40,
    "max_messages_per_minute": 6,
    "max_visitor_messages_per_minute": 10,
    "monthly_spend_usd": 20.0,
    # Rough model price, US dollars per million tokens. Set to your model's real price.
    "price_in_per_mtok": 0.5,
    "price_out_per_mtok": 1.5,
}

_ENV = {
    "max_messages_per_chat": "ANA_MAX_MESSAGES_PER_CHAT",
    "max_messages_per_minute": "ANA_MAX_MESSAGES_PER_MINUTE",
    "max_visitor_messages_per_minute": "ANA_MAX_VISITOR_MESSAGES_PER_MINUTE",
    "monthly_spend_usd": "ANA_MONTHLY_SPEND_USD",
    "price_in_per_mtok": "ANA_PRICE_IN_PER_MTOK",
    "price_out_per_mtok": "ANA_PRICE_OUT_PER_MTOK",
}

CHAT_FULL = "We've covered a lot in this chat. To keep things running smoothly, please start a new chat or contact the team directly."
TOO_FAST = "You're sending messages a little fast. Please wait a moment and try again."
OVER_BUDGET = "Sorry, I can't answer new questions right now. Please contact the team directly and they'll be happy to help."


def setting(cfg, name):
    """A limit from the environment, then the brand config, then the default."""
    raw = os.environ.get(_ENV[name], "").strip()
    if not raw:
        raw = ((cfg or {}).get("limits") or {}).get(name, DEFAULTS[name])
    try:
        return float(raw)
    except (TypeError, ValueError):
        return float(DEFAULTS[name])


# --- messages per chat and per minute -------------------------------------------------

def check_chat(state: dict, cfg=None, now=None) -> str | None:
    """Count one message against a chat. Returns a polite refusal, or None if allowed.

    `state` is the chat's own storage (Streamlit's session_state works).
    """
    now = time.time() if now is None else now
    max_chat = setting(cfg, "max_messages_per_chat")
    max_min = setting(cfg, "max_messages_per_minute")
    stamps = [t for t in state.get("_ana_msg_times", []) if now - t < 60]
    count = state.get("_ana_msg_count", 0)
    if max_chat and count >= max_chat:
        return CHAT_FULL
    if max_min and len(stamps) >= max_min:
        state["_ana_msg_times"] = stamps
        return TOO_FAST
    stamps.append(now)
    state["_ana_msg_times"] = stamps
    state["_ana_msg_count"] = count + 1
    return None


class RateLimiter:
    """Sliding one-minute window per key (e.g. a visitor's address), shared across chats."""

    def __init__(self):
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key, per_minute, now=None) -> bool:
        if not key or not per_minute:
            return True
        now = time.time() if now is None else now
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] >= 60:
                q.popleft()
            if len(q) >= per_minute:
                return False
            q.append(now)
            if len(self._hits) > 10000:  # forget idle visitors so memory stays bounded
                for k in [k for k, v in self._hits.items() if not v or now - v[-1] >= 60]:
                    del self._hits[k]
            return True


# --- monthly spend ceiling per brand --------------------------------------------------

_spend_lock = threading.Lock()


def _month(now=None) -> str:
    return datetime.fromtimestamp(time.time() if now is None else now, timezone.utc).strftime("%Y-%m")


def spend_file(cfg) -> Path:
    if cfg.get("spend_file"):
        return Path(cfg["spend_file"])
    return Path(cfg["analytics_log"]).with_suffix(".spend.json")


def cost_usd(cfg, prompt_tokens, completion_tokens) -> float:
    return (
        prompt_tokens * setting(cfg, "price_in_per_mtok")
        + completion_tokens * setting(cfg, "price_out_per_mtok")
    ) / 1_000_000


def spent_this_month(cfg, now=None) -> float:
    p = spend_file(cfg)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return 0.0
    return float((data.get(_month(now)) or {}).get("usd", 0.0))


def over_budget(cfg, now=None) -> bool:
    ceiling = setting(cfg, "monthly_spend_usd")
    return bool(ceiling) and spent_this_month(cfg, now) >= ceiling


def record_spend(cfg, usage, now=None) -> float:
    """Add a message's token usage (list of {prompt_tokens, completion_tokens}) to this month."""
    pt = sum(int(u.get("prompt_tokens", 0) or 0) for u in usage)
    ct = sum(int(u.get("completion_tokens", 0) or 0) for u in usage)
    usd = cost_usd(cfg, pt, ct)
    if not usd:
        return 0.0
    p = spend_file(cfg)
    month = _month(now)
    with _spend_lock:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            data = {}
        row = data.get(month) or {"usd": 0.0, "prompt_tokens": 0, "completion_tokens": 0}
        row["usd"] = round(row.get("usd", 0.0) + usd, 6)
        row["prompt_tokens"] = row.get("prompt_tokens", 0) + pt
        row["completion_tokens"] = row.get("completion_tokens", 0) + ct
        data[month] = row
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
        tmp.replace(p)
    return usd
