"""Floods, long chats and a spent budget are refused politely."""
import json

import pytest

import chat
from src import generate, limits

NOW = 1_800_000_000.0


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in limits._ENV.values():
        monkeypatch.delenv(name, raising=False)


def test_flood_of_messages_is_refused():
    state = {}
    results = [limits.check_chat(state, now=NOW + i) for i in range(20)]
    assert results[:6] == [None] * 6
    assert all(r == limits.TOO_FAST for r in results[6:])


def test_messages_allowed_again_after_a_minute():
    state = {}
    for i in range(6):
        assert limits.check_chat(state, now=NOW + i) is None
    assert limits.check_chat(state, now=NOW + 7) == limits.TOO_FAST
    assert limits.check_chat(state, now=NOW + 61) is None


def test_chat_message_cap(monkeypatch):
    monkeypatch.setenv("ANA_MAX_MESSAGES_PER_CHAT", "3")
    state = {}
    for i in range(3):
        assert limits.check_chat(state, now=NOW + i * 60) is None
    assert limits.check_chat(state, now=NOW + 500) == limits.CHAT_FULL


def test_brand_config_sets_limit_and_env_overrides(monkeypatch):
    cfg = {"limits": {"max_messages_per_minute": 2}}
    assert limits.setting(cfg, "max_messages_per_minute") == 2
    monkeypatch.setenv("ANA_MAX_MESSAGES_PER_MINUTE", "9")
    assert limits.setting(cfg, "max_messages_per_minute") == 9


def test_visitor_limit_spans_chats():
    rl = limits.RateLimiter()
    assert all(rl.allow("1.2.3.4", 10, now=NOW + i) for i in range(10))
    assert not rl.allow("1.2.3.4", 10, now=NOW + 11)
    assert rl.allow("5.6.7.8", 10, now=NOW + 11)
    assert rl.allow(None, 10, now=NOW)  # unknown visitor: chat limit still applies


def _cfg(tmp_path, ceiling=1.0):
    return {"analytics_log": str(tmp_path / "brand.jsonl"), "limits": {"monthly_spend_usd": ceiling}}


def test_spend_is_recorded_per_month(tmp_path):
    cfg = _cfg(tmp_path)
    limits.record_spend(cfg, [{"prompt_tokens": 1_000_000, "completion_tokens": 0}], now=NOW)
    assert limits.spent_this_month(cfg, now=NOW) == pytest.approx(0.5)
    assert limits.spent_this_month(cfg, now=NOW + 40 * 86400) == 0.0  # new month starts at zero
    data = json.loads(limits.spend_file(cfg).read_text())
    assert list(data.values())[0]["prompt_tokens"] == 1_000_000


def test_over_budget_after_ceiling(tmp_path):
    cfg = _cfg(tmp_path, ceiling=1.0)
    assert not limits.over_budget(cfg, now=NOW)
    limits.record_spend(cfg, [{"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000}], now=NOW)
    assert limits.over_budget(cfg, now=NOW)


def test_zero_ceiling_switches_spend_limit_off(tmp_path):
    cfg = _cfg(tmp_path, ceiling=0)
    limits.record_spend(cfg, [{"prompt_tokens": 10**9, "completion_tokens": 0}])
    assert not limits.over_budget(cfg)


def test_track_usage_collects_reported_or_estimated_tokens(monkeypatch):
    msgs = [{"role": "user", "content": "x" * 400}]
    with generate.track_usage() as usage:
        generate._note_usage(msgs, {"usage": {"prompt_tokens": 7, "completion_tokens": 3}}, "hi")
        generate._note_usage(msgs, {}, "y" * 40)
    assert usage == [{"prompt_tokens": 7, "completion_tokens": 3}, {"prompt_tokens": 100, "completion_tokens": 10}]
    generate._note_usage(msgs, {}, "z")  # outside the block: nothing recorded, no error


class _Emb:
    def embed(self, texts):
        raise AssertionError("no work should happen once the budget is spent")


def test_ask_refuses_politely_when_budget_spent(tmp_path):
    cfg = _cfg(tmp_path, ceiling=0.01)
    limits.record_spend(cfg, [{"prompt_tokens": 1_000_000, "completion_tokens": 0}])
    out = chat.ask([], [], None, _Emb(), "p", [], [], [], cfg, "Where is my parcel?")
    assert out == limits.OVER_BUDGET
