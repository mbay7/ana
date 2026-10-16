"""Limits that keep one chat, one visitor or one brand from running up the bill.

Checks, all in-process:
- messages per minute for the whole server: always on, so even with no way to
  tell visitors apart there is a conservative ceiling, never "no limit";
- messages per minute and per hour per visitor, kept on the server, so reloading
  the page or opening a new chat does not reset them. The visitor's address is
  used only when it comes from Cloudflare (ANA_BEHIND_CLOUDFLARE switched on);
  a header a visitor can forge, like X-Forwarded-For, is never trusted;
- messages per chat and per minute in that chat (an extra, resettable layer);
- a monthly spend ceiling per brand. The likely cost of a message is reserved
  BEFORE the model is called and settled with the real token count after, so a
  burst of parallel messages cannot overshoot the ceiling.

Everything fails closed: if the spend file cannot be read, written or locked,
or the limiter is full, the message is refused politely rather than let through.

Settings come from the brand's config.yaml (`limits:` block) or environment
variables; the environment wins. 0 switches a limit off (except the server-wide
limit and the spend ceiling's reservation, which always apply); negative,
non-numeric or infinite values fall back to the default.

This is the in-app layer only. The real per-address limit must also live at the
proxy (Cloudflare rate limiting) so floods are stopped before they reach the app.
"""
import contextlib
import json
import math
import os
import tempfile
import threading
import time
from collections import OrderedDict, deque
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows; the thread lock still applies
    fcntl = None

DEFAULTS = {
    "max_messages_per_chat": 40,
    "max_messages_per_minute": 6,
    "max_visitor_messages_per_minute": 10,
    "max_visitor_messages_per_hour": 60,
    "max_server_messages_per_minute": 60,
    "monthly_spend_usd": 20.0,
    # Rough model price, US dollars per million tokens. Set to your model's real price.
    "price_in_per_mtok": 0.5,
    "price_out_per_mtok": 1.5,
    # Tokens reserved per message before the model is called (system prompt + documents).
    "reserve_prompt_tokens": 3000,
}

_ENV = {
    "max_messages_per_chat": "ANA_MAX_MESSAGES_PER_CHAT",
    "max_messages_per_minute": "ANA_MAX_MESSAGES_PER_MINUTE",
    "max_visitor_messages_per_minute": "ANA_MAX_VISITOR_MESSAGES_PER_MINUTE",
    "max_visitor_messages_per_hour": "ANA_MAX_VISITOR_MESSAGES_PER_HOUR",
    "max_server_messages_per_minute": "ANA_MAX_SERVER_MESSAGES_PER_MINUTE",
    "monthly_spend_usd": "ANA_MONTHLY_SPEND_USD",
    "price_in_per_mtok": "ANA_PRICE_IN_PER_MTOK",
    "price_out_per_mtok": "ANA_PRICE_OUT_PER_MTOK",
    "reserve_prompt_tokens": "ANA_RESERVE_PROMPT_TOKENS",
}

# Limits that may never be switched off with 0.
_ALWAYS_ON = {"max_server_messages_per_minute", "reserve_prompt_tokens", "price_in_per_mtok", "price_out_per_mtok"}

CHAT_FULL = "We've covered a lot in this chat. To keep things running smoothly, please start a new chat or contact the team directly."
TOO_FAST = "You're sending messages a little fast. Please wait a moment and try again."
BUSY = "I'm a little busy right now. Please try again in a minute."
OVER_BUDGET = "Sorry, I can't answer new questions right now. Please contact the team directly and they'll be happy to help."

SERVER_KEY = "*server*"
_KEEP_MONTHS = 12


def setting(cfg, name) -> float:
    """A limit from the environment, then the brand config, then the default."""
    default = float(DEFAULTS[name])
    raw = os.environ.get(_ENV[name], "").strip()
    if not raw:
        raw = ((cfg or {}).get("limits") or {}).get(name, default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    if math.isnan(value) or math.isinf(value) or value < 0:
        return default
    if value == 0 and name in _ALWAYS_ON:
        return default
    return value


# --- message limits -----------------------------------------------------------------

def _now(now):
    return time.time() if now is None else now


def check_chat(state, cfg=None, now=None) -> str | None:
    """Count one message against a chat. Returns a polite refusal, or None if allowed.

    `state` is the chat's own storage (Streamlit's session_state). A visitor can
    reset it by reloading, so it is only an extra layer: `check_message` applies
    the limits kept on the server first.
    """
    now = _now(now)
    max_chat = setting(cfg, "max_messages_per_chat")
    max_min = setting(cfg, "max_messages_per_minute")
    try:
        # A stamp "in the future" (clock moved back) is dropped, not kept forever.
        stamps = [t for t in state.get("_ana_msg_times", []) if 0 <= now - t < 60]
        count = int(state.get("_ana_msg_count", 0))
    except (TypeError, ValueError, AttributeError):
        return TOO_FAST  # unreadable state: refuse rather than let through
    if max_chat and count >= max_chat:
        return CHAT_FULL
    if max_min and len(stamps) >= max_min:
        state["_ana_msg_times"] = stamps
        return TOO_FAST
    stamps.append(now)
    state["_ana_msg_times"] = stamps[-max(int(max_min), 1):]  # never grows past the limit
    state["_ana_msg_count"] = count + 1
    return None


class RateLimiter:
    """Sliding-window counts per key, shared by every chat on the server.

    Memory is bounded: at most `max_keys` keys are tracked and each holds at most
    `limit` timestamps. When it is full of active keys, new keys are refused
    (fail closed) rather than evicting someone else's count.
    """

    def __init__(self, max_keys=10000):
        self._hits = OrderedDict()
        self._lock = threading.Lock()
        self.max_keys = max_keys

    def allow(self, key, limit, window=60, now=None) -> bool:
        if not limit:
            return True
        if not key:
            raise ValueError("a rate-limit key is required")
        now = _now(now)
        limit = int(min(limit, 100_000))
        with self._lock:
            q = self._hits.get(key)
            if q is None:
                if len(self._hits) >= self.max_keys:
                    self._forget_idle(now)
                if len(self._hits) >= self.max_keys:
                    return False
                q = self._hits[key] = deque()
            while q and not (0 <= now - q[0] < window):
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            self._hits.move_to_end(key)
            return True

    def _forget_idle(self, now):
        # Idle for an hour (the longest window used) or holding a future stamp.
        for k in [k for k, v in self._hits.items() if not v or not (0 <= now - v[-1] < 3600)]:
            del self._hits[k]

    def __len__(self):
        return len(self._hits)


def visitor_key(headers, env=None):
    """The visitor's address, only when the request really came through Cloudflare.

    Cloudflare sets CF-Connecting-IP itself, but anyone reaching the app directly
    could forge it, so it is used only when ANA_BEHIND_CLOUDFLARE is switched on
    (the app is reachable only through Cloudflare). X-Forwarded-For is never used:
    its first entry is whatever the visitor sent. Returns None when unknown.
    """
    env = os.environ if env is None else env
    if env.get("ANA_BEHIND_CLOUDFLARE", "").strip().lower() not in ("1", "true", "yes", "on"):
        return None
    try:
        ip = ((headers or {}).get("CF-Connecting-IP") or "").strip()
    except Exception:
        return None
    if not ip or len(ip) > 45 or not all(c in "0123456789abcdefABCDEF.:" for c in ip):
        return None
    return "ip:" + ip


def check_message(state, cfg, limiter, visitor=None, now=None) -> str | None:
    """All per-message limits in one place. Returns a polite refusal, or None if allowed.

    The server-wide limit always applies, so an unknown visitor still meets a
    ceiling. A known visitor is also counted per minute and per hour on the
    server, which a reload cannot reset.
    """
    if not limiter.allow(SERVER_KEY, setting(cfg, "max_server_messages_per_minute"), 60, now):
        return BUSY
    if visitor:
        if not limiter.allow(visitor + "/m", setting(cfg, "max_visitor_messages_per_minute"), 60, now):
            return TOO_FAST
        if not limiter.allow(visitor + "/h", setting(cfg, "max_visitor_messages_per_hour"), 3600, now):
            return CHAT_FULL
    return check_chat(state, cfg, now)


# --- monthly spend ceiling per brand --------------------------------------------------

_spend_lock = threading.Lock()
LOCK_TIMEOUT = 2.0  # seconds to wait for the spend file before refusing


class LedgerError(Exception):
    """The spend file cannot be read, written or locked."""


def _month(now=None) -> str:
    # Always UTC, so a server's local time zone or daylight saving cannot shift months.
    return datetime.fromtimestamp(_now(now), timezone.utc).strftime("%Y-%m")


def spend_file(cfg) -> Path:
    if cfg.get("spend_file"):
        return Path(cfg["spend_file"])
    return Path(cfg["analytics_log"]).with_suffix(".spend.json")


def cost_usd(cfg, prompt_tokens, completion_tokens) -> float:
    return (
        max(prompt_tokens, 0) * setting(cfg, "price_in_per_mtok")
        + max(completion_tokens, 0) * setting(cfg, "price_out_per_mtok")
    ) / 1_000_000


def estimate_usd(cfg, question="") -> float:
    """The most a single message is expected to cost, reserved before the model call."""
    prompt = setting(cfg, "reserve_prompt_tokens") + len(question or "") // 2
    try:
        completion = max(float((cfg or {}).get("max_tokens", 250) or 250), 0)
    except (TypeError, ValueError):
        completion = 250.0
    return cost_usd(cfg, prompt, completion)


def _read_ledger(p: Path) -> dict:
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}  # a new brand or a new install: nothing spent yet
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
        raise LedgerError(str(e)) from e
    if not isinstance(data, dict):
        raise LedgerError("spend file is not a JSON object")
    return data


def _write_ledger(p: Path, data: dict):
    for month in sorted(data)[:-_KEEP_MONTHS]:  # keep the file small: last twelve months
        del data[month]
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=p.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)  # atomic: readers see the old file or the new one, never half
    except OSError as e:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise LedgerError(str(e)) from e


@contextlib.contextmanager
def _locked(p: Path, timeout=None):
    """One writer at a time, across threads and processes. Raises LedgerError if it cannot lock."""
    timeout = LOCK_TIMEOUT if timeout is None else timeout
    if not _spend_lock.acquire(timeout=timeout):
        raise LedgerError("spend file busy")
    try:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            lf = open(str(p) + ".lock", "a")
        except OSError as e:
            raise LedgerError(str(e)) from e
        with lf:
            if fcntl:
                deadline = time.monotonic() + timeout
                while True:
                    try:
                        fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except OSError:
                        if time.monotonic() > deadline:
                            raise LedgerError("spend file locked")
                        time.sleep(0.02)
            try:
                yield
            finally:
                if fcntl:
                    fcntl.flock(lf, fcntl.LOCK_UN)
    finally:
        _spend_lock.release()


def spent_this_month(cfg, now=None) -> float:
    """Spend so far this month. Raises LedgerError if the file is unreadable."""
    try:
        return float((_read_ledger(spend_file(cfg)).get(_month(now)) or {}).get("usd", 0.0))
    except (TypeError, ValueError, AttributeError) as e:
        raise LedgerError(str(e)) from e


def over_budget(cfg, now=None) -> bool:
    ceiling = setting(cfg, "monthly_spend_usd")
    if not ceiling:
        return False
    try:
        return spent_this_month(cfg, now) >= ceiling
    except LedgerError:
        return True  # cannot tell how much was spent: refuse rather than overspend


def _add(row, usd, pt=0, ct=0):
    row["usd"] = round(float(row.get("usd", 0.0)) + usd, 6)
    row["prompt_tokens"] = int(row.get("prompt_tokens", 0)) + pt
    row["completion_tokens"] = int(row.get("completion_tokens", 0)) + ct


def reserve(cfg, usd, now=None):
    """Hold `usd` against this month's ceiling before calling the model.

    Returns a reservation to pass to `settle`, or None when the ceiling would be
    passed or the spend file cannot be read, written or locked (fail closed).
    """
    ceiling = setting(cfg, "monthly_spend_usd")
    p = spend_file(cfg)
    month = _month(now)
    try:
        with _locked(p):
            data = _read_ledger(p)
            row = data.get(month) or {}
            if ceiling and float(row.get("usd", 0.0)) + usd > ceiling:
                return None
            _add(row, usd)
            data[month] = row
            _write_ledger(p, data)
    except (LedgerError, OSError, TypeError, ValueError, AttributeError):
        return None
    return {"month": month, "usd": usd}


def settle(cfg, reservation, usage) -> float:
    """Replace a reservation with the real cost of the calls made (list of token counts).

    Settled against the month the reservation was made in, so a message that
    crosses midnight at the month's end is not charged twice or lost.
    """
    pt = sum(max(int(u.get("prompt_tokens", 0) or 0), 0) for u in usage)
    ct = sum(max(int(u.get("completion_tokens", 0) or 0), 0) for u in usage)
    actual = cost_usd(cfg, pt, ct)
    held = reservation["usd"] if reservation else 0.0
    month = reservation["month"] if reservation else _month()
    p = spend_file(cfg)
    try:
        with _locked(p):
            data = _read_ledger(p)
            row = data.get(month) or {}
            _add(row, actual - held, pt, ct)
            data[month] = row
            _write_ledger(p, data)
    except (LedgerError, OSError, TypeError, ValueError, AttributeError):
        pass  # the reservation stays charged: errs toward spending less, not more
    return actual


def record_spend(cfg, usage, now=None) -> float:
    """Add token usage to this month with no reservation (owner tools and tests)."""
    return settle(cfg, {"month": _month(now), "usd": 0.0}, usage)
