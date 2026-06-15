"""Tests for P6 DC Constraint Debug: schema, generator, evaluator, anti-cheat."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from eda_agentbench.schema import validate_metadata
from eda_agentbench.task.loader import TaskLoader, TaskValidationError

SMOKE_DIR = Path(__file__).resolve().parent.parent / "tasks" / "p6_dc_constraint_debug" / "smoke"
GENERATED_DIR = Path(__file__).resolve().parent.parent / "tasks" / "p6_dc_constraint_debug" / "generated"


# --- Schema Validation ---

def test_smoke_metadata_valid():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "metadata.json").read_text())
    errors = validate_metadata(meta)
    assert errors == [], f"Metadata errors: {errors}"


def test_smoke_task_id_format():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "metadata.json").read_text())
    assert meta["task_id"].startswith("dc_constraint_")


def test_smoke_track_is_p6():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "metadata.json").read_text())
    assert meta["track"] == "p6_dc_constraint_debug"


def test_smoke_tool_is_dc():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "metadata.json").read_text())
    assert "dc" in meta["tool"]


def test_smoke_weights_sum_to_one():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "metadata.json").read_text())
    total = sum(meta["scoring"]["weights"].values())
    assert abs(total - 1.0) < 0.01, f"Weights sum to {total}"


def test_smoke_files_exist():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "metadata.json").read_text())
    for f in meta["files"]["visible"]:
        assert (SMOKE_DIR / "files" / f).is_file(), f"Visible file missing: {f}"
    for f in meta["files"]["hidden"]:
        assert (SMOKE_DIR / "hidden" / f).is_file(), f"Hidden file missing: {f}"
    assert (SMOKE_DIR / "solution").is_dir()


def test_smoke_editable_subset_of_visible():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "metadata.json").read_text())
    visible = set(meta["files"]["visible"])
    editable = set(meta["files"]["editable"])
    assert editable.issubset(visible)


def test_smoke_constraints_sdc_is_editable():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "metadata.json").read_text())
    assert meta["files"]["editable"] == ["constraints.sdc"]


def test_smoke_design_v_is_forbidden():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "metadata.json").read_text())
    assert "design.v" in meta["files"]["forbidden"]


def test_smoke_solution_differs_from_buggy():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    buggy = (SMOKE_DIR / "files" / "constraints.sdc").read_text()
    solution = (SMOKE_DIR / "solution" / "constraints.sdc").read_text()
    assert buggy != solution


def test_smoke_run_scripts_are_executable():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    assert (SMOKE_DIR / "files" / "run_public.sh").stat().st_mode & 0o111
    assert (SMOKE_DIR / "hidden" / "run_hidden.sh").stat().st_mode & 0o111


# --- Generator Tests ---

def test_generator_deterministic(tmp_path):
    from generators.p6_dc_constraint_debug_gen import P6DCConstraintDebugGenerator
    gen1 = P6DCConstraintDebugGenerator(seed=42, output_dir=tmp_path / "a")
    gen2 = P6DCConstraintDebugGenerator(seed=42, output_dir=tmp_path / "b")
    p1 = gen1.generate_one(0)
    p2 = gen2.generate_one(0)
    meta1 = json.loads((p1 / "metadata.json").read_text())
    meta2 = json.loads((p2 / "metadata.json").read_text())
    assert meta1["task_id"] == meta2["task_id"]
    assert meta1["generator"]["bug_type"] == meta2["generator"]["bug_type"]
    assert (p1 / "files" / "constraints.sdc").read_text() == (p2 / "files" / "constraints.sdc").read_text()


def test_generator_metadata_valid(tmp_path):
    from generators.p6_dc_constraint_debug_gen import P6DCConstraintDebugGenerator
    gen = P6DCConstraintDebugGenerator(seed=42, output_dir=tmp_path)
    for i in range(12):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        errors = validate_metadata(meta)
        assert errors == [], f"Task {i} metadata errors: {errors}"


def test_generator_files_exist(tmp_path):
    from generators.p6_dc_constraint_debug_gen import P6DCConstraintDebugGenerator
    gen = P6DCConstraintDebugGenerator(seed=42, output_dir=tmp_path)
    p = gen.generate_one(0)
    assert (p / "metadata.json").is_file()
    assert (p / "prompt.md").is_file()
    assert (p / "files" / "design.v").is_file()
    assert (p / "files" / "constraints.sdc").is_file()
    assert (p / "files" / "run_public.sh").is_file()
    assert (p / "files" / "run_public.tcl").is_file()
    assert (p / "hidden" / "run_hidden.sh").is_file()
    assert (p / "hidden" / "run_hidden.tcl").is_file()
    assert (p / "solution" / "constraints.sdc").is_file()


def test_generator_buggy_differs_from_solution(tmp_path):
    from generators.p6_dc_constraint_debug_gen import P6DCConstraintDebugGenerator
    gen = P6DCConstraintDebugGenerator(seed=42, output_dir=tmp_path)
    for i in range(12):
        p = gen.generate_one(i)
        buggy = (p / "files" / "constraints.sdc").read_text()
        solution = (p / "solution" / "constraints.sdc").read_text()
        assert buggy != solution, f"Task {i}: buggy and solution should differ"


def test_generator_batch_creates_count(tmp_path):
    from generators.p6_dc_constraint_debug_gen import P6DCConstraintDebugGenerator
    gen = P6DCConstraintDebugGenerator(seed=42, output_dir=tmp_path)
    paths = gen.generate_batch(12)
    assert len(paths) == 12
    for p in paths:
        assert (p / "metadata.json").is_file()


def test_generator_bug_type_diversity(tmp_path):
    """12 tasks cover all 6 bug types (2 each)."""
    from collections import Counter
    from generators.p6_dc_constraint_debug_gen import P6DCConstraintDebugGenerator
    gen = P6DCConstraintDebugGenerator(seed=42, output_dir=tmp_path)
    paths = gen.generate_batch(12)
    types = Counter()
    for p in paths:
        meta = json.loads((p / "metadata.json").read_text())
        types[meta["generator"]["bug_type"]] += 1
    assert len(types) == 6, f"Expected 6 bug types, got {len(types)}"
    for bt, count in types.items():
        assert count == 2, f"{bt}: expected 2, got {count}"


def test_generator_rtl_diversity(tmp_path):
    """12 tasks cover 2 RTL templates (6 each)."""
    from collections import Counter
    from generators.p6_dc_constraint_debug_gen import P6DCConstraintDebugGenerator
    gen = P6DCConstraintDebugGenerator(seed=42, output_dir=tmp_path)
    paths = gen.generate_batch(12)
    templates = Counter()
    for p in paths:
        meta = json.loads((p / "metadata.json").read_text())
        templates[meta["generator"]["rtl_template"]] += 1
    assert len(templates) == 2
    for tmpl, count in templates.items():
        assert count == 6, f"{tmpl}: expected 6, got {count}"


def test_generator_unique_task_ids(tmp_path):
    from generators.p6_dc_constraint_debug_gen import P6DCConstraintDebugGenerator
    gen = P6DCConstraintDebugGenerator(seed=42, output_dir=tmp_path)
    ids = set()
    for i in range(12):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        assert meta["task_id"] not in ids
        ids.add(meta["task_id"])


def test_generator_validate_sample_tasks(tmp_path):
    from generators.p6_dc_constraint_debug_gen import P6DCConstraintDebugGenerator
    gen = P6DCConstraintDebugGenerator(seed=42, output_dir=tmp_path)
    loader = TaskLoader(tmp_path)
    paths = gen.generate_batch(3)
    for p in paths:
        meta = loader.load(p)
        assert meta["track"] == "p6_dc_constraint_debug"


def test_generator_only_reliable_categories(tmp_path):
    """All generated tasks use only the 6 reliable bug categories."""
    from generators.p6_dc_constraint_debug_gen import EXPECTED_BUG_TYPE_NAMES, P6DCConstraintDebugGenerator
    gen = P6DCConstraintDebugGenerator(seed=42, output_dir=tmp_path)
    paths = gen.generate_batch(12)
    for p in paths:
        meta = json.loads((p / "metadata.json").read_text())
        assert meta["generator"]["bug_type"] in EXPECTED_BUG_TYPE_NAMES


# --- Evaluator Tests (mocked, no DC) ---

def test_evaluator_loads():
    from eda_agentbench.evaluator.dc_constraint_debug import DCConstraintDebugEvaluator
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "metadata.json").read_text())
    evaluator = DCConstraintDebugEvaluator(SMOKE_DIR, meta)
    assert evaluator.weights == meta["scoring"]["weights"]


def test_evaluator_constraint_pass():
    """Constraint component passes when CONSTRAINTS_OK is present."""
    from eda_agentbench.evaluator.dc_constraint_debug import DCConstraintDebugEvaluator
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "metadata.json").read_text())
    evaluator = DCConstraintDebugEvaluator(SMOKE_DIR, meta)
    log = "some DC output\nCONSTRAINTS_OK\n"
    comp = evaluator.evaluate_component("constraint_pass", Path(), log)
    assert comp.raw_score == 1.0


def test_evaluator_constraint_fail():
    """Constraint component fails when CONSTRAINTS_FAIL is present."""
    from eda_agentbench.evaluator.dc_constraint_debug import DCConstraintDebugEvaluator
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "metadata.json").read_text())
    evaluator = DCConstraintDebugEvaluator(SMOKE_DIR, meta)
    log = "Error: Can't find clock\nCONSTRAINTS_FAIL: no_clocks_created\n"
    comp = evaluator.evaluate_component("constraint_pass", Path(), log)
    assert comp.raw_score == 0.0
    assert "no_clocks_created" in comp.details


def test_evaluator_constraint_fail_port_not_found():
    """Constraint component fails when port not found."""
    from eda_agentbench.evaluator.dc_constraint_debug import DCConstraintDebugEvaluator
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "metadata.json").read_text())
    evaluator = DCConstraintDebugEvaluator(SMOKE_DIR, meta)
    log = "CONSTRAINTS_FAIL: port_not_found:reset_n\n"
    comp = evaluator.evaluate_component("constraint_pass", Path(), log)
    assert comp.raw_score == 0.0
    assert "port_not_found" in comp.details


def test_evaluator_execution_pass():
    """Execution component passes when CONSTRAINTS_OK is present."""
    from eda_agentbench.evaluator.dc_constraint_debug import DCConstraintDebugEvaluator
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "metadata.json").read_text())
    evaluator = DCConstraintDebugEvaluator(SMOKE_DIR, meta)
    log = "DC output\nCONSTRAINTS_OK\n"
    comp = evaluator.evaluate_component("execution_pass", Path(), log)
    assert comp.raw_score == 1.0


def test_evaluator_execution_fail():
    """Execution component fails when CONSTRAINTS_FAIL is present."""
    from eda_agentbench.evaluator.dc_constraint_debug import DCConstraintDebugEvaluator
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "metadata.json").read_text())
    evaluator = DCConstraintDebugEvaluator(SMOKE_DIR, meta)
    log = "DC output\nCONSTRAINTS_FAIL: no_clocks_created\n"
    comp = evaluator.evaluate_component("execution_pass", Path(), log)
    assert comp.raw_score == 0.0


def test_evaluator_explanation_always_passes():
    from eda_agentbench.evaluator.dc_constraint_debug import DCConstraintDebugEvaluator
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "metadata.json").read_text())
    evaluator = DCConstraintDebugEvaluator(SMOKE_DIR, meta)
    comp = evaluator.evaluate_component("explanation", Path(), "", mode="submission")
    assert comp.raw_score == 1.0


def test_evaluator_unknown_component():
    from eda_agentbench.evaluator.dc_constraint_debug import DCConstraintDebugEvaluator
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "metadata.json").read_text())
    evaluator = DCConstraintDebugEvaluator(SMOKE_DIR, meta)
    comp = evaluator.evaluate_component("nonexistent", Path(), "")
    assert comp.raw_score == 0.0


def test_evaluator_fail_when_tool_did_not_run():
    """Regression: empty / no-marker / crash logs score 0.0 for both marker
    components -- never a false 1.0 (the same false-pass class as P5/P4/P1).
    A missing CONSTRAINTS_OK marker means DC never confirmed success."""
    from eda_agentbench.evaluator.dc_constraint_debug import DCConstraintDebugEvaluator
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "metadata.json").read_text())
    evaluator = DCConstraintDebugEvaluator(SMOKE_DIR, meta)
    for bad_log in ["", "random DC output, no markers\n", "Segmentation fault (core dumped)\n"]:
        for comp_name in ("constraint_pass", "execution_pass"):
            comp = evaluator.evaluate_component(comp_name, Path(), bad_log)
            assert comp.raw_score == 0.0, f"{comp_name} on {bad_log!r} should be 0.0, got {comp.raw_score}"


# --- Anti-Cheat Tests ---

def test_submission_forbidden_design_v(tmp_path):
    from eda_agentbench.task.validator import check_submission_forbidden
    sub = tmp_path / "submission"
    sub.mkdir()
    (sub / "constraints.sdc").write_text("create_clock -period 5 [get_ports {clk}]")
    (sub / "design.v").write_text("module counter; endmodule")
    violations = check_submission_forbidden(sub, ["design.v", "run_public.sh"])
    assert "design.v" in violations


def test_submission_clean(tmp_path):
    from eda_agentbench.task.validator import check_submission_forbidden
    sub = tmp_path / "submission"
    sub.mkdir()
    (sub / "constraints.sdc").write_text("create_clock -period 5 [get_ports {clk}]")
    violations = check_submission_forbidden(sub, ["design.v", "run_public.sh"])
    assert violations == []


# --- Generated Tasks Validation ---

def test_generated_metadata_valid():
    if not GENERATED_DIR.is_dir():
        pytest.skip("Generated tasks not created")
    for task_dir in sorted(GENERATED_DIR.iterdir()):
        if not task_dir.is_dir():
            continue
        meta = json.loads((task_dir / "metadata.json").read_text())
        errors = validate_metadata(meta)
        assert errors == [], f"{task_dir.name}: {errors}"


def test_generated_track_is_p6():
    if not GENERATED_DIR.is_dir():
        pytest.skip("Generated tasks not created")
    for task_dir in sorted(GENERATED_DIR.iterdir()):
        if not task_dir.is_dir():
            continue
        meta = json.loads((task_dir / "metadata.json").read_text())
        assert meta["track"] == "p6_dc_constraint_debug"


def test_generated_files_exist():
    if not GENERATED_DIR.is_dir():
        pytest.skip("Generated tasks not created")
    for task_dir in sorted(GENERATED_DIR.iterdir()):
        if not task_dir.is_dir():
            continue
        meta = json.loads((task_dir / "metadata.json").read_text())
        for f in meta["files"]["visible"]:
            assert (task_dir / "files" / f).is_file(), f"{task_dir.name}: visible file missing: {f}"
        for f in meta["files"]["hidden"]:
            assert (task_dir / "hidden" / f).is_file(), f"{task_dir.name}: hidden file missing: {f}"


def test_generated_no_raw_logs():
    if not GENERATED_DIR.is_dir():
        pytest.skip("Generated tasks not created")
    for ext in [".lis", ".log", ".raw", ".st0", ".sw0", ".trn", ".ac0", ".ic0"]:
        for f in GENERATED_DIR.rglob(f"*{ext}"):
            pytest.fail(f"Raw simulator output found: {f}")


def test_generated_tcl_has_constraint_checks():
    """Generated TCL scripts contain explicit constraint validation."""
    if not GENERATED_DIR.is_dir():
        pytest.skip("Generated tasks not created")
    for task_dir in sorted(GENERATED_DIR.iterdir()):
        if not task_dir.is_dir():
            continue
        tcl = (task_dir / "files" / "run_public.tcl").read_text()
        assert "all_clocks" in tcl, f"{task_dir.name}: missing clock check"
        assert "CONSTRAINTS_OK" in tcl, f"{task_dir.name}: missing CONSTRAINTS_OK"
        assert "CONSTRAINTS_FAIL" in tcl, f"{task_dir.name}: missing CONSTRAINTS_FAIL"


# --- Smoke Skip Behavior ---

def test_smoke_script_skips_gracefully(tmp_path):
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    import subprocess
    result = subprocess.run(
        ["bash", str(SMOKE_DIR / "files" / "run_public.sh")],
        cwd=SMOKE_DIR / "files",
        capture_output=True, text=True, timeout=30,
        env={"PATH": "/usr/bin:/bin", "EDA_DC_CMD": "nonexistent_dc_shell"},
    )
    assert "SKIP" in result.stdout or result.returncode == 0


# --- Schema: task_id pattern ---

def test_task_id_pattern_dc_constraint():
    meta = {
        "task_id": "dc_constraint_0042",
        "track": "p6_dc_constraint_debug",
        "tool": ["dc"],
        "difficulty": "easy",
        "data_type": "template_synthetic",
        "resource_preset": "standard",
        "timeout_sec": 300,
        "max_tool_calls": 30,
        "max_patch_attempts": 8,
        "max_output_tokens": 32000,
        "files": {
            "visible": ["a.txt"],
            "editable": ["a.txt"],
            "hidden": [],
            "forbidden": [],
        },
        "run_command": "echo ok",
        "scoring": {
            "weights": {"constraint_pass": 0.6, "execution_pass": 0.3, "explanation": 0.1},
        },
    }
    errors = validate_metadata(meta)
    assert errors == [], f"Unexpected errors: {errors}"
