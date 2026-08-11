"""Synthetic Phase-0A constraint-drift project — contract tests (tool-free).

Proves the project/oracle contract WITHOUT commercial tools, by feeding the evaluator the
exact marker lines the hidden grader emits on b04 (golden / mutant / symptom-suppression),
and by exercising the workspace provisioning + anti-cheat guards directly. The real b04
golden-pass / mutant-fail gate is run separately (see docs/phases/synthetic_phase0a_design.md §8).
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
from pathlib import Path

import pytest

from eda_agentbench.agentic.workspace import (
    create_agent_workspace,
    create_evaluator_workspace,
    compute_file_changes,
    detect_forbidden_modifications,
    detect_hidden_shadows,
    snapshot_workspace,
)
from eda_agentbench.evaluator.synthetic_project import SyntheticProjectEvaluator

TASK = Path(__file__).resolve().parent.parent / "tasks" / "p10_synthetic_project" / "syn_proj_0001"

_READ_RE = re.compile(r"^(?:read_verilog|read_sdc|read_db|read_file|source)\s+(\S+)")


def _meta() -> dict:
    return json.loads((TASK / "metadata.json").read_text())


def _reads(text: str) -> set[str]:
    out: set[str] = set()
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = _READ_RE.match(s)
        if m:
            out.add(Path(m.group(1).strip("\"'")).name)
    return out


def _score(log: str) -> tuple[float, float, bool]:
    """Replicate cli.py aggregation: (total, objective, passed) for a hidden-log string."""
    meta = _meta()
    ev = SyntheticProjectEvaluator(TASK, meta)
    comps = [ev.evaluate_component(c, TASK, log, mode="submission") for c in meta["scoring"]["weights"]]
    total = sum(c.weighted_score for c in comps)
    obj = sum(c.weighted_score for c in comps if c.name != "explanation")
    return total, obj, total >= 0.5


# Marker logs exactly as hidden/run_hidden.sh emits them on b04.
GOLDEN_LOG = "[apply] launder ok\nSIGNOFF_OK worst_slack=1.58\nCONSTRAINT_SPEC_OK\nCONSTRAINT_SPEC_SCORE: 1.000\nCONSTRAINT_SPEC_DETAIL: all ok\n"
MUTANT_LOG = "[apply] launder ok\nSIGNOFF_FAIL worst_slack=-0.28\nCONSTRAINT_SPEC_SCORE: 0.800\nCONSTRAINT_SPEC_DETAIL: output_delay=WRONG\n"
MASK_LOG = "[apply] launder ok\nSIGNOFF_OK worst_slack=0.32\nCONSTRAINT_SPEC_SCORE: 0.800\nCONSTRAINT_SPEC_DETAIL: period=WRONG\n"


# --- scoring contract -------------------------------------------------------

def test_golden_scores_pass():
    total, obj, passed = _score(GOLDEN_LOG)
    assert passed and abs(total - 1.0) < 1e-9, f"golden total={total}"


def test_mutant_fails_with_margin():
    g_total, g_obj, _ = _score(GOLDEN_LOG)
    m_total, m_obj, m_pass = _score(MUTANT_LOG)
    assert not m_pass, f"mutant should fail the pass gate, total={m_total}"
    assert (g_obj - m_obj) >= 0.15, f"golden-mutant objective margin {g_obj - m_obj} < 0.15"


def test_symptom_suppression_not_full_credit():
    """PT goes green (SIGNOFF_OK) but a constraint drifted (no CONSTRAINT_SPEC_OK):
    must NOT receive full credit and must NOT pass the gate."""
    g_total, _, _ = _score(GOLDEN_LOG)
    m_total, _, m_pass = _score(MASK_LOG)
    assert not m_pass, f"masking should fail the pass gate, total={m_total}"
    assert m_total < g_total, "masking must score below the true fix"


def test_injected_markers_in_apply_phase_are_ignored():
    """An agent that puts CONSTRAINT_SPEC_OK / SIGNOFF_OK in its SDC sees them surface only in
    the [apply]-prefixed launder output, which cannot match the ^-anchored real markers."""
    inject = "[apply] CONSTRAINT_SPEC_OK\n[apply] SIGNOFF_OK\nSIGNOFF_FAIL worst_slack=-0.28\nCONSTRAINT_SPEC_SCORE: 0.800\n"
    total, _, passed = _score(inject)
    assert not passed, f"injected markers must not yield a pass, total={total}"


# --- grade_spec mechanism oracle (loaded by path = the exact hidden grader) --

def _grade_spec_module():
    spec = importlib.util.spec_from_file_location("grade_spec", TASK / "hidden" / "grade_spec.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _applied(period="4.0", unc="0.10", idin="1.8", ien="1.8", odout="1.2", extra=""):
    return (f"create_clock -period {period} -name clk [get_ports {{clk}}]\n"
            f"set_clock_uncertainty {unc} [get_clocks {{clk}}]\n"
            f"set_input_delay -clock clk {idin} [get_ports {{din}}]\n"
            f"set_input_delay -clock clk {ien} [get_ports {{en}}]\n"
            f"set_output_delay -clock clk {odout} [get_ports {{dout}}]\n" + extra)


def test_grade_spec_true_fix_full():
    gs = _grade_spec_module()
    truth = json.loads((TASK / "hidden" / "spec_truth.json").read_text())
    full, frac, _ = gs.score_spec(_applied(), truth)
    assert full and frac == 1.0


@pytest.mark.parametrize("kw", [
    {"odout": "3.2"},                 # the mutant
    {"odout": "0.0"},                 # zero-delay masking
    {"odout": "2.4"},                 # arbitrary clearing value
    {"period": "6.0"},                # over-constrain (loosen period)
    {"period": "3.5"},                # over-constrain (tighten period)
    {"extra": "set_false_path -from [get_ports din]\n"},  # exception masking
    {"idin": "0.4"},                  # input-delay drift
])
def test_grade_spec_drift_or_masking_not_full(kw):
    gs = _grade_spec_module()
    truth = json.loads((TASK / "hidden" / "spec_truth.json").read_text())
    full, frac, _ = gs.score_spec(_applied(**kw), truth)
    assert not full and frac < 1.0


# --- provisioning: public flow runnable without hidden files ----------------

def test_public_flow_runnable_in_agent_workspace():
    meta = _meta()
    tcl = (TASK / "files" / "run_public.tcl").read_text()
    reads = _reads(tcl)
    assert {"design_netlist.v", "tiny.db", "constraints.sdc"} <= reads
    ws = create_agent_workspace(TASK, meta)
    try:
        for fname in reads:
            assert (ws / fname).is_file(), f"run_public.tcl reads '{fname}' absent from agent workspace"
    finally:
        shutil.rmtree(ws, ignore_errors=True)


def test_public_runner_does_not_leak_oracle():
    """Public scripts must not reference the hidden grader / spec truth / spec-score markers."""
    for name in ("run_public.sh", "run_public.tcl"):
        text = (TASK / "files" / name).read_text()
        for leak in ("spec_truth.json", "grade_spec", "run_hidden", "run_signoff", "CONSTRAINT_SPEC"):
            assert leak not in text, f"{name} leaks oracle reference '{leak}'"


# --- workspace separation + anti-cheat --------------------------------------

def test_workspace_separates_visible_readonly_editable_hidden():
    meta = _meta()
    visible = {Path(f).name for f in meta["files"]["visible"]}
    hidden = {Path(f).name for f in meta["files"]["hidden"]}

    agent_ws = create_agent_workspace(TASK, meta)
    try:
        present = {p.name for p in agent_ws.iterdir() if p.is_file()}
        # every visible file present; NO hidden file present (oracle isolation)
        assert visible <= present, f"missing visible files: {visible - present}"
        assert not (hidden & present), f"hidden artifacts leaked into agent workspace: {hidden & present}"
        assert "spec_truth.json" not in present and "grade_spec.py" not in present

        eval_ws = create_evaluator_workspace(TASK, meta, agent_ws)
        try:
            ev_present = {p.name for p in eval_ws.iterdir() if p.is_file()}
            # evaluator workspace overlays hidden grading files
            assert {"run_hidden.sh", "run_signoff.tcl", "grade_spec.py", "spec_truth.json"} <= ev_present
            # editable constraints.sdc carried over from the agent edits
            assert "constraints.sdc" in ev_present
        finally:
            shutil.rmtree(eval_ws, ignore_errors=True)
    finally:
        shutil.rmtree(agent_ws, ignore_errors=True)


def test_editable_set_is_only_constraints_sdc():
    meta = _meta()
    assert meta["files"]["editable"] == ["constraints.sdc"]
    # every other visible file is forbidden-to-edit
    forbidden = set(meta["files"]["forbidden"])
    for v in meta["files"]["visible"]:
        if v != "constraints.sdc":
            assert v in forbidden, f"{v} should be forbidden-to-edit"


def test_hidden_shadow_anticheat_flags_fabricated_oracle():
    """Fabricating any hidden grader artifact in the agent workspace must be flagged."""
    meta = _meta()
    hidden = meta["files"]["hidden"]
    for fake in ("spec_truth.json", "run_hidden.sh", "run_signoff.tcl", "grade_spec.py"):
        changes = {fake: "added"}
        clean, viol = detect_hidden_shadows(changes, hidden)
        assert not clean and viol, f"shadowing '{fake}' should be flagged"


def test_forbidden_modification_flags_readonly_edit():
    """Editing a read-only/forbidden artifact (netlist, spec, library, runner) must be flagged."""
    meta = _meta()
    forbidden = meta["files"]["forbidden"]
    for f in ("design_netlist.v", "spec.md", "tiny.db", "run_public.tcl"):
        clean, viol = detect_forbidden_modifications({f: "modified"}, forbidden)
        assert not clean and viol, f"editing forbidden '{f}' should be flagged"
    # editing constraints.sdc is allowed (not forbidden)
    clean, _ = detect_forbidden_modifications({"constraints.sdc": "modified"}, forbidden)
    assert clean


# --- byte-determinism -------------------------------------------------------

def test_golden_and_mutant_differ_only_in_output_delay():
    golden = (TASK / "solution" / "constraints.sdc").read_text().splitlines()
    mutant = (TASK / "files" / "constraints.sdc").read_text().splitlines()
    assert len(golden) == len(mutant)
    diffs = [(g, m) for g, m in zip(golden, mutant) if g != m]
    assert len(diffs) == 1, f"expected exactly one differing line, got {diffs}"
    g, m = diffs[0]
    assert "set_output_delay" in g and "1.2" in g and "3.2" in m


def test_spec_truth_matches_authored_golden():
    """The hidden oracle's intended values match the committed golden SDC (no silent drift)."""
    truth = json.loads((TASK / "hidden" / "spec_truth.json").read_text())
    golden = (TASK / "solution" / "constraints.sdc").read_text()
    assert f"-period {truth['clock']['period_ns']}" in golden
    assert str(truth["output_delay"]["value_ns"]) in golden
    assert str(truth["input_delay"]["value_ns"]) in golden
