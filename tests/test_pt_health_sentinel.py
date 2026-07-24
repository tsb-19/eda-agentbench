"""Tests for the b04/PT health sentinel (scripts/pt_health_sentinel.py).

Covers: a healthy PT stage1 (MET signoff on the golden config) reports healthy=True; a PT that
produces no/bad timing_report reports healthy=False with an error; the record carries a timestamp and
is structurally separate from task-fairness data. The PT subprocess is mocked so these are no-call."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pt_health_sentinel as sen  # noqa: E402


def _fake_run_factory(header_ok, rc=0, err=""):
    def fake_run(cmd, cwd=None, env=None, capture_output=True, text=True, timeout=None):
        # mimic run_evidence_stage1.sh: write timing_report.rpt with the given header
        (Path(cwd) / "timing_report.rpt").write_text(
            "# acc_stage evidence report\n"
            + (("# consumed_netlist=netlist_v2.v clock=clk_main scenario=slow corner=func signoff=OK paths=1 slack=0.130000\n")
               if header_ok else "# consumed_netlist=netlist_v1.v clock=clk_old scenario=func corner=typ signoff=FAIL\n")
            + "=== REPORT_TIMING BEGIN ===\nslack (MET) 0.13\n=== REPORT_TIMING END ===\n")
        class _R:
            returncode = rc
            stdout = ""
            stderr = err
        return _R()
    return fake_run


def _stage_task(tmp_path):
    task = tmp_path / "wf_0009"
    (task / "files").mkdir(parents=True)
    (task / "files" / "run_evidence_stage1.sh").write_text("#!/bin/bash\nexit 0\n")
    (task / "hidden").mkdir()
    (task / "solution").mkdir(parents=True)
    (task / "solution" / "flow_config.json").write_text(
        '{"netlist":"netlist_v2.v","scenario":"slow","corner":"func"}')
    return task


def test_healthy_pt_reports_healthy(tmp_path, monkeypatch):
    task = _stage_task(tmp_path)
    monkeypatch.setattr(sen.subprocess, "run", _fake_run_factory(header_ok=True))
    rec = sen.check_pt_health(task, {}, deadline=30)
    assert rec["healthy"] is True
    assert rec["signoff_ok"] is True
    assert rec["ts"] and rec["elapsed_s"] is not None
    assert rec["error"] is None


def test_bad_signoff_reports_unhealthy(tmp_path, monkeypatch):
    task = _stage_task(tmp_path)
    monkeypatch.setattr(sen.subprocess, "run", _fake_run_factory(header_ok=False))
    rec = sen.check_pt_health(task, {}, deadline=30)
    assert rec["healthy"] is False
    assert rec["signoff_ok"] is False


def test_missing_timing_report_reports_unhealthy(tmp_path, monkeypatch):
    task = _stage_task(tmp_path)
    def fake_run(cmd, cwd=None, env=None, capture_output=True, text=True, timeout=None):
        class _R:
            returncode = 1
            stdout = ""
            stderr = "pt_shell crashed"
        return _R()
    monkeypatch.setattr(sen.subprocess, "run", fake_run)
    rec = sen.check_pt_health(task, {}, deadline=30)
    assert rec["healthy"] is False
    assert rec["error"]


def test_timeout_reports_unhealthy(tmp_path, monkeypatch):
    task = _stage_task(tmp_path)
    def fake_run(cmd, cwd=None, env=None, capture_output=True, text=True, timeout=None):
        raise sen.subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)
    monkeypatch.setattr(sen.subprocess, "run", fake_run)
    rec = sen.check_pt_health(task, {}, deadline=5)
    assert rec["healthy"] is False
    assert "exceeded" in rec["error"]


def test_record_is_separate_from_fairness_data(tmp_path, monkeypatch):
    task = _stage_task(tmp_path)
    monkeypatch.setattr(sen.subprocess, "run", _fake_run_factory(header_ok=True))
    rec = sen.check_pt_health(task, {}, deadline=30)
    # the sentinel record contains NO candidate/task-fairness fields (no score, no candidate name)
    for forbidden in ("total_score", "candidate", "components", "passed"):
        assert forbidden not in rec
    assert set(rec) <= {"ts", "deadline_s", "task", "healthy", "signoff_ok", "elapsed_s", "error"}
