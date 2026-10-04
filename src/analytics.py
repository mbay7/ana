"""Minimal usage analytics: append interactions to a JSONL log and aggregate them.

One JSON object per line, so the log is append-only, cheap, and readable later.
Each row records the question, whether it was answered or deflected (abstained),
the top retrieved source, and the confidence. Client-agnostic: the log path is
resolved per-client in config.py.
"""
import json
import time
from collections import Counter
from pathlib import Path


def log(path, *, question, answered, source, confidence, error=None):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
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