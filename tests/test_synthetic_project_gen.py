"""Phase-0B synthetic-project GENERATOR contract tests (tool-free).

Proves the generator emits fair, oracle-checkable, byte-deterministic constraint-drift
variants WITHOUT commercial tools: determinism / seed diversity, no hidden-artifact
references, runnable agent workspace, golden-vs-mutant score separation, masking resistance,
schema/inventory validity, and no literal-answer leak. The real golden-pass / mutant-fail on
PrimeTime is the b04 gate (validate_dataset.py); see docs/synthetic_phase0b_generator_design.md §8.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from eda_agentbench.agentic.runner import _select_evaluator
from eda_agentbench.agentic.workspace import create_agent_workspace
from eda_agentbench.evaluator.synthetic_project import SyntheticProjectEvaluator
from eda_agentbench.schema import validate_metadata
from eda_agentbench.task.loader import structural_validate
from generators.p10_synthetic_project_gen import SyntheticProjectGenerator, _fmt, _has_token

REPO = Path(__file__).resolve().parent.parent
TRACK = REPO / "tasks" / "p10_synthetic_project"
GEN_TASKS = sorted(TRACK.glob("syn_proj_000[2-6]"))      # the committed generated five
SEED = 43

_READ_RE = re.compile(r"^(?:read_verilog|read_sdc|read_db|read_file|source)\s+(\S+)")


def _grade_spec(task: Path):
    spec = importlib.util.spec_from_file_location("gs", task / "hidden" / "grade_spec.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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


def _score(task: Path, log: str) -> tuple[float, float, bool]:
    """Replicate cli.py aggregation: (total, objective, passed)."""
    meta = json.loads((task / "metadata.json").read_text())
    ev = SyntheticProjectEvaluator(task, meta)
    comps = [ev.evaluate_component(c, task, log, mode="submission") for c in meta["scoring"]["weights"]]
    total = sum(c.weighted_score for c in comps)
    obj = sum(c.weighted_score for c in comps if c.name != "explanation")
    return total, obj, total >= 0.5


def _marker_log(task: Path, sdc_text: str, signoff_ok: bool) -> str:
    """Build the combined grader log the hidden flow would emit for this applied SDC."""
    gs = _grade_spec(task)
    truth = json.loads((task / "hidden" / "spec_truth.json").read_text())
    full, frac, detail = gs.score_spec(sdc_text, truth)
    lines = ["[apply] launder ok",
             f"SIGNOFF_OK worst_slack=1.0" if signoff_ok else "SIGNOFF_FAIL worst_slack=-0.30"]
    if full:
        lines.append("CONSTRAINT_SPEC_OK")
    lines.append(f"CONSTRAINT_SPEC_SCORE: {frac:.3f}")
    lines.append(f"CONSTRAINT_SPEC_DETAIL: {detail}")
    return "\n".join(lines) + "\n"


def _hash_tree(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*")) if p.is_file()
    }


def test_committed_set_present():
    assert len(GEN_TASKS) == 5, f"expected 5 generated tasks, found {[p.name for p in GEN_TASKS]}"


# --- 1. determinism: same seed -> byte-identical tasks ----------------------

def test_deterministic_same_seed(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    SyntheticProjectGenerator(seed=SEED, output_dir=a, id_start=2).generate_batch(5)
    SyntheticProjectGenerator(seed=SEED, output_dir=b, id_start=2).generate_batch(5)
    assert _hash_tree(a) == _hash_tree(b), "same seed must produce byte-identical task trees"


def test_committed_matches_seed(tmp_path):
    """The committed generated tasks reproduce exactly from (seed=43, id_start=2)."""
    regen = tmp_path / "regen"
    SyntheticProjectGenerator(seed=SEED, output_dir=regen, id_start=2).generate_batch(5)
    for t in GEN_TASKS:
        for f in ("metadata.json", "files/constraints.sdc", "solution/constraints.sdc",
                  "files/spec.md", "files/design_netlist.v", "hidden/spec_truth.json"):
            assert (regen / t.name / f).read_bytes() == (t / f).read_bytes(), f"{t.name}/{f} drifted"


# --- 2. seed diversity ------------------------------------------------------

def test_seed_diversity(tmp_path):
    def vec(seed):
        g = SyntheticProjectGenerator(seed=seed, output_dir=tmp_path / str(seed), id_start=2)
        return [tuple(p[k] for k in ("drift", "T", "I", "O", "U")) for p in (g._solve() for _ in range(5))]
    assert vec(SEED) != vec(SEED + 1), "different seeds must produce different parameterized tasks"


# --- 3. generated public scripts reference no hidden artifacts --------------

@pytest.mark.parametrize("task", GEN_TASKS, ids=lambda p: p.name)
def test_public_scripts_no_hidden_refs(task):
    for name in ("run_public.sh", "run_public.tcl"):
        text = (task / "files" / name).read_text()
        for leak in ("spec_truth.json", "grade_spec", "run_hidden", "run_signoff", "CONSTRAINT_SPEC"):
            assert leak not in text, f"{task.name}/{name} leaks oracle reference '{leak}'"


# --- 4. generated workspace runnable without hidden files -------------------

@pytest.mark.parametrize("task", GEN_TASKS, ids=lambda p: p.name)
def test_workspace_runnable_without_hidden(task):
    meta = json.loads((task / "metadata.json").read_text())
    reads = _reads((task / "files" / "run_public.tcl").read_text())
    assert {"design_netlist.v", "tiny.db", "constraints.sdc"} <= reads
    ws = create_agent_workspace(task, meta)
    try:
        present = {p.name for p in ws.iterdir() if p.is_file()}
        for fname in reads:
            assert (ws / fname).is_file(), f"{task.name}: run_public reads '{fname}' absent from workspace"
        for hid in meta["files"]["hidden"]:
            assert Path(hid).name not in present, f"{task.name}: hidden '{hid}' leaked into workspace"
    finally:
        shutil.rmtree(ws, ignore_errors=True)


# --- 5. golden vs mutant score separation -----------------------------------

@pytest.mark.parametrize("task", GEN_TASKS, ids=lambda p: p.name)
def test_golden_mutant_separation(task):
    golden_sdc = (task / "solution" / "constraints.sdc").read_text()
    mutant_sdc = (task / "files" / "constraints.sdc").read_text()
    g_total, g_obj, g_pass = _score(task, _marker_log(task, golden_sdc, signoff_ok=True))
    m_total, m_obj, m_pass = _score(task, _marker_log(task, mutant_sdc, signoff_ok=False))
    assert g_pass and abs(g_total - 1.0) < 1e-9, f"{task.name} golden total={g_total}"
    assert not m_pass, f"{task.name} mutant must fail the gate, total={m_total}"
    assert (g_obj - m_obj) >= 0.15, f"{task.name} golden-mutant objective margin {g_obj - m_obj} < 0.15"


def test_golden_and_mutant_differ_one_line():
    for task in GEN_TASKS:
        g = (task / "solution" / "constraints.sdc").read_text().splitlines()
        m = (task / "files" / "constraints.sdc").read_text().splitlines()
        assert len(g) == len(m)
        diffs = [(x, y) for x, y in zip(g, m) if x != y]
        assert len(diffs) == 1, f"{task.name}: expected one differing line, got {diffs}"


# --- 6. masking / over-constrain not full credit ----------------------------

@pytest.mark.parametrize("task", GEN_TASKS, ids=lambda p: p.name)
def test_masking_not_full_credit(task):
    gs = _grade_spec(task)
    truth = json.loads((task / "hidden" / "spec_truth.json").read_text())
    golden = (task / "solution" / "constraints.sdc").read_text()
    masks = {
        "loosen_period": re.sub(r"-period \S+", "-period 99.0", golden),
        "inflate_uncertainty": re.sub(r"set_clock_uncertainty \S+", "set_clock_uncertainty 5.0", golden),
        "zero_output": re.sub(r"set_output_delay\s+\S+", "set_output_delay 0.0", golden),
        "zero_input": re.sub(r"set_input_delay\s+\S+", "set_input_delay 0.0", golden),
        "false_path": golden + "set_false_path -from [get_ports din]\n",
    }
    for name, text in masks.items():
        full, frac, _ = gs.score_spec(text, truth)
        assert not full and frac < 1.0, f"{task.name}: masking '{name}' wrongly got full credit"
    # the genuine fix is still full credit
    full, frac, _ = gs.score_spec(golden, truth)
    assert full and frac == 1.0, f"{task.name}: golden should be full credit"


# --- 7. schema / inventory validity -----------------------------------------

@pytest.mark.parametrize("task", GEN_TASKS, ids=lambda p: p.name)
def test_schema_and_structural_valid(task):
    meta = json.loads((task / "metadata.json").read_text())
    assert validate_metadata(meta) == [], f"{task.name} metadata invalid"
    assert structural_validate(task) == [], f"{task.name} structurally invalid"
    assert meta["track"] == "p10_synthetic_project"
    assert re.match(r"^syn_proj_000[2-6]$", meta["task_id"])
    assert meta["files"]["editable"] == ["constraints.sdc"]


# --- 8. no literal-answer leak ----------------------------------------------

@pytest.mark.parametrize("task", GEN_TASKS, ids=lambda p: p.name)
def test_no_literal_answer_leak(task):
    meta = json.loads((task / "metadata.json").read_text())
    truth = json.loads((task / "hidden" / "spec_truth.json").read_text())
    drift = meta["generator"]["params"]["drift_type"]
    target = {
        "output_delay": truth["output_delay"]["value_ns"],
        "input_delay": truth["input_delay"]["value_ns"],
        "uncertainty": truth["clock"]["uncertainty_ns"],
    }[drift]
    visible = "".join((task / "files" / f).read_text()
                      for f in meta["files"]["visible"] if not f.endswith((".db",)))
    assert not _has_token(visible, target), (
        f"{task.name}: drifted property ({drift}) value {_fmt(target)} leaks as a literal in files/")


# --- 9. verdict-first public runner (the Phase-0D feedback fix) --------------

# A mock pt_shell that emits a >1000-byte banner BEFORE the verdict, mimicking the real
# PrimeTime license banner that previously pushed PUBLIC_SIGNOFF past the agent's obs cap.
_MOCK_PT = """#!/bin/bash
# ignore args (-f run_public.tcl); emit banner-then-verdict like real pt_shell
printf 'PrimeTime (R) license banner padding %s\\n' $(seq 1 60)
echo "=== WORST SETUP PATH ==="
echo "PUBLIC_SIGNOFF: VIOLATION worst_slack=-0.300000"
echo "PUBLIC_HINT: inspect constraints.sdc against spec.md timing budgets"
echo "  long timing detail line ......................................"
echo "PUBLIC_DONE"
"""


def _run_public_with_mock(task: Path, tmp_path: Path) -> str:
    meta = json.loads((task / "metadata.json").read_text())
    ws = create_agent_workspace(task, meta)
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


@pytest.mark.parametrize("task", GEN_TASKS, ids=lambda p: p.name)
def test_public_verdict_within_first_1000_bytes(task, tmp_path):
    """PUBLIC_SIGNOFF must be hoisted to the top of run_public.sh stdout, even when the
    underlying pt_shell prints a >1000-byte banner first (the Phase-0D feedback bug)."""
    out = _run_public_with_mock(task, tmp_path)
    off = out.find("PUBLIC_SIGNOFF:")
    assert off != -1, f"{task.name}: PUBLIC_SIGNOFF absent from public stdout"
    assert off < 1000, f"{task.name}: PUBLIC_SIGNOFF at byte {off} (>=1000) — verdict not hoisted"
    assert "PUBLIC_HINT:" in out


@pytest.mark.parametrize("task", GEN_TASKS, ids=lambda p: p.name)
def test_public_stdout_no_hidden_oracle_markers(task, tmp_path):
    """Public stdout must never carry hidden-oracle fields."""
    out = _run_public_with_mock(task, tmp_path)
    for leak in ("CONSTRAINT_SPEC", "spec_truth", "grade_spec", "run_hidden", "run_signoff"):
        assert leak not in out, f"{task.name}: public stdout leaks '{leak}'"


# --- 10. agentic evaluator DISPATCH (the Phase-0D dispatch-bug fix) ----------
# The agentic runner has its own _select_evaluator; before the fix it had no
# p10 branch, so every p10 agentic episode silently fell through to the
# VCSRTLEvaluator default -> "Unknown component" for constraint_spec/signoff ->
# 0.10 floor regardless of the agent's edit. These tests pin the dispatch.

def _spec_of(ev) -> str:
    """Reconstruct the 'module.Class' evaluator-spec string from an instance."""
    return f"{type(ev).__module__.split('.')[-1]}.{type(ev).__name__}"


@pytest.mark.parametrize("task", GEN_TASKS, ids=lambda p: p.name)
def test_agentic_dispatch_selects_synthetic_evaluator(task):
    meta = json.loads((task / "metadata.json").read_text())
    ev = _select_evaluator(meta, task)
    assert isinstance(ev, SyntheticProjectEvaluator), (
        f"{task.name}: agentic dispatch returned {type(ev).__name__}, "
        "not SyntheticProjectEvaluator (regression for the dispatch bug)")


@pytest.mark.parametrize("task", GEN_TASKS, ids=lambda p: p.name)
def test_agentic_and_cli_dispatch_do_not_diverge(task):
    """The agentic _select_evaluator must resolve the SAME evaluator the metadata
    declares (the spec cli.py resolves in submission mode) — no silent fallback."""
    meta = json.loads((task / "metadata.json").read_text())
    declared = meta["scoring"]["evaluator"]
    assert declared == "synthetic_project.SyntheticProjectEvaluator"
    ev = _select_evaluator(meta, task)
    assert _spec_of(ev) == declared, (
        f"{task.name}: agentic dispatch resolved '{_spec_of(ev)}' but metadata "
        f"declares '{declared}' — agentic/CLI dispatch diverge")


# --- 11. agentic-PATH grading: correct -> 1.0, masking -> partial -----------

def _agentic_score(task: Path, log: str) -> tuple[float, float, bool]:
    """Grade through the evaluator the AGENTIC runner selects, exactly as runner.py
    does (mode='submission' over scoring.weights with the hidden marker log).
    Mirrors eda_agentbench/agentic/runner.py lines ~166-197."""
    meta = json.loads((task / "metadata.json").read_text())
    ev = _select_evaluator(meta, task)
    comps = [ev.evaluate_component(c, task, log, mode="submission")
             for c in meta["scoring"]["weights"]]
    total = sum(c.weighted_score for c in comps)
    obj = sum(c.weighted_score for c in comps if c.name != "explanation")
    return total, obj, total >= 0.5


@pytest.mark.parametrize("task", GEN_TASKS, ids=lambda p: p.name)
def test_agentic_correct_edit_scores_full(task):
    """A spec-correct constraints.sdc scores 1.0 through the agentic grading path
    (the dispatch bug previously floored this at 0.10)."""
    golden = (task / "solution" / "constraints.sdc").read_text()
    total, _obj, passed = _agentic_score(task, _marker_log(task, golden, signoff_ok=True))
    assert passed and abs(total - 1.0) < 1e-9, f"{task.name}: agentic correct edit total={total}"


@pytest.mark.parametrize("task", GEN_TASKS, ids=lambda p: p.name)
def test_agentic_masking_edit_partial_not_full(task):
    """A masking edit that makes sign-off pass but drifts the period from spec must get
    PARTIAL credit (sign-off only), never full, through the agentic grading path."""
    golden = (task / "solution" / "constraints.sdc").read_text()
    masking = re.sub(r"-period \S+", "-period 99.0", golden)   # sign-off passes, spec drifts
    total, _obj, passed = _agentic_score(task, _marker_log(task, masking, signoff_ok=True))
    assert not passed, f"{task.name}: masking edit wrongly passed the gate, total={total}"
    assert 0.0 < total < 1.0, f"{task.name}: masking edit total={total} not partial credit"

