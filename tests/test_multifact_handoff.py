"""p12 multi-artifact FlowHandoff escalation (mf_handoff_0001) task + evaluator contract tests.

Tool-free. Proves the hand-authored stale-package-triangle task is fair, oracle-checkable,
leak-free, graded through BOTH dispatch sites (the Phase-0D parity lesson), and -- the defining
property -- that NO single-file edit reaches the pass gate (the escalation's coupling filter).

Two grading surfaces are exercised without PrimeTime:
  * the data-only axes (ARTIFACT_CONSISTENCY, PROVENANCE) are produced by running the real hidden
    grade_handoff.py on each repair state (it hashes the consumed netlist on disk, reads as data);
  * SIGNOFF + the SCENARIO_CLOCK coverage facts (intended_clock_present / constrained_paths) are
    PrimeTime-derived in the live oracle, so here they are SYNTHESIZED from the known physics of the
    package (a netlist signs off with >=1 constrained path IFF the consumed netlist's clock port and
    the SDC-bound clock name agree). The b04 gate validates the same states on real PrimeTime.

The single-edit-fails matrix is the central test: golden, mutant, each of the 3 single edits, each
of the 3 pairwise edits, the full coordinated repair, PT-green-on-stale-island, and masking.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
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
from eda_agentbench.evaluator.multifact_handoff import MultiFactHandoffEvaluator
from eda_agentbench.schema import validate_metadata
from eda_agentbench.task.loader import structural_validate

REPO = Path(__file__).resolve().parent.parent
TASK = REPO / "tasks" / "p12_multifact_handoff" / "mf_handoff_0001"

V2 = "netlist_v2.v"
V1 = "netlist_v1.v"
CLK_MAIN = "clk_main"
CLK_OLD = "clk_old"


def _meta() -> dict:
    return json.loads((TASK / "metadata.json").read_text())


def _sha(name: str) -> str:
    return hashlib.sha256((TASK / "files" / name).read_bytes()).hexdigest()


# ------------------------------------------------------------------ package state builders

def _flow_config(netlist: str) -> str:
    base = json.loads((TASK / "files" / "flow_config.json").read_text())
    base["netlist"] = netlist
    return json.dumps(base)


def _sdc(clock: str) -> str:
    """An SDC binding the given clock name to the matching port (mirrors files/solution sdc)."""
    if clock == CLK_MAIN:
        return (TASK / "solution" / "constraints.sdc").read_text()
    return (TASK / "files" / "constraints.sdc").read_text()


def _provenance(rev: str) -> str:
    """Provenance pointer for v1 (stale) or v2 (reconciled)."""
    return (TASK / "solution" / "provenance.json").read_text() if rev == "v2" \
        else (TASK / "files" / "provenance.json").read_text()


def _coverage_facts(consumed_netlist: str, sdc_clock: str) -> tuple[int, int, bool]:
    """Synthesize the PrimeTime coverage facts for a (consumed netlist, SDC clock) pair.

    Physics of the package: v2 has port clk_main, v1 has port clk_old. A clock binds (and
    constrains the sequential paths) IFF the SDC clock name == the consumed netlist's clock port.
    intended clock is clk_main. Returns (intended_clock_present, constrained_paths, signoff_ok).
    """
    net_clk = CLK_MAIN if consumed_netlist == V2 else CLK_OLD
    bound = (sdc_clock == net_clk)  # the SDC port exists on the consumed netlist
    constrained_paths = 1 if bound else 0
    intended_present = 1 if (sdc_clock == CLK_MAIN and bound) else 0
    signoff_ok = bound  # golden timing is met (slack 0.13) whenever paths are constrained
    return intended_present, constrained_paths, signoff_ok


def _run_oracle_data_axes(flow_text: str, prov_text: str, applied_sdc_clock: str,
                          coverage: tuple[int, int]) -> str:
    """Run the REAL hidden grade_handoff.py on a repair state (data axes; no PT).

    applied_sdc_clock is what write_sdc would have laundered (the create_clock -name). coverage is
    the (intended_clock_present, constrained_paths) the live run_hidden.tcl would record.
    """
    d = Path(tempfile.mkdtemp(prefix="mf_grade_"))
    try:
        for f in (V1, V2, "handoff_manifest.json"):
            shutil.copy2(TASK / "files" / f, d / f)
        shutil.copy2(TASK / "hidden" / "handoff_truth.json", d / "handoff_truth.json")
        shutil.copy2(TASK / "hidden" / "grade_handoff.py", d / "grade_handoff.py")
        (d / "flow_config.json").write_text(flow_text)
        (d / "provenance.json").write_text(prov_text)
        # applied_hidden.sdc as write_sdc would canonicalize it: a create_clock with -name
        (d / "applied_hidden.sdc").write_text(
            f"create_clock -name {applied_sdc_clock} -period 3.0 [get_ports {applied_sdc_clock}]\n")
        present, paths = coverage
        (d / "coverage.txt").write_text(
            f"intended_clock_present {present}\nconstrained_paths {paths}\n"
            f"consumed_netlist {json.loads(flow_text)['netlist']}\n")
        p = subprocess.run(
            ["python3", "grade_handoff.py", "applied_hidden.sdc", "handoff_truth.json",
             "handoff_manifest.json", "coverage.txt", "flow_config.json", "provenance.json"],
            cwd=d, capture_output=True, text=True, timeout=60)
        return p.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _full_log(consumed_netlist: str, sdc_clock: str, prov_rev: str,
              extra_sdc: str = "") -> str:
    """Build the full hidden-grader marker log for a repair state, exactly as run_hidden.sh would
    concatenate it: SIGNOFF marker + grade_handoff.py data-axis markers."""
    present, paths, signoff_ok = _coverage_facts(consumed_netlist, sdc_clock)
    flow_text = _flow_config(consumed_netlist)
    prov_text = _provenance(prov_rev)
    # masking: if extra_sdc weakens timing, the laundered SDC carries it; emit a masking-flagged run
    applied_clock = sdc_clock
    data = _run_oracle_data_axes(flow_text, prov_text, applied_clock, (present, paths))
    if extra_sdc.strip():
        # rerun the data grader with the weakening line present so masking is detected
        data = _run_oracle_with_raw_sdc(flow_text, prov_text, applied_clock, (present, paths), extra_sdc)
    sign = (f"SIGNOFF_OK worst_slack=0.13" if signoff_ok
            else "SIGNOFF_FAIL worst_slack=NONE no_paths")
    return sign + "\n" + data


def _run_oracle_with_raw_sdc(flow_text, prov_text, applied_clock, coverage, extra) -> str:
    d = Path(tempfile.mkdtemp(prefix="mf_grade_"))
    try:
        for f in (V1, V2, "handoff_manifest.json"):
            shutil.copy2(TASK / "files" / f, d / f)
        shutil.copy2(TASK / "hidden" / "handoff_truth.json", d / "handoff_truth.json")
        shutil.copy2(TASK / "hidden" / "grade_handoff.py", d / "grade_handoff.py")
        (d / "flow_config.json").write_text(flow_text)
        (d / "provenance.json").write_text(prov_text)
        (d / "applied_hidden.sdc").write_text(
            f"create_clock -name {applied_clock} -period 3.0 [get_ports {applied_clock}]\n{extra}\n")
        present, paths = coverage
        (d / "coverage.txt").write_text(
            f"intended_clock_present {present}\nconstrained_paths {paths}\n")
        p = subprocess.run(
            ["python3", "grade_handoff.py", "applied_hidden.sdc", "handoff_truth.json",
             "handoff_manifest.json", "coverage.txt", "flow_config.json", "provenance.json"],
            cwd=d, capture_output=True, text=True, timeout=60)
        return p.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _score(log: str) -> tuple[float, float, bool, dict]:
    """Grade through the evaluator the AGENTIC runner selects."""
    meta = _meta()
    ev = _select_evaluator(meta, TASK)
    comps = [ev.evaluate_component(c, TASK, log, mode="submission") for c in meta["scoring"]["weights"]]
    total = sum(c.weighted_score for c in comps)
    obj = sum(c.weighted_score for c in comps if c.name != "explanation")
    return round(total, 4), round(obj, 4), total >= 0.5, {c.name: c.raw_score for c in comps}


# --- 1. dispatch parity (the Phase-0D lesson) --------------------------------

def test_agentic_dispatch_selects_multifact():
    ev = _select_evaluator(_meta(), TASK)
    assert isinstance(ev, MultiFactHandoffEvaluator), f"agentic dispatch returned {type(ev).__name__}"


def test_dispatch_matches_declared_spec_both_sites():
    meta = _meta()
    declared = meta["scoring"]["evaluator"]
    assert declared == "multifact_handoff.MultiFactHandoffEvaluator"
    ev = _select_evaluator(meta, TASK)
    got = f"{type(ev).__module__.split('.')[-1]}.{type(ev).__name__}"
    assert got == declared
    cli = (REPO / "eda_agentbench" / "cli.py").read_text()
    runner = (REPO / "eda_agentbench" / "agentic" / "runner.py").read_text()
    assert 'evaluator_spec == "multifact_handoff.MultiFactHandoffEvaluator"' in cli
    assert 'evaluator_spec == "multifact_handoff.MultiFactHandoffEvaluator"' in runner


# --- 2. schema / structural --------------------------------------------------

def test_schema_and_structural_valid():
    meta = _meta()
    assert validate_metadata(meta) == [], "metadata invalid"
    assert structural_validate(TASK) == [], "structurally invalid"
    assert meta["track"] == "p12_multifact_handoff"
    assert meta["task_id"] == "mf_handoff_0001"
    assert set(meta["files"]["editable"]) == {"flow_config.json", "constraints.sdc", "provenance.json"}
    assert abs(sum(meta["scoring"]["weights"].values()) - 1.0) < 1e-9


# --- 3. public scripts reference no hidden artifacts -------------------------

def test_public_scripts_no_hidden_refs():
    for name in ("run_public.sh", "run_public.tcl"):
        text = (TASK / "files" / name).read_text()
        for leak in ("handoff_truth", "grade_handoff", "run_hidden", "run_signoff",
                     "ARTIFACT_CONSISTENCY", "SCENARIO_CLOCK", "PROVENANCE_OK", "applied_hidden"):
            assert leak not in text, f"{name} leaks oracle reference '{leak}'"


# --- 4. no literal-answer leak (golden hash / expected clock not in a visible secret) ---

def test_no_literal_answer_leak():
    truth = json.loads((TASK / "hidden" / "handoff_truth.json").read_text())
    # the golden hash legitimately appears in the manifest authority + provenance solution, but the
    # mutant package visible files must not pre-leak the *fix*: the manifest is the authority so its
    # v2 hash is allowed; ensure no hidden-only secret (truth file) is duplicated in a visible file.
    meta = _meta()
    # truth-only fields that must never appear verbatim in visible files
    for visible in meta["files"]["visible"]:
        if visible.endswith(".db"):
            continue
        text = (TASK / "files" / visible).read_text(errors="ignore")
        assert "handoff_truth" not in text
        assert "stale_netlist_sha256" not in text  # a truth-only key name


def test_manifest_is_authority_not_mutated():
    """The manifest names v2/clk_main (correct authority); the defect is downstream, not here."""
    m = json.loads((TASK / "files" / "handoff_manifest.json").read_text())
    assert m["netlist"] == V2 and m["clock"] == CLK_MAIN
    assert m["netlist_provenance_sha256"] == _sha(V2)


# --- 5. agent workspace runnable without hidden files -----------------------

def test_workspace_runnable_without_hidden():
    meta = _meta()
    ws = create_agent_workspace(TASK, meta)
    try:
        for need in ("flow_config.json", "constraints.sdc", "provenance.json",
                     "handoff_manifest.json", V1, V2, "tiny.db", "run_public.sh", "run_public.tcl"):
            assert (ws / need).is_file(), f"workspace missing {need}"
        present = {p.name for p in ws.iterdir() if p.is_file()}
        for hid in meta["files"]["hidden"]:
            assert Path(hid).name not in present, f"hidden '{hid}' leaked into workspace"
    finally:
        shutil.rmtree(ws, ignore_errors=True)


# --- 6. verdict-first public runner (mock PT) -------------------------------

_MOCK_PT = """#!/bin/bash
printf 'PrimeTime (R) license banner padding %s\\n' $(seq 1 60)
echo "HANDOFF_PUBLIC: MISMATCH consumed=netlist_v1.v/clk_old manifest=netlist_v2.v/clk_main constrained_paths=1 signoff=OK"
echo "PUBLIC_HINT: the flow consumes a netlist the manifest authority does not name"
echo "=== CONSUMED FLOW ==="
echo "PUBLIC_DONE"
"""


def _run_public_with_mock(tmp_path: Path) -> str:
    meta = _meta()
    ws = create_agent_workspace(TASK, meta)
    mock = tmp_path / "mock_pt_shell"
    mock.write_text(_MOCK_PT)
    mock.chmod(0o755)
    try:
        env = dict(os.environ, EDA_PT_CMD=str(mock))
        p = subprocess.run(["bash", "run_public.sh"], cwd=ws, env=env,
                           capture_output=True, text=True, timeout=60)
        return p.stdout
    finally:
        shutil.rmtree(ws, ignore_errors=True)


def test_public_verdict_within_first_1000_bytes(tmp_path):
    out = _run_public_with_mock(tmp_path)
    off = out.find("HANDOFF_PUBLIC:")
    assert off != -1 and off < 1000, f"HANDOFF_PUBLIC at byte {off}"
    assert "PUBLIC_HINT:" in out


def test_public_stdout_no_hidden_oracle_markers(tmp_path):
    out = _run_public_with_mock(tmp_path)
    for leak in ("ARTIFACT_CONSISTENCY", "SCENARIO_CLOCK_OK", "PROVENANCE_OK",
                 "handoff_truth", "grade_handoff"):
        assert leak not in out, f"public stdout leaks '{leak}'"


# --- 7. data-axis oracle sanity (golden vs mutant) --------------------------

def test_oracle_data_axes_golden_vs_mutant():
    g = _run_oracle_data_axes(_flow_config(V2), _provenance("v2"), CLK_MAIN, (1, 1))
    m = _run_oracle_data_axes(_flow_config(V1), _provenance("v1"), CLK_OLD, (0, 0))
    assert "ARTIFACT_CONSISTENCY_OK" in g and "SCENARIO_CLOCK_OK" in g and "PROVENANCE_OK" in g, g
    assert "ARTIFACT_CONSISTENCY_OK" not in m, m
    assert "SCENARIO_CLOCK_OK" not in m, m
    assert "PROVENANCE_OK" not in m, m


# --- 8. THE single-edit-fails matrix (central escalation property) ----------

def test_golden_full_repair_scores_1():
    log = _full_log(V2, CLK_MAIN, "v2")
    total, _obj, passed, comps = _score(log)
    assert passed and abs(total - 1.0) < 1e-9, f"golden total={total} comps={comps}"


def test_mutant_below_pass():
    total, _obj, passed, comps = _score(_full_log(V1, CLK_OLD, "v1"))
    assert not passed, f"mutant wrongly passed total={total} comps={comps}"


def test_single_edit_flow_config_only_fails():
    """Fix flow_config->v2 only; SDC still clk_old (absent on v2) -> 0 paths -> SIGNOFF/SCENARIO fail."""
    total, _obj, passed, comps = _score(_full_log(V2, CLK_OLD, "v1"))
    assert comps["signoff"] == 0.0, f"expected SIGNOFF_FAIL: {comps}"
    assert comps["scenario_clock_consistency"] == 0.0
    assert not passed, f"flow_config-only wrongly passed total={total} comps={comps}"


def test_single_edit_sdc_only_fails():
    """Fix SDC->clk_main only; flow still reads v1 (no clk_main port) -> 0 paths -> fail."""
    total, _obj, passed, comps = _score(_full_log(V1, CLK_MAIN, "v1"))
    assert comps["signoff"] == 0.0, f"expected SIGNOFF_FAIL: {comps}"
    assert comps["scenario_clock_consistency"] == 0.0
    assert comps["artifact_consistency"] == 0.0  # consumed still v1
    assert not passed, f"sdc-only wrongly passed total={total} comps={comps}"


def test_single_edit_provenance_only_fails():
    """Fix provenance->v2 only; consumed design still stale -> ARTIFACT + SIGNOFF fail."""
    total, _obj, passed, comps = _score(_full_log(V1, CLK_OLD, "v2"))
    assert comps["artifact_consistency"] == 0.0
    assert not passed, f"provenance-only wrongly passed total={total} comps={comps}"


def test_pairwise_flow_and_provenance_no_sdc_fails():
    """flow->v2 + provenance->v2 but SDC still clk_old -> 0 paths -> below pass."""
    total, _obj, passed, comps = _score(_full_log(V2, CLK_OLD, "v2"))
    assert comps["signoff"] == 0.0 and comps["scenario_clock_consistency"] == 0.0
    assert not passed, f"flow+prov (no sdc) wrongly passed total={total} comps={comps}"


def test_pairwise_sdc_and_provenance_no_flow_fails():
    """SDC->clk_main + provenance->v2 but flow still v1 -> 0 paths + artifact fail -> below pass."""
    total, _obj, passed, comps = _score(_full_log(V1, CLK_MAIN, "v2"))
    assert comps["signoff"] == 0.0 and comps["artifact_consistency"] == 0.0
    assert not passed, f"sdc+prov (no flow) wrongly passed total={total} comps={comps}"


def test_pairwise_flow_and_sdc_no_provenance_passes_but_not_full():
    """The coordinated coupling pair (flow->v2 AND SDC->clk_main) reaches the pass gate even with
    stale provenance: SIGNOFF+ARTIFACT+SCENARIO all OK (=0.85), PROVENANCE the only missing axis."""
    total, _obj, passed, comps = _score(_full_log(V2, CLK_MAIN, "v1"))
    assert comps["signoff"] == 1.0 and comps["artifact_consistency"] == 1.0
    assert comps["scenario_clock_consistency"] == 1.0
    assert comps["provenance_report_consistency"] == 0.0
    assert passed, f"coupled pair should pass (provenance is the refinement axis): {comps}"
    assert total < 1.0, f"missing provenance should not be full credit: total={total}"


def test_pt_green_on_stale_island_below_pass():
    """If the stale island self-signs-off green (v1+clk_old), SIGNOFF may be OK but ARTIFACT and
    PROVENANCE fail -> signoff-only 0.25 -> far below pass. 'PT green' cannot buy a pass."""
    present, paths, signoff_ok = _coverage_facts(V1, CLK_OLD)
    assert signoff_ok, "stale island must self-sign-off green (the false pass)"
    log = _full_log(V1, CLK_OLD, "v1")
    total, obj, passed, comps = _score(log)
    assert comps["signoff"] == 1.0, "stale island signs off green"
    assert comps["artifact_consistency"] == 0.0
    assert not passed and total <= 0.30, f"PT-green-on-stale total={total} comps={comps}"


def test_golden_mutant_objective_margin():
    _gt, g_obj, _gp, _gc = _score(_full_log(V2, CLK_MAIN, "v2"))
    _mt, m_obj, _mp, _mc = _score(_full_log(V1, CLK_OLD, "v1"))
    assert (g_obj - m_obj) >= 0.15, f"objective margin {g_obj - m_obj} < 0.15"


# --- 9. masking & anti-cheat -------------------------------------------------

def test_masking_sdc_weakening_rejected():
    """Even with the coordinated flow->v2 + SDC->clk_main, adding a timing exception is masking ->
    consistency axes zeroed -> below pass."""
    log = _full_log(V2, CLK_MAIN, "v2", extra_sdc="set_false_path -from [get_ports din]")
    total, _obj, passed, comps = _score(log)
    assert comps["artifact_consistency"] == 0.0 and comps["scenario_clock_consistency"] == 0.0
    assert not passed, f"masking wrongly passed total={total} comps={comps}"


def test_forbidden_netlist_edit_detected():
    meta = _meta()
    for forbidden in ("netlist_v2.v", "handoff_manifest.json", "timing_report.rpt"):
        clean, violations = detect_forbidden_modifications({forbidden: "modified"},
                                                           meta["files"]["forbidden"])
        assert not clean and any(forbidden in v for v in violations), (forbidden, violations)
