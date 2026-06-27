"""p13 trajectory / evidence-generation handoff (traj_handoff_0001) contract tests (tool-free).

Proves the task is fair, dispatch-parity-correct, leak-free, and -- the defining properties -- that
the pass gate requires the full repair-AND-rerun trajectory, that hand-edited / stale / wrong-package
/ missing evidence all fail, and that final-state-only repair without a rerun fails. The PrimeTime
re-run is exercised on b04 (separate real-tool gate); here SIGNOFF + the evidence/coverage markers
are synthesized to drive the evaluator, and the stdlib grader (grade_trajectory.py) is run directly
on crafted submitted-vs-reference evidence to verify the EVIDENCE master-gate logic without PT.

The forgery matrix (hand-edited report, hand-edited manifest, stale reuse, wrong-package, missing
evidence, fix-without-rerun) is the central validation: if hand-crafted evidence that merely matches
the documented format + hash formula could pass, this task is a NO-GO.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from eda_agentbench.agentic.runner import _select_evaluator
from eda_agentbench.agentic.workspace import (
    create_agent_workspace,
    detect_forbidden_modifications,
)
from eda_agentbench.evaluator.trajectory_handoff import TrajectoryHandoffEvaluator
from eda_agentbench.schema import validate_metadata
from eda_agentbench.task.loader import structural_validate

REPO = Path(__file__).resolve().parent.parent
TASK = REPO / "tasks" / "p13_trajectory_handoff" / "traj_handoff_0001"


def _meta() -> dict:
    return json.loads((TASK / "metadata.json").read_text())


def _score(log: str) -> tuple[float, bool, dict]:
    meta = _meta()
    ev = _select_evaluator(meta, TASK)
    comps = [ev.evaluate_component(c, TASK, log, mode="submission") for c in meta["scoring"]["weights"]]
    total = sum(c.weighted_score for c in comps)
    return round(total, 4), total >= 0.5, {c.name: c.raw_score for c in comps}


def _log(sg, ev_ok, fin, scn, prov, masking=False):
    """Synthesize a hidden-grader marker log for a trajectory state."""
    L = ["SIGNOFF_OK worst_slack=0.13" if sg else "SIGNOFF_FAIL no_paths"]
    if masking:
        L.append("HANDOFF_MASKING_DETECTED: sdc_exception:set_false_path")
    if ev_ok and not masking:
        L.append("EVIDENCE_OK")
    L.append("EVIDENCE_SCORE: %.3f" % (1.0 if ev_ok else 0.0))
    for pref, v in (("FINAL_ARTIFACT_CONSISTENCY", fin), ("SCENARIO_CLOCK", scn),
                    ("PROVENANCE", prov)):
        if v and not masking:
            L.append(pref + "_OK")
        L.append(pref + "_SCORE: %.3f" % (1.0 if v else 0.0))
    return "\n".join(L)


# --- 1. dispatch parity (Phase-0D lesson) -----------------------------------

def test_agentic_dispatch_selects_trajectory():
    assert isinstance(_select_evaluator(_meta(), TASK), TrajectoryHandoffEvaluator)


def test_dispatch_parity_both_sites():
    meta = _meta()
    assert meta["scoring"]["evaluator"] == "trajectory_handoff.TrajectoryHandoffEvaluator"
    ev = _select_evaluator(meta, TASK)
    got = f"{type(ev).__module__.split('.')[-1]}.{type(ev).__name__}"
    assert got == meta["scoring"]["evaluator"]
    cli = (REPO / "eda_agentbench" / "cli.py").read_text()
    runner = (REPO / "eda_agentbench" / "agentic" / "runner.py").read_text()
    assert 'evaluator_spec == "trajectory_handoff.TrajectoryHandoffEvaluator"' in cli
    assert 'evaluator_spec == "trajectory_handoff.TrajectoryHandoffEvaluator"' in runner


# --- 2. schema / structural -------------------------------------------------

def test_schema_and_structural_valid():
    meta = _meta()
    assert validate_metadata(meta) == []
    assert structural_validate(TASK) == []
    assert meta["track"] == "p13_trajectory_handoff"
    assert meta["task_id"] == "traj_handoff_0001"
    assert set(meta["files"]["editable"]) == {
        "flow_config.json", "constraints.sdc", "timing_report.rpt", "evidence_manifest.json"}
    assert abs(sum(meta["scoring"]["weights"].values()) - 1.0) < 1e-9


# --- 3. evaluator gate math (the trajectory pass gate) ----------------------

def test_golden_full_trajectory_scores_1():
    total, passed, comps = _score(_log(1, 1, 1, 1, 1))
    assert passed and abs(total - 1.0) < 1e-9, comps


def test_fix_inputs_without_rerun_fails():
    # final files correct, but no fresh evidence => EVIDENCE not OK => gated axes 0
    total, passed, comps = _score(_log(1, 0, 1, 1, 1))
    assert not passed and total <= 0.30, comps
    assert comps["evidence_generation"] == 0.0


def test_wrong_package_evidence_fails():
    # fresh evidence but for the wrong package => EVIDENCE_OK not emitted (authority clause)
    total, passed, comps = _score(_log(1, 0, 0, 0, 0))
    assert not passed and total <= 0.30, comps


def test_partial_repair_signoff_fail_below_pass():
    total, passed, comps = _score(_log(0, 0, 0, 0, 0))
    assert not passed and total <= 0.10, comps


def test_masking_zeroes_consistency():
    total, passed, comps = _score(_log(1, 1, 1, 1, 1, masking=True))
    assert not passed, comps
    assert comps["evidence_generation"] == 0.0


def test_evidence_is_hard_precondition():
    # even with final/scenario/provenance "ok", no EVIDENCE_OK keeps them gated to 0
    total, passed, comps = _score(_log(1, 0, 1, 1, 1))
    assert comps["final_artifact_consistency"] == 0.0
    assert comps["scenario_clock_consistency"] == 0.0
    assert comps["provenance_consistency"] == 0.0


def test_golden_mutant_margin():
    g, _, _ = _score(_log(1, 1, 1, 1, 1))
    m, _, _ = _score(_log(1, 0, 0, 0, 0))   # mutant-like: signoff green on stale island, no fresh ev
    assert (g - m) >= 0.15


# --- 4. stdlib grader: the forgery matrix (no PT; crafted submitted vs reference) ---

def _run_grader(setup) -> str:
    """Run the real grade_trajectory.py in a temp dir populated by setup(dir).

    setup writes: flow_config.json, constraints.sdc, handoff_manifest.json, applied_hidden.sdc,
    coverage.txt, evidence_manifest.json, timing_report.rpt, ref_evidence_manifest.json,
    ref_timing_report.rpt, and the netlists. Returns the grader's marker block.
    """
    d = Path(tempfile.mkdtemp(prefix="p13g_"))
    try:
        for f in ("netlist_v1.v", "netlist_v2.v", "handoff_manifest.json"):
            shutil.copy2(TASK / "files" / f, d / f)
        shutil.copy2(TASK / "hidden" / "handoff_truth.json", d / "handoff_truth.json")
        shutil.copy2(TASK / "hidden" / "grade_trajectory.py", d / "grade_trajectory.py")
        setup(d)
        p = subprocess.run(["python3", "grade_trajectory.py", "handoff_truth.json"],
                           cwd=d, capture_output=True, text=True, timeout=60)
        return p.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


# a reference report body + manifest representing a correct v2/clk_main re-run
_REF_BODY = ("=== REPORT_TIMING BEGIN ===\nStartpoint: din\nEndpoint: cap_reg\n"
             "i_b0/Y (BUFX1) 0.10 1.50 r\nslack (MET) 0.13\n=== REPORT_TIMING END ===\n")


def _digest_of(body_inner: str) -> str:
    import re
    m = re.search(r"=== REPORT_TIMING BEGIN ===\n(.*?)\n=== REPORT_TIMING END ===", body_inner, re.DOTALL)
    inner = m.group(1) if m else ""
    out = []
    for line in inner.splitlines():
        s = re.sub(r"\s+", " ", line).strip()
        if s:
            out.append(s)
    return hashlib.sha256(("\n".join(out) + "\n").encode()).hexdigest()


def _good_manifest(d, consumed="netlist_v2.v", clk="clk_main", report_path="timing_report.rpt",
                   nonce=None, digest=None):
    rd = digest if digest is not None else _digest_of((d / report_path).read_text())
    ih = {"flow_config.json": "fc", "constraints.sdc": "sd", "consumed_netlist": "nl"}
    nn = nonce if nonce is not None else hashlib.sha256(
        ("fc" + "sd" + "nl" + clk + "func" + "typ" + rd).encode()).hexdigest()[:16]
    return {
        "input_hashes": ih, "selected_netlist": consumed, "selected_sdc": "constraints.sdc",
        "selected_clock": clk, "scenario": "func", "corner": "typ", "tool": "pt_shell",
        "tool_exit": 0, "signoff": "OK", "constrained_paths": 1,
        "report_digest": rd, "run_nonce": nn,
    }


def _common(d, consumed="netlist_v2.v", clk="clk_main"):
    (d / "flow_config.json").write_text(json.dumps(
        {"netlist": consumed, "top_module": "acc_stage", "constraints": "constraints.sdc",
         "library": "tiny.db", "scenario": "func", "corner": "typ"}))
    (d / "constraints.sdc").write_text(
        f"create_clock -name {clk} -period 3.0 [get_ports {clk}]\n")
    (d / "applied_hidden.sdc").write_text(
        f"create_clock -name {clk} -period 3.0 [get_ports {clk}]\n")
    (d / "coverage.txt").write_text(
        "intended_clock_present %d\nconstrained_paths %d\n"
        % (1 if clk == "clk_main" else 0, 1))
    # reference (hidden re-run) evidence for a CORRECT v2 run
    (d / "ref_timing_report.rpt").write_text(_REF_BODY)
    (d / "ref_evidence_manifest.json").write_text(json.dumps(
        _good_manifest_for(_REF_BODY)))


def _good_manifest_for(body):
    rd = _digest_of(body)
    ih = {"flow_config.json": "fc", "constraints.sdc": "sd", "consumed_netlist": "nl"}
    nn = hashlib.sha256(("fc" + "sd" + "nl" + "clk_main" + "func" + "typ" + rd).encode()).hexdigest()[:16]
    return {"input_hashes": ih, "selected_netlist": "netlist_v2.v", "selected_sdc": "constraints.sdc",
            "selected_clock": "clk_main", "scenario": "func", "corner": "typ", "tool": "pt_shell",
            "tool_exit": 0, "signoff": "OK", "constrained_paths": 1, "report_digest": rd, "run_nonce": nn}


def test_grader_golden_evidence_ok():
    def setup(d):
        _common(d)
        (d / "timing_report.rpt").write_text(_REF_BODY)
        (d / "evidence_manifest.json").write_text(json.dumps(_good_manifest_for(_REF_BODY)))
    out = _run_grader(setup)
    assert "EVIDENCE_OK" in out, out
    assert "FINAL_ARTIFACT_CONSISTENCY_OK" in out
    assert "SCENARIO_CLOCK_OK" in out
    assert "PROVENANCE_OK" in out


def test_grader_hand_edited_report_fails():
    def setup(d):
        _common(d)
        tampered = _REF_BODY.replace("slack (MET) 0.13", "slack (MET) 0.99")
        (d / "timing_report.rpt").write_text(tampered)
        # manifest still claims the correct (reference) digest -> body no longer matches it
        (d / "evidence_manifest.json").write_text(json.dumps(_good_manifest_for(_REF_BODY)))
    out = _run_grader(setup)
    assert "EVIDENCE_OK" not in out, out


def test_grader_hand_edited_manifest_nonce_fails():
    def setup(d):
        _common(d)
        (d / "timing_report.rpt").write_text(_REF_BODY)
        m = _good_manifest_for(_REF_BODY)
        m["run_nonce"] = "deadbeefdeadbeef"
        (d / "evidence_manifest.json").write_text(json.dumps(m))
    out = _run_grader(setup)
    assert "EVIDENCE_OK" not in out, out


def test_grader_stale_evidence_reuse_fails():
    # inputs repaired (v2) but submitted evidence is the STALE v1 evidence (mismatched digest/nonce)
    def setup(d):
        _common(d)
        stale_body = _REF_BODY.replace("cap_reg", "cap_reg_v1").replace("0.13", "0.65")
        (d / "timing_report.rpt").write_text(stale_body)
        sm = _good_manifest_for(_REF_BODY)
        sm["selected_netlist"] = "netlist_v1.v"; sm["selected_clock"] = "clk_old"
        sm["report_digest"] = _digest_of(stale_body)
        (d / "evidence_manifest.json").write_text(json.dumps(sm))
    out = _run_grader(setup)
    assert "EVIDENCE_OK" not in out, out


def test_grader_wrong_package_evidence_fails():
    # consumed v1, evidence faithfully describes v1 (its own re-run would match) but != authority
    def setup(d):
        _common(d, consumed="netlist_v1.v", clk="clk_old")
        body = _REF_BODY.replace("0.13", "0.65")
        (d / "timing_report.rpt").write_text(body)
        # make a self-consistent v1 reference so authenticity passes; authority clause must still fail
        rd = _digest_of(body)
        nn = hashlib.sha256(("fc" + "sd" + "nl" + "clk_old" + "func" + "typ" + rd).encode()).hexdigest()[:16]
        sm = {"input_hashes": {"flow_config.json": "fc", "constraints.sdc": "sd", "consumed_netlist": "nl"},
              "selected_netlist": "netlist_v1.v", "selected_sdc": "constraints.sdc",
              "selected_clock": "clk_old", "scenario": "func", "corner": "typ", "tool": "pt_shell",
              "tool_exit": 0, "signoff": "OK", "constrained_paths": 1, "report_digest": rd, "run_nonce": nn}
        (d / "evidence_manifest.json").write_text(json.dumps(sm))
        (d / "ref_timing_report.rpt").write_text(body)
        (d / "ref_evidence_manifest.json").write_text(json.dumps(sm))
    out = _run_grader(setup)
    assert "EVIDENCE_OK" not in out, out
    assert "FINAL_ARTIFACT_CONSISTENCY_OK" not in out
    assert "PROVENANCE_OK" not in out


def test_grader_missing_report_fails():
    def setup(d):
        _common(d)
        (d / "evidence_manifest.json").write_text(json.dumps(_good_manifest_for(_REF_BODY)))
        # no timing_report.rpt
    out = _run_grader(setup)
    assert "EVIDENCE_OK" not in out, out


def test_grader_missing_manifest_fails():
    def setup(d):
        _common(d)
        (d / "timing_report.rpt").write_text(_REF_BODY)
        # no evidence_manifest.json
    out = _run_grader(setup)
    assert "EVIDENCE_OK" not in out, out


def test_grader_masking_detected():
    def setup(d):
        _common(d)
        (d / "applied_hidden.sdc").write_text(
            "create_clock -name clk_main -period 3.0 [get_ports clk_main]\n"
            "set_false_path -from [get_ports din]\n")
        (d / "timing_report.rpt").write_text(_REF_BODY)
        (d / "evidence_manifest.json").write_text(json.dumps(_good_manifest_for(_REF_BODY)))
    out = _run_grader(setup)
    assert "HANDOFF_MASKING_DETECTED" in out, out
    assert "EVIDENCE_OK" not in out


# --- 5. public scripts: no hidden refs / verdict-first / no leak ------------

def test_public_scripts_no_hidden_refs():
    for name in ("run_public.sh", "run_public.tcl"):
        text = (TASK / "files" / name).read_text()
        for leak in ("handoff_truth", "grade_trajectory", "run_hidden", "regen_reference",
                     "EVIDENCE_OK", "ref_evidence_manifest", "applied_hidden"):
            assert leak not in text, f"{name} leaks '{leak}'"


def test_no_secret_leak_in_visible():
    truth = json.loads((TASK / "hidden" / "handoff_truth.json").read_text())
    meta = _meta()
    for v in meta["files"]["visible"]:
        if v.endswith((".db",)):
            continue
        text = (TASK / "files" / v).read_text(errors="ignore")
        assert "handoff_truth" not in text
        assert "stale_netlist_sha256" not in text


_MOCK_PT = """#!/bin/bash
printf 'PrimeTime banner padding %s\\n' $(seq 1 60)
echo "TRAJECTORY_PUBLIC: MISMATCH consumed=netlist_v1.v/clk_old manifest=netlist_v2.v/clk_main constrained_paths=1 signoff=OK evidence=STALE"
echo "PUBLIC_HINT: evidence is STALE -- rerun run_evidence.sh"
echo "PUBLIC_DONE"
"""


def test_public_verdict_within_first_1000_bytes(tmp_path):
    meta = _meta()
    ws = create_agent_workspace(TASK, meta)
    mock = tmp_path / "mock_pt_shell"
    mock.write_text(_MOCK_PT)
    mock.chmod(0o755)
    try:
        env = dict(os.environ, EDA_PT_CMD=str(mock))
        out = subprocess.run(["bash", "run_public.sh"], cwd=ws, env=env,
                             capture_output=True, text=True, timeout=60).stdout
        off = out.find("TRAJECTORY_PUBLIC:")
        assert off != -1 and off < 1000, f"verdict at {off}"
        for leak in ("EVIDENCE_OK", "handoff_truth", "grade_trajectory"):
            assert leak not in out
    finally:
        shutil.rmtree(ws, ignore_errors=True)


# --- 6. workspace runnable without hidden; forbidden edits caught -----------

def test_workspace_runnable_without_hidden():
    meta = _meta()
    ws = create_agent_workspace(TASK, meta)
    try:
        for need in ("flow_config.json", "constraints.sdc", "run_evidence.sh", "gen_evidence.py",
                     "evidence_signoff.tcl", "handoff_manifest.json", "netlist_v2.v", "tiny.db"):
            assert (ws / need).is_file(), need
        present = {p.name for p in ws.iterdir() if p.is_file()}
        for hid in meta["files"]["hidden"]:
            assert Path(hid).name not in present, f"hidden {hid} leaked"
    finally:
        shutil.rmtree(ws, ignore_errors=True)


def test_forbidden_edits_detected():
    meta = _meta()
    for forbidden in ("netlist_v2.v", "run_evidence.sh", "gen_evidence.py", "handoff_manifest.json"):
        clean, viol = detect_forbidden_modifications({forbidden: "modified"}, meta["files"]["forbidden"])
        assert not clean and any(forbidden in v for v in viol), (forbidden, viol)


def test_run_nonce_is_deterministic_no_wallclock():
    gen = (TASK / "files" / "gen_evidence.py").read_text()
    assert "run_nonce" in gen
    for banned in ("time.time", "datetime", "strftime", "localtime"):
        assert banned not in gen, f"gen_evidence uses wall-clock: {banned}"
