"""The quality-check pass mark (eval/run_eval.py) — pure logic, no model load."""
import json

import pytest

from eval.run_eval import check, load_thresholds

BAR = {"min_hits_at5": 47, "max_wrong_idk": 0, "min_right_idk": 2}


def metrics(**over):
    m = {"answerable": 50, "unanswerable": 10, "dense_hits": 47, "wrong_idk": 0, "right_idk": 2}
    m.update(over)
    return m


def test_today_passes():
    assert check(metrics(), BAR) == []


def test_better_than_today_passes():
    assert check(metrics(dense_hits=50, right_idk=9), BAR) == []


def test_fewer_documents_found_fails():
    fails = check(metrics(dense_hits=46), BAR)
    assert len(fails) == 1 and "46/50" in fails[0]


def test_giving_up_on_answerable_questions_fails():
    fails = check(metrics(wrong_idk=1), BAR)
    assert len(fails) == 1 and "I don't know" in fails[0]


def test_guessing_on_unanswerable_questions_fails():
    fails = check(metrics(right_idk=1), BAR)
    assert len(fails) == 1 and "1/10" in fails[0]


def test_every_failure_is_reported():
    assert len(check(metrics(dense_hits=10, wrong_idk=5, right_idk=0), BAR)) == 3


def test_committed_bar_is_never_below_baseline():
    t = load_thresholds()
    assert t["min_hits_at5"] >= 47
    assert t["max_wrong_idk"] <= 0
    assert t["min_right_idk"] >= 5


@pytest.mark.parametrize("bad", [{"min_hits_at5": -1}, {"max_wrong_idk": "0"}, {"min_right_idk": None}, {}])
def test_malformed_bar_is_refused(tmp_path, bad):
    t = dict(BAR)
    t.update(bad)
    if not bad:
        t.pop("min_hits_at5")
    p = tmp_path / "thresholds.json"
    p.write_text(json.dumps(t))
    with pytest.raises(ValueError):
        load_thresholds(p)
