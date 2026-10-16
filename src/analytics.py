"""Minimal usage analytics: append interactions to a JSONL log and aggregate them.

One JSON object per line, so the log is append-only, cheap, and readable later.
Each row records the question, whether it was answered or deflected (abstained),
the top retrieved source, and the confidence. Client-agnostic: the log path is
resolved per-client in config.py.

Privacy: emails, phone numbers and order-like numbers are hidden before a
question is written, and rows older than the retention period (30 days by
default, ANA_LOG_RETENTION_DAYS to change) are deleted on each write.
"""
import json
import os
import re
import time
from collections import Counter
from pathlib import Path

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# "order 12345", "order #AB-1234", "order no: 98765", "ref X12345", "#100234"
_ORDER = re.compile(
    r"(?i)\b(?:order|ord|invoice|ref|reference|tracking)\b\s*(?:no\.?|number|num|id)?\s*[:#]?\s*"
    r"(?=[A-Z0-9-]*\d)[A-Z0-9][A-Z0-9-]{2,}"
    r"|#\s?\d{3,}"
)
# Phone numbers: optional +, then at least 7 digits with spaces, dots, dashes or brackets.
_PHONE = re.compile(r"\+?\(?\d[\d\s().-]{5,}\d")
# Any other long run of digits (account, card or order numbers without a label).
_LONG_NUMBER = re.compile(r"\d{5,}")

DEFAULT_RETENTION_DAYS = 30


def redact(text: str) -> str:
    """Hide emails, order numbers, phone numbers and long digit runs in shopper text."""
    text = _EMAIL.sub("[email]", text or "")
    text = _ORDER.sub("[order]", text)
    text = _PHONE.sub(lambda m: "[phone]" if sum(c.isdigit() for c in m.group(0)) >= 7 else m.group(0), text)
    return _LONG_NUMBER.sub("[number]", text)


def retention_days() -> int:
    """How many days of log rows to keep. ANA_LOG_RETENTION_DAYS overrides; 0 keeps everything."""
    raw = os.environ.get("ANA_LOG_RETENTION_DAYS", "").strip()
    try:
        return int(raw) if raw else DEFAULT_RETENTION_DAYS
    except ValueError:
        return DEFAULT_RETENTION_DAYS


def prune(path, days=None, now=None) -> int:
    """Delete rows older than `days` from the log. Returns how many were removed."""
    days = retention_days() if days is None else days
    p = Path(path)
    if days <= 0 or not p.exists():
        return 0
    cutoff = (now or time.time()) - days * 86400
    keep, removed = [], 0
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            ts = json.loads(line).get("ts", 0)
        except (json.JSONDecodeError, AttributeError):
            ts = 0  # unreadable rows are not kept past their welcome
        if isinstance(ts, (int, float)) and ts >= cutoff:
            keep.append(line)
        else:
            removed += 1
    if removed:
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text("".join(l + "\n" for l in keep), encoding="utf-8")
        tmp.replace(p)
    return removed


def log(path, *, question, answered, source, confidence, error=None, retention=None):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    prune(p, retention)
    question = redact(question or "")
    row = {
        "ts": time.time(),
        "question": question,
        "answered": answered,
        "source": source,
        "confidence": round(confidence, 4) if confidence is not None else None,
    }
    if error:
        row["error"] = error
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def recent_failures(path, limit=20):
    """Return the most recent rows that recorded an error, for a failure alert."""
    p = Path(path)
    if not p.exists():
        return []
    fails = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("error"):
            fails.append(e)
    return fails[-limit:]


def summarize(path, limit_recent=10):
    events = []
    p = Path(path)
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                events.append(json.loads(line))
    total = len(events)
    answered = sum(1 for e in events if e.get("answered"))
    deflected = total - answered
    sources = Counter(e.get("source") for e in events if e.get("source"))
    return {
        "total": total,
        "answered": answered,
        "deflected": deflected,
        "deflection_rate": (deflected / total) if total else 0.0,
        "top_sources": sources.most_common(5),
        "recent": events[-limit_recent:],
    }