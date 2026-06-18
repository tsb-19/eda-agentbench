"""Tool-free unit tests for scripts/scan_discrimination.py (pure stats + classify)."""
import json
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


# --------------------------------------------------------------------------- #
# primary_score: continuous-track de-blinding (the P4-damping reporting fix)
# --------------------------------------------------------------------------- #
def _result(total, comps=None, **extra):
    d = {"total_score": total, "passed": total >= 0.6}
    if comps is not None:
        d["components"] = [{"name": n, "raw": r, "weight": w} for n, r, w in comps]
    d.update(extra)
    return d


def test_primary_score_continuous_uses_isolated_component():
    # P4-damping do-nothing floor: total 0.60 (looks "passing"), spec_score 0.333.
    floor = _result(0.60, [("tool_run", 1.0, 0.2), ("output_generated", 1.0, 0.1),
                           ("spec_score", 0.3333, 0.6), ("explanation", 1.0, 0.1)])
    assert abs(sd.primary_score(floor) - 0.3333) < 1e-9   # NOT 0.60


def test_primary_score_binary_track_falls_back_to_total():
    binr = _result(0.85, [("compile", 1.0, 0.2), ("hidden_test", 0.8, 0.4)])
    assert sd.primary_score(binr) == 0.85                 # no continuous component


def test_primary_score_dirty_episode_zero():
    # anti-cheat-zeroed: no components serialized, total 0.0 -> 0.0
    assert sd.primary_score({"total_score": 0.0, "components": []}) == 0.0
    assert sd.primary_score({"total_score": 0.0}) == 0.0


def test_primary_score_none_raw_and_clamp():
    assert sd.primary_score(_result(0.5, [("spec_score", None, 0.6)])) == 0.0
    assert sd.primary_score(_result(1.0, [("spec_score", 1.5, 0.6)])) == 1.0


def test_load_results_picks_continuous_component(tmp_path):
    # Build a tiny results tree: one continuous task (P4) + one binary task.
    def write(model, track, tid, payload):
        p = tmp_path / model / track
        p.mkdir(parents=True, exist_ok=True)
        (p / f"{tid}.json").write_text(json.dumps(
            {**payload, "model": model, "track": track, "task_id": tid}))

    write("A", "p4_spice_sim", "task_009000",
          _result(1.00, [("spec_score", 1.00, 0.6)]))
    write("B", "p4_spice_sim", "task_009000",
          _result(0.60, [("spec_score", 0.333, 0.6)]))
    write("A", "p1_rtl_debug", "task_1", _result(1.00))   # binary, no components
    write("B", "p1_rtl_debug", "task_1", _result(0.00))
    # sidecar agentlog (no total_score) must NOT clobber the real score with 0.0
    (tmp_path / "A" / "p4_spice_sim" / "task_009000.agentlog.json").write_text(
        json.dumps({"model": "A", "track": "p4_spice_sim", "task_id": "task_009000",
                    "actions": [], "usage": {}}))

    scores, track_of, cont = sd.load_results(tmp_path)
    # continuous task uses spec_score (0.333), not total_score (0.60)
    assert abs(scores["task_009000"]["B"] - 0.333) < 1e-9
    assert scores["task_009000"]["A"] == 1.00
    assert cont == {"p4_spice_sim"}                        # only P4 flagged continuous
    # the P4 task is now correctly discriminating (spread .667), not "weak ~0.6"
    s = sd.task_stats(list(scores["task_009000"].values()))
    assert s["discriminating"] and not s["saturated"] and abs(s["spread"] - 0.667) < 1e-3

