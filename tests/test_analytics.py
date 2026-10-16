"""Logs hide personal details and keep only the retention period."""
import json
import time

import pytest

from src import analytics


@pytest.mark.parametrize("text,hidden,marker", [
    ("my email is sarah@example.com", "sarah@example.com", "[email]"),
    ("call me on +44 7700 900123 please", "7700 900123", "[phone]"),
    ("ring 07700-900-123", "07700-900-123", "[phone]"),
    ("where is order #AB-12345?", "AB-12345", "[order]"),
    ("order number: 987654 is late", "987654", "[order]"),
    ("ref X1234567", "X1234567", "[order]"),
    ("is #100234 shipped", "100234", "[order]"),
    ("my code 4815162342", "4815162342", "["),
])
def test_redact_hides_personal_details(text, hidden, marker):
    out = analytics.redact(text)
    assert hidden not in out
    assert marker in out


def test_redact_leaves_ordinary_questions_alone():
    q = "Do you deliver in 2-3 days for under £40 on 3 lamps?"
    assert analytics.redact(q) == q


def test_log_writes_redacted_question(tmp_path):
    path = tmp_path / "log.jsonl"
    analytics.log(path, question="order 55512345, phone +971 50 123 4567", answered=True, source="s", confidence=0.5)
    row = json.loads(path.read_text().strip())
    assert "55512345" not in row["question"] and "123 4567" not in row["question"]


def _rows(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def test_log_prunes_rows_older_than_retention(tmp_path, monkeypatch):
    monkeypatch.delenv("ANA_LOG_RETENTION_DAYS", raising=False)
    path = tmp_path / "log.jsonl"
    old = {"ts": time.time() - 31 * 86400, "question": "old", "answered": True}
    recent = {"ts": time.time() - 2 * 86400, "question": "recent", "answered": True}
    path.write_text(json.dumps(old) + "\n" + json.dumps(recent) + "\n")
    analytics.log(path, question="new", answered=True, source=None, confidence=None)
    assert [r["question"] for r in _rows(path)] == ["recent", "new"]


def test_retention_setting_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("ANA_LOG_RETENTION_DAYS", "1")
    path = tmp_path / "log.jsonl"
    path.write_text(json.dumps({"ts": time.time() - 2 * 86400, "question": "q"}) + "\n")
    analytics.log(path, question="new", answered=True, source=None, confidence=None)
    assert [r["question"] for r in _rows(path)] == ["new"]


def test_retention_zero_keeps_everything(tmp_path):
    path = tmp_path / "log.jsonl"
    path.write_text(json.dumps({"ts": 1, "question": "ancient"}) + "\n")
    assert analytics.prune(path, days=0) == 0
    assert _rows(path)[0]["question"] == "ancient"
