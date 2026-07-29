"""Tests for the block measurement-control protocol (scripts/measurement_control.py).

Covers: admissibility decided SOLELY by bookend health (score-independent); symmetry (a 1.0 inside an
out-of-control block is invalid just as 0.1/0.2 is); inadmissible blocks preserve all candidate
outcomes as diagnostic; admissible blocks make unexpected scores HARD fails (not retried)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import measurement_control as MC  # noqa: E402


def _res(score):
    return {"total_score": score, "error": None, "submitted": {}, "candidate": None, "attempt": 1,
            "components": []}


def _block(before_healthy, after_healthy, scores):
    cands = {}
    for cand, sc in scores.items():
        r = _res(sc)
        r["block_admissible"] = before_healthy and after_healthy
        r["measurement_valid"] = before_healthy and after_healthy
        cands[cand] = r
    return {"admissible": before_healthy and after_healthy, "candidates": cands,
            "before": {"healthy": before_healthy}, "after": {"healthy": after_healthy}}


def test_admissible_block_results_authoritative():
    b = _block(True, True, {"golden": 1.0, "wrong_axis": 0.2, "stale_decoy": 0.1, "unchanged_mutant": 0.1})
    assert b["admissible"] is True
    assert all(c["measurement_valid"] for c in b["candidates"].values())
    assert MC.block_hard_fail(b) == []  # all expected -> no hard fail


def test_admissible_block_unexpected_score_is_hard_fail():
    b = _block(True, True, {"golden": 0.2, "wrong_axis": 0.2, "stale_decoy": 0.1, "unchanged_mutant": 0.1})
    assert b["admissible"] is True
    hf = MC.block_hard_fail(b)
    assert len(hf) == 1 and hf[0]["candidate"] == "golden"  # hard fail, NOT retried


def test_before_check_fails_inadmissible_block():
    b = _block(False, True, {"golden": 0.2, "wrong_axis": 0.2, "stale_decoy": 0.1, "unchanged_mutant": 0.1})
    assert b["admissible"] is False
    assert MC.block_hard_fail(b) == []  # not authoritative -> no hard-fail verdict; rerun instead


def test_symmetry_1p0_in_out_of_control_block_is_invalid():
    b = _block(False, False, {"golden": 1.0, "wrong_axis": 0.2, "stale_decoy": 0.1, "unchanged_mutant": 0.1})
    assert b["admissible"] is False
    # a 1.0 (good) inside an out-of-control block is measurement-invalid, just like a 0.1 would be
    assert all(c["measurement_valid"] is False for c in b["candidates"].values())
    assert MC.block_hard_fail(b) == []  # never hard-fail an inadmissible block


def test_after_check_fails_inadmissible_block():
    b = _block(True, False, {"golden": 1.0, "wrong_axis": 0.2})
    assert b["admissible"] is False
    assert all(c["measurement_valid"] is False for c in b["candidates"].values())


def test_admissibility_uses_only_control_evidence_not_scores():
    # block_hard_fail on an inadmissible block must be [] even if all scores are wildly wrong
    b = _block(False, False, {"golden": 0.0, "wrong_axis": 1.0, "stale_decoy": 0.5, "unchanged_mutant": 0.9})
    assert MC.block_hard_fail(b) == []  # control evidence (bookends) decides, not scores
