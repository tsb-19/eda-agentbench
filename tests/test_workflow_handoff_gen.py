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
    # Dispatch parity: both call sites must delegate to the single shared resolver, so an
    # evaluator can never be reachable from the CLI but not from the agentic runner (the bug
    # this guard was written for). The chained if/elif that used to name each spec twice was
    # replaced by evaluator/resolve.py, so parity is now checked as delegation.
    cli = (REPO / "eda_agentbench" / "cli.py").read_text()
    runner = (REPO / "eda_agentbench" / "agentic" / "runner.py").read_text()
    assert "resolve_evaluator(" in cli
    assert "resolve_evaluator(" in runner


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


# ===========================================================================
# Phase-4D: workflow_handoff_0003 cross-source-conflict hazard preset
# ===========================================================================
T3 = TASKS_DIR / "workflow_handoff_0003"


def _grade_run_hazard(setup) -> str:
    """Run grade_workflow.py for the hazard task in a temp dir populated by setup(dir)."""
    d = Path(tempfile.mkdtemp(prefix="p14h_"))
    try:
        for f in ("netlist_v1.v", "netlist_v2.v", "handoff_manifest.json"):
            shutil.copy2(T3 / "files" / f, d / f)
        shutil.copy2(T3 / "hidden" / "handoff_truth.json", d / "handoff_truth.json")
        shutil.copy2(T3 / "hidden" / "grade_workflow.py", d / "grade_workflow.py")
        (d / "applied_hidden.sdc").write_text(
            "create_clock -name clk_main -period 3.0 [get_ports clk_main]\n")
        (d / "coverage.txt").write_text("intended_clock_present 1\nconstrained_paths 1\n")
        setup(d)
        p = subprocess.run(["python3", "grade_workflow.py", "handoff_truth.json"],
                           cwd=d, capture_output=True, text=True, timeout=60)
        return p.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_0003_exists_and_schema_valid():
    meta = _meta(T3)
    assert validate_metadata(meta) == []
    assert structural_validate(T3) == []
    assert meta["track"] == "p14_workflow_handoff"
    assert meta["task_id"] == "workflow_handoff_0003"
    assert meta["generator"]["params"]["hazard_type"] == "cross_source_conflict"
    assert abs(sum(meta["scoring"]["weights"].values()) - 1.0) < 1e-9
    assert {"authority_consistency", "hazard_recovery"} <= set(meta["scoring"]["weights"])


def test_0003_authority_hierarchy_encoded():
    truth = json.loads((T3 / "hidden" / "handoff_truth.json").read_text())
    assert truth["authority_source"] == "handoff_manifest.json"
    assert truth["hazard_type"] == "cross_source_conflict"
    # manifest out-ranks flow_config / evidence / report / log in the hierarchy
    h = truth["authority_hierarchy"]
    assert h.index("handoff_manifest.json") < h.index("flow_config.json")
    assert h.index("flow_config.json") < h.index("evidence_manifest.json")
    assert h.index("evidence_manifest.json") < h.index("prev_signoff.log")
    assert truth["expected_netlist"] == "netlist_v2.v"   # authority target is v2 regardless of decoys


def test_0003_dispatch_parity():
    meta = _meta(T3)
    assert meta["scoring"]["evaluator"] == "workflow_handoff.WorkflowHandoffEvaluator"
    assert isinstance(_select_evaluator(meta, T3), WorkflowHandoffEvaluator)


def test_0003_shipped_manifest_lies_about_package():
    # the cross-source conflict: shipped manifest CLAIMS v2 but its digest is the v1 run
    m = json.loads((T3 / "files" / "evidence_manifest.json").read_text())
    assert m["selected_netlist"] == "netlist_v2.v"        # the lie
    assert m["selected_clock"] == "clk_main"
    sol = json.loads((T3 / "solution" / "evidence_manifest.json").read_text())
    assert m["report_digest"] != sol["report_digest"]     # but the body is NOT the real v2 run
    # flow_config still selects v1 (the real consumed source)
    fc = json.loads((T3 / "files" / "flow_config.json").read_text())
    assert fc["netlist"] == "netlist_v1.v"


def test_0003_decoy_log_present_and_forbidden():
    assert (T3 / "files" / "prev_signoff.log").exists()
    meta = _meta(T3)
    assert "prev_signoff.log" in meta["files"]["visible"]
    assert "prev_signoff.log" in meta["files"]["forbidden"]
    assert "prev_signoff.log" not in meta["files"]["editable"]
    log = (T3 / "files" / "prev_signoff.log").read_text()
    assert "NON-AUTHORITATIVE" in log and "netlist_v1.v" in log


# -- grader behavior (tool-free, crafted submitted-vs-reference) --
_BEGIN2 = "=== REPORT_TIMING BEGIN ==="
_END2 = "=== REPORT_TIMING END ==="


def _hz_inputs(d: Path, netlist="netlist_v2.v", clk="clk_main"):
    (d / "flow_config.json").write_text(json.dumps({
        "netlist": netlist, "top_module": "acc_stage", "constraints": "constraints.sdc",
        "library": "tiny.db", "scenario": "func", "corner": "typ"}, indent=2) + "\n")
    (d / "constraints.sdc").write_text(
        f"create_clock -name {clk} -period 3.0 [get_ports {clk}]\n")


def _hz_stage1(d: Path, consumed="netlist_v2.v", clk="clk_main", body="din i0 cap_reg slack MET 0.13"):
    dig = _digest(body)
    ih = _ih(d)
    nonce = hashlib.sha256((ih["flow_config.json"] + ih["constraints.sdc"] + ih["consumed_netlist"]
                            + clk + "func" + "typ" + dig).encode()).hexdigest()[:16]
    mani = {"stage": "stage1", "upstream_evidence_digest": None, "input_hashes": ih,
            "selected_netlist": consumed, "selected_sdc": "constraints.sdc", "selected_clock": clk,
            "scenario": "func", "corner": "typ", "tool": "pt_shell", "tool_exit": 0,
            "signoff": "OK", "constrained_paths": 1, "report_digest": dig, "run_nonce": nonce}
    (d / "timing_report.rpt").write_text(f"# h\n{_BEGIN2}\n{body}\n{_END2}\n")
    (d / "evidence_manifest.json").write_text(json.dumps(mani, indent=2, sort_keys=True))
    (d / "ref_timing_report.rpt").write_text(f"# h\n{_BEGIN2}\n{body}\n{_END2}\n")
    (d / "ref_evidence_manifest.json").write_text(json.dumps(mani, indent=2, sort_keys=True))
    return mani


def _hz_stage2(d: Path, upstream, body="cap_reg r0 acc_reg slack MET 0.20"):
    ih = _ih(d); s2dig = _digest(body)
    nonce = hashlib.sha256((ih["flow_config.json"] + ih["constraints.sdc"] + ih["consumed_netlist"]
                            + "clk_main" + "func" + "typ" + s2dig + (upstream or "")).encode()).hexdigest()[:16]
    s2 = {"stage": "stage2", "upstream_evidence_digest": upstream, "upstream_stage_ok": True,
          "input_hashes": ih, "selected_netlist": "netlist_v2.v", "selected_clock": "clk_main",
          "scenario": "func", "corner": "typ", "tool": "pt_shell", "tool_exit": 0, "signoff": "OK",
          "stage2_constrained_paths": 1, "stage2_slack": "0.20", "stage2_report_digest": s2dig,
          "run_nonce": nonce}
    (d / "stage2_summary.json").write_text(json.dumps(s2, indent=2, sort_keys=True))
    (d / "ref_stage2_summary.json").write_text(json.dumps(s2, indent=2, sort_keys=True))
    return s2


def test_0003_grader_full_recovery_emits_hazard_markers():
    def setup(d):
        _hz_inputs(d, "netlist_v2.v", "clk_main")
        m = _hz_stage1(d, "netlist_v2.v", "clk_main")
        _hz_stage2(d, m["report_digest"])
    out = _grade_run_hazard(setup)
    assert "EVIDENCE_OK" in out
    assert "AUTHORITY_CONSISTENCY_OK" in out
    assert "HAZARD_RECOVERY_OK" in out


def test_0003_grader_wrong_authority_v1_fails():
    # agent "made files agree" with the stale v1 source (wrong authority) -> evidence describes v1.
    # The oracle must deny the hazard gates because it pins the authority target to v2.
    def setup(d):
        _hz_inputs(d, "netlist_v1.v", "clk_old")
        m = _hz_stage1(d, "netlist_v1.v", "clk_old")
        _hz_stage2(d, m["report_digest"])
        # the laundered SDC the oracle reads reflects the v1/clk_old choice
        (d / "applied_hidden.sdc").write_text(
            "create_clock -name clk_old -period 3.0 [get_ports clk_old]\n")
    out = _grade_run_hazard(setup)
    assert "EVIDENCE_OK" not in out                 # authority clause denies the master gate
    assert "AUTHORITY_CONSISTENCY_OK" not in out     # the hard hazard gate fails
    assert "HAZARD_RECOVERY_OK" not in out
    assert "evidence_is_authority_pkg=WRONG" in out  # oracle pins the target to the v2 authority


def test_0003_grader_decoy_claim_not_trusted():
    # submit the lying manifest (claims v2) with a v1 body -> report!=manifest, not authority pkg
    def setup(d):
        _hz_inputs(d, "netlist_v2.v", "clk_main")
        m = _hz_stage1(d, "netlist_v2.v", "clk_main", body="din i0 cap_reg slack MET 0.13")
        # tamper: manifest claims v2 (kept) but report body is a different (v1-like) run
        (d / "timing_report.rpt").write_text(f"# h\n{_BEGIN2}\ndin cap_reg slack MET 0.65\n{_END2}\n")
    out = _grade_run_hazard(setup)
    assert "EVIDENCE_OK" not in out
    assert "AUTHORITY_CONSISTENCY_OK" not in out


def test_0003_grader_stage1_only_fails():
    def setup(d):
        _hz_inputs(d, "netlist_v2.v", "clk_main")
        _hz_stage1(d, "netlist_v2.v", "clk_main")
        # no stage2
    out = _grade_run_hazard(setup)
    assert "EVIDENCE_OK" not in out
    assert "HAZARD_RECOVERY_OK" not in out


def test_0003_no_hidden_leak():
    public_blob = ""
    for p in (T3 / "files").iterdir():
        public_blob += p.read_text(errors="ignore")
    for needle in ("def grade(truth)", "AUTHORITY_CONSISTENCY_SCORE", "recovery_step_expected",
                   "stale_source_id"):
        assert needle not in public_blob, needle


def test_0003_public_verdict_early():
    sh = (T3 / "files" / "run_public.sh").read_text()
    assert "WORKFLOW_PUBLIC:" in sh
    assert sh.index("WORKFLOW_PUBLIC:") < 1000


def test_0003_no_answer_literal_leak():
    sol = json.loads((T3 / "solution" / "evidence_manifest.json").read_text())
    nonce = sol["run_nonce"]
    for p in (T3 / "files").iterdir():
        assert nonce not in p.read_text(errors="ignore"), p.name


def test_0003_deterministic_generation(tmp_path):
    a = build_task_skeleton(tmp_path / "a", "workflow_handoff_0003", 0, 2,
                            hazard_type="cross_source_conflict")
    b = build_task_skeleton(tmp_path / "b", "workflow_handoff_0003", 0, 2,
                            hazard_type="cross_source_conflict")
    fa = sorted(p.relative_to(a) for p in a.rglob("*") if p.is_file())
    fb = sorted(p.relative_to(b) for p in b.rglob("*") if p.is_file())
    assert fa == fb
    for rel in fa:
        assert (a / rel).read_bytes() == (b / rel).read_bytes(), rel


def test_0001_0002_skeleton_unchanged_by_hazard_support(tmp_path):
    # regenerating 0001/0002 with hazard_type=None must match the committed skeleton (ex-solution),
    # i.e. adding the cross-source + scenario/corner presets did not perturb the v1 tasks.
    for tid, steps, committed in (("workflow_handoff_0001", 1, T1), ("workflow_handoff_0002", 2, T2)):
        gen = build_task_skeleton(tmp_path / tid, tid, 0, steps, hazard_type=None)
        for rel in (p.relative_to(gen) for p in gen.rglob("*") if p.is_file()):
            if rel.parts[0] == "solution":
                continue  # solution evidence is tool-baked, not part of the pure skeleton
            # the shared hidden oracle (grade_workflow.py) is a single source reused by every p14 task;
            # it gained gated, behavior-inert blocks for the hazard presets. It is kept UNIFORM across
            # all committed tasks (synced), so the regenerated copy must byte-match committed.
            assert (gen / rel).read_bytes() == (committed / rel).read_bytes(), rel


# ===========================================================================
# p14 v3 -- workflow_handoff_0004 (scenario/corner cross-source conflict)
# ===========================================================================
T4 = TASKS_DIR / "workflow_handoff_0004"


def test_0004_exists_and_schema_valid():
    meta = _meta(T4)
    assert validate_metadata(meta) == []
    assert structural_validate(T4) == []
    assert meta["track"] == "p14_workflow_handoff"
    assert meta["task_id"] == "workflow_handoff_0004"
    gp = meta["generator"]["params"]
    assert gp["hazard_type"] == "scenario_corner_cross_source_conflict"
    assert abs(sum(meta["scoring"]["weights"].values()) - 1.0) < 1e-9
    assert {"authority_consistency", "hazard_recovery"} <= set(meta["scoring"]["weights"])


def test_0004_authority_hierarchy_and_targets():
    truth = json.loads((T4 / "hidden" / "handoff_truth.json").read_text())
    assert truth["hazard_type"] == "scenario_corner_cross_source_conflict"
    assert truth["authority_source"] == "handoff_manifest.json"
    # netlist/clock are ALREADY correct; only scenario/corner provenance is in conflict
    assert truth["netlist_clock_already_correct"] is True
    assert truth["expected_scenario"] == "slow"
    assert truth["expected_corner"] == "func"
    assert truth["stale_scenario"] == "test"
    assert truth["stale_corner"] == "typ"
    # the decoy log is the lowest-authority source
    h = truth["authority_hierarchy"]
    assert h.index("handoff_manifest.json") < h.index("flow_config.json")
    assert h.index("flow_config.json") < h.index("evidence_manifest.json")
    assert h.index("evidence_manifest.json") < h.index("prev_corner_signoff.log")


def test_0004_dispatch_parity():
    meta = _meta(T4)
    assert meta["scoring"]["evaluator"] == "workflow_handoff.WorkflowHandoffEvaluator"
    assert isinstance(_select_evaluator(meta, T4), WorkflowHandoffEvaluator)


def test_0004_mutant_netlist_clock_correct_scenario_corner_wrong():
    # the defect: netlist + clock are already right; scenario/corner are the wrong provenance
    fc = json.loads((T4 / "files" / "flow_config.json").read_text())
    assert fc["netlist"] == "netlist_v2.v"          # already correct
    assert fc["corner"] == "typ"                     # wrong (authority = func)
    csdc = (T4 / "files" / "constraints.sdc").read_text()
    assert "clk_main" in csdc                         # clock already correct
    sol = json.loads((T4 / "solution" / "flow_config.json").read_text())
    assert sol["scenario"] == "slow" and sol["corner"] == "func"   # golden = authority
    # the manifest authority names slow/func
    man = json.loads((T4 / "files" / "handoff_manifest.json").read_text())
    assert man["scenario"] == "slow" and man["corner"] == "func"


def test_0004_shipped_manifest_lies_about_scenario_corner():
    # the conflict: shipped manifest CLAIMS slow/func while the run was test/typ
    m = json.loads((T4 / "files" / "evidence_manifest.json").read_text())
    assert m["scenario"] == "slow" and m["corner"] == "func"   # the lie (claim)
    assert m["selected_netlist"] == "netlist_v2.v"             # netlist claim is honest
    fc = json.loads((T4 / "files" / "flow_config.json").read_text())
    assert fc["scenario"] == "test" and fc["corner"] == "typ"  # flow_config tells the truth (wrong)


def test_0004_decoy_log_present_and_forbidden():
    assert (T4 / "files" / "prev_corner_signoff.log").exists()
    meta = _meta(T4)
    assert "prev_corner_signoff.log" in meta["files"]["visible"]
    assert "prev_corner_signoff.log" in meta["files"]["forbidden"]
    assert "prev_corner_signoff.log" not in meta["files"]["editable"]
    log = (T4 / "files" / "prev_corner_signoff.log").read_text()
    assert "NON-AUTHORITATIVE" in log and ("test" in log or "typ" in log)


# -- grader behavior (tool-free, crafted submitted-vs-reference) --
def _grade_run_sc(setup) -> str:
    """Run grade_workflow.py for the 0004 scenario/corner hazard task."""
    d = Path(tempfile.mkdtemp(prefix="p14sc_"))
    try:
        for f in ("netlist_v1.v", "netlist_v2.v", "handoff_manifest.json"):
            shutil.copy2(T4 / "files" / f, d / f)
        shutil.copy2(T4 / "hidden" / "handoff_truth.json", d / "handoff_truth.json")
        shutil.copy2(T4 / "hidden" / "grade_workflow.py", d / "grade_workflow.py")
        (d / "applied_hidden.sdc").write_text(
            "create_clock -name clk_main -period 3.0 [get_ports clk_main]\n")
        (d / "coverage.txt").write_text("intended_clock_present 1\nconstrained_paths 1\n")
        setup(d)
        p = subprocess.run(["python3", "grade_workflow.py", "handoff_truth.json"],
                           cwd=d, capture_output=True, text=True, timeout=60)
        return p.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _sc_inputs(d: Path, scenario="slow", corner="func"):
    """flow_config: netlist/clock always correct; scenario/corner parametrize the provenance."""
    (d / "flow_config.json").write_text(json.dumps({
        "netlist": "netlist_v2.v", "top_module": "acc_stage", "constraints": "constraints.sdc",
        "library": "tiny.db", "scenario": scenario, "corner": corner}, indent=2) + "\n")
    (d / "constraints.sdc").write_text(
        "create_clock -name clk_main -period 3.0 [get_ports clk_main]\n")


def _sc_stage1(d: Path, scenario="slow", corner="func",
               body="din i0 cap_reg slack MET 0.13"):
    """Build stage1 evidence + reference. In the real harness the reference re-run stamps the
    ACTUAL scenario/corner from the submitted flow_config, so ref.scenario/corner == flow_config."""
    dig = _digest(body)
    ih = _ih(d)
    nonce = hashlib.sha256((ih["flow_config.json"] + ih["constraints.sdc"] + ih["consumed_netlist"]
                            + "clk_main" + scenario + corner + dig).encode()).hexdigest()[:16]
    mani = {"stage": "stage1", "upstream_evidence_digest": None, "input_hashes": ih,
            "selected_netlist": "netlist_v2.v", "selected_sdc": "constraints.sdc",
            "selected_clock": "clk_main", "scenario": scenario, "corner": corner,
            "tool": "pt_shell", "tool_exit": 0, "signoff": "OK", "constrained_paths": 1,
            "report_digest": dig, "run_nonce": nonce}
    (d / "timing_report.rpt").write_text(f"# h\n{_BEGIN2}\n{body}\n{_END2}\n")
    (d / "evidence_manifest.json").write_text(json.dumps(mani, indent=2, sort_keys=True))
    (d / "ref_timing_report.rpt").write_text(f"# h\n{_BEGIN2}\n{body}\n{_END2}\n")
    (d / "ref_evidence_manifest.json").write_text(json.dumps(mani, indent=2, sort_keys=True))
    return mani


def _sc_stage2(d: Path, upstream, scenario="slow", corner="func",
               body="cap_reg r0 acc_reg slack MET 0.20"):
    ih = _ih(d); s2dig = _digest(body)
    nonce = hashlib.sha256((ih["flow_config.json"] + ih["constraints.sdc"] + ih["consumed_netlist"]
                            + "clk_main" + scenario + corner + s2dig + (upstream or "")
                            ).encode()).hexdigest()[:16]
    s2 = {"stage": "stage2", "upstream_evidence_digest": upstream, "upstream_stage_ok": True,
          "input_hashes": ih, "selected_netlist": "netlist_v2.v", "selected_clock": "clk_main",
          "scenario": scenario, "corner": corner, "tool": "pt_shell", "tool_exit": 0, "signoff": "OK",
          "stage2_constrained_paths": 1, "stage2_slack": "0.20", "stage2_report_digest": s2dig,
          "run_nonce": nonce}
    (d / "stage2_summary.json").write_text(json.dumps(s2, indent=2, sort_keys=True))
    (d / "ref_stage2_summary.json").write_text(json.dumps(s2, indent=2, sort_keys=True))
    return s2


def test_0004_grader_full_slow_func_recovery_emits_markers():
    def setup(d):
        _sc_inputs(d, "slow", "func")
        m = _sc_stage1(d, "slow", "func")
        _sc_stage2(d, m["report_digest"], "slow", "func")
    out = _grade_run_sc(setup)
    assert "EVIDENCE_OK" in out
    assert "AUTHORITY_CONSISTENCY_OK" in out
    assert "HAZARD_RECOVERY_OK" in out
    assert "SCENARIO_AUTHORITY_OK" in out
    assert "CORNER_AUTHORITY_OK" in out
    assert "SCENARIO_CORNER_AUTHORITY_OK" in out


def test_0004_grader_wrong_corner_recovery_fails():
    # agent leaves flow_config under the wrong scenario/corner (test/typ); ref reflects test/typ.
    def setup(d):
        _sc_inputs(d, "test", "typ")
        m = _sc_stage1(d, "test", "typ")
        _sc_stage2(d, m["report_digest"], "test", "typ")
    out = _grade_run_sc(setup)
    assert "EVIDENCE_OK" not in out                  # scenario/corner echecks deny the master gate
    assert "SCENARIO_CORNER_AUTHORITY_OK" not in out
    assert "HAZARD_RECOVERY_OK" not in out
    assert "evidence_scenario_is_authority=WRONG" in out
    assert "evidence_corner_is_authority=WRONG" in out


def test_0004_grader_hand_edited_manifest_claim_fails():
    # agent edits the manifest to CLAIM slow/func while flow_config (and thus the ref re-run) is test/typ.
    def setup(d):
        _sc_inputs(d, "test", "typ")
        # ref re-run reflects the actual test/typ flow_config (truth the agent can't forge)
        m_ref = _sc_stage1(d, "test", "typ")
        # but the SUBMITTED manifest lies about slow/func
        sub = json.loads((d / "evidence_manifest.json").read_text())
        sub["scenario"], sub["corner"] = "slow", "func"
        (d / "evidence_manifest.json").write_text(json.dumps(sub, indent=2, sort_keys=True))
    out = _grade_run_sc(setup)
    assert "EVIDENCE_OK" not in out
    assert "SCENARIO_CORNER_AUTHORITY_OK" not in out


def test_0004_grader_stage1_only_fails():
    def setup(d):
        _sc_inputs(d, "slow", "func")
        _sc_stage1(d, "slow", "func")
        # no stage2
    out = _grade_run_sc(setup)
    assert "EVIDENCE_OK" not in out
    assert "HAZARD_RECOVERY_OK" not in out


def test_0004_grader_stage2_from_wrong_corner_stage1_fails():
    def setup(d):
        _sc_inputs(d, "slow", "func")
        # stage1 honest (slow/func), but stage2 binds a WRONG-corner upstream digest
        m = _sc_stage1(d, "slow", "func")
        wrong = hashlib.sha256(b"wrongcorner").hexdigest()
        _sc_stage2(d, wrong, "slow", "func")
    out = _grade_run_sc(setup)
    assert "STAGE_CHAIN_OK" not in out
    assert "HAZARD_RECOVERY_OK" not in out


def test_0004_grader_decoy_claim_not_trusted():
    # accept the prev_corner_signoff.log decoy: submit a slow/func manifest but a test/typ report body
    def setup(d):
        _sc_inputs(d, "slow", "func")
        _sc_stage1(d, "slow", "func", body="din cap_reg slack MET 0.13")
        (d / "timing_report.rpt").write_text(f"# h\n{_BEGIN2}\ndin cap_reg slack MET 0.40\n{_END2}\n")
    out = _grade_run_sc(setup)
    assert "EVIDENCE_OK" not in out


def test_0004_no_hidden_leak():
    public_blob = ""
    for p in (T4 / "files").iterdir():
        public_blob += p.read_text(errors="ignore")
    for needle in ("def grade(truth)", "SCENARIO_CORNER_AUTHORITY_SCORE", "recovery_step_expected",
                   "expected_scenario"):
        assert needle not in public_blob, needle


def test_0004_public_verdict_early():
    sh = (T4 / "files" / "run_public.sh").read_text()
    assert "WORKFLOW_PUBLIC:" in sh
    assert sh.index("WORKFLOW_PUBLIC:") < 1000


def test_0004_no_answer_literal_leak():
    # the golden solution evidence nonce must not appear in any visible file
    solm = (T4 / "solution" / "evidence_manifest.json")
    if solm.exists():
        nonce = json.loads(solm.read_text())["run_nonce"]
        for p in (T4 / "files").iterdir():
            assert nonce not in p.read_text(errors="ignore"), p.name


def test_0004_deterministic_generation(tmp_path):
    a = build_task_skeleton(tmp_path / "a", "workflow_handoff_0004", 0, 2,
                            hazard_type="scenario_corner_cross_source_conflict")
    b = build_task_skeleton(tmp_path / "b", "workflow_handoff_0004", 0, 2,
                            hazard_type="scenario_corner_cross_source_conflict")
    fa = sorted(p.relative_to(a) for p in a.rglob("*") if p.is_file())
    fb = sorted(p.relative_to(b) for p in b.rglob("*") if p.is_file())
    assert fa == fb
    for rel in fa:
        assert (a / rel).read_bytes() == (b / rel).read_bytes(), rel


def test_0001_0002_0003_grader_markers_unchanged_by_sc_support():
    # behavior-invariance: the shared grader's output for non-sc truth (no expected_scenario) must not
    # emit any scenario/corner markers.
    for src in (T1 / "hidden" / "handoff_truth.json", T2 / "hidden" / "handoff_truth.json",
                T3 / "hidden" / "handoff_truth.json"):
        truth = json.loads(src.read_text())
        assert "expected_scenario" not in truth   # non-sc tasks have no scenario/corner authority pin


# =========================================================================== p14 v4 (0005)
# multi-conflict partially-truthful-decoy: global authority = netlist_v2/clk_main/slow/func. Several
# decoys are each partially true; only the full global package + fresh ordered chain passes. The
# forgery-resistant consumed-netlist/clock echecks (pinned to flow_config / applied_hidden.sdc) reject a
# manifest that CLAIMS netlist_v2 while the consumed netlist is v1.
T5 = TASKS_DIR / "workflow_handoff_0005"


def _grade_run_mc(setup) -> str:
    """Run grade_workflow.py for the 0005 multi-conflict task."""
    d = Path(tempfile.mkdtemp(prefix="p14mc_"))
    try:
        for f in ("netlist_v1.v", "netlist_v2.v", "handoff_manifest.json"):
            shutil.copy2(T5 / "files" / f, d / f)
        shutil.copy2(T5 / "hidden" / "handoff_truth.json", d / "handoff_truth.json")
        shutil.copy2(T5 / "hidden" / "grade_workflow.py", d / "grade_workflow.py")
        (d / "coverage.txt").write_text("intended_clock_present 1\nconstrained_paths 1\n")
        setup(d)
        p = subprocess.run(["python3", "grade_workflow.py", "handoff_truth.json"],
                           cwd=d, capture_output=True, text=True, timeout=60)
        return p.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _mc_ih(d: Path, consumed: str):
    fc = hashlib.sha256((d / "flow_config.json").read_bytes()).hexdigest()
    sdc = hashlib.sha256((d / "constraints.sdc").read_bytes()).hexdigest()
    net = hashlib.sha256((d / consumed).read_bytes()).hexdigest()
    return {"flow_config.json": fc, "constraints.sdc": sdc, "consumed_netlist": net}


def _mc_inputs(d: Path, netlist="netlist_v2.v", scenario="slow", corner="func", clk="clk_main"):
    (d / "flow_config.json").write_text(json.dumps({
        "netlist": netlist, "top_module": "acc_stage", "constraints": "constraints.sdc",
        "library": "tiny.db", "scenario": scenario, "corner": corner}, indent=2) + "\n")
    (d / "constraints.sdc").write_text("create_clock -name %s -period 3.0 [get_ports %s]\n" % (clk, clk))
    # applied_hidden.sdc is the TRUSTED laundered SDC -> the forgery-resistant consumed-clock source
    (d / "applied_hidden.sdc").write_text("create_clock -name %s -period 3.0 [get_ports %s]\n" % (clk, clk))


def _mc_stage1(d: Path, consumed="netlist_v2.v", scenario="slow", corner="func", clk="clk_main",
               body="din i0 cap_reg slack MET 0.13"):
    ih = _mc_ih(d, consumed)
    dig = _digest(body)
    nonce = hashlib.sha256((ih["flow_config.json"] + ih["constraints.sdc"] + ih["consumed_netlist"]
                            + clk + scenario + corner + dig).encode()).hexdigest()[:16]
    mani = {"stage": "stage1", "upstream_evidence_digest": None, "input_hashes": ih,
            "selected_netlist": consumed, "selected_sdc": "constraints.sdc", "selected_clock": clk,
            "scenario": scenario, "corner": corner, "tool": "pt_shell", "tool_exit": 0,
            "signoff": "OK", "constrained_paths": 1, "report_digest": dig, "run_nonce": nonce}
    (d / "timing_report.rpt").write_text("# h\n%s\n%s\n%s\n" % (_BEGIN2, body, _END2))
    (d / "evidence_manifest.json").write_text(json.dumps(mani, indent=2, sort_keys=True))
    # ref re-run reflects the ACTUAL submitted flow_config package (consumed/scenario/corner)
    (d / "ref_timing_report.rpt").write_text("# h\n%s\n%s\n%s\n" % (_BEGIN2, body, _END2))
    (d / "ref_evidence_manifest.json").write_text(json.dumps(mani, indent=2, sort_keys=True))
    return mani


def _mc_stage2(d: Path, upstream, consumed="netlist_v2.v", scenario="slow", corner="func",
               clk="clk_main", body="cap_reg r0 acc_reg slack MET 0.20"):
    ih = _mc_ih(d, consumed)
    s2dig = _digest(body)
    nonce = hashlib.sha256((ih["flow_config.json"] + ih["constraints.sdc"] + ih["consumed_netlist"]
                            + clk + scenario + corner + s2dig + (upstream or "")).encode()).hexdigest()[:16]
    s2 = {"stage": "stage2", "upstream_evidence_digest": upstream, "upstream_stage_ok": True,
          "input_hashes": ih, "selected_netlist": consumed, "selected_clock": clk,
          "scenario": scenario, "corner": corner, "tool": "pt_shell", "tool_exit": 0,
          "signoff": "OK", "stage2_constrained_paths": 1, "stage2_slack": "0.20",
          "stage2_report_digest": s2dig, "run_nonce": nonce}
    (d / "stage2_summary.json").write_text(json.dumps(s2, indent=2, sort_keys=True))
    (d / "ref_stage2_summary.json").write_text(json.dumps(s2, indent=2, sort_keys=True))
    return s2


def test_0005_grader_global_recovery_emits_markers():
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk_main")
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "slow", "func", "clk_main")
    out = _grade_run_mc(setup)
    assert "EVIDENCE_OK" in out
    assert "GLOBAL_AUTHORITY_OK" in out
    assert "MULTI_CONFLICT_OK" in out
    assert "SCENARIO_CORNER_AUTHORITY_OK" in out
    assert "AUTHORITY_CONSISTENCY_OK" in out and "HAZARD_RECOVERY_OK" in out
    assert "PARTIAL_DECOY_REJECTED" not in out


def test_0005_report_A_only_recovery_fails():
    # follow report A: right netlist/clock (v2/clk_main), WRONG scenario/corner (test/typ)
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "test", "typ", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "test", "typ", "clk_main")
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "test", "typ", "clk_main")
    out = _grade_run_mc(setup)
    assert "EVIDENCE_OK" not in out
    assert "GLOBAL_AUTHORITY_OK" not in out
    assert "PARTIAL_DECOY_REJECTED" in out


def test_0005_report_B_only_recovery_fails():
    # follow report B: right scenario/corner (slow/func), STALE netlist (v1)
    def setup(d):
        _mc_inputs(d, "netlist_v1.v", "slow", "func", "clk_main")
        m = _mc_stage1(d, "netlist_v1.v", "slow", "func", "clk_main")
        _mc_stage2(d, m["report_digest"], "netlist_v1.v", "slow", "func", "clk_main")
    out = _grade_run_mc(setup)
    assert "EVIDENCE_OK" not in out
    assert "GLOBAL_AUTHORITY_OK" not in out
    assert "PARTIAL_DECOY_REJECTED" in out


def test_0005_evidence_C_only_recovery_fails():
    # follow evidence C: fresh chain on a semantically wrong package (netlist_v1/slow/func)
    def setup(d):
        _mc_inputs(d, "netlist_v1.v", "slow", "func", "clk_main")
        m = _mc_stage1(d, "netlist_v1.v", "slow", "func", "clk_main")
        _mc_stage2(d, m["report_digest"], "netlist_v1.v", "slow", "func", "clk_main")
    out = _grade_run_mc(setup)
    assert "EVIDENCE_OK" not in out
    assert "GLOBAL_AUTHORITY_OK" not in out


def test_0005_forged_manifest_claims_v2_but_consumed_v1_fails():
    # forgery attempt: run on netlist_v1 but hand-edit the manifest to CLAIM netlist_v2. The grader's
    # consumed-netlist echeck is pinned to flow_config (forgery-resistant), so this is rejected.
    def setup(d):
        _mc_inputs(d, "netlist_v1.v", "slow", "func", "clk_main")  # flow_config consumes v1
        m = _mc_stage1(d, "netlist_v1.v", "slow", "func", "clk_main")
        _mc_stage2(d, m["report_digest"], "netlist_v1.v", "slow", "func", "clk_main")
        sub = json.loads((d / "evidence_manifest.json").read_text())
        sub["selected_netlist"] = "netlist_v2.v"   # the LIE: claim the authority netlist
        (d / "evidence_manifest.json").write_text(json.dumps(sub, indent=2, sort_keys=True))
    out = _grade_run_mc(setup)
    assert "EVIDENCE_OK" not in out
    assert "GLOBAL_AUTHORITY_OK" not in out


def test_0005_stale_clock_consumed_fails():
    # stale clock (clk_old) consumed via applied_hidden.sdc -> consumed-clock authority fails
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_old")
        m = _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk_old")
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "slow", "func", "clk_old")
    out = _grade_run_mc(setup)
    assert "EVIDENCE_OK" not in out
    assert "GLOBAL_AUTHORITY_OK" not in out


def test_0005_stage1_only_fails():
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_main")
        _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk_main")
    out = _grade_run_mc(setup)
    assert "EVIDENCE_OK" not in out
    assert "MULTI_CONFLICT_OK" not in out


def test_0005_stage2_from_semantically_wrong_stage1_fails():
    # stage2 binds a valid digest, but the chain is on the wrong package (netlist_v1) -> global authority
    # denied at the package level even though the chain is syntactically ordered.
    def setup(d):
        _mc_inputs(d, "netlist_v1.v", "slow", "func", "clk_main")
        m = _mc_stage1(d, "netlist_v1.v", "slow", "func", "clk_main")
        _mc_stage2(d, m["report_digest"], "netlist_v1.v", "slow", "func", "clk_main")
    out = _grade_run_mc(setup)
    assert "GLOBAL_AUTHORITY_OK" not in out
    assert "MULTI_CONFLICT_OK" not in out


def test_0005_hand_edited_report_fails():
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_main")
        _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk_main")
        (d / "timing_report.rpt").write_text("# h\n%s\ndin cap_reg slack MET 9.99\n%s\n" % (_BEGIN2, _END2))
    out = _grade_run_mc(setup)
    assert "EVIDENCE_OK" not in out


def test_0005_metadata_and_decoys():
    meta = _meta(T5)
    assert meta["generator"]["params"]["hazard_type"] == "multi_conflict_partially_truthful_decoy"
    assert meta["generator"]["params"]["global_authority_tuple"] == ["netlist_v2.v", "clk_main", "slow", "func"]
    assert abs(sum(meta["scoring"]["weights"].values()) - 1.0) < 1e-9
    assert {"authority_consistency", "hazard_recovery"} <= set(meta["scoring"]["weights"])
    for decoy in ("report_A_typ_test.rpt", "report_B_stale_netlist.rpt", "evidence_C_manifest.json",
                  "prev_signoff.log"):
        assert decoy in meta["files"]["visible"]
        assert decoy in meta["files"]["forbidden"]
    truth = json.loads((T5 / "hidden" / "handoff_truth.json").read_text())
    assert truth["global_authority_tuple"] == ["netlist_v2.v", "clk_main", "slow", "func"]
    assert len(truth["decoy_sources"]) >= 3
    assert len(truth["partial_truth_sources"]) >= 3


def test_0005_dispatch_parity():
    meta = _meta(T5)
    assert meta["scoring"]["evaluator"] == "workflow_handoff.WorkflowHandoffEvaluator"
    assert isinstance(_select_evaluator(meta, T5), WorkflowHandoffEvaluator)


def test_0005_no_hidden_leak():
    public_blob = ""
    for p in (T5 / "files").iterdir():
        public_blob += p.read_text(errors="ignore")
    for needle in ("global_authority_tuple", "MULTI_CONFLICT_OK", "def grade(truth)",
                   "evidence_consumed_netlist_is_authority", "decoy_sources"):
        assert needle not in public_blob, needle


def test_0005_public_verdict_early():
    sh = (T5 / "files" / "run_public.sh").read_text()
    assert "WORKFLOW_PUBLIC:" in sh
    assert sh.index("WORKFLOW_PUBLIC:") < 1000


def test_0005_deterministic():
    a = Path(tempfile.mkdtemp(prefix="p14d1_"))
    b = Path(tempfile.mkdtemp(prefix="p14d2_"))
    try:
        build_task_skeleton(a, "workflow_handoff_0005", 0, 2, "multi_conflict_partially_truthful_decoy")
        build_task_skeleton(b, "workflow_handoff_0005", 0, 2, "multi_conflict_partially_truthful_decoy")
        fa = [p.relative_to(a / "workflow_handoff_0005") for p in (a / "workflow_handoff_0005").rglob("*") if p.is_file()]
        fb = [p.relative_to(b / "workflow_handoff_0005") for p in (b / "workflow_handoff_0005").rglob("*") if p.is_file()]
        assert {str(p) for p in fa} == {str(p) for p in fb}
        for rel in fa:
            assert (a / "workflow_handoff_0005" / rel).read_bytes() == (b / "workflow_handoff_0005" / rel).read_bytes(), rel
    finally:
        shutil.rmtree(a, ignore_errors=True); shutil.rmtree(b, ignore_errors=True)


def test_0005_grader_byte_identical_across_all_tasks():
    import hashlib
    h = {}
    for tid in ("workflow_handoff_0001", "workflow_handoff_0002", "workflow_handoff_0003",
                "workflow_handoff_0004", "workflow_handoff_0005", "workflow_handoff_0006",
                "workflow_handoff_0007", "workflow_handoff_0008",
                "workflow_handoff_0009", "workflow_handoff_0010"):
        h[tid] = hashlib.sha256((TASKS_DIR / tid / "hidden" / "grade_workflow.py").read_bytes()).hexdigest()
    assert len(set(h.values())) == 1, h


def test_0001_0002_0003_grader_markers_unchanged_by_mc_support():
    # behavior-invariance: non-mc truth (no global_authority_tuple) must not emit multi-conflict markers.
    for src in (T1 / "hidden" / "handoff_truth.json", T2 / "hidden" / "handoff_truth.json",
                T3 / "hidden" / "handoff_truth.json", T4 / "hidden" / "handoff_truth.json"):
        truth = json.loads(src.read_text())
        assert "global_authority_tuple" not in truth



# ===========================================================================
# p14 v5 -- workflow_handoff_0006 (constraint-graph multi-source recovery)
# ===========================================================================
T6 = TASKS_DIR / "workflow_handoff_0006"


def _grade_run_cg(setup) -> str:
    """Run grade_workflow.py for the 0006 constraint-graph task."""
    d = Path(tempfile.mkdtemp(prefix="p14cg_"))
    try:
        for f in ("netlist_v1.v", "netlist_v2.v", "handoff_manifest.json"):
            shutil.copy2(T6 / "files" / f, d / f)
        shutil.copy2(T6 / "hidden" / "handoff_truth.json", d / "handoff_truth.json")
        shutil.copy2(T6 / "hidden" / "grade_workflow.py", d / "grade_workflow.py")
        (d / "coverage.txt").write_text("intended_clock_present 1\nconstrained_paths 1\n")
        setup(d)
        p = subprocess.run(["python3", "grade_workflow.py", "handoff_truth.json"],
                           cwd=d, capture_output=True, text=True, timeout=60)
        return p.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_0006_exists_and_schema_valid():
    assert T6.is_dir()
    m = _meta(T6)
    validate_metadata(m)
    assert m["track"] == "p14_workflow_handoff"
    assert m["generator"]["params"]["hazard_type"] == "constraint_graph_multi_source_recovery"
    structural_validate(T6)


def test_0006_constraint_graph_metadata_present():
    truth = json.loads((T6 / "hidden" / "handoff_truth.json").read_text())
    assert truth["hazard_type"] == "constraint_graph_multi_source_recovery"
    cg = truth["constraint_graph"]
    assert set(cg["axes"]) == {"netlist", "clock", "scenario", "corner"}
    assert len(cg["constraints"]) == 3   # C1 netlist-family, C2 clock-coverage, C3 scenario/corner pair
    assert cg["expected_unique_assignment"] == {"netlist": "netlist_v2.v", "clock": "clk_main",
                                                "scenario": "slow", "corner": "func"}
    assert set(cg["decoy_violates"]) == {"report_A_scenario_corner.rpt",
                                         "report_B_stale_netlist.rpt", "report_C_wrong_clock.rpt",
                                         "evidence_D_manifest.json"}


def test_0006_uniqueness_exactly_one_assignment():
    """The make-or-break gate: exactly one assignment satisfies all constraints AND equals expected."""
    truth = json.loads((T6 / "hidden" / "handoff_truth.json").read_text())
    u = truth["constraint_graph"]["uniqueness"]
    assert u["exactly_one"] is True
    assert u["unique_matches_expected"] is True
    assert u["satisfying_count"] == 1
    assert u["satisfying_assignments"][0] == {"netlist": "netlist_v2.v", "clock": "clk_main",
                                              "scenario": "slow", "corner": "func"}
    # re-derive independently from the constraint graph (no cached value trusted)
    from generators.p14_workflow_handoff_gen import enumerate_constraint_graph
    fresh = enumerate_constraint_graph(truth["constraint_graph"])
    assert fresh["exactly_one"] and fresh["satisfying_count"] == 1


def test_0006_no_visible_file_states_full_tuple():
    """NO single visible file reveals the full target tuple (the v5 design principle)."""
    bad_patterns = [r"netlist_v2\.v.*clk_main.*slow.*func", r"slow.*func.*netlist_v2\.v.*clk_main",
                    r"scenario.*slow.*corner.*func.*netlist_v2"]
    for rel in ("spec.md", "handoff_manifest.json", "prompt.md"):
        f = T6 / rel
        if not f.exists():
            f = T6.parent / rel if rel == "prompt.md" else T6 / "files" / rel
        txt = f.read_text()
        for pat in bad_patterns:
            assert not re.search(pat, txt, re.DOTALL), f"{rel} leaks the full tuple: {pat}"
    # manifest must be PARTIAL authority (no concrete scenario/corner/clock)
    man = json.loads((T6 / "files" / "handoff_manifest.json").read_text())
    for k in ("scenario", "corner", "clock"):
        assert k not in man, f"manifest must not state concrete {k} (partial authority)"
    assert "netlist_family" in man


def test_0006_decoy_files_present_and_forbidden():
    m = _meta(T6)
    for f in ("report_A_scenario_corner.rpt", "report_B_stale_netlist.rpt",
              "report_C_wrong_clock.rpt", "evidence_D_manifest.json", "prev_signoff.log"):
        assert f in m["files"]["visible"], f
        assert f in m["files"]["forbidden"], f


def test_0006_full_global_recovery_emits_markers():
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk_main")
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "slow", "func", "clk_main")
    out = _grade_run_cg(setup)
    assert "EVIDENCE_OK" in out
    assert "GLOBAL_CONSTRAINT_OK" in out
    assert "UNIQUE_ASSIGNMENT_OK" in out
    assert "EVIDENCE_CHAIN_SEMANTIC_OK" in out
    assert "GLOBAL_AUTHORITY_OK" in out and "MULTI_CONFLICT_OK" in out
    assert "PAIRWISE_DECOY_REJECTED" not in out


def test_0006_report_A_only_fails():
    # report_A: right netlist/clock (v2/clk_main), WRONG scenario/corner -> violates C3
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "test", "typ", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "test", "typ", "clk_main")
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "test", "typ", "clk_main")
    out = _grade_run_cg(setup)
    assert "EVIDENCE_OK" not in out and "GLOBAL_CONSTRAINT_OK" not in out
    assert "PAIRWISE_DECOY_REJECTED" in out


def test_0006_report_B_only_fails():
    # report_B: right scenario/corner (slow/func), STALE netlist (v1) -> violates C1
    def setup(d):
        _mc_inputs(d, "netlist_v1.v", "slow", "func", "clk_main")
        m = _mc_stage1(d, "netlist_v1.v", "slow", "func", "clk_main")
        _mc_stage2(d, m["report_digest"], "netlist_v1.v", "slow", "func", "clk_main")
    out = _grade_run_cg(setup)
    assert "EVIDENCE_OK" not in out and "GLOBAL_CONSTRAINT_OK" not in out


def test_0006_report_C_only_fails():
    # report_C: right netlist/scenario (v2/slow), WRONG clock (clk_old) -> violates C2
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_old")
        m = _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk_old")
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "slow", "func", "clk_old")
    out = _grade_run_cg(setup)
    assert "EVIDENCE_OK" not in out and "GLOBAL_CONSTRAINT_OK" not in out


def test_0006_evidence_D_only_fails():
    # evidence_D: valid-looking chain on invalidated prerequisite (stale v1) -> violates C1/C6
    def setup(d):
        _mc_inputs(d, "netlist_v1.v", "slow", "func", "clk_main")
        m = _mc_stage1(d, "netlist_v1.v", "slow", "func", "clk_main")
        _mc_stage2(d, m["report_digest"], "netlist_v1.v", "slow", "func", "clk_main")
    out = _grade_run_cg(setup)
    assert "EVIDENCE_OK" not in out and "GLOBAL_CONSTRAINT_OK" not in out


def test_0006_single_axis_repairs_fail():
    # repair only scenario (netlist still stale v1) -> still violates C1
    def setup(d):
        _mc_inputs(d, "netlist_v1.v", "slow", "func", "clk_main")
        m = _mc_stage1(d, "netlist_v1.v", "slow", "func", "clk_main")
        _mc_stage2(d, m["report_digest"], "netlist_v1.v", "slow", "func", "clk_main")
    out = _grade_run_cg(setup)
    assert "EVIDENCE_OK" not in out


def test_0006_stage2_only_rerun_fails():
    # final-state correct but stage2 bound to a stale stage1 (broken chain) -> violates C5/C6
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk_main")
        _mc_stage2(d, "deadbeefdeadbeef", "netlist_v2.v", "slow", "func", "clk_main")  # stale upstream
    out = _grade_run_cg(setup)
    assert "STAGE_CHAIN_OK" not in out and "EVIDENCE_OK" not in out


def test_0006_final_state_only_fails():
    # correct flow_config but NO regenerated evidence -> EVIDENCE fails (no re-derivation)
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_main")
        # no timing_report / evidence_manifest / stage2 produced
    out = _grade_run_cg(setup)
    assert "EVIDENCE_OK" not in out and "GLOBAL_CONSTRAINT_OK" not in out


def test_0006_hand_edited_evidence_fails():
    # correct package but hand-forged report_digest (does not match report body) -> provenance fails
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk_main")
        sub = json.loads((d / "evidence_manifest.json").read_text())
        sub["report_digest"] = "f" * 64   # the LIE: digest does not match the report body
        (d / "evidence_manifest.json").write_text(json.dumps(sub, indent=2, sort_keys=True))
    out = _grade_run_cg(setup)
    assert "EVIDENCE_OK" not in out


def test_0006_deterministic_generation(tmp_path):
    a = tmp_path / "a"; b = tmp_path / "b"
    try:
        build_task_skeleton(a, "workflow_handoff_0006", 0, 2, "constraint_graph_multi_source_recovery")
        build_task_skeleton(b, "workflow_handoff_0006", 0, 2, "constraint_graph_multi_source_recovery")
        fa = [p.relative_to(a / "workflow_handoff_0006") for p in (a / "workflow_handoff_0006").rglob("*") if p.is_file()]
        fb = [p.relative_to(b / "workflow_handoff_0006") for p in (b / "workflow_handoff_0006").rglob("*") if p.is_file()]
        assert {str(p) for p in fa} == {str(p) for p in fb}
        for rel in fa:
            assert (a / "workflow_handoff_0006" / rel).read_bytes() == (b / "workflow_handoff_0006" / rel).read_bytes(), rel
    finally:
        shutil.rmtree(a, ignore_errors=True); shutil.rmtree(b, ignore_errors=True)


def test_0006_no_hidden_leak():
    files = {p.name for p in (T6 / "files").iterdir()}
    assert "handoff_truth.json" not in files and "grade_workflow.py" not in files
    assert "netlist_v1.v" in files and "netlist_v2.v" in files  # netlists visible (forbidden to edit)


def test_0006_public_verdict_first():
    # the public runner must exist and not embed the hidden verdict / truth
    rp = (T6 / "files" / "run_public.sh").read_text()
    assert "handoff_truth.json" not in rp and "grade_workflow.py" not in rp


# ===========================================================================
# p14 v6 -- workflow_handoff_0007 (axis-binding / value-invention stress)
# ===========================================================================
T7 = TASKS_DIR / "workflow_handoff_0007"


def _grade_run_ab(setup) -> str:
    """Run grade_workflow.py for the 0007 axis-binding task."""
    d = Path(tempfile.mkdtemp(prefix="p14ab_"))
    try:
        for f in ("netlist_v1.v", "netlist_v2.v", "handoff_manifest.json", "axis_schema.json"):
            shutil.copy2(T7 / "files" / f, d / f)
        shutil.copy2(T7 / "hidden" / "handoff_truth.json", d / "handoff_truth.json")
        shutil.copy2(T7 / "hidden" / "grade_workflow.py", d / "grade_workflow.py")
        (d / "coverage.txt").write_text("intended_clock_present 1\nconstrained_paths 1\n")
        setup(d)
        p = subprocess.run(["python3", "grade_workflow.py", "handoff_truth.json"],
                           cwd=d, capture_output=True, text=True, timeout=60)
        return p.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_0007_exists_and_schema_valid():
    assert T7.is_dir()
    m = _meta(T7)
    validate_metadata(m)
    assert m["track"] == "p14_workflow_handoff"
    assert m["generator"]["params"]["hazard_type"] == "axis_binding_value_invention"
    assert abs(sum(m["scoring"]["weights"].values()) - 1.0) < 1e-9
    structural_validate(T7)


def test_0007_axis_schema_metadata_present():
    truth = json.loads((T7 / "hidden" / "handoff_truth.json").read_text())
    assert truth["hazard_type"] == "axis_binding_value_invention"
    assert truth["expected_scenario"] == "slow" and truth["expected_corner"] == "func"
    assert truth["stale_scenario"] == "func" and truth["stale_corner"] == "typ"   # the value-swap
    assert truth["global_authority_tuple"] == ["netlist_v2.v", "clk_main", "slow", "func"]
    ax = truth["axis_schema"]
    assert set(ax["typed_axes"]) == {"netlist_axis", "clock_axis", "scenario_axis",
                                     "corner_axis", "pvt_label_axis"}
    assert ax["typed_axes"]["scenario_axis"] == ["slow", "typ", "fast"]
    assert ax["typed_axes"]["corner_axis"] == ["func", "test", "lowpower"]
    assert ax["pvt_label_mapping"]["slow_1.0V_125C"] == ["slow", "func"]
    assert len(ax["constraints"]) == 5   # C1 family, C2 clock identity, C3 scenario-typed, C4 corner-typed, C5 pair
    assert ax["expected_unique_assignment"] == {"netlist": "netlist_v2.v", "clock": "clk_main",
                                                "scenario": "slow", "corner": "func"}
    assert set(ax["decoy_violates"]) == {"report_A_value_swap.rpt", "report_B_pvt_corner.rpt",
                                         "report_C_wrong_clock.rpt", "evidence_D_typed_mismatch.json"}


def test_0007_uniqueness_exactly_one_typed_assignment():
    """THE make-or-break gate #1: exactly one typed assignment satisfies all constraints AND equals expected."""
    truth = json.loads((T7 / "hidden" / "handoff_truth.json").read_text())
    u = truth["axis_schema"]["uniqueness"]
    assert u["exactly_one"] is True
    assert u["unique_matches_expected"] is True
    assert u["satisfying_count"] == 1
    assert u["satisfying_assignments"][0] == {"netlist": "netlist_v2.v", "clock": "clk_main",
                                              "scenario": "slow", "corner": "func"}
    from generators.p14_workflow_handoff_gen import enumerate_constraint_graph
    fresh = enumerate_constraint_graph(truth["axis_schema"])
    assert fresh["exactly_one"] and fresh["satisfying_count"] == 1


def test_0007_typed_binding_failures_machine_provable():
    """swapped-axis / PVT-substitution / wrong-clock-alias assignments all violate >=1 typed constraint."""
    truth = json.loads((T7 / "hidden" / "handoff_truth.json").read_text())
    ax = truth["axis_schema"]

    def satisfies(assign):
        for c in ax["constraints"]:
            if tuple(assign[o] for o in c["over"]) not in {tuple(x) for x in c["allowed"]}:
                return False
        return True
    # the value-swap (DeepSeek k=3 failure): corner value 'func' in scenario slot, scenario value 'typ' in corner
    assert not satisfies({"netlist": "netlist_v2.v", "clock": "clk_main",
                          "scenario": "func", "corner": "typ"})
    # PVT-label-as-corner (DeepSeek k=5 failure family)
    assert not satisfies({"netlist": "netlist_v2.v", "clock": "clk_main",
                          "scenario": "slow", "corner": "slow_1.0V_125C"})
    # wrong clock alias
    assert not satisfies({"netlist": "netlist_v2.v", "clock": "clk",
                          "scenario": "slow", "corner": "func"})
    # the unique typed assignment DOES satisfy
    assert satisfies({"netlist": "netlist_v2.v", "clock": "clk_main",
                      "scenario": "slow", "corner": "func"})


def test_0007_axis_schema_json_visible_and_publishes_vocab_only():
    """axis_schema.json is VISIBLE (binding challenge, not vocabulary hiding) but states no expected answer."""
    m = _meta(T7)
    assert "axis_schema.json" in m["files"]["visible"]
    assert "axis_schema.json" in m["files"]["forbidden"]
    ax = json.loads((T7 / "files" / "axis_schema.json").read_text())
    for k in ("scenario_axis", "corner_axis", "clock_axis", "pvt_label_axis", "pvt_label_mapping"):
        assert k in ax
    # publishes the VOCABULARY (members appear as axis values), but must NOT flag which member is correct
    for key in ax:
        assert not key.startswith("expected"), key
        assert key not in ("answer", "correct_assignment", "unique_assignment"), key


def test_0007_no_visible_file_states_full_tuple():
    """NO single visible file reveals the answer tuple. Vocabulary members are PUBLISHED by design in
    axis_schema.json (each in its own axis list); what is forbidden is flagging the four answer values as a
    contiguous assignment, or stating concrete scenario/corner/clock in the partial-authority manifest."""
    # the partial-authority manifest must not state concrete scenario/corner/clock
    man = json.loads((T7 / "files" / "handoff_manifest.json").read_text())
    for k in ("scenario", "corner", "clock"):
        assert k not in man, f"manifest must not state concrete {k} (partial authority)"
    # the answer as a CONTIGUOUS assignment phrase must not appear anywhere visible (no re.DOTALL: this
    # requires the values on one line as a tuple, not scattered as vocabulary members across axes)
    contiguous = [r"netlist_v2\.v\b.{0,40}\bclk_main\b.{0,40}\bslow\b.{0,40}\bfunc\b",
                  r"\bslow\s*/\s*func\b", r"signoff.{0,30}\bslow\b"]
    for rel in ("spec.md", "handoff_manifest.json", "axis_schema.json", "prompt.md"):
        f = T7 / rel
        if not f.exists():
            f = T7.parent / rel if rel == "prompt.md" else T7 / "files" / rel
        txt = f.read_text()
        for pat in contiguous:
            assert not re.search(pat, txt), f"{rel} leaks the answer tuple: {pat}"


def test_0007_decoy_files_present_and_forbidden():
    m = _meta(T7)
    for f in ("axis_schema.json", "report_A_value_swap.rpt", "report_B_pvt_corner.rpt",
              "report_C_wrong_clock.rpt", "evidence_D_typed_mismatch.json", "prev_signoff.log"):
        assert f in m["files"]["visible"], f
        assert f in m["files"]["forbidden"], f


def test_0007_mutant_ships_value_swap():
    fc = json.loads((T7 / "files" / "flow_config.json").read_text())
    # the mutant is the value-swap: a corner value in the scenario slot, a scenario value in the corner slot
    assert fc["scenario"] == "func" and fc["corner"] == "typ"   # both mis-slotted
    assert fc["netlist"] == "netlist_v1.v"                       # stale netlist too


def test_0007_full_typed_recovery_emits_markers():
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk_main")
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "slow", "func", "clk_main")
    out = _grade_run_ab(setup)
    assert "EVIDENCE_OK" in out
    assert "AXIS_SCHEMA_OK" in out and "TYPED_BINDING_OK" in out and "PVT_LABEL_OK" in out
    assert "GLOBAL_CONSTRAINT_OK" in out and "UNIQUE_ASSIGNMENT_OK" in out
    assert "EVIDENCE_CHAIN_TYPED_OK" in out
    assert "HAZARD_RECOVERY_OK" in out
    assert "MISTYPED_BINDING_REJECTED" not in out


def test_0007_value_swap_signoff_green_fails():
    """THE make-or-break gate #2: a signoff-green-but-mis-typed package is floored below pass.

    Correct netlist+clock+fresh chain (PrimeTime signs off green) but scenario/corner are SWAPPED
    (the exact DeepSeek k=3 failure). Typed binding, not signoff, must reject it."""
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "func", "typ", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "func", "typ", "clk_main")    # signoff OK in the manifest
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "func", "typ", "clk_main")
    out = _grade_run_ab(setup)
    assert "EVIDENCE_OK" not in out and "TYPED_BINDING_OK" not in out and "AXIS_SCHEMA_OK" not in out
    assert "GLOBAL_CONSTRAINT_OK" not in out
    assert "MISTYPED_BINDING_REJECTED" in out


def test_0007_pvt_label_as_corner_fails():
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "slow_1.0V_125C", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "slow", "slow_1.0V_125C", "clk_main")
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "slow", "slow_1.0V_125C", "clk_main")
    out = _grade_run_ab(setup)
    assert "EVIDENCE_OK" not in out and "TYPED_BINDING_OK" not in out
    assert "MISTYPED_BINDING_REJECTED" in out


def test_0007_wrong_clock_alias_fails():
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk")
        m = _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk")
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "slow", "func", "clk")
    out = _grade_run_ab(setup)
    assert "EVIDENCE_OK" not in out and "TYPED_BINDING_OK" not in out
    assert "MISTYPED_BINDING_REJECTED" in out


def test_0007_report_A_only_fails():    # right netlist/clock, scenario/corner swapped -> C3+C4
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "func", "typ", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "func", "typ", "clk_main")
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "func", "typ", "clk_main")
    out = _grade_run_ab(setup)
    assert "EVIDENCE_OK" not in out and "GLOBAL_CONSTRAINT_OK" not in out


def test_0007_report_B_only_fails():    # PVT label as corner -> C4
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "slow_1.0V_125C", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "slow", "slow_1.0V_125C", "clk_main")
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "slow", "slow_1.0V_125C", "clk_main")
    out = _grade_run_ab(setup)
    assert "EVIDENCE_OK" not in out and "GLOBAL_CONSTRAINT_OK" not in out


def test_0007_report_C_only_fails():    # generic clock alias 'clk' -> C2
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk")
        m = _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk")
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "slow", "func", "clk")
    out = _grade_run_ab(setup)
    assert "EVIDENCE_OK" not in out and "GLOBAL_CONSTRAINT_OK" not in out


def test_0007_evidence_D_only_fails():  # typed-field mismatch -> C3+C4
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "func", "typ", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "func", "typ", "clk_main")
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "func", "typ", "clk_main")
    out = _grade_run_ab(setup)
    assert "EVIDENCE_OK" not in out and "GLOBAL_CONSTRAINT_OK" not in out


def test_0007_stage2_only_rerun_fails():   # broken chain (stale upstream) -> C6/C7
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk_main")
        _mc_stage2(d, "deadbeefdeadbeef", "netlist_v2.v", "slow", "func", "clk_main")
    out = _grade_run_ab(setup)
    assert "STAGE_CHAIN_OK" not in out and "EVIDENCE_OK" not in out


def test_0007_final_state_only_fails():    # correct flow_config, NO regenerated evidence
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_main")
    out = _grade_run_ab(setup)
    assert "EVIDENCE_OK" not in out and "GLOBAL_CONSTRAINT_OK" not in out


def test_0007_hand_edited_evidence_fails():   # forged report_digest -> provenance fails
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_main")
        _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk_main")
        sub = json.loads((d / "evidence_manifest.json").read_text())
        sub["report_digest"] = "f" * 64
        (d / "evidence_manifest.json").write_text(json.dumps(sub, indent=2, sort_keys=True))
    out = _grade_run_ab(setup)
    assert "EVIDENCE_OK" not in out


def test_0007_deterministic_generation(tmp_path):
    a = tmp_path / "a"; b = tmp_path / "b"
    try:
        build_task_skeleton(a, "workflow_handoff_0007", 0, 2, "axis_binding_value_invention")
        build_task_skeleton(b, "workflow_handoff_0007", 0, 2, "axis_binding_value_invention")
        fa = [p.relative_to(a / "workflow_handoff_0007") for p in (a / "workflow_handoff_0007").rglob("*") if p.is_file()]
        fb = [p.relative_to(b / "workflow_handoff_0007") for p in (b / "workflow_handoff_0007").rglob("*") if p.is_file()]
        assert {str(p) for p in fa} == {str(p) for p in fb}
        for rel in fa:
            assert (a / "workflow_handoff_0007" / rel).read_bytes() == (b / "workflow_handoff_0007" / rel).read_bytes(), rel
    finally:
        shutil.rmtree(a, ignore_errors=True); shutil.rmtree(b, ignore_errors=True)


def test_0007_no_hidden_leak():
    files = {p.name for p in (T7 / "files").iterdir()}
    assert "handoff_truth.json" not in files and "grade_workflow.py" not in files
    assert "netlist_v1.v" in files and "netlist_v2.v" in files
    assert "axis_schema.json" in files   # vocabulary PUBLISHED


def test_0007_public_verdict_first():
    rp = (T7 / "files" / "run_public.sh").read_text()
    assert "handoff_truth.json" not in rp and "grade_workflow.py" not in rp


# ===========================================================================
# p14 v7 -- workflow_handoff_0008 (implicit typed-axis binding) -- PHASE-4Q GATE
# Goal: prove inferable (domain-aware solver recovers the tuple from visible
# only) + not leaked (no single visible file gives the tuple/membership table) +
# unambiguous (hidden enumeration exactly one).
# ===========================================================================
T8 = TASKS_DIR / "workflow_handoff_0008"


def test_0008_exists_and_schema_valid():
    assert T8.is_dir()
    m = _meta(T8)
    validate_metadata(m)
    assert m["track"] == "p14_workflow_handoff"
    assert m["generator"]["params"]["hazard_type"] == "implicit_axis_binding"
    assert abs(sum(m["scoring"]["weights"].values()) - 1.0) < 1e-9
    structural_validate(T8)


def test_0008_no_axis_schema_shipped():
    """THE 0007 collapse mode must NOT recur: no axis_schema.json is visible."""
    files = {p.name for p in (T8 / "files").iterdir()}
    assert "axis_schema.json" not in files, "0008 must NOT publish axis_schema.json (would saturate like 0007)"
    m = _meta(T8)
    assert "axis_schema.json" not in m["files"]["visible"]
    # the implicit-context decoys + glossary + public summary ARE visible
    for f in ("report_A_context_swap.rpt", "report_B_context_stale.rpt",
              "report_C_context_pvt.rpt", "evidence_D_context_mismatch.json",
              "public_check_summary.json", "glossary.md"):
        assert f in m["files"]["visible"], f
        assert f in m["files"]["forbidden"], f


def test_0008_glossary_is_not_a_complete_schema():
    """glossary.md + spec.md + public_check_summary may give EXAMPLES / partial terminology, but must NOT
    form a complete value-to-axis membership table that resolves the binding by lookup."""
    corpus = (T8 / "files" / "glossary.md").read_text() + "\n" + (T8 / "files" / "spec.md").read_text()
    # no explicit axis vocabulary lists
    assert "scenario_axis" not in corpus and "corner_axis" not in corpus
    # no complete enumeration of the scenario or corner values as a typed set
    for needle in ('"slow", "typ", "fast"', '"func", "test", "lowpower"',
                   "slow, typ, fast", "func, test, lowpower"):
        assert needle not in corpus, f"glossary/spec leaks vocabulary: {needle}"


def test_0008_uniqueness_exactly_one_typed_assignment():
    truth = json.loads((T8 / "hidden" / "handoff_truth.json").read_text())
    u = truth["axis_schema"]["uniqueness"]
    assert u["exactly_one"] is True and u["satisfying_count"] == 1
    assert u["satisfying_assignments"][0] == {"netlist": "netlist_v2.v", "clock": "clk_main",
                                              "scenario": "slow", "corner": "func"}
    from generators.p14_workflow_handoff_gen import enumerate_constraint_graph
    fresh = enumerate_constraint_graph(truth["axis_schema"])
    assert fresh["exactly_one"] and fresh["satisfying_count"] == 1


def test_0008_typed_binding_failures_machine_provable():
    """swapped-axis / PVT-substitution / wrong-clock assignments all violate >=1 typed constraint."""
    truth = json.loads((T8 / "hidden" / "handoff_truth.json").read_text())
    ax = truth["axis_schema"]

    def satisfies(assign):
        for c in ax["constraints"]:
            if tuple(assign[o] for o in c["over"]) not in {tuple(x) for x in c["allowed"]}:
                return False
        return True
    assert not satisfies({"netlist": "netlist_v2.v", "clock": "clk_main", "scenario": "func", "corner": "typ"})
    assert not satisfies({"netlist": "netlist_v2.v", "clock": "clk_main", "scenario": "slow",
                          "corner": "slow_1.0V_125C"})
    assert not satisfies({"netlist": "netlist_v2.v", "clock": "clk", "scenario": "slow", "corner": "func"})
    assert satisfies({"netlist": "netlist_v2.v", "clock": "clk_main", "scenario": "slow", "corner": "func"})


def test_0008_domain_solver_recovers_tuple_visible_only():
    """THE human-inferrability gate: a domain-aware scripted solver recovers the unique typed assignment
    using ONLY the visible artifacts (never hidden truth)."""
    import sys
    sys.path.insert(0, str(REPO / "scripts"))
    from implicit_axis_solver import solve
    # sanity: the solver must not read hidden truth -- it only takes the files/ dir
    res = solve(T8 / "files")
    assert res == {"netlist": "netlist_v2.v", "clock": "clk_main", "scenario": "slow", "corner": "func"}, res


def test_0008_no_visible_file_states_full_tuple():
    """NO single visible file reveals the canonical tuple (netlist_v2 + clk_main + slow + func) as a
    contiguous/canonical answer. The tuple is split across artifacts + requires inference."""
    import re as _re
    # canonical contiguous answer strings must be absent from every visible file
    contiguous = [r"netlist_v2\.v.{0,40}clk_main.{0,40}\bslow\b.{0,40}\bfunc\b",
                  r"\bslow\b.{0,20}\bfunc\b.{0,20}clk_main", r"scenario.*slow.*corner.*func.*clk_main"]
    for rel in ("spec.md", "handoff_manifest.json", "glossary.md", "public_check_summary.json",
                "flow_config.json", "prompt.md"):
        f = T8 / rel
        if not f.exists():
            f = T8.parent / rel if rel == "prompt.md" else T8 / "files" / rel
        txt = f.read_text()
        for pat in contiguous:
            assert not _re.search(pat, txt, _re.DOTALL), f"{rel} leaks the full tuple: {pat}"
    # the shipped flow_config is the MUTANT (wrong), not the golden tuple
    fc = json.loads((T8 / "files" / "flow_config.json").read_text())
    assert (fc["netlist"], fc["scenario"], fc["corner"]) != ("netlist_v2.v", "slow", "func"), "flow_config ships the GOLDEN tuple (mutant must be wrong)"


def test_0008_mutant_is_value_swap():
    fc = json.loads((T8 / "files" / "flow_config.json").read_text())
    # mutant: stale netlist + a corner value in the scenario slot + a scenario value in the corner slot
    assert fc["netlist"] == "netlist_v1.v"
    assert fc["scenario"] == "func" and fc["corner"] == "typ"


def test_0008_deterministic_generation(tmp_path):
    a = tmp_path / "a"; b = tmp_path / "b"
    try:
        build_task_skeleton(a, "workflow_handoff_0008", 0, 2, "implicit_axis_binding")
        build_task_skeleton(b, "workflow_handoff_0008", 0, 2, "implicit_axis_binding")
        fa = [p.relative_to(a / "workflow_handoff_0008") for p in (a / "workflow_handoff_0008").rglob("*") if p.is_file()]
        fb = [p.relative_to(b / "workflow_handoff_0008") for p in (b / "workflow_handoff_0008").rglob("*") if p.is_file()]
        assert {str(p) for p in fa} == {str(p) for p in fb}
        for rel in fa:
            assert (a / "workflow_handoff_0008" / rel).read_bytes() == (b / "workflow_handoff_0008" / rel).read_bytes(), rel
    finally:
        shutil.rmtree(a, ignore_errors=True); shutil.rmtree(b, ignore_errors=True)


def test_0008_no_hidden_leak_and_coverage_fact_present():
    files = {p.name for p in (T8 / "files").iterdir()}
    assert "handoff_truth.json" not in files and "grade_workflow.py" not in files
    # the coverage fact (clock inferability without PT) is surfaced in the public pairwise summary
    pcs = json.loads((T8 / "files" / "public_check_summary.json").read_text())
    assert pcs.get("intended_clock_coverage", {}).get("clk_main", 0) > 0
    assert pcs.get("intended_clock_coverage", {}).get("clk_old", 0) == 0


# --- Phase-4R: full build + acceptance matrix (golden baked on real PT) ---
def _grade_run_imp(setup) -> str:
    """Run grade_workflow.py for the 0008 implicit-axis task (canonical flow_config scenario/corner)."""
    d = Path(tempfile.mkdtemp(prefix="p14imp_"))
    try:
        for f in ("netlist_v1.v", "netlist_v2.v", "handoff_manifest.json"):
            shutil.copy2(T8 / "files" / f, d / f)
        shutil.copy2(T8 / "hidden" / "handoff_truth.json", d / "handoff_truth.json")
        shutil.copy2(T8 / "hidden" / "grade_workflow.py", d / "grade_workflow.py")
        (d / "coverage.txt").write_text("intended_clock_present 1\nconstrained_paths 1\n")
        setup(d)
        p = subprocess.run(["python3", "grade_workflow.py", "handoff_truth.json"],
                           cwd=d, capture_output=True, text=True, timeout=60)
        return p.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_0008_golden_baked_solution_evidence():
    """Phase-4R bake: real-PT golden evidence is present in solution/ with signoff OK + fresh chain."""
    sol = T8 / "solution"
    assert (sol / "timing_report.rpt").is_file() and (sol / "evidence_manifest.json").is_file()
    assert (sol / "stage2_summary.json").is_file() and (sol / "flow_config.json").is_file()
    m = json.loads((sol / "evidence_manifest.json").read_text())
    assert m.get("signoff") == "OK"
    assert m.get("scenario") == "slow" and m.get("corner") == "func"   # the golden typed assignment
    s2 = json.loads((sol / "stage2_summary.json").read_text())
    assert s2.get("upstream_evidence_digest") == m.get("report_digest")   # fresh ordered chain
    # report_A_context_swap baked with a real netlist_v2 body
    assert (T8 / "files" / "report_A_context_swap.rpt").stat().st_size > 500


def test_0008_grader_full_recovery_emits_markers():
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk_main")
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "slow", "func", "clk_main")
    out = _grade_run_imp(setup)
    assert "EVIDENCE_OK" in out
    assert "AXIS_SCHEMA_OK" in out and "TYPED_BINDING_OK" in out and "PVT_LABEL_OK" in out
    assert "GLOBAL_CONSTRAINT_OK" in out and "UNIQUE_ASSIGNMENT_OK" in out
    assert "HAZARD_RECOVERY_OK" in out
    assert "MISTYPED_BINDING_REJECTED" not in out


def test_0008_grader_signoff_green_value_swap_fails():
    """signoff-green-but-mis-typed (value-swap scenario=func/corner=typ) -> below pass."""
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "func", "typ", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "func", "typ", "clk_main")   # signoff OK in the manifest
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "func", "typ", "clk_main")
    out = _grade_run_imp(setup)
    assert "EVIDENCE_OK" not in out and "TYPED_BINDING_OK" not in out
    assert "MISTYPED_BINDING_REJECTED" in out


def test_0008_grader_pvt_corner_fails():
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "slow_1.0V_125C", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "slow", "slow_1.0V_125C", "clk_main")
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "slow", "slow_1.0V_125C", "clk_main")
    out = _grade_run_imp(setup)
    assert "EVIDENCE_OK" not in out and "MISTYPED_BINDING_REJECTED" in out


def test_0008_grader_wrong_clock_fails():
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk")
        m = _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk")
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "slow", "func", "clk")
    out = _grade_run_imp(setup)
    assert "EVIDENCE_OK" not in out and "MISTYPED_BINDING_REJECTED" in out


def test_0008_grader_final_state_only_fails():
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_main")
    out = _grade_run_imp(setup)
    assert "EVIDENCE_OK" not in out and "GLOBAL_CONSTRAINT_OK" not in out


def test_0008_grader_stage2_typed_wrong_fails():
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk_main")
        _mc_stage2(d, "deadbeefdeadbeef", "netlist_v2.v", "slow", "func", "clk_main")  # stale upstream
    out = _grade_run_imp(setup)
    assert "STAGE_CHAIN_OK" not in out and "EVIDENCE_OK" not in out


def test_0008_grader_hand_edited_evidence_fails():
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_main")
        _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk_main")
        sub = json.loads((d / "evidence_manifest.json").read_text())
        sub["report_digest"] = "f" * 64
        (d / "evidence_manifest.json").write_text(json.dumps(sub, indent=2, sort_keys=True))
    out = _grade_run_imp(setup)
    assert "EVIDENCE_OK" not in out


# =========================================================================== v8: 0009 / 0010
# semantic-role-binding REPRODUCTION -- the controlled pair. workflow_handoff_0009 (ambiguous) reproduces
# the 0006 difficulty; workflow_handoff_0010 (clear_control) is the negative control. Both share an
# IDENTICAL hidden truth + the byte-identical typed-binding grader; they differ ONLY in the visible clarity
# bundle (report-label semantics + inference anchors). The variant is passed explicitly (the schema requires
# numeric task_ids), so 0009/0010 encode the pair, not the variant suffix. The grader-logic tests are
# parametrized over both variants because the grader ignores `variant`.
T9 = TASKS_DIR / "workflow_handoff_0009"    # variant=ambiguous (overloaded labels, no anchors)
T10 = TASKS_DIR / "workflow_handoff_0010"   # variant=clear_control (canonical labels + anchors)
_VARIANTS = [T9, T10]


def _grade_run_srb(setup, task: Path) -> str:
    """Run grade_workflow.py for a 0009 semantic-role-binding task (canonical flow_config scenario/corner)."""
    d = Path(tempfile.mkdtemp(prefix="p14srb_"))
    try:
        for f in ("netlist_v1.v", "netlist_v2.v", "handoff_manifest.json"):
            shutil.copy2(task / "files" / f, d / f)
        shutil.copy2(task / "hidden" / "handoff_truth.json", d / "handoff_truth.json")
        shutil.copy2(task / "hidden" / "grade_workflow.py", d / "grade_workflow.py")
        (d / "coverage.txt").write_text("intended_clock_present 1\nconstrained_paths 1\n")
        setup(d)
        p = subprocess.run(["python3", "grade_workflow.py", "handoff_truth.json"],
                           cwd=d, capture_output=True, text=True, timeout=60)
        return p.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


@pytest.mark.parametrize("task", _VARIANTS, ids=["0009_ambiguous", "0010_clear"])
def test_0009_exists_and_schema_valid(task):
    assert task.is_dir()
    m = _meta(task)
    validate_metadata(m)
    assert m["track"] == "p14_workflow_handoff"
    assert m["generator"]["params"]["hazard_type"] == "semantic_role_binding_reproduction"
    assert abs(sum(m["scoring"]["weights"].values()) - 1.0) < 1e-9
    structural_validate(task)


@pytest.mark.parametrize("task,variant,mapping", [
    (T9, "ambiguous", {"op_point": "scenario", "mode": "corner"}),
    (T10, "clear_control", {"scenario": "scenario", "corner": "corner"})])
def test_0009_variant_metadata(task, variant, mapping):
    truth = json.loads((task / "hidden" / "handoff_truth.json").read_text())
    assert truth["hazard_type"] == "semantic_role_binding_reproduction"
    assert truth["variant"] == variant
    assert truth["expected_scenario"] == "slow" and truth["expected_corner"] == "func"
    assert truth["stale_scenario"] == "func" and truth["stale_corner"] == "typ"   # the value-swap mutant
    assert truth["global_authority_tuple"] == ["netlist_v2.v", "clk_main", "slow", "func"]
    assert truth["semantic_role_mapping"] == mapping
    # the swapped pair func/typ is recorded as embedded inside the genuine-looking report bodies
    assert truth["decoy_embedded_values"]["report_A_role_swap.rpt"] == {"scenario_slot": "func",
                                                                        "corner_slot": "typ"}


@pytest.mark.parametrize("task", _VARIANTS, ids=["0009", "0010"])
def test_0009_uniqueness_exactly_one_typed_assignment(task):
    """make-or-break gate #1: exactly one typed assignment satisfies all constraints AND equals expected."""
    truth = json.loads((task / "hidden" / "handoff_truth.json").read_text())
    u = truth["axis_schema"]["uniqueness"]
    assert u["total_assignments"] == 294
    assert u["exactly_one"] is True and u["unique_matches_expected"] is True and u["satisfying_count"] == 1
    assert u["satisfying_assignments"][0] == {"netlist": "netlist_v2.v", "clock": "clk_main",
                                              "scenario": "slow", "corner": "func"}
    from generators.p14_workflow_handoff_gen import enumerate_constraint_graph
    fresh = enumerate_constraint_graph(truth["axis_schema"])
    assert fresh["exactly_one"] and fresh["satisfying_count"] == 1


@pytest.mark.parametrize("task", _VARIANTS, ids=["0009", "0010"])
def test_0009_typed_binding_failures_machine_provable(task):
    """the 0006 failure family is machine-provably rejected: value-swap / PVT-corner / wrong-clock-alias."""
    truth = json.loads((task / "hidden" / "handoff_truth.json").read_text())
    ax = truth["axis_schema"]

    def satisfies(assign):
        for c in ax["constraints"]:
            if tuple(assign[o] for o in c["over"]) not in {tuple(x) for x in c["allowed"]}:
                return False
        return True
    # Failure A (DeepSeek 0006 k=3): the value-swap scenario=func/corner=typ
    assert not satisfies({"netlist": "netlist_v2.v", "clock": "clk_main",
                          "scenario": "func", "corner": "typ"})
    # Failure B (DeepSeek 0006 k=5): PVT-label-as-corner
    assert not satisfies({"netlist": "netlist_v2.v", "clock": "clk_main",
                          "scenario": "slow", "corner": "slow_1.0V_125C"})
    # wrong clock alias
    assert not satisfies({"netlist": "netlist_v2.v", "clock": "clk",
                          "scenario": "slow", "corner": "func"})
    # the unique typed assignment DOES satisfy
    assert satisfies({"netlist": "netlist_v2.v", "clock": "clk_main",
                      "scenario": "slow", "corner": "func"})


@pytest.mark.parametrize("task", _VARIANTS, ids=["0009", "0010"])
def test_0009_no_axis_schema_shipped(task):
    """neither variant publishes axis_schema.json (the typed-binding oracle stays hidden)."""
    m = _meta(task)
    assert "axis_schema.json" not in m["files"]["visible"]
    assert not (task / "files" / "axis_schema.json").exists()


def test_0009_ambiguous_labels_and_no_anchors():
    """0009: reports use OVERLOADED op_point/mode labels; NO glossary/summary anchors shipped."""
    m = _meta(T9)
    for f in ("report_A_role_swap.rpt", "report_B_role_stale.rpt", "report_C_role_pvt.rpt",
              "evidence_D_role_mismatch.json", "prev_signoff.log"):
        assert f in m["files"]["visible"] and f in m["files"]["forbidden"], f
    # the ambiguous variant ships NO glossary / NO public_check_summary
    assert "glossary.md" not in m["files"]["visible"]
    assert "public_check_summary.json" not in m["files"]["visible"]
    assert not (T9 / "files" / "glossary.md").exists()
    assert not (T9 / "files" / "public_check_summary.json").exists()
    # reports use the overloaded op_point/mode labels (the role must be INFERRED)
    a = (T9 / "files" / "report_A_role_swap.rpt").read_text()
    assert "op_point=func" in a and "mode=typ" in a   # the swapped values under overloaded labels
    b = (T9 / "files" / "report_B_role_stale.rpt").read_text()
    assert "op_point=slow" in b and "mode=func" in b  # correct role fields (on a stale netlist)


def test_0010_clear_labels_and_anchors():
    """0010: reports use CANONICAL scenario/corner labels; glossary + public_check_summary ARE shipped."""
    m = _meta(T10)
    for f in ("glossary.md", "public_check_summary.json"):
        assert f in m["files"]["visible"] and f in m["files"]["forbidden"], f
    a = (T10 / "files" / "report_A_role_swap.rpt").read_text()
    assert "scenario=func" in a and "corner=typ" in a   # canonical labels, the swap is visible
    b = (T10 / "files" / "report_B_role_stale.rpt").read_text()
    assert "scenario=slow" in b and "corner=func" in b
    # the public summary hands over the coverage fact (the inference anchor 0009 lacks)
    s = json.loads((T10 / "files" / "public_check_summary.json").read_text())
    assert s["intended_clock_coverage"] == {"clk_main": 1, "clk_old": 0, "clk": 0}


@pytest.mark.parametrize("task", _VARIANTS, ids=["0009", "0010"])
def test_0009_decoy_swap_embedded_in_report_bodies(task):
    """the 0006 body-embedding mechanism: the swapped pair func/typ appears inside genuine-looking reports."""
    blob = (task / "files" / "report_A_role_swap.rpt").read_text()
    assert "func" in blob and "typ" in blob   # the swapped values embedded in report_A's header/body
    # report_A carries the real timing body (a genuine-looking PT report) -- bake_golden refreshes it
    assert "REPORT_TIMING" in blob or (task / "files" / "report_A_role_swap.rpt").stat().st_size > 200


@pytest.mark.parametrize("task", _VARIANTS, ids=["0009", "0010"])
def test_0009_mutant_is_value_swap(task):
    fc = json.loads((task / "files" / "flow_config.json").read_text())
    assert fc["scenario"] == "func" and fc["corner"] == "typ"   # the value-swap (both mis-slotted)
    assert fc["netlist"] == "netlist_v1.v"                       # stale netlist too


@pytest.mark.parametrize("task", _VARIANTS, ids=["0009", "0010"])
def test_0009_no_visible_file_states_full_tuple(task):
    """NO single visible file states the answer as a contiguous 4-tuple assignment."""
    man = json.loads((task / "files" / "handoff_manifest.json").read_text())
    for k in ("scenario", "corner", "clock"):
        assert k not in man, f"manifest must not state concrete {k} (partial authority)"
    contiguous = [r"netlist_v2\.v\b.{0,40}\bclk_main\b.{0,40}\bslow\b.{0,40}\bfunc\b"]
    for rel in ("spec.md", "handoff_manifest.json", "prompt.md"):
        f = task / "files" / rel if rel != "prompt.md" else task.parent / (task.name + "/prompt.md")
        f = task.parent / task.name / rel if rel == "prompt.md" else task / "files" / rel
        txt = f.read_text()
        for pat in contiguous:
            assert not re.search(pat, txt), f"{rel} leaks the answer tuple: {pat}"


def test_0009_spec_has_no_partial_binding_hint():
    """0009 (ambiguous) spec gives NO binding hint: it states neither the signoff pair (slow/func) nor the
    disjoint-axis rule. (The shipped evidence_manifest.json's stale CLAIM of slow/func is the known
    untrustworthy 'lie' present in 0005-0009 alike -- it is not a spec/glossary/summary anchor, and the
    grader's forgery-resistant checks never trust it. The experiment's variable is the spec/anchor clarity,
    not the manifest claim, which is identical across a/b.)"""
    spec = (T9 / "files" / "spec.md").read_text()
    assert "slow scenario" not in spec and "functional corner" not in spec
    assert "DISJOINT typed axes" not in spec and "disjoint typed axes" not in spec
    # contrast: 0010's spec DOES state the signoff pair + the disjoint-axis rule (the clear-control hint)
    spec_b = (T10 / "files" / "spec.md").read_text()
    assert "slow scenario" in spec_b and "functional corner" in spec_b
    assert "DISJOINT typed axes" in spec_b


@pytest.mark.parametrize("task", _VARIANTS, ids=["0009", "0010"])
def test_0009_no_hidden_leak(task):
    public_blob = ""
    for p in (task / "files").iterdir():
        public_blob += p.read_text(errors="ignore")
    for needle in ("global_authority_tuple", "SEMANTIC_ROLE_BINDING_OK", "def grade(truth)",
                   "evidence_consumed_netlist_is_authority", "decoy_sources", "axis_schema"):
        assert needle not in public_blob, needle


@pytest.mark.parametrize("task,variant", [(T9, "ambiguous"), (T10, "clear_control")], ids=["0009", "0010"])
def test_0009_deterministic_generation(tmp_path, task, variant):
    a = Path(tempfile.mkdtemp(prefix="p14s1_"))
    b = Path(tempfile.mkdtemp(prefix="p14s2_"))
    try:
        build_task_skeleton(a, task.name, 0, 2, "semantic_role_binding_reproduction", variant=variant)
        build_task_skeleton(b, task.name, 0, 2, "semantic_role_binding_reproduction", variant=variant)
        fa = [p.relative_to(a / task.name) for p in (a / task.name).rglob("*") if p.is_file()]
        fb = [p.relative_to(b / task.name) for p in (b / task.name).rglob("*") if p.is_file()]
        assert {str(p) for p in fa} == {str(p) for p in fb}
        for rel in fa:
            assert (a / task.name / rel).read_bytes() == (b / task.name / rel).read_bytes(), rel
    finally:
        shutil.rmtree(a, ignore_errors=True); shutil.rmtree(b, ignore_errors=True)


def test_0009_0010_share_axis_schema_and_grader():
    """the controlled pair: a and b share the IDENTICAL axis_schema/uniqueness/grader (only variant
    metadata differs) -- so the oracle measures the SAME capability; only presentation difficulty differs."""
    ta = json.loads((T9 / "hidden" / "handoff_truth.json").read_text())
    tb = json.loads((T10 / "hidden" / "handoff_truth.json").read_text())
    assert ta["axis_schema"]["axes"] == tb["axis_schema"]["axes"]
    assert ta["axis_schema"]["constraints"] == tb["axis_schema"]["constraints"]
    assert ta["axis_schema"]["expected_unique_assignment"] == tb["axis_schema"]["expected_unique_assignment"]
    assert ta["axis_schema"]["uniqueness"] == tb["axis_schema"]["uniqueness"]
    assert ta["global_authority_tuple"] == tb["global_authority_tuple"]
    assert (T9 / "hidden" / "grade_workflow.py").read_bytes() == \
           (T10 / "hidden" / "grade_workflow.py").read_bytes()


# ---- grader-logic (run grade_workflow.py on crafted submissions; parametrized over both variants) ----
@pytest.mark.parametrize("task", _VARIANTS, ids=["0009", "0010"])
def test_0009_grader_full_recovery_emits_markers(task):
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk_main")
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "slow", "func", "clk_main")
    out = _grade_run_srb(setup, task)
    assert "EVIDENCE_OK" in out
    assert "AXIS_SCHEMA_OK" in out and "TYPED_BINDING_OK" in out and "PVT_LABEL_OK" in out
    assert "GLOBAL_CONSTRAINT_OK" in out and "UNIQUE_ASSIGNMENT_OK" in out
    assert "HAZARD_RECOVERY_OK" in out
    assert "MISTYPED_BINDING_REJECTED" not in out


@pytest.mark.parametrize("task", _VARIANTS, ids=["0009", "0010"])
def test_0009_grader_signoff_green_value_swap_fails(task):
    """make-or-break gate #2: a signoff-green-but-mis-typed package (the exact 0006 failure A) is floored
    below pass. Correct netlist+clock+fresh chain (PT signs off green) but scenario=func/corner=typ swapped.
    Semantic-role binding, not signoff, must reject it -- for BOTH variants (the oracle is identical)."""
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "func", "typ", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "func", "typ", "clk_main")   # signoff OK in the manifest
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "func", "typ", "clk_main")
    out = _grade_run_srb(setup, task)
    assert "EVIDENCE_OK" not in out and "TYPED_BINDING_OK" not in out and "AXIS_SCHEMA_OK" not in out
    assert "GLOBAL_CONSTRAINT_OK" not in out
    assert "MISTYPED_BINDING_REJECTED" in out


@pytest.mark.parametrize("task", _VARIANTS, ids=["0009", "0010"])
def test_0009_grader_pvt_corner_fails(task):
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "slow_1.0V_125C", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "slow", "slow_1.0V_125C", "clk_main")
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "slow", "slow_1.0V_125C", "clk_main")
    out = _grade_run_srb(setup, task)
    assert "EVIDENCE_OK" not in out and "MISTYPED_BINDING_REJECTED" in out


@pytest.mark.parametrize("task", _VARIANTS, ids=["0009", "0010"])
def test_0009_grader_wrong_clock_fails(task):
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk")
        m = _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk")
        _mc_stage2(d, m["report_digest"], "netlist_v2.v", "slow", "func", "clk")
    out = _grade_run_srb(setup, task)
    assert "EVIDENCE_OK" not in out and "MISTYPED_BINDING_REJECTED" in out


@pytest.mark.parametrize("task", _VARIANTS, ids=["0009", "0010"])
def test_0009_grader_final_state_only_fails(task):
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_main")   # correct flow_config, NO regenerated evidence
    out = _grade_run_srb(setup, task)
    assert "EVIDENCE_OK" not in out and "GLOBAL_CONSTRAINT_OK" not in out


@pytest.mark.parametrize("task", _VARIANTS, ids=["0009", "0010"])
def test_0009_grader_stage2_typed_wrong_fails(task):
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_main")
        m = _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk_main")
        _mc_stage2(d, "deadbeefdeadbeef", "netlist_v2.v", "slow", "func", "clk_main")  # stale upstream
    out = _grade_run_srb(setup, task)
    assert "STAGE_CHAIN_OK" not in out and "EVIDENCE_OK" not in out


@pytest.mark.parametrize("task", _VARIANTS, ids=["0009", "0010"])
def test_0009_grader_hand_edited_evidence_fails(task):
    def setup(d):
        _mc_inputs(d, "netlist_v2.v", "slow", "func", "clk_main")
        _mc_stage1(d, "netlist_v2.v", "slow", "func", "clk_main")
        sub = json.loads((d / "evidence_manifest.json").read_text())
        sub["report_digest"] = "f" * 64
        (d / "evidence_manifest.json").write_text(json.dumps(sub, indent=2, sort_keys=True))
    out = _grade_run_srb(setup, task)
    assert "EVIDENCE_OK" not in out
