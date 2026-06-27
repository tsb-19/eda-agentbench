"""FlowHandoff Variant-C (clock-name mismatch / unconstrained false-clean) contract tests (tool-free).

Variant C reuses the shared FlowHandoffEvaluator unchanged; its hidden grade_handoff.py emits the
same markers from a clock-binding + path-coverage oracle. These tests prove the headline property
WITHOUT commercial tools: a stale clock name leaves zero intended paths constrained, so neither
sign-off nor the coverage gate is satisfied -- "PT green/clean" cannot pass. Real golden-pass /
mutant-fail on PrimeTime is the b04 gate. (fhandoff_0001 tests live in test_flow_handoff.py and
must remain unchanged.)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from eda_agentbench.agentic.runner import _select_evaluator
from eda_agentbench.agentic.workspace import create_agent_workspace, detect_forbidden_modifications
from eda_agentbench.evaluator.flow_handoff import FlowHandoffEvaluator
from eda_agentbench.schema import validate_metadata
from eda_agentbench.task.loader import structural_validate

REPO = Path(__file__).resolve().parent.parent
TASK = REPO / "tasks" / "p11_flow_handoff" / "fhandoff_0002"


def _meta() -> dict:
    return json.loads((TASK / "metadata.json").read_text())


def _run_grade(applied_sdc: str, present: int, paths: int) -> str:
    """Run the Variant-C oracle on a simulated laundered SDC + PT coverage facts (no PT)."""
    d = Path(tempfile.mkdtemp(prefix="fhc_grade_"))
    try:
        shutil.copy2(TASK / "hidden" / "grade_handoff.py", d / "grade_handoff.py")
        shutil.copy2(TASK / "hidden" / "handoff_truth.json", d / "handoff_truth.json")
        shutil.copy2(TASK / "files" / "handoff_manifest.json", d / "handoff_manifest.json")
        (d / "applied_hidden.sdc").write_text(applied_sdc)
        (d / "coverage.txt").write_text(f"intended_clock_present {present}\nconstrained_paths {paths}\n")
        p = subprocess.run(["python3", "grade_handoff.py", "applied_hidden.sdc",
                            "handoff_truth.json", "handoff_manifest.json", "coverage.txt"],
                           cwd=d, capture_output=True, text=True, timeout=60)
        return p.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _marker_log(applied_sdc: str, present: int, paths: int, signoff_ok: bool) -> str:
    sign = "SIGNOFF_OK worst_slack=0.13" if signoff_ok else "SIGNOFF_FAIL worst_slack=NONE no_paths"
    return sign + "\n" + _run_grade(applied_sdc, present, paths)


def _score(log: str) -> tuple[float, bool, dict]:
    meta = _meta()
    ev = _select_evaluator(meta, TASK)
    comps = [ev.evaluate_component(c, TASK, log, mode="submission") for c in meta["scoring"]["weights"]]
    total = sum(c.weighted_score for c in comps)
    return round(total, 4), total >= 0.5, {c.name: c.raw_score for c in comps}


# golden laundered SDC (clk_main) and the mutant's laundered form (no clock object survives)
_GOLDEN_SDC = (TASK / "solution" / "constraints.sdc").read_text()
_MUTANT_LAUNDERED = "# write_sdc output: stale clock matched no port, no create_clock emitted\n"


# --- dispatch parity (reused evaluator) -------------------------------------

def test_dispatch_selects_flow_handoff():
    ev = _select_evaluator(_meta(), TASK)
    assert isinstance(ev, FlowHandoffEvaluator)
    assert _meta()["scoring"]["evaluator"] == "flow_handoff.FlowHandoffEvaluator"


# --- schema / structural ----------------------------------------------------

def test_schema_and_structural_valid():
    meta = _meta()
    assert validate_metadata(meta) == [], "metadata invalid"
    assert structural_validate(TASK) == [], "structurally invalid"
    assert meta["task_id"] == "fhandoff_0002"
    assert meta["track"] == "p11_flow_handoff"
    assert meta["files"]["editable"] == ["constraints.sdc"]


# --- no hidden leak ---------------------------------------------------------

def test_public_scripts_no_hidden_refs():
    for name in ("run_public.sh", "run_public.tcl"):
        text = (TASK / "files" / name).read_text()
        for leak in ("handoff_truth", "grade_handoff", "run_hidden", "run_signoff",
                     "HANDOFF_CONSISTENCY", "MANIFEST_OK", "coverage.txt"):
            assert leak not in text, f"{name} leaks oracle reference '{leak}'"


# --- agent workspace runnable without hidden files --------------------------

def test_workspace_runnable_without_hidden():
    meta = _meta()
    ws = create_agent_workspace(TASK, meta)
    try:
        present = {p.name for p in ws.iterdir() if p.is_file()}
        for need in ("constraints.sdc", "design_netlist.v", "tiny.db", "handoff_manifest.json",
                     "run_public.sh", "run_public.tcl"):
            assert (ws / need).is_file(), f"workspace missing {need}"
        for hid in meta["files"]["hidden"]:
            assert Path(hid).name not in present, f"hidden '{hid}' leaked into workspace"
    finally:
        shutil.rmtree(ws, ignore_errors=True)


# --- verdict-first public runner (mock) -------------------------------------

_MOCK_PT = """#!/bin/bash
printf 'PrimeTime (R) license banner padding %s\\n' $(seq 1 60)
echo "HANDOFF_PUBLIC: MISMATCH clock=clk_main clock_bound=0 constrained_paths=0 signoff=NO_PATHS"
echo "PUBLIC_HINT: zero intended paths are constrained -- check the clock NAME in constraints.sdc"
echo "=== CLOCKS / WORST PATH ==="
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
    finally:
        shutil.rmtree(ws, ignore_errors=True)
    off = out.find("HANDOFF_PUBLIC:")
    assert off != -1 and off < 1000, f"verdict at byte {off}"
    assert "PUBLIC_HINT:" in out
    for leak in ("HANDOFF_CONSISTENCY", "MANIFEST_OK", "handoff_truth"):
        assert leak not in out, f"public stdout leaks '{leak}'"


# --- oracle: golden vs stale clock ------------------------------------------

def test_oracle_golden_vs_stale_clock():
    g = _run_grade(_GOLDEN_SDC, present=1, paths=1)
    s = _run_grade(_MUTANT_LAUNDERED, present=0, paths=0)
    assert "MANIFEST_OK" in g and "HANDOFF_CONSISTENCY_OK" in g, g
    assert "HANDOFF_CONSISTENCY_OK" not in s, s
    assert "constrained_paths=0" in s, s


# --- agentic-path grading ---------------------------------------------------

def test_correct_fix_scores_full():
    total, passed, comps = _score(_marker_log(_GOLDEN_SDC, present=1, paths=1, signoff_ok=True))
    assert passed and abs(total - 1.0) < 1e-9, f"correct fix total={total} comps={comps}"


def test_stale_clock_below_pass():
    """Mutant: stale clock -> no clock object -> 0 paths -> SIGNOFF_FAIL + coverage fail."""
    total, passed, comps = _score(_marker_log(_MUTANT_LAUNDERED, present=0, paths=0, signoff_ok=False))
    assert not passed, f"stale clock wrongly passed total={total} comps={comps}"
    assert comps["handoff_consistency"] == 0.0


def test_unconstrained_paths_not_full_even_if_signoff_marker_present():
    """Coverage gate: zero constrained intended paths must NOT score full handoff credit, even if
    a SIGNOFF_OK marker were present (defends the 'PT clean but unconstrained' false-pass)."""
    total, passed, comps = _score(_marker_log(_GOLDEN_SDC, present=1, paths=0, signoff_ok=True))
    assert comps["handoff_consistency"] == 0.0, f"unconstrained paths scored handoff credit: {comps}"
    assert total < 1.0


def test_signoff_failure_below_pass():
    """A correct clock binding that does not sign off cleanly must not pass (precondition)."""
    total, passed, comps = _score(_marker_log(_GOLDEN_SDC, present=1, paths=1, signoff_ok=False))
    assert comps["handoff_consistency"] == 0.0
    assert not passed, f"signoff failure wrongly passed total={total}"


def test_masking_weakening_rejected():
    weak = _GOLDEN_SDC + "\nset_false_path -from [get_ports din]\n"
    total, passed, comps = _score(_marker_log(weak, present=1, paths=1, signoff_ok=True))
    assert comps["handoff_consistency"] == 0.0, f"masking not rejected: {comps}"
    assert not passed


def test_golden_mutant_objective_margin():
    g = _score(_marker_log(_GOLDEN_SDC, 1, 1, True))
    m = _score(_marker_log(_MUTANT_LAUNDERED, 0, 0, False))
    g_obj = g[0] - 0.1  # minus explanation weight
    m_obj = m[0] - 0.1
    assert (g_obj - m_obj) >= 0.15, f"objective margin {g_obj - m_obj} < 0.15"


def test_forbidden_netlist_edit_detected():
    meta = _meta()
    clean, violations = detect_forbidden_modifications({"design_netlist.v": "modified"},
                                                       meta["files"]["forbidden"])
    assert not clean and any("design_netlist.v" in v for v in violations), violations
