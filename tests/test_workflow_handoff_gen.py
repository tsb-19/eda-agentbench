"""Phase-4B p14 workflow / multi-stage evidence-chain handoff: tool-free tests.

No real EDA tool runs here. The evaluator gate math is driven with synthesized hidden-grader marker
logs; the stdlib chain oracle (grade_workflow.py) is run directly on crafted submitted-vs-reference
manifests. Real-PrimeTime acceptance is validated separately on b04 (see the Phase-4B report).

Covers: dispatch parity (both sites), schema/structural validity, generator determinism + seed
sensitivity, p13-reproduction (evidence_steps=1) vs chain (evidence_steps=2) gate math, the chain
oracle forgery matrix (missing/stale/wrong-package stage1, hand-edited, stage2 from stale stage1),
no hidden leaks, verdict-early, workspace runnable without hidden files.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from eda_agentbench.agentic.runner import _select_evaluator
from eda_agentbench.evaluator.workflow_handoff import WorkflowHandoffEvaluator
from eda_agentbench.schema import validate_metadata
from eda_agentbench.task.loader import structural_validate

REPO = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO / "tasks" / "p14_workflow_handoff"
T1 = TASKS_DIR / "workflow_handoff_0001"   # evidence_steps=1
T2 = TASKS_DIR / "workflow_handoff_0002"   # evidence_steps=2

import sys
sys.path.insert(0, str(REPO))
from generators.p14_workflow_handoff_gen import build_task_skeleton  # noqa: E402


# --------------------------------------------------------------------------- helpers
def _meta(task: Path) -> dict:
    return json.loads((task / "metadata.json").read_text())


def _score(task: Path, log: str) -> tuple[float, bool, dict]:
    meta = _meta(task)
    ev = _select_evaluator(meta, task)
    comps = [ev.evaluate_component(c, task, log, mode="submission") for c in meta["scoring"]["weights"]]
    total = sum(c.weighted_score for c in comps)
    return round(total, 4), total >= 0.5, {c.name: c.raw_score for c in comps}


def _log(sg, ev_ok, fin, chain, prov, masking=False):
    """Synthesize a hidden-grader marker log for a workflow state."""
    L = ["SIGNOFF_OK worst_slack=0.13" if sg else "SIGNOFF_FAIL no_paths"]
    if masking:
        L.append("HANDOFF_MASKING_DETECTED: sdc_exception:set_false_path")
    if ev_ok and not masking:
        L.append("EVIDENCE_OK")
    L.append("EVIDENCE_SCORE: %.3f" % (1.0 if ev_ok else 0.0))
    for pref, v in (("FINAL_STATE", fin), ("STAGE_CHAIN", chain), ("PROVENANCE", prov)):
        if v and not masking:
            L.append(pref + "_OK")
        L.append(pref + "_SCORE: %.3f" % (1.0 if v else 0.0))
    return "\n".join(L)


# --------------------------------------------------------------------------- 1. dispatch parity
def test_agentic_dispatch_selects_workflow():
    assert isinstance(_select_evaluator(_meta(T1), T1), WorkflowHandoffEvaluator)
    assert isinstance(_select_evaluator(_meta(T2), T2), WorkflowHandoffEvaluator)


def test_dispatch_parity_both_sites():
    meta = _meta(T2)
    assert meta["scoring"]["evaluator"] == "workflow_handoff.WorkflowHandoffEvaluator"
    ev = _select_evaluator(meta, T2)
    got = f"{type(ev).__module__.split('.')[-1]}.{type(ev).__name__}"
    assert got == meta["scoring"]["evaluator"]
    cli = (REPO / "eda_agentbench" / "cli.py").read_text()
    runner = (REPO / "eda_agentbench" / "agentic" / "runner.py").read_text()
    assert 'evaluator_spec == "workflow_handoff.WorkflowHandoffEvaluator"' in cli
    assert 'evaluator_spec == "workflow_handoff.WorkflowHandoffEvaluator"' in runner


# --------------------------------------------------------------------------- 2. schema / structural
@pytest.mark.parametrize("task,steps", [(T1, 1), (T2, 2)])
def test_schema_and_structural_valid(task, steps):
    meta = _meta(task)
    assert validate_metadata(meta) == []
    assert structural_validate(task) == []
    assert meta["track"] == "p14_workflow_handoff"
    assert re.match(r"^workflow_handoff_[0-9]{4}$", meta["task_id"])
    assert meta["generator"]["params"]["evidence_steps"] == steps
    assert abs(sum(meta["scoring"]["weights"].values()) - 1.0) < 1e-9
    assert set(meta["scoring"]["weights"]) == {
        "signoff", "final_state", "evidence_generation", "stage_chain", "provenance", "explanation"}


# --------------------------------------------------------------------------- 3. evaluator gate math
def test_golden_full_chain_scores_1():
    for task in (T1, T2):
        total, passed, comps = _score(task, _log(1, 1, 1, 1, 1))
        assert passed and abs(total - 1.0) < 1e-9, (task, comps)


def test_final_state_only_no_rerun_fails():
    # final files correct, no fresh evidence => EVIDENCE not OK => gated axes 0
    total, passed, comps = _score(T2, _log(1, 0, 1, 1, 1))
    assert not passed and total <= 0.30, comps
    assert comps["evidence_generation"] == 0.0
    assert comps["final_state"] == 0.0 and comps["stage_chain"] == 0.0


def test_partial_chain_no_evidence_ok_fails():
    # stage1 evidence ok but chain incomplete: in real grading STAGE_CHAIN feeds EVIDENCE_OK, so the
    # only consistent log has ev_ok=0; gated axes drop to 0.
    total, passed, comps = _score(T2, _log(1, 0, 0, 0, 0))
    assert not passed and total <= 0.30, comps


def test_evidence_is_hard_precondition():
    total, passed, comps = _score(T2, _log(1, 0, 1, 1, 1))
    assert comps["final_state"] == 0.0
    assert comps["stage_chain"] == 0.0
    assert comps["provenance"] == 0.0


def test_partial_repair_signoff_fail_below_pass():
    total, passed, comps = _score(T2, _log(0, 0, 0, 0, 0))
    assert not passed and total <= 0.10, comps


def test_masking_zeroes_consistency():
    total, passed, comps = _score(T2, _log(1, 1, 1, 1, 1, masking=True))
    assert not passed, comps
    assert comps["evidence_generation"] == 0.0


def test_golden_mutant_margin():
    g, _, _ = _score(T2, _log(1, 1, 1, 1, 1))
    m, _, _ = _score(T2, _log(1, 0, 0, 0, 0))
    assert (g - m) >= 0.15


# --------------------------------------------------------------------------- 4. generator determinism
def test_generator_deterministic_same_seed(tmp_path):
    a = build_task_skeleton(tmp_path / "a", "workflow_handoff_0002", seed=0, evidence_steps=2)
    b = build_task_skeleton(tmp_path / "b", "workflow_handoff_0002", seed=0, evidence_steps=2)
    fa = sorted(p.relative_to(a) for p in a.rglob("*") if p.is_file())
    fb = sorted(p.relative_to(b) for p in b.rglob("*") if p.is_file())
    assert fa == fb
    for rel in fa:
        assert (a / rel).read_bytes() == (b / rel).read_bytes(), rel


def test_generator_steps_change_tree(tmp_path):
    one = build_task_skeleton(tmp_path / "1", "workflow_handoff_0001", seed=0, evidence_steps=1)
    two = build_task_skeleton(tmp_path / "2", "workflow_handoff_0002", seed=0, evidence_steps=2)
    one_files = {p.name for p in (one / "files").iterdir()}
    two_files = {p.name for p in (two / "files").iterdir()}
    # steps=2 adds the stage-2 generator + summary artifacts
    assert "run_evidence_stage2.sh" in two_files and "run_evidence_stage2.sh" not in one_files
    assert "stage2_summary.json" in two_files and "stage2_summary.json" not in one_files


def test_p13_reproduction_mode_shape(tmp_path):
    # evidence_steps=1 reproduces the p13 trajectory pattern: same editable surface, single-stage.
    one = build_task_skeleton(tmp_path / "r", "workflow_handoff_0001", seed=0, evidence_steps=1)
    meta = json.loads((one / "metadata.json").read_text())
    assert meta["generator"]["params"]["evidence_steps"] == 1
    assert "timing_report.rpt" in meta["files"]["editable"]
    files = {p.name for p in (one / "files").iterdir()}
    assert "stage2_summary.json" not in files
    assert "run_evidence_stage2.sh" not in files


# --------------------------------------------------------------------------- 5. chain oracle forgery matrix
_BEGIN = "=== REPORT_TIMING BEGIN ==="
_END = "=== REPORT_TIMING END ==="


def _digest(body_inner: str) -> str:
    vol = re.compile(r"(?i)\b(date|version|copyright|license|synopsys|solvnet|report_timing|"
                     r"design\s*:\s|tool created|loading|information:|warning:)\b")
    out = []
    for line in body_inner.splitlines():
        s = re.sub(r"\s+", " ", line).strip()
        if not s or vol.search(s):
            continue
        out.append(s)
    return hashlib.sha256(("\n".join(out) + "\n").encode()).hexdigest()


def _report(body_inner: str) -> str:
    return f"# header\n{_BEGIN}\n{body_inner}\n{_END}\n"


def _run_grader(task: Path, steps: int, setup) -> str:
    d = Path(tempfile.mkdtemp(prefix="p14g_"))
    try:
        for f in ("netlist_v1.v", "netlist_v2.v", "handoff_manifest.json"):
            shutil.copy2(task / "files" / f, d / f)
        shutil.copy2(task / "hidden" / "handoff_truth.json", d / "handoff_truth.json")
        shutil.copy2(task / "hidden" / "grade_workflow.py", d / "grade_workflow.py")
        # minimal trusted-side artifacts the grader reads as data
        (d / "applied_hidden.sdc").write_text(
            "create_clock -name clk_main -period 3.0 [get_ports clk_main]\n")
        (d / "coverage.txt").write_text("intended_clock_present 1\nconstrained_paths 1\n")
        setup(d)
        p = subprocess.run(["python3", "grade_workflow.py", "handoff_truth.json"],
                           cwd=d, capture_output=True, text=True, timeout=60)
        return p.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _ih(d: Path):
    fc = hashlib.sha256((d / "flow_config.json").read_bytes()).hexdigest()
    sdc = hashlib.sha256((d / "constraints.sdc").read_bytes()).hexdigest()
    net = hashlib.sha256((d / "netlist_v2.v").read_bytes()).hexdigest()
    return {"flow_config.json": fc, "constraints.sdc": sdc, "consumed_netlist": net}


def _good_inputs(d: Path):
    (d / "flow_config.json").write_text(json.dumps({
        "netlist": "netlist_v2.v", "top_module": "acc_stage", "constraints": "constraints.sdc",
        "library": "tiny.db", "scenario": "func", "corner": "typ"}, indent=2) + "\n")
    (d / "constraints.sdc").write_text(
        "create_clock -name clk_main -period 3.0 [get_ports clk_main]\n")


def _stage1(d: Path, body="din i0 i1 cap_reg slack MET 0.13", consumed="netlist_v2.v",
            clk="clk_main", make_ref=True):
    ih = _ih(d)
    dig = _digest(body)
    nonce = hashlib.sha256((ih["flow_config.json"] + ih["constraints.sdc"] + ih["consumed_netlist"]
                            + clk + "func" + "typ" + dig).encode()).hexdigest()[:16]
    mani = {"stage": "stage1", "upstream_evidence_digest": None, "input_hashes": ih,
            "selected_netlist": consumed, "selected_sdc": "constraints.sdc", "selected_clock": clk,
            "scenario": "func", "corner": "typ", "tool": "pt_shell", "tool_exit": 0,
            "signoff": "OK", "constrained_paths": 1, "report_digest": dig, "run_nonce": nonce}
    (d / "timing_report.rpt").write_text(_report(body))
    (d / "evidence_manifest.json").write_text(json.dumps(mani, indent=2, sort_keys=True))
    if make_ref:
        (d / "ref_timing_report.rpt").write_text(_report(body))
        (d / "ref_evidence_manifest.json").write_text(json.dumps(mani, indent=2, sort_keys=True))
    return mani


def _stage2(d: Path, upstream_digest, body="cap_reg r0 acc_reg slack MET 0.20", make_ref=True,
            run_nonce=None, signoff="OK"):
    ih = _ih(d)
    s2dig = _digest(body)
    nonce = run_nonce or hashlib.sha256(
        (ih["flow_config.json"] + ih["constraints.sdc"] + ih["consumed_netlist"]
         + "clk_main" + "func" + "typ" + s2dig + (upstream_digest or "")).encode()).hexdigest()[:16]
    s2 = {"stage": "stage2", "upstream_evidence_digest": upstream_digest, "upstream_stage_ok": True,
          "input_hashes": ih, "selected_netlist": "netlist_v2.v", "selected_clock": "clk_main",
          "scenario": "func", "corner": "typ", "tool": "pt_shell", "tool_exit": 0,
          "signoff": signoff, "stage2_constrained_paths": 1, "stage2_slack": "0.20",
          "stage2_report_digest": s2dig, "run_nonce": nonce}
    (d / "stage2_summary.json").write_text(json.dumps(s2, indent=2, sort_keys=True))
    if make_ref:
        (d / "ref_stage2_summary.json").write_text(json.dumps(s2, indent=2, sort_keys=True))
    return s2


# -- steps=1 (p13-reproduction) grader checks --
def test_grader_steps1_golden_evidence_ok():
    def setup(d):
        _good_inputs(d)
        _stage1(d)
    out = _run_grader(T1, 1, setup)
    assert "EVIDENCE_OK" in out and "STAGE_CHAIN_OK" in out
    assert "FINAL_STATE_OK" in out and "PROVENANCE_OK" in out


def test_grader_steps1_hand_edited_report_fails():
    def setup(d):
        _good_inputs(d)
        m = _stage1(d)
        # tamper the submitted report body but keep the manifest digest -> mismatch
        (d / "timing_report.rpt").write_text(_report("din i0 cap_reg slack MET 9.99"))
    out = _run_grader(T1, 1, setup)
    assert "EVIDENCE_OK" not in out


def test_grader_steps1_wrong_package_fails():
    def setup(d):
        _good_inputs(d)
        # flow_config still v2 but evidence claims v1 selection -> authority clause fails
        _stage1(d, consumed="netlist_v1.v", clk="clk_old")
    out = _run_grader(T1, 1, setup)
    assert "EVIDENCE_OK" not in out


# -- steps=2 chain grader checks --
def test_grader_steps2_golden_chain_ok():
    def setup(d):
        _good_inputs(d)
        m = _stage1(d)
        _stage2(d, upstream_digest=m["report_digest"])
    out = _run_grader(T2, 2, setup)
    assert "EVIDENCE_OK" in out and "STAGE_CHAIN_OK" in out


def test_grader_steps2_missing_stage2_fails():
    def setup(d):
        _good_inputs(d)
        _stage1(d)
        # no stage2_summary.json, no ref_stage2_summary.json
    out = _run_grader(T2, 2, setup)
    assert "EVIDENCE_OK" not in out
    assert "STAGE_CHAIN_OK" not in out


def test_grader_steps2_stage2_from_stale_stage1_fails():
    def setup(d):
        _good_inputs(d)
        m = _stage1(d)
        # stage2 binds a STALE/old upstream digest, not the fresh stage1 digest
        _stage2(d, upstream_digest="0" * 64)
    out = _run_grader(T2, 2, setup)
    assert "EVIDENCE_OK" not in out
    assert "STAGE_CHAIN_OK" not in out


def test_grader_steps2_stale_stage1_breaks_chain():
    def setup(d):
        _good_inputs(d)
        # submitted stage1 differs from the hidden reference (stale body) but stage2 binds the submitted
        m = _stage1(d, make_ref=True)
        # now overwrite the REFERENCE stage1 to a different (fresh) digest -> submitted stage1 stale
        fresh = _digest("din i0 i1 i2 cap_reg slack MET 0.13")
        ref = json.loads((d / "ref_evidence_manifest.json").read_text())
        ref["report_digest"] = fresh
        (d / "ref_evidence_manifest.json").write_text(json.dumps(ref))
        (d / "ref_timing_report.rpt").write_text(_report("din i0 i1 i2 cap_reg slack MET 0.13"))
        _stage2(d, upstream_digest=m["report_digest"])  # binds the STALE submitted stage1
    out = _run_grader(T2, 2, setup)
    assert "EVIDENCE_OK" not in out


def test_grader_steps2_hand_edited_stage2_nonce_fails():
    def setup(d):
        _good_inputs(d)
        m = _stage1(d)
        _stage2(d, upstream_digest=m["report_digest"])  # faithful submitted + ref
        # now tamper ONLY the submitted stage2 nonce -> differs from the faithful reference
        s2 = json.loads((d / "stage2_summary.json").read_text())
        s2["run_nonce"] = "deadbeefdeadbeef"
        (d / "stage2_summary.json").write_text(json.dumps(s2, indent=2, sort_keys=True))
    out = _run_grader(T2, 2, setup)
    assert "EVIDENCE_OK" not in out


# --------------------------------------------------------------------------- 6. leak / verdict / runnable
@pytest.mark.parametrize("task", [T1, T2])
def test_no_hidden_artifact_leak_in_public(task):
    # A leak = a HIDDEN file's CONTENT (oracle code / truth values / reference artifacts) appearing
    # verbatim in a visible file. A hidden script being *named* in a doc comment is not a leak.
    public_blob = ""
    for p in (task / "files").iterdir():
        public_blob += p.read_text(errors="ignore")
    grader_body = (task / "hidden" / "grade_workflow.py").read_text()
    truth_body = (task / "hidden" / "handoff_truth.json").read_text()
    # distinctive grader internals / the whole truth file must not be embedded in public files
    for needle in ("def grade(truth)", "EVIDENCE_SCORE: %.3f", "stage2_binds_fresh_stage1"):
        assert needle not in public_blob, needle
    assert "expected_netlist_sha256" not in public_blob  # a truth-only field name
    assert truth_body.strip() not in public_blob


@pytest.mark.parametrize("task", [T1, T2])
def test_no_answer_literal_leak(task):
    # the golden run_nonce / report_digest must not be echoed in any visible file
    sol_mani = json.loads((task / "solution" / "evidence_manifest.json").read_text())
    nonce = sol_mani["run_nonce"]
    for p in (task / "files").iterdir():
        assert nonce not in p.read_text(errors="ignore"), (task.name, p.name)


@pytest.mark.parametrize("task", [T1, T2])
def test_public_verdict_marker_present_and_early(task):
    tcl = (task / "files" / "run_public.tcl").read_text()
    sh = (task / "files" / "run_public.sh").read_text()
    assert "WORKFLOW_PUBLIC:" in tcl
    # the sh hoists the verdict grep to the top of stdout (within first 1000 bytes of the script body)
    assert sh.index("WORKFLOW_PUBLIC:") < 1000


@pytest.mark.parametrize("task", [T1, T2])
def test_workspace_runnable_without_hidden(task):
    # every visible file referenced by the public runner exists under files/ (no hidden dependency)
    files = {p.name for p in (task / "files").iterdir()}
    assert "run_public.sh" in files and "run_public.tcl" in files
    assert "run_evidence_stage1.sh" in files and "gen_evidence_stage1.py" in files
    if _meta(task)["generator"]["params"]["evidence_steps"] == 2:
        assert "run_evidence_stage2.sh" in files and "gen_evidence_stage2.py" in files
    # hidden grader files must NOT be in files/
    assert "grade_workflow.py" not in files and "handoff_truth.json" not in files


@pytest.mark.parametrize("task", [T1, T2])
def test_forbidden_includes_generators_and_oracle(task):
    forb = set(_meta(task)["files"]["forbidden"])
    assert {"run_evidence_stage1.sh", "gen_evidence_stage1.py", "grade_workflow.py",
            "handoff_truth.json", "handoff_manifest.json"} <= forb
    if _meta(task)["generator"]["params"]["evidence_steps"] == 2:
        assert "run_evidence_stage2.sh" in forb and "gen_evidence_stage2.py" in forb
