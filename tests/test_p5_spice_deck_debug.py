"""Tests for P5 SPICE Deck Debug: external loader, schema, evaluator, integration."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from eda_agentbench.task.external_loader import (
    load_manifest, load_grader_contract, validate_external_task, ExternalBundleError,
)
from eda_agentbench.schema import validate_metadata
from eda_agentbench.task.loader import TaskLoader, TaskValidationError

BUNDLE_ROOT = Path(__file__).resolve().parent.parent.parent / "eda-bench-prototypes" / "tasks_eval_private"
IMPORTED_ROOT = Path(__file__).resolve().parent.parent / "tasks" / "p5_spice_deck_debug" / "imported"


# --- Manifest Loading ---

def test_manifest_loads():
    """manifest.jsonl loads without error."""
    if not (BUNDLE_ROOT / "manifest.jsonl").is_file():
        pytest.skip("External bundle not available")
    entries = load_manifest(BUNDLE_ROOT / "manifest.jsonl")
    assert len(entries) == 100
    for e in entries:
        assert "task_id" in e
        assert "backend" in e
        assert "editable_files" in e


def test_manifest_required_fields():
    """Manifest entries have all required fields."""
    if not (BUNDLE_ROOT / "manifest.jsonl").is_file():
        pytest.skip("External bundle not available")
    entries = load_manifest(BUNDLE_ROOT / "manifest.jsonl")
    for e in entries:
        assert e["backend"] == "hspice"
        assert e["backend_env_var"] == "EDA_HSPICE_CMD"
        assert e["grader_contract_file"] == "grader_contract.json"
        assert len(e["editable_files"]) > 0


# --- Grader Contract Validation ---

def test_grader_contract_loads():
    """grader_contract.json loads and validates."""
    if not (BUNDLE_ROOT / "manifest.jsonl").is_file():
        pytest.skip("External bundle not available")
    contract_path = BUNDLE_ROOT / "spice_deck_debug_0001" / "grader_contract.json"
    contract = load_grader_contract(contract_path)
    assert contract["task_id"] == "spice_deck_debug_0001"
    assert contract["success_criteria"]["execution_based"] is True
    assert contract["success_criteria"]["exit_code"] == 0


def test_grader_contract_missing_file():
    """Missing grader_contract.json raises error."""
    with pytest.raises(ExternalBundleError, match="not found"):
        load_grader_contract(Path("/nonexistent/grader_contract.json"))


def test_grader_contract_requires_execution_based():
    """Grader contract must have execution_based=true."""
    tmp = Path(tempfile.mkdtemp())
    contract = {
        "task_id": "test",
        "success_criteria": {"execution_based": False},
        "command_template": "hspice {file}",
        "backend": "hspice",
    }
    (tmp / "grader_contract.json").write_text(json.dumps(contract))
    with pytest.raises(ExternalBundleError, match="execution_based"):
        load_grader_contract(tmp / "grader_contract.json")
    shutil.rmtree(tmp)


# --- External Task Validation ---

def test_validate_external_task_passes():
    """Valid external task passes validation."""
    if not (BUNDLE_ROOT / "manifest.jsonl").is_file():
        pytest.skip("External bundle not available")
    entries = load_manifest(BUNDLE_ROOT / "manifest.jsonl")
    task_dir = BUNDLE_ROOT / "spice_deck_debug_0001"
    errors = validate_external_task(task_dir, entries[0])
    assert errors == [], f"Unexpected errors: {errors}"


def test_validate_editable_under_visible():
    """Editable files must be under visible/."""
    if not (BUNDLE_ROOT / "manifest.jsonl").is_file():
        pytest.skip("External bundle not available")
    entry = {
        "task_id": "spice_deck_debug_0001",
        "backend": "hspice",
        "backend_env_var": "EDA_HSPICE_CMD",
        "editable_files": ["hidden/spice_deck_debug_0001_fixed.sp"],  # wrong: under hidden/
        "grader_contract_file": "grader_contract.json",
    }
    errors = validate_external_task(BUNDLE_ROOT / "spice_deck_debug_0001", entry)
    assert any("not under visible" in e for e in errors)


def test_validate_backend_env_var():
    """backend_env_var must be EDA_HSPICE_CMD."""
    if not (BUNDLE_ROOT / "manifest.jsonl").is_file():
        pytest.skip("External bundle not available")
    entry = {
        "task_id": "spice_deck_debug_0001",
        "backend": "hspice",
        "backend_env_var": "WRONG_VAR",
        "editable_files": ["visible/spice_deck_debug_0001_bug.sp"],
        "grader_contract_file": "grader_contract.json",
    }
    errors = validate_external_task(BUNDLE_ROOT / "spice_deck_debug_0001", entry)
    assert any("EDA_HSPICE_CMD" in e for e in errors)


# --- P5 Schema Conversion ---

def test_imported_metadata_valid():
    """Imported P5 task metadata passes schema validation."""
    if not IMPORTED_ROOT.is_dir():
        pytest.skip("P5 tasks not imported")
    for task_dir in sorted(IMPORTED_ROOT.iterdir()):
        if not task_dir.is_dir():
            continue
        meta = json.loads((task_dir / "metadata.json").read_text())
        errors = validate_metadata(meta)
        assert errors == [], f"{task_dir.name}: {errors}"


def test_imported_track_is_p5():
    """All imported tasks have track=p5_spice_deck_debug."""
    if not IMPORTED_ROOT.is_dir():
        pytest.skip("P5 tasks not imported")
    for task_dir in sorted(IMPORTED_ROOT.iterdir()):
        if not task_dir.is_dir():
            continue
        meta = json.loads((task_dir / "metadata.json").read_text())
        assert meta["track"] == "p5_spice_deck_debug"


def test_imported_task_id_format():
    """Imported task_id matches spice_deck_debug_NNNN pattern."""
    if not IMPORTED_ROOT.is_dir():
        pytest.skip("P5 tasks not imported")
    for task_dir in sorted(IMPORTED_ROOT.iterdir()):
        if not task_dir.is_dir():
            continue
        meta = json.loads((task_dir / "metadata.json").read_text())
        assert meta["task_id"].startswith("spice_deck_debug_")


def test_imported_has_grader_contract():
    """Every imported task has grader_contract.json."""
    if not IMPORTED_ROOT.is_dir():
        pytest.skip("P5 tasks not imported")
    for task_dir in sorted(IMPORTED_ROOT.iterdir()):
        if not task_dir.is_dir():
            continue
        assert (task_dir / "grader_contract.json").is_file(), f"{task_dir.name}: missing grader_contract.json"


def test_imported_no_raw_logs():
    """Imported tasks contain no raw simulator outputs."""
    if not IMPORTED_ROOT.is_dir():
        pytest.skip("P5 tasks not imported")
    for ext in [".lis", ".log", ".raw", ".st0", ".sw0", ".trn", ".ac0", ".ic0"]:
        for f in IMPORTED_ROOT.rglob(f"*{ext}"):
            pytest.fail(f"Raw simulator output found: {f}")


def test_imported_files_exist():
    """All visible and hidden files referenced in metadata exist."""
    if not IMPORTED_ROOT.is_dir():
        pytest.skip("P5 tasks not imported")
    for task_dir in sorted(IMPORTED_ROOT.iterdir()):
        if not task_dir.is_dir():
            continue
        meta = json.loads((task_dir / "metadata.json").read_text())
        for f in meta["files"]["visible"]:
            assert (task_dir / f).is_file(), f"{task_dir.name}: visible file missing: {f}"
        for f in meta["files"]["hidden"]:
            assert (task_dir / f).is_file(), f"{task_dir.name}: hidden file missing: {f}"


# --- P5 Evaluator (unit, no HSPICE) ---

def test_evaluator_loads_grader_contract():
    """SPICEDeckDebugEvaluator loads grader_contract.json."""
    if not IMPORTED_ROOT.is_dir():
        pytest.skip("P5 tasks not imported")
    from eda_agentbench.evaluator.spice_deck_debug import SPICEDeckDebugEvaluator
    task_dir = IMPORTED_ROOT / "spice_deck_debug_0001"
    meta = json.loads((task_dir / "metadata.json").read_text())
    evaluator = SPICEDeckDebugEvaluator(task_dir, meta)
    assert evaluator.contract["task_id"] == "spice_deck_debug_0001"


def test_evaluator_pass_on_concluded_log():
    """Evaluator passes when log contains 'job concluded'."""
    if not IMPORTED_ROOT.is_dir():
        pytest.skip("P5 tasks not imported")
    from eda_agentbench.evaluator.spice_deck_debug import SPICEDeckDebugEvaluator
    task_dir = IMPORTED_ROOT / "spice_deck_debug_0001"
    meta = json.loads((task_dir / "metadata.json").read_text())
    evaluator = SPICEDeckDebugEvaluator(task_dir, meta)
    log = "some output\n***** hspice job concluded\n"
    comp = evaluator.evaluate_component("execution_pass", Path(), log)
    assert comp.raw_score == 1.0


def test_evaluator_fail_on_abort_log():
    """Evaluator fails when log contains 'hspice job aborted'."""
    if not IMPORTED_ROOT.is_dir():
        pytest.skip("P5 tasks not imported")
    from eda_agentbench.evaluator.spice_deck_debug import SPICEDeckDebugEvaluator
    task_dir = IMPORTED_ROOT / "spice_deck_debug_0001"
    meta = json.loads((task_dir / "metadata.json").read_text())
    evaluator = SPICEDeckDebugEvaluator(task_dir, meta)
    log = "**error** model not found\n>error ***** hspice job aborted\n"
    comp = evaluator.evaluate_component("execution_pass", Path(), log)
    assert comp.raw_score == 0.0


def test_evaluator_explanation_always_passes():
    """Explanation component always scores 1.0 in submission mode."""
    if not IMPORTED_ROOT.is_dir():
        pytest.skip("P5 tasks not imported")
    from eda_agentbench.evaluator.spice_deck_debug import SPICEDeckDebugEvaluator
    task_dir = IMPORTED_ROOT / "spice_deck_debug_0001"
    meta = json.loads((task_dir / "metadata.json").read_text())
    evaluator = SPICEDeckDebugEvaluator(task_dir, meta)
    comp = evaluator.evaluate_component("explanation", Path(), "", mode="submission")
    assert comp.raw_score == 1.0


# --- Integration: P5 via CLI (requires HSPICE) ---

@pytest.fixture
def p5_task():
    if not IMPORTED_ROOT.is_dir():
        pytest.skip("P5 tasks not imported")
    return IMPORTED_ROOT / "spice_deck_debug_0001"


def test_p5_validate_task(p5_task):
    """eda-bench validate-task works for P5."""
    from eda_agentbench.cli import main
    import io, contextlib
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        main(["validate-task", str(p5_task)])
    output = f.getvalue()
    assert "VALID" in output
    assert "spice_deck_debug_0001" in output


def test_p5_solution_passes(p5_task):
    """P5 solution mode passes (requires HSPICE)."""
    from eda_agentbench.cli import _evaluate_single
    meta = json.loads((p5_task / "metadata.json").read_text())
    _, sr = _evaluate_single(p5_task, p5_task / "hidden", meta, 300)
    assert sr.total_score >= 0.9, f"Expected >= 0.9, got {sr.total_score}"
    assert sr.passed


def test_p5_buggy_fails(p5_task):
    """P5 buggy mode fails (requires HSPICE)."""
    from eda_agentbench.cli import _evaluate_single
    meta = json.loads((p5_task / "metadata.json").read_text())
    buggy_dir = Path(tempfile.mkdtemp(prefix="p5_test_"))
    for ef in meta["files"]["editable"]:
        src = p5_task / ef
        if src.is_file():
            shutil.copy2(src, buggy_dir / Path(ef).name)
    try:
        _, sr = _evaluate_single(p5_task, buggy_dir, meta, 300)
        assert sr.total_score < 0.5, f"Expected < 0.5, got {sr.total_score}"
        assert not sr.passed
    finally:
        shutil.rmtree(buggy_dir, ignore_errors=True)


def test_p5_equivalent_fix_passes(p5_task):
    """P5 accepts equivalent non-identical fix (requires HSPICE)."""
    from eda_agentbench.cli import _evaluate_single
    meta = json.loads((p5_task / "metadata.json").read_text())

    # Create a different but equivalent fix for task 1
    fix = Path(tempfile.mkdtemp(prefix="p5_fix_"))
    (fix / "my_fix.sp").write_text(
        ".title CMOS Inverter - Equivalent Fix\n"
        "M1 out gate vdd vdd pmos W=2u L=180n\n"
        "M2 out gate gnd gnd nmos W=1u L=180n\n"
        ".model pmos pmos (level=1 vto=-0.7 kp=50u)\n"
        ".model nmos nmos (level=1 vto=0.7 kp=120u)\n"
        "Vdd vdd gnd 1.8\n"
        "Vin gate gnd PULSE(0 1.8 1n 100p 100p 1n 2n)\n"
        ".tran 10p 4n\n"
        ".end\n"
    )
    try:
        _, sr = _evaluate_single(p5_task, fix, meta, 300)
        assert sr.total_score >= 0.9
        assert sr.passed
    finally:
        shutil.rmtree(fix, ignore_errors=True)


def test_p5_exact_diff_not_required(p5_task):
    """P5 does NOT require exact text match with oracle."""
    from eda_agentbench.evaluator.spice_deck_debug import SPICEDeckDebugEvaluator
    meta = json.loads((p5_task / "metadata.json").read_text())
    evaluator = SPICEDeckDebugEvaluator(p5_task, meta)
    # A successful HSPICE run with different content should pass
    log = "title: my custom fix\n***** hspice job concluded\n"
    comp = evaluator.evaluate_component("execution_pass", Path(), log)
    assert comp.raw_score == 1.0


# --- Report includes P5 ---

def test_report_includes_p5_track():
    """Report generation handles p5_spice_deck_debug track."""
    from eda_agentbench.cli import _build_dataset_summary
    results = [
        {"task_id": "spice_deck_debug_0001", "track": "p5_spice_deck_debug",
         "tool": ["hspice"], "difficulty": "easy", "status": "pass",
         "total_score": 1.0, "objective_score": 0.9, "explanation_score": 0.1,
         "components": [], "score_path": ""},
    ]
    summary = _build_dataset_summary(results, "test", "solution", "p5_spice_deck_debug")
    assert "p5_spice_deck_debug" in summary["per_track"]
    assert summary["per_track"]["p5_spice_deck_debug"]["total"] == 1
    assert summary["per_track"]["p5_spice_deck_debug"]["passed"] == 1


# --- Missing bundle fails clearly ---

def test_missing_bundle_manifest():
    """Missing manifest.jsonl raises clear error."""
    with pytest.raises(ExternalBundleError, match="not found"):
        load_manifest(Path("/nonexistent/manifest.jsonl"))
