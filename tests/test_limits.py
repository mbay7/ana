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
    assert all(rl.allow("ip:1.2.3.4", 10, now=NOW + i) for i in range(10))
    assert not rl.allow("ip:1.2.3.4", 10, now=NOW + 11)
    assert rl.allow("ip:5.6.7.8", 10, now=NOW + 11)


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


# --- review round: trust boundary, fail-closed, bounded state, reservation ---------

def test_cloudflare_header_ignored_unless_behind_cloudflare():
    h = {"CF-Connecting-IP": "1.2.3.4", "X-Forwarded-For": "6.6.6.6, 1.2.3.4"}
    assert limits.visitor_key(h, env={}) is None
    assert limits.visitor_key(h, env={"ANA_BEHIND_CLOUDFLARE": "1"}) == "ip:1.2.3.4"
    # X-Forwarded-For is never used, even behind Cloudflare.
    assert limits.visitor_key({"X-Forwarded-For": "6.6.6.6"}, env={"ANA_BEHIND_CLOUDFLARE": "1"}) is None
    assert limits.visitor_key({"CF-Connecting-IP": "evil<script>"}, env={"ANA_BEHIND_CLOUDFLARE": "1"}) is None


def test_reload_does_not_reset_server_side_visitor_limit():
    rl = limits.RateLimiter()
    allowed = 0
    for i in range(30):
        fresh_chat = {}  # a reload gives a brand-new session every time
        if limits.check_message(fresh_chat, {}, rl, "ip:1.2.3.4", now=NOW + i) is None:
            allowed += 1
    assert allowed == 10


def test_visitor_hourly_cap_survives_new_chats():
    rl = limits.RateLimiter()
    cfg = {"limits": {"max_visitor_messages_per_hour": 5}}
    results = [limits.check_message({}, cfg, rl, "ip:1.2.3.4", now=NOW + i * 61) for i in range(7)]
    assert results[:5] == [None] * 5
    assert results[5] == limits.CHAT_FULL


def test_unknown_visitors_still_meet_a_server_wide_limit():
    rl = limits.RateLimiter()
    results = [limits.check_message({}, {}, rl, None, now=NOW) for _ in range(80)]
    assert results.count(None) == 60
    assert limits.BUSY in results


@pytest.mark.parametrize("bad", ["-5", "nan", "inf", "lots", "0"])
def test_bad_or_zero_server_limit_falls_back_to_default(monkeypatch, bad):
    monkeypatch.setenv("ANA_MAX_SERVER_MESSAGES_PER_MINUTE", bad)
    assert limits.setting({}, "max_server_messages_per_minute") == 60


def test_negative_chat_limit_uses_default(monkeypatch):
    monkeypatch.setenv("ANA_MAX_MESSAGES_PER_MINUTE", "-1")
    assert limits.setting({}, "max_messages_per_minute") == 6


def test_limiter_memory_bounded_and_fails_closed_when_full():
    rl = limits.RateLimiter(max_keys=100)
    results = [rl.allow(f"ip:{i}", 5, now=NOW) for i in range(150)]
    assert len(rl) <= 100
    assert results[:100] == [True] * 100 and not any(results[100:])
    # Idle keys are forgotten later, making room again.
    assert rl.allow("ip:new", 5, now=NOW + 4000)


def test_chat_state_bounded_even_with_minute_limit_off(monkeypatch):
    monkeypatch.setenv("ANA_MAX_MESSAGES_PER_MINUTE", "0")
    monkeypatch.setenv("ANA_MAX_MESSAGES_PER_CHAT", "0")
    state = {}
    for i in range(1000):
        limits.check_chat(state, now=NOW + i)
    assert len(state["_ana_msg_times"]) <= 1


def test_clock_moving_back_does_not_lock_forever():
    state = {}
    for i in range(6):
        limits.check_chat(state, now=NOW + 3600 + i)  # stamps "in the future"
    assert limits.check_chat(state, now=NOW) is None


def test_corrupt_spend_file_fails_closed(tmp_path):
    cfg = _cfg(tmp_path)
    limits.spend_file(cfg).write_text("{not json")
    assert limits.over_budget(cfg)
    assert limits.reserve(cfg, 0.001) is None
    assert limits.spend_file(cfg).read_text() == "{not json"  # never overwritten


def test_unwritable_spend_file_fails_closed(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)

    def boom(*a, **k):
        raise limits.LedgerError("disk full")

    monkeypatch.setattr(limits, "_write_ledger", boom)
    assert limits.reserve(cfg, 0.001) is None


def test_locked_spend_file_fails_closed(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    monkeypatch.setattr(limits, "LOCK_TIMEOUT", 0.05)
    assert limits._spend_lock.acquire()
    try:
        with pytest.raises(limits.LedgerError):
            with limits._locked(limits.spend_file(cfg), timeout=0.05):
                pass
        assert limits.reserve(cfg, 0.001) is None  # could not lock: refused
    finally:
        limits._spend_lock.release()


def test_reservation_stops_a_parallel_burst_at_the_ceiling(tmp_path):
    import threading
    cfg = _cfg(tmp_path, ceiling=0.01)
    est = 0.001
    got = []
    threads = [threading.Thread(target=lambda: got.append(limits.reserve(cfg, est))) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(1 for r in got if r) == 10  # exactly ceiling / estimate, never more
    assert limits.spent_this_month(cfg) <= 0.01 + 1e-9


def test_settle_replaces_reservation_with_actual_cost(tmp_path):
    cfg = _cfg(tmp_path, ceiling=5)
    r = limits.reserve(cfg, 1.0, now=NOW)
    assert limits.spent_this_month(cfg, now=NOW) == pytest.approx(1.0)
    limits.settle(cfg, r, [{"prompt_tokens": 1_000_000, "completion_tokens": 0}])
    assert limits.spent_this_month(cfg, now=NOW) == pytest.approx(0.5)


def test_settle_goes_to_the_reservation_month_across_rollover(tmp_path):
    cfg = _cfg(tmp_path, ceiling=5)
    r = limits.reserve(cfg, 1.0, now=NOW)
    limits.settle(cfg, r, [])  # settled "next month": the hold is released where it was made
    assert limits.spent_this_month(cfg, now=NOW) == pytest.approx(0.0)
    assert limits.spent_this_month(cfg, now=NOW + 40 * 86400) == 0.0


def test_spend_file_keeps_twelve_months(tmp_path):
    cfg = _cfg(tmp_path, ceiling=0)
    for m in range(20):
        limits.record_spend(cfg, [{"prompt_tokens": 1000, "completion_tokens": 0}], now=NOW + m * 31 * 86400)
    assert len(json.loads(limits.spend_file(cfg).read_text())) == 12


def test_ask_reserves_before_any_model_work(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path, ceiling=0.01)
    monkeypatch.setattr(limits, "estimate_usd", lambda cfg, q="": 0.02)  # one message would pass the ceiling
    out = chat.ask([], [], None, _Emb(), "p", [], [], [], cfg, "Where is my parcel?")
    assert out == limits.OVER_BUDGET
