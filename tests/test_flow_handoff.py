"""FlowHandoff Variant-A (manifest->stale-netlist) task + evaluator contract tests (tool-free).

Proves the hand-authored fhandoff_0001 task is fair, oracle-checkable, leak-free, and graded
through BOTH dispatch sites without commercial tools: dispatch parity (the Phase-0D lesson),
no hidden/answer leak, runnable agent workspace, verdict-first public runner, and the headline
anti-collapse property -- a stale manifest that still signs off green ("PT green but wrong
handoff") must NOT pass. Real golden-pass / mutant-green-but-wrong on PrimeTime is the b04 gate.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from eda_agentbench.agentic.runner import _select_evaluator
from eda_agentbench.agentic.workspace import (
    compute_file_changes,
    create_agent_workspace,
    detect_forbidden_modifications,
)
from eda_agentbench.evaluator.flow_handoff import FlowHandoffEvaluator
from eda_agentbench.schema import validate_metadata
from eda_agentbench.task.loader import structural_validate

REPO = Path(__file__).resolve().parent.parent
TASK = REPO / "tasks" / "p11_flow_handoff" / "fhandoff_0001"


def _meta() -> dict:
    return json.loads((TASK / "metadata.json").read_text())


def _run_grade_handoff(manifest_text: str, sdc_text: str | None = None) -> str:
    """Run the hidden oracle (stdlib, no PT) in a temp package mirroring the eval workspace,
    returning its MANIFEST_*/HANDOFF_* marker block."""
    import tempfile
    d = Path(tempfile.mkdtemp(prefix="fh_grade_"))
    try:
        for f in ("netlist_v1.v", "netlist_v2.v", "constraints.sdc"):
            shutil.copy2(TASK / "files" / f, d / f)
        if sdc_text is not None:
            (d / "constraints.sdc").write_text(sdc_text)
        shutil.copy2(TASK / "hidden" / "handoff_truth.json", d / "handoff_truth.json")
        shutil.copy2(TASK / "hidden" / "grade_handoff.py", d / "grade_handoff.py")
        (d / "handoff_manifest.json").write_text(manifest_text)
        p = subprocess.run(["python3", "grade_handoff.py", "handoff_manifest.json",
                            "handoff_truth.json"], cwd=d, capture_output=True, text=True, timeout=60)
        return p.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _marker_log(manifest_text: str, signoff_ok: bool, sdc_text: str | None = None) -> str:
    """Combined hidden grader log: SIGNOFF marker + the oracle's handoff/manifest markers."""
    grade = _run_grade_handoff(manifest_text, sdc_text)
    sign = "SIGNOFF_OK worst_slack=0.13" if signoff_ok else "SIGNOFF_FAIL worst_slack=-0.30"
    return sign + "\n" + grade


def _score(log: str) -> tuple[float, float, bool, dict]:
    """Grade through the evaluator the AGENTIC runner selects (mirrors runner.py)."""
    meta = _meta()
    ev = _select_evaluator(meta, TASK)
    comps = [ev.evaluate_component(c, TASK, log, mode="submission") for c in meta["scoring"]["weights"]]
    total = sum(c.weighted_score for c in comps)
    obj = sum(c.weighted_score for c in comps if c.name != "explanation")
    return round(total, 4), round(obj, 4), total >= 0.5, {c.name: c.raw_score for c in comps}


# --- 1. dispatch parity (the Phase-0D lesson: wire BOTH dispatch sites) ------

def test_agentic_dispatch_selects_flow_handoff():
    ev = _select_evaluator(_meta(), TASK)
    assert isinstance(ev, FlowHandoffEvaluator), f"agentic dispatch returned {type(ev).__name__}"


def test_agentic_and_cli_dispatch_match_declared_spec():
    meta = _meta()
    declared = meta["scoring"]["evaluator"]
    assert declared == "flow_handoff.FlowHandoffEvaluator"
    ev = _select_evaluator(meta, TASK)
    got = f"{type(ev).__module__.split('.')[-1]}.{type(ev).__name__}"
    assert got == declared, f"agentic dispatch resolved '{got}' but metadata declares '{declared}'"


def test_cli_dispatch_has_flow_handoff_branch():
    """cli.py submission-mode dispatch must also resolve p11 (no fallback divergence)."""
    cli = (REPO / "eda_agentbench" / "cli.py").read_text()
    assert 'evaluator_spec == "flow_handoff.FlowHandoffEvaluator"' in cli
    runner = (REPO / "eda_agentbench" / "agentic" / "runner.py").read_text()
    assert 'evaluator_spec == "flow_handoff.FlowHandoffEvaluator"' in runner


# --- 2. schema / structural validity ----------------------------------------

def test_schema_and_structural_valid():
    meta = _meta()
    assert validate_metadata(meta) == [], "metadata invalid"
    assert structural_validate(TASK) == [], "structurally invalid"
    assert meta["track"] == "p11_flow_handoff"
    assert meta["task_id"] == "fhandoff_0001"
    assert meta["files"]["editable"] == ["handoff_manifest.json"]


# --- 3. public scripts reference no hidden artifacts -------------------------

def test_public_scripts_no_hidden_refs():
    for name in ("run_public.sh", "run_public.tcl"):
        text = (TASK / "files" / name).read_text()
        for leak in ("handoff_truth", "grade_handoff", "run_hidden", "run_signoff",
                     "HANDOFF_CONSISTENCY", "MANIFEST_OK"):
            assert leak not in text, f"{name} leaks oracle reference '{leak}'"


# --- 4. no literal-answer leak (golden v2 provenance hash) -------------------

def test_no_literal_answer_leak():
    truth = json.loads((TASK / "hidden" / "handoff_truth.json").read_text())
    secret = truth["expected_netlist_sha256"]
    meta = _meta()
    for f in meta["files"]["visible"]:
        if f.endswith((".db",)):
            continue
        text = (TASK / "files" / f).read_text(errors="ignore")
        assert secret not in text, f"golden v2 provenance hash leaks as a literal in files/{f}"


# --- 5. agent workspace runnable without hidden files -----------------------

def test_workspace_runnable_without_hidden():
    meta = _meta()
    ws = create_agent_workspace(TASK, meta)
    try:
        present = {p.name for p in ws.iterdir() if p.is_file()}
        for need in ("handoff_manifest.json", "netlist_v1.v", "netlist_v2.v",
                     "constraints.sdc", "tiny.db", "run_public.sh", "run_public.tcl"):
            assert (ws / need).is_file(), f"workspace missing {need}"
        for hid in meta["files"]["hidden"]:
            assert Path(hid).name not in present, f"hidden '{hid}' leaked into workspace"
    finally:
        shutil.rmtree(ws, ignore_errors=True)


# --- 6. verdict-first public runner -----------------------------------------

_MOCK_PT = """#!/bin/bash
# mock pt_shell: print a >1000-byte banner, then run the real run_public.tcl logic is not
# possible without PT, so emit the markers the wrapper greps for, banner-first.
printf 'PrimeTime (R) license banner padding %s\\n' $(seq 1 60)
echo "HANDOFF_PUBLIC: MISMATCH selected=netlist_v1.v provenance=MATCH signoff=OK worst_slack=0.13"
echo "PUBLIC_HINT: confirm handoff_manifest.json selects the CURRENT revision"
echo "=== SELECTED NETLIST SIGN-OFF ==="
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
    assert off != -1, "HANDOFF_PUBLIC absent from public stdout"
    assert off < 1000, f"HANDOFF_PUBLIC at byte {off} (>=1000) -- verdict not hoisted"
    assert "PUBLIC_HINT:" in out


def test_public_stdout_no_hidden_oracle_markers(tmp_path):
    out = _run_public_with_mock(tmp_path)
    for leak in ("HANDOFF_CONSISTENCY", "MANIFEST_OK", "handoff_truth", "grade_handoff",
                 "expected_netlist_sha256"):
        assert leak not in out, f"public stdout leaks '{leak}'"


# --- 7. oracle: golden vs stale manifest ------------------------------------

def test_oracle_golden_vs_stale():
    golden = (TASK / "solution" / "handoff_manifest.json").read_text()
    stale = (TASK / "files" / "handoff_manifest.json").read_text()
    g = _run_grade_handoff(golden)
    s = _run_grade_handoff(stale)
    assert "MANIFEST_OK" in g and "HANDOFF_CONSISTENCY_OK" in g, f"golden oracle: {g}"
    assert "MANIFEST_OK" not in s and "HANDOFF_CONSISTENCY_OK" not in s, f"stale oracle: {s}"
    assert "missing=['en']" in s or "interface_port=WRONG" in s, f"stale must flag missing en: {s}"


# --- 8. agentic-path grading: correct/stale/PT-green-wrong/masking/incomplete/forbidden ---

def test_correct_fix_scores_full():
    golden = (TASK / "solution" / "handoff_manifest.json").read_text()
    total, _obj, passed, comps = _score(_marker_log(golden, signoff_ok=True))
    assert passed and abs(total - 1.0) < 1e-9, f"correct fix total={total} comps={comps}"


def test_stale_manifest_below_pass():
    stale = (TASK / "files" / "handoff_manifest.json").read_text()
    total, _obj, passed, comps = _score(_marker_log(stale, signoff_ok=True))
    assert not passed, f"stale manifest wrongly passed total={total} comps={comps}"


def test_pt_green_but_wrong_handoff_not_full():
    """The headline: stale netlist signs off green, but the handoff is wrong -> not full, not pass."""
    stale = (TASK / "files" / "handoff_manifest.json").read_text()
    total, obj, passed, comps = _score(_marker_log(stale, signoff_ok=True))  # PT GREEN
    assert comps["signoff"] == 1.0, "stale netlist should sign off green (PT green)"
    assert comps["handoff_consistency"] == 0.0 and comps["manifest_correctness"] == 0.0
    assert total < 1.0 and not passed, f"PT-green-but-wrong-handoff total={total}"


def test_golden_mutant_objective_margin():
    golden = (TASK / "solution" / "handoff_manifest.json").read_text()
    stale = (TASK / "files" / "handoff_manifest.json").read_text()
    _gt, g_obj, _gp, _gc = _score(_marker_log(golden, signoff_ok=True))
    _mt, m_obj, _mp, _mc = _score(_marker_log(stale, signoff_ok=True))
    assert (g_obj - m_obj) >= 0.15, f"golden-mutant objective margin {g_obj - m_obj} < 0.15"


def test_incomplete_repair_below_pass():
    """Fix the netlist pointer to v2 but forget to update the stale provenance hash -> the
    declared hash no longer matches disk -> handoff + manifest fail -> below pass."""
    m = json.loads((TASK / "solution" / "handoff_manifest.json").read_text())
    stale_hash = json.loads((TASK / "files" / "handoff_manifest.json").read_text())["netlist_provenance_sha256"]
    m["netlist_provenance_sha256"] = stale_hash  # left stale
    total, _obj, passed, comps = _score(_marker_log(json.dumps(m), signoff_ok=True))
    assert not passed, f"incomplete repair wrongly passed total={total} comps={comps}"


def test_signoff_failure_below_pass():
    """A manifest that matches the contract but does not sign off cleanly must not pass
    (sign-off precondition)."""
    golden = (TASK / "solution" / "handoff_manifest.json").read_text()
    total, _obj, passed, comps = _score(_marker_log(golden, signoff_ok=False))
    assert comps["handoff_consistency"] == 0.0, "handoff credit requires SIGNOFF_OK precondition"
    assert not passed, f"signoff failure wrongly passed total={total} comps={comps}"


def test_masking_sdc_weakening_rejected():
    """Weakening the frozen SDC (a forbidden artifact) to suppress the symptom is flagged as
    masking by the oracle and earns no handoff credit even with the golden manifest + green PT."""
    golden = (TASK / "solution" / "handoff_manifest.json").read_text()
    weak_sdc = (TASK / "files" / "constraints.sdc").read_text() + "\nset_false_path -from [get_ports din]\n"
    total, _obj, passed, comps = _score(_marker_log(golden, signoff_ok=True, sdc_text=weak_sdc))
    assert comps["handoff_consistency"] == 0.0, f"masking not rejected: {comps}"
    assert not passed, f"masking wrongly passed total={total}"


def test_forbidden_netlist_edit_detected():
    """Editing a netlist (forbidden) is caught by the anti-cheat layer the runner applies."""
    meta = _meta()
    changes = {"netlist_v2.v": "modified"}
    clean, violations = detect_forbidden_modifications(changes, meta["files"]["forbidden"])
    assert not clean and any("netlist_v2.v" in v for v in violations), violations
