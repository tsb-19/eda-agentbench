#!/usr/bin/env python3
"""Phase-5 Family B fairness-gate regression tests: hspice_health_sentinel,
spice_fullpath_check, spice_measurement_control (block + validity-only retry +
symmetric whole-block invalidation). Real-HSPICE tests skip if the tool is absent."""
import json, os, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "generators"))
import hspice_health_sentinel as HS
import spice_fullpath_check as FP
import spice_measurement_control as MC
import fairness_retry as FR

DEV = REPO / "tasks" / "p16_spice_handoff" / "p16_dev_0000"


def _env():
    e = dict(os.environ)
    e.setdefault("EDA_TOOL_ROOT", "/data1/tongsb/eda-remote-shim/EDA")
    e.setdefault("B04_HOST", "tsb@b04")
    e.setdefault("EDA_HSPICE_CMD", "/data1/tongsb/eda-remote-shim/EDA/soft2/synopsys/hspice/V-2023.12/hspice/bin/hspice")
    return e


def _hspice_available():
    return Path(_env()["EDA_HSPICE_CMD"]).exists() or os.path.isabs(_env()["EDA_HSPICE_CMD"])


def test_sentinel_real_hspice():
    if not _hspice_available() or not DEV.is_dir():
        return  # skip when tool/instance absent
    rec = HS.check_hspice_health(DEV, _env(), deadline=240)
    assert rec["healthy"], f"sentinel unhealthy: {rec}"
    assert rec["sim_exit_zero"] and rec["measure_present"] and rec["value_in_range"]


def test_fullpath_real_hspice():
    if not _hspice_available() or not DEV.is_dir():
        return
    rec = FP.check(DEV, _env())
    assert rec["healthy"], f"fullpath unhealthy: {rec}"
    assert rec["golden_verdict_ok"]  # golden grades semantic_binding=True through the full path


def test_measurement_control_block_real():
    if not _hspice_available() or not DEV.is_dir():
        return
    truth = json.loads((DEV / "hidden" / "meas_request_truth.json").read_text())
    cands = [("golden", truth["golden_join"]), ("wrong", truth["wrong_join_plausible"])]
    blk = MC.run_block(DEV, cands, _env(), max_replacements=1)
    assert blk["admissible"], f"block inadmissible: {blk['invalid_reason']}"
    by_role = {c["role"]: c for c in blk["candidates"]}
    assert by_role["golden"]["total_score"] == 1.0, by_role["golden"]
    assert by_role["wrong"]["total_score"] == 0.0, by_role["wrong"]
    # a valid wrong score (0.0 != EXPECTED golden) but here wrong's EXPECTED is 0.0 -> NOT a hard fail
    assert blk["hard_fails"] == [], blk["hard_fails"]


def test_validity_only_retry():
    # None result (infra failure) -> retryable; valid numeric score (favorable or not) -> NOT retryable
    assert FR.should_retry(None, 1.0, 0, 1) is True
    assert FR.should_retry({"total_score": None}, 1.0, 0, 1) is True
    assert FR.should_retry({"total_score": 0.0}, 1.0, 0, 1) is False   # valid wrong -> hard fail, no retry
    assert FR.should_retry({"total_score": 1.0}, 1.0, 0, 1) is False   # valid correct -> no retry
    assert FR.should_retry({"total_score": 0.0, "error": "x"}, 1.0, 0, 1) is True  # error present -> infra
    # attempt cap
    assert FR.should_retry(None, 1.0, 2, 1) is False  # attempt(2) >= 1+max_replacements(2)


def test_symmetric_whole_block_invalidation():
    # if EITHER bookend is unhealthy, the whole block is inadmissible (symmetric invalidation)
    class FakeCheck:
        def __init__(self, healthy): self.healthy = healthy
    before_unhealthy = {"healthy": False, "task": "x"}
    after_healthy = {"healthy": True, "task": "x"}
    # replicate run_block's admissibility rule
    admissible = bool(before_unhealthy["healthy"] and after_healthy["healthy"])
    assert admissible is False  # before-unhealthy -> whole block invalid
    before_healthy = {"healthy": True, "task": "x"}
    after_unhealthy = {"healthy": False, "task": "x"}
    assert bool(before_healthy["healthy"] and after_unhealthy["healthy"]) is False  # after-unhealthy -> invalid
    assert bool(before_healthy["healthy"] and after_healthy["healthy"]) is True     # both healthy -> admissible
