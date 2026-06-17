"""Tool-free unit tests for scripts/scan_discrimination.py (pure stats + classify)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import scripts.scan_discrimination as sd  # noqa: E402


def test_saturated_all_perfect():
    s = sd.task_stats([1.0, 1.0, 1.0, 1.0, 1.0])
    assert s["saturated"] and not s["discriminating"] and s["spread"] == 0.0
    assert sd.classify(s) == "saturated"
    assert s["emp_difficulty"] == 0.0


def test_discriminating_one_model_bombs():
    # 4 perfect, 1 zero -> spread 1.0, mean 0.8 (the common pattern in the baseline)
    s = sd.task_stats([1.0, 1.0, 1.0, 1.0, 0.0])
    assert s["discriminating"] and not s["saturated"]
    assert abs(s["mean"] - 0.8) < 1e-9 and s["spread"] == 1.0
    assert sd.classify(s) == "discriminating"


def test_dead_all_fail():
    s = sd.task_stats([0.2, 0.3, 0.1, 0.0, 0.4])
    assert s["dead"] and not s["saturated"]
    assert sd.classify(s) == "dead"


def test_weak_clustered_below_one():
    # everyone ~0.74, low spread -> hard-for-all but not separating models
    s = sd.task_stats([0.74, 0.72, 0.76, 0.74, 0.75], spread_thresh=0.1)
    assert not s["saturated"] and not s["dead"] and not s["discriminating"]
    assert sd.classify(s) == "weak"


def test_spread_threshold_controls_discriminating():
    scores = [1.0, 1.0, 1.0, 0.95, 1.0]  # spread 0.05
    assert not sd.task_stats(scores, spread_thresh=0.1)["discriminating"]
    assert sd.task_stats(scores, spread_thresh=0.04)["discriminating"]


def test_build_rows_joins_track_and_difficulty():
    scores = {"t1": {"m1": 1.0, "m2": 1.0}, "t2": {"m1": 1.0, "m2": 0.0}}
    rows = sd.build_rows(scores, {"t1": "p1", "t2": "p1"}, {"t1": "easy", "t2": "hard"}, 0.1)
    by = {r["task_id"]: r for r in rows}
    assert by["t1"]["saturated"] and by["t1"]["difficulty"] == "easy"
    assert by["t2"]["discriminating"] and by["t2"]["track"] == "p1"
