"""Phase-4I: opt-in probe-artifact preservation (tool-free unit tests).

Tests `_preserve_final_workspace` directly (a pure function). No model, no EDA tool, no scoring change.
The preservation is OFF by default and only copies the agent's declared EDITABLE submitted files (never
hidden truth, netlists, library, decoys, .env, or model configs), so a confident-wrong episode's final
package can be byte-confirmed after the eval workspace is cleaned up.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from eda_agentbench.agentic.runner import _preserve_final_workspace, _PRESERVE_ENV


@pytest.fixture(autouse=True)
def _clean_env():
    prev = os.environ.pop(_PRESERVE_ENV, None)
    yield
    if prev is not None:
        os.environ[_PRESERVE_ENV] = prev
    else:
        os.environ.pop(_PRESERVE_ENV, None)


def _fake_eval_workspace() -> Path:
    ew = Path(tempfile.mkdtemp(prefix="p4i_ew_"))
    # declared editable submitted files
    (ew / "flow_config.json").write_text('{"netlist":"netlist_v2.v","scenario":"slow","corner":"func"}')
    (ew / "constraints.sdc").write_text("create_clock -name clk_main -period 3.0 [get_ports clk_main]\n")
    (ew / "timing_report.rpt").write_text("# report\n=== REPORT_TIMING BEGIN ===\nx\n=== REPORT_TIMING END ===\n")
    (ew / "evidence_manifest.json").write_text('{"selected_netlist":"netlist_v2.v"}')
    (ew / "stage2_summary.json").write_text('{"stage":"stage2"}')
    # hidden truth + forbidden + secrets that MUST NOT be copied (present in the eval workspace)
    (ew / "handoff_truth.json").write_text('{"_oracle":"HIDDEN_TRUTH"}')   # hidden truth
    (ew / "grade_workflow.py").write_text("def grade(): ...")              # hidden grader
    (ew / "netlist_v2.v").write_text("module v2;")                         # forbidden design
    (ew / "tiny.db").write_text("lib")                                     # forbidden library
    (ew / "report_A_typ_test.rpt").write_text("decoy")                     # forbidden decoy
    (ew / ".env").write_text("API_KEY=SECRET")                             # secret
    (ew / "model_config.json").write_text('{"key":"SECRET"}')              # secret-ish config
    return ew


def _meta():
    return {"task_id": "workflow_handoff_0005", "track": "p14_workflow_handoff",
            "files": {"editable": ["flow_config.json", "constraints.sdc", "timing_report.rpt",
                                   "evidence_manifest.json", "stage2_summary.json"]}}


def _score(total=1.0, passed=True):
    return SimpleNamespace(total_score=total, passed=passed,
                           anti_cheat={"forbidden_files_modified": False, "hash_mismatches": []})


def test_1_disabled_by_default():
    rd = Path(tempfile.mkdtemp(prefix="p4i_rd_"))
    ew = _fake_eval_workspace()
    try:
        ret = _preserve_final_workspace(rd, ew, _meta(), _score(), "EVIDENCE_OK\n")
        assert ret is None
        assert not (rd / "preserved").exists()
        assert not (rd / "preserved_artifacts.json").exists()
    finally:
        shutil.rmtree(rd, ignore_errors=True); shutil.rmtree(ew, ignore_errors=True)


def test_2_enabled_creates_artifact_dir():
    os.environ[_PRESERVE_ENV] = "1"
    rd = Path(tempfile.mkdtemp(prefix="p4i_rd_"))
    ew = _fake_eval_workspace()
    try:
        ret = _preserve_final_workspace(rd, ew, _meta(), _score(), "EVIDENCE_OK\nSIGNOFF_OK\n")
        assert ret is not None and ret.exists()
        assert (rd / "preserved_artifacts.json").exists()
    finally:
        shutil.rmtree(rd, ignore_errors=True); shutil.rmtree(ew, ignore_errors=True)


def test_3_editable_files_preserved():
    os.environ[_PRESERVE_ENV] = "1"
    rd = Path(tempfile.mkdtemp(prefix="p4i_rd_"))
    ew = _fake_eval_workspace()
    try:
        _preserve_final_workspace(rd, ew, _meta(), _score(), "EVIDENCE_OK\n")
        names = {p.name for p in (rd / "preserved").iterdir()}
        for ef in ("flow_config.json", "constraints.sdc", "timing_report.rpt",
                   "evidence_manifest.json", "stage2_summary.json"):
            assert ef in names, ef
    finally:
        shutil.rmtree(rd, ignore_errors=True); shutil.rmtree(ew, ignore_errors=True)


def test_4_hidden_truth_not_copied():
    os.environ[_PRESERVE_ENV] = "1"
    rd = Path(tempfile.mkdtemp(prefix="p4i_rd_"))
    ew = _fake_eval_workspace()
    try:
        _preserve_final_workspace(rd, ew, _meta(), _score(), "EVIDENCE_OK\n")
        # file-level: forbidden + hidden files are NOT copied into preserved/
        for bad in ("handoff_truth.json", "grade_workflow.py", "netlist_v2.v", "tiny.db",
                    "report_A_typ_test.rpt"):
            assert not (rd / "preserved" / bad).exists(), bad
        # content-level: the hidden-truth string must NEVER appear in any preserved file
        for p in (rd / "preserved").iterdir():
            assert "HIDDEN_TRUTH" not in p.read_text(errors="ignore"), p.name
    finally:
        shutil.rmtree(rd, ignore_errors=True); shutil.rmtree(ew, ignore_errors=True)


def test_5_env_and_model_config_not_copied():
    os.environ[_PRESERVE_ENV] = "1"
    rd = Path(tempfile.mkdtemp(prefix="p4i_rd_"))
    ew = _fake_eval_workspace()
    try:
        _preserve_final_workspace(rd, ew, _meta(), _score(), "EVIDENCE_OK\n")
        assert not (rd / "preserved" / ".env").exists()
        assert not (rd / "preserved" / "model_config.json").exists()
        for p in (rd / "preserved").iterdir():
            t = p.read_text(errors="ignore")
            assert "API_KEY" not in t and "SECRET" not in t, p.name
        man = json.loads((rd / "preserved_artifacts.json").read_text())
        blob = json.dumps(man)
        assert "API_KEY" not in blob and "SECRET" not in blob
        assert man["secrets_excluded"] is True
    finally:
        shutil.rmtree(rd, ignore_errors=True); shutil.rmtree(ew, ignore_errors=True)


def test_6_score_unchanged_on_vs_off():
    rd = Path(tempfile.mkdtemp(prefix="p4i_rd_"))
    ew = _fake_eval_workspace()
    try:
        sc = _score(total=0.2, passed=False)
        before = (sc.total_score, sc.passed, dict(sc.anti_cheat))
        _preserve_final_workspace(rd, ew, _meta(), sc, "EVIDENCE_OK\n")  # OFF -> no-op
        assert (sc.total_score, sc.passed, dict(sc.anti_cheat)) == before
        os.environ[_PRESERVE_ENV] = "1"
        ret = _preserve_final_workspace(rd, ew, _meta(), sc, "EVIDENCE_OK\n")
        assert (sc.total_score, sc.passed, dict(sc.anti_cheat)) == before  # score object untouched
        man = json.loads((rd / "preserved_artifacts.json").read_text())
        assert man["total_score"] == 0.2 and man["passed"] is False  # recorded, not changed
    finally:
        shutil.rmtree(rd, ignore_errors=True); shutil.rmtree(ew, ignore_errors=True)


def test_7_failed_timeout_run_preserves_state():
    os.environ[_PRESERVE_ENV] = "1"
    rd = Path(tempfile.mkdtemp(prefix="p4i_rd_"))
    ew = _fake_eval_workspace()
    try:
        # score_result=None (run errored / timed out before grading); eval workspace still present
        ret = _preserve_final_workspace(rd, ew, _meta(), None, "")
        assert ret is not None and ret.exists()
        man = json.loads((rd / "preserved_artifacts.json").read_text())
        assert man["total_score"] is None and man["passed"] is None
        assert man["preserved_editable_files"]  # editable files still preserved
        # eval_workspace=None -> safe no-op
        assert _preserve_final_workspace(rd, None, _meta(), None, "") is None
    finally:
        shutil.rmtree(rd, ignore_errors=True); shutil.rmtree(ew, ignore_errors=True)


def test_8_manifest_valid_json_and_hashes():
    os.environ[_PRESERVE_ENV] = "1"
    rd = Path(tempfile.mkdtemp(prefix="p4i_rd_"))
    ew = _fake_eval_workspace()
    try:
        import hashlib
        _preserve_final_workspace(rd, ew, _meta(), _score(), "SIGNOFF_OK\nEVIDENCE_OK\nGLOBAL_AUTHORITY_OK\nGLOBAL_AUTHORITY_SCORE: 1.000\n")
        man = json.loads((rd / "preserved_artifacts.json").read_text())  # valid JSON (no raise)
        assert man["task_id"] == "workflow_handoff_0005"
        # presence-only markers (note: _SCORE fractions live in score.json, not parsed here)
        assert man["grader_markers"].get("EVIDENCE_OK") is True
        assert man["grader_markers"].get("SIGNOFF_OK") is True
        assert man["grader_markers"].get("GLOBAL_AUTHORITY_OK") is True
        # submitted_file_hashes match the preserved file contents
        fc_hash = hashlib.sha256((ew / "flow_config.json").read_bytes()).hexdigest()
        assert man["submitted_file_hashes"]["flow_config.json"] == fc_hash
        assert set(man["submitted_file_hashes"]) == set(_meta()["files"]["editable"])
    finally:
        shutil.rmtree(rd, ignore_errors=True); shutil.rmtree(ew, ignore_errors=True)
