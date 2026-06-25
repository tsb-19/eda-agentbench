"""Tool-free test for the agentic reliability-block join in scripts/run_agentic_baseline.py.

Mirrors the single-shot join (run_model_baseline._reliability_block) but consumes the agentic
driver's sidecar log + the runner-side outcome (anti-cheat, timeout)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import eda_agentbench.reliability as R

_spec = importlib.util.spec_from_file_location(
    "run_agentic_baseline",
    Path(__file__).resolve().parents[1] / "scripts" / "run_agentic_baseline.py")
RAB = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RAB)


def _log(tmp_path: Path, **fields) -> Path:
    p = tmp_path / "ep.agentlog.json"
    base = {"actions": [], "finished": False, "edited": [], "error": None,
            "confidence": "", "confidence_format_ok": None}
    base.update(fields)
    p.write_text(json.dumps(base))
    return p


def test_block_confident_correct(tmp_path):
    lp = _log(tmp_path, finished=True, edited=["design.v"], confidence="high",
              confidence_format_ok=True,
              actions=[{"type": "run"}, {"type": "write"}, {"type": "finish"}])
    b = RAB._agentic_reliability_block(lp, passed=True, clean=True, timed_out=False)
    assert b["protocol_status"] == "ok"
    assert b["confidence_decision"] == "high" and b["confidence_format_ok"] is True
    assert b["overconfident_wrong"] is False and b["abstained"] is False


def test_block_overconfident_wrong(tmp_path):
    lp = _log(tmp_path, finished=True, edited=["design.v"], confidence="high",
              actions=[{"type": "write"}, {"type": "finish"}])
    b = RAB._agentic_reliability_block(lp, passed=False, clean=True, timed_out=False)
    assert b["protocol_status"] == "ok" and b["overconfident_wrong"] is True


def test_block_nocommit_when_no_edits_and_not_finished(tmp_path):
    lp = _log(tmp_path, finished=False, edited=[],
              actions=[{"type": "run"}, {"type": "run"}])
    b = RAB._agentic_reliability_block(lp, passed=False, clean=True, timed_out=False)
    assert b["protocol_status"] == R.NOCOMMIT


def test_block_budget_exhausted_partial_work(tmp_path):
    lp = _log(tmp_path, finished=False, edited=["design.v"],
              actions=[{"type": "write"}, {"type": "run"}])
    b = RAB._agentic_reliability_block(lp, passed=False, clean=True, timed_out=False)
    assert b["protocol_status"] == R.BUDGET_EXHAUSTED


def test_block_anticheat_overrides(tmp_path):
    lp = _log(tmp_path, finished=True, edited=["design.v"], confidence="high",
              actions=[{"type": "write"}, {"type": "finish"}])
    b = RAB._agentic_reliability_block(lp, passed=False, clean=False, timed_out=False)
    # anti-cheat dirty -> protocol DQ; the confident-wrong calibration is NOT charged (proto != ok)
    assert b["protocol_status"] == R.ANTI_CHEAT and b["overconfident_wrong"] is False


def test_block_infra_error_path(tmp_path):
    # exception path: no usable log, run_error carries the failure
    b = RAB._agentic_reliability_block(tmp_path / "missing.json", passed=None, clean=True,
                                       timed_out=False, run_error="HTTP 429 from gateway")
    assert b["protocol_status"] == R.HTTP_429


def test_block_missing_log_is_nocommit(tmp_path):
    # no sidecar at all + no error -> nothing was committed
    b = RAB._agentic_reliability_block(tmp_path / "missing.json", passed=None, clean=True,
                                       timed_out=False)
    assert b["protocol_status"] == R.NOCOMMIT
