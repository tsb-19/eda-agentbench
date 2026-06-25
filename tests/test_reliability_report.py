"""Tool-free test for scripts/reliability_report.py aggregation."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import eda_agentbench.reliability as R

_spec = importlib.util.spec_from_file_location(
    "reliability_report", Path(__file__).resolve().parents[1] / "scripts" / "reliability_report.py")
RR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RR)


def _w(tree: Path, task: str, passed: bool, conf: str = "high", proto: str = "ok"):
    p = tree / "M" / "p3_timing_report_qa"
    p.mkdir(parents=True, exist_ok=True)
    (p / f"{task}.json").write_text(json.dumps({
        "ok": True, "passed": passed,
        "reliability": {"confidence_decision": conf, "protocol_status": proto,
                        "confidence_format_ok": True}}))


def test_report_aggregates_flip_and_overconfidence(tmp_path):
    a, b = tmp_path / "A", tmp_path / "B"
    _w(a, "t1", True);  _w(b, "t1", False)      # flip -> pass^k drops, B is fail@HIGH (overconfident)
    _w(a, "t2", True);  _w(b, "t2", True)       # consistent pass
    rows = {m: R.per_model(ts) for m, ts in RR.load_trees([a, b], None).items()}
    r = rows["M"]
    assert r["n_tasks"] == 2
    assert abs(r["passk_all"] - 0.5) < 1e-9     # t1 inconsistent (0), t2 consistent (1)
    assert abs(r["passk_any"] - 1.0) < 1e-9
    assert r["flip_rate"] == 0.5
    assert r["n_overconf_wrong"] == 1           # the failing HIGH-confidence trial
    assert r["format_compliance"] == 1.0


def test_report_protocol_failure_tracked(tmp_path):
    a = tmp_path / "A"
    _w(a, "t1", True)
    _w(a, "t2", False, conf="", proto=R.HTTP_429)   # infra: excluded from capability
    rows = {m: R.per_model(ts) for m, ts in RR.load_trees([a], None).items()}
    r = rows["M"]
    assert r["n_tasks"] == 1                     # the 429 task contributes no capability stat
    assert r["protocol"].get(R.HTTP_429) == 1
    assert r["pass1"] == 1.0                     # only the valid task counts


def test_render_md_smoke(tmp_path):
    a = tmp_path / "A"
    _w(a, "t1", True)
    rows = {m: R.per_model(ts) for m, ts in RR.load_trees([a], None).items()}
    md = RR.render_md(rows, 1)
    assert "Reliability / Calibration leaderboard" in md and "trust" in md


def test_load_trees_skips_agentlog_sidecars(tmp_path):
    # An agentic results tree carries `<task>.agentlog.json` next to `<task>.json`; the
    # report must grade only the real result, not the driver sidecar.
    a = tmp_path / "A"
    _w(a, "t1", True)
    (a / "M" / "p3_timing_report_qa" / "t1.agentlog.json").write_text(
        json.dumps({"model": "M", "actions": [], "finished": True}))
    by_model = RR.load_trees([a], None)
    assert len(by_model["M"]) == 1                # the sidecar contributed no trial


def test_cost_block_threaded_and_rendered(tmp_path):
    # an agentic result carries a `cost` block; the report aggregates + renders it.
    a = tmp_path / "A"
    p = a / "M" / "p7_primetime_sta_debug"
    p.mkdir(parents=True)
    (p / "t1.json").write_text(json.dumps({
        "ok": True, "passed": True,
        "reliability": {"confidence_decision": "high", "protocol_status": "ok",
                        "confidence_format_ok": True},
        "cost": {"tokens_in": 28000, "tokens_out": 4000, "tool_calls": 6,
                 "retries": 2, "wall_time_sec": 150.0}}))
    trials = RR.load_trees([a], None)["M"]
    assert trials[0]["tokens"] == 32000 and trials[0]["tool_calls"] == 6
    assert trials[0]["retries"] == 2 and trials[0]["latency"] == 150.0
    md = RR.render_md({m: R.per_model(ts) for m, ts in {"M": trials}.items()}, 1)
    assert "tok" in md and "tools" in md and "retry" in md and "32.0k" in md
