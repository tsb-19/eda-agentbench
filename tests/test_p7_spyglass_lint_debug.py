"""Tests for P7 SpyGlass Lint Debug: schema, generator, evaluator, anti-cheat."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from eda_agentbench.schema import validate_metadata
from eda_agentbench.task.loader import TaskLoader, TaskValidationError

SMOKE_DIR = Path(__file__).resolve().parent.parent / "tasks" / "p7_spyglass_lint_debug" / "smoke"
GENERATED_DIR = Path(__file__).resolve().parent.parent / "tasks" / "p7_spyglass_lint_debug" / "generated"


# --- Schema Validation ---

def test_smoke_metadata_valid():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "sg_lint_0000" / "metadata.json").read_text())
    errors = validate_metadata(meta)
    assert errors == [], f"Metadata errors: {errors}"


def test_smoke_task_id_format():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "sg_lint_0000" / "metadata.json").read_text())
    assert meta["task_id"].startswith("sg_lint_")


def test_smoke_track_is_p7():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "sg_lint_0000" / "metadata.json").read_text())
    assert meta["track"] == "p7_spyglass_lint_debug"


def test_smoke_tool_is_spyglass():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "sg_lint_0000" / "metadata.json").read_text())
    assert "spyglass" in meta["tool"]


def test_smoke_weights_sum_to_one():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "sg_lint_0000" / "metadata.json").read_text())
    total = sum(meta["scoring"]["weights"].values())
    assert abs(total - 1.0) < 0.01, f"Weights sum to {total}"


def test_smoke_files_exist():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    task_dir = SMOKE_DIR / "sg_lint_0000"
    meta = json.loads((task_dir / "metadata.json").read_text())
    for f in meta["files"]["visible"]:
        assert (task_dir / "files" / f).is_file(), f"Visible file missing: {f}"
    for f in meta["files"]["hidden"]:
        assert (task_dir / "hidden" / f).is_file(), f"Hidden file missing: {f}"
    assert (task_dir / "solution").is_dir()


def test_smoke_editable_subset_of_visible():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "sg_lint_0000" / "metadata.json").read_text())
    visible = set(meta["files"]["visible"])
    editable = set(meta["files"]["editable"])
    assert editable.issubset(visible)


def test_smoke_design_v_is_editable():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "sg_lint_0000" / "metadata.json").read_text())
    assert "design.v" in meta["files"]["editable"]


def test_smoke_run_scripts_are_forbidden():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    meta = json.loads((SMOKE_DIR / "sg_lint_0000" / "metadata.json").read_text())
    forbidden = set(meta["files"]["forbidden"])
    assert "run_public.sh" in forbidden
    assert "run_public.tcl" in forbidden
    assert "run_hidden.sh" in forbidden
    assert "run_hidden.tcl" in forbidden
    assert "spyglass.prj" in forbidden


def test_smoke_solution_differs_from_buggy():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    task_dir = SMOKE_DIR / "sg_lint_0000"
    buggy = (task_dir / "files" / "design.v").read_text()
    solution = (task_dir / "solution" / "design.v").read_text()
    assert buggy != solution


def test_smoke_run_scripts_are_executable():
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    task_dir = SMOKE_DIR / "sg_lint_0000"
    assert (task_dir / "files" / "run_public.sh").stat().st_mode & 0o111
    assert (task_dir / "hidden" / "run_hidden.sh").stat().st_mode & 0o111


# --- Generator Tests ---

def test_generator_deterministic(tmp_path):
    """Same seed produces identical output."""
    from generators.p7_spyglass_lint_debug_gen import P7SpyGlassLintDebugGenerator
    gen1 = P7SpyGlassLintDebugGenerator(seed=42, output_dir=tmp_path / "a")
    gen2 = P7SpyGlassLintDebugGenerator(seed=42, output_dir=tmp_path / "b")
    p1 = gen1.generate_one(0)
    p2 = gen2.generate_one(0)
    meta1 = json.loads((p1 / "metadata.json").read_text())
    meta2 = json.loads((p2 / "metadata.json").read_text())
    assert meta1["generator"]["bug_type"] == meta2["generator"]["bug_type"]
    assert (p1 / "files" / "design.v").read_text() == (p2 / "files" / "design.v").read_text()
    assert (p1 / "solution" / "design.v").read_text() == (p2 / "solution" / "design.v").read_text()


def test_generator_different_seeds(tmp_path):
    """Different seeds may produce different bug types."""
    from generators.p7_spyglass_lint_debug_gen import P7SpyGlassLintDebugGenerator, EXPECTED_BUG_TYPE_NAMES
    gen1 = P7SpyGlassLintDebugGenerator(seed=1, output_dir=tmp_path / "a")
    gen2 = P7SpyGlassLintDebugGenerator(seed=99, output_dir=tmp_path / "b")
    p1 = gen1.generate_one(0)
    p2 = gen2.generate_one(0)
    meta1 = json.loads((p1 / "metadata.json").read_text())
    meta2 = json.loads((p2 / "metadata.json").read_text())
    assert meta1["generator"]["bug_type"] in EXPECTED_BUG_TYPE_NAMES
    assert meta2["generator"]["bug_type"] in EXPECTED_BUG_TYPE_NAMES


def test_generator_metadata_valid(tmp_path):
    """Generated task metadata passes schema validation."""
    from generators.p7_spyglass_lint_debug_gen import P7SpyGlassLintDebugGenerator
    gen = P7SpyGlassLintDebugGenerator(seed=42, output_dir=tmp_path)
    for i in range(8):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        errors = validate_metadata(meta)
        assert errors == [], f"Task {i} metadata errors: {errors}"


def test_generator_files_exist(tmp_path):
    """All required files are created."""
    from generators.p7_spyglass_lint_debug_gen import P7SpyGlassLintDebugGenerator
    gen = P7SpyGlassLintDebugGenerator(seed=42, output_dir=tmp_path)
    p = gen.generate_one(0)
    assert (p / "metadata.json").is_file()
    assert (p / "prompt.md").is_file()
    assert (p / "files" / "design.v").is_file()
    assert (p / "files" / "spyglass.prj").is_file()
    assert (p / "files" / "run_public.sh").is_file()
    assert (p / "files" / "run_public.tcl").is_file()
    assert (p / "hidden" / "run_hidden.sh").is_file()
    assert (p / "hidden" / "run_hidden.tcl").is_file()
    assert (p / "solution" / "design.v").is_file()


def test_generator_buggy_differs_from_solution(tmp_path):
    """Buggy design is different from solution."""
    from generators.p7_spyglass_lint_debug_gen import P7SpyGlassLintDebugGenerator
    gen = P7SpyGlassLintDebugGenerator(seed=42, output_dir=tmp_path)
    for i in range(8):
        p = gen.generate_one(i)
        buggy = (p / "files" / "design.v").read_text()
        solution = (p / "solution" / "design.v").read_text()
        assert buggy != solution, f"Task {i}: buggy and solution should differ"


def test_generator_batch_creates_count(tmp_path):
    """generate_batch creates the requested number of tasks."""
    from generators.p7_spyglass_lint_debug_gen import P7SpyGlassLintDebugGenerator
    gen = P7SpyGlassLintDebugGenerator(seed=42, output_dir=tmp_path)
    paths = gen.generate_batch(16)
    assert len(paths) == 16
    for p in paths:
        assert (p / "metadata.json").is_file()


def test_generator_distribution_balanced(tmp_path):
    """15 tasks should cover all 3 bug types, 5 each."""
    from collections import Counter
    from generators.p7_spyglass_lint_debug_gen import P7SpyGlassLintDebugGenerator, EXPECTED_BUG_TYPE_NAMES
    gen = P7SpyGlassLintDebugGenerator(seed=42, output_dir=tmp_path)
    paths = gen.generate_batch(15)
    types = Counter()
    for p in paths:
        meta = json.loads((p / "metadata.json").read_text())
        types[meta["generator"]["bug_type"]] += 1
    assert set(types.keys()) == set(EXPECTED_BUG_TYPE_NAMES), f"Bug types mismatch: got {set(types.keys())}"
    for bt in EXPECTED_BUG_TYPE_NAMES:
        assert types[bt] == 5, f"{bt}: expected 5, got {types[bt]}"


def test_generator_validate_sample_tasks(tmp_path):
    """Sample generated tasks pass structural validation."""
    from generators.p7_spyglass_lint_debug_gen import P7SpyGlassLintDebugGenerator
    gen = P7SpyGlassLintDebugGenerator(seed=42, output_dir=tmp_path)
    loader = TaskLoader(tmp_path)
    paths = gen.generate_batch(3)
    for p in paths:
        meta = loader.load(p)  # raises on failure
        assert meta["track"] == "p7_spyglass_lint_debug"


# --- Evaluator Tests ---

def test_evaluator_lint_pass():
    """Evaluator scores LINT_PASS as 1.0."""
    from eda_agentbench.evaluator.spyglass_lint_debug import SpyGlassLintDebugEvaluator
    meta = {
        "scoring": {"weights": {"lint_pass": 0.9, "explanation": 0.1}},
    }
    evaluator = SpyGlassLintDebugEvaluator(Path("/tmp"), meta)
    log = "Some output\nLINT_PASS\n"
    comp = evaluator.evaluate_component("lint_pass", Path("/tmp"), log)
    assert comp.raw_score == 1.0
    assert comp.weighted_score == 0.9


def test_evaluator_lint_fail():
    """Evaluator scores LINT_FAIL as 0.0."""
    from eda_agentbench.evaluator.spyglass_lint_debug import SpyGlassLintDebugEvaluator
    meta = {
        "scoring": {"weights": {"lint_pass": 0.9, "explanation": 0.1}},
    }
    evaluator = SpyGlassLintDebugEvaluator(Path("/tmp"), meta)
    log = "Some output\nLint violations: 3\nLINT_FAIL\n"
    comp = evaluator.evaluate_component("lint_pass", Path("/tmp"), log)
    assert comp.raw_score == 0.0
    assert comp.weighted_score == 0.0


def test_evaluator_crash():
    """Evaluator scores crash as 0.0."""
    from eda_agentbench.evaluator.spyglass_lint_debug import SpyGlassLintDebugEvaluator
    meta = {
        "scoring": {"weights": {"lint_pass": 0.9, "explanation": 0.1}},
    }
    evaluator = SpyGlassLintDebugEvaluator(Path("/tmp"), meta)
    log = "Segmentation fault\n"
    comp = evaluator.evaluate_component("lint_pass", Path("/tmp"), log)
    assert comp.raw_score == 0.0


def test_evaluator_no_markers():
    """Evaluator scores missing markers as 0.0."""
    from eda_agentbench.evaluator.spyglass_lint_debug import SpyGlassLintDebugEvaluator
    meta = {
        "scoring": {"weights": {"lint_pass": 0.9, "explanation": 0.1}},
    }
    evaluator = SpyGlassLintDebugEvaluator(Path("/tmp"), meta)
    log = "Some random output without markers\n"
    comp = evaluator.evaluate_component("lint_pass", Path("/tmp"), log)
    assert comp.raw_score == 0.0


def test_evaluator_explanation_submission():
    """Explanation component scores 1.0 in submission mode."""
    from eda_agentbench.evaluator.spyglass_lint_debug import SpyGlassLintDebugEvaluator
    meta = {
        "scoring": {"weights": {"lint_pass": 0.9, "explanation": 0.1}},
    }
    evaluator = SpyGlassLintDebugEvaluator(Path("/tmp"), meta)
    comp = evaluator.evaluate_component("explanation", Path("/tmp"), "", mode="submission")
    assert comp.raw_score == 1.0


def test_evaluator_unknown_component():
    """Unknown component scores 0.0."""
    from eda_agentbench.evaluator.spyglass_lint_debug import SpyGlassLintDebugEvaluator
    meta = {
        "scoring": {"weights": {"lint_pass": 0.9, "explanation": 0.1}},
    }
    evaluator = SpyGlassLintDebugEvaluator(Path("/tmp"), meta)
    comp = evaluator.evaluate_component("nonexistent", Path("/tmp"), "")
    assert comp.raw_score == 0.0


def test_evaluator_license_error():
    """Evaluator scores license checkout failure as crash (0.0)."""
    from eda_agentbench.evaluator.spyglass_lint_debug import SpyGlassLintDebugEvaluator
    meta = {
        "scoring": {"weights": {"lint_pass": 0.9, "explanation": 0.1}},
    }
    evaluator = SpyGlassLintDebugEvaluator(Path("/tmp"), meta)
    log = "Cannot checkout license for feature spyglass\n"
    comp = evaluator.evaluate_component("lint_pass", Path("/tmp"), log)
    assert comp.raw_score == 0.0


# --- Anti-Cheat Tests ---

def test_anti_cheat_forbidden_files():
    """Submission containing forbidden files should be rejected."""
    from eda_agentbench.task.validator import check_submission_forbidden
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    task_dir = SMOKE_DIR / "sg_lint_0000"
    meta = json.loads((task_dir / "metadata.json").read_text())

    # Create a submission that contains a forbidden file
    with tempfile.TemporaryDirectory() as tmp:
        sub = Path(tmp)
        (sub / "design.v").write_text("fixed")
        (sub / "run_public.sh").write_text("evil")  # forbidden!
        violations = check_submission_forbidden(sub, meta["files"]["forbidden"])
        assert len(violations) > 0, "Should detect forbidden file"


def test_anti_cheat_clean_submission():
    """Submission with only editable files should pass."""
    from eda_agentbench.task.validator import check_submission_forbidden
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    task_dir = SMOKE_DIR / "sg_lint_0000"
    meta = json.loads((task_dir / "metadata.json").read_text())

    with tempfile.TemporaryDirectory() as tmp:
        sub = Path(tmp)
        (sub / "design.v").write_text("fixed")
        violations = check_submission_forbidden(sub, meta["files"]["forbidden"])
        assert violations == [], f"Unexpected violations: {violations}"


# --- Run Script Tests ---

def test_run_script_skip_behavior():
    """Run script should skip gracefully when sg_shell is not available."""
    if not SMOKE_DIR.is_dir():
        pytest.skip("Smoke task not generated")
    task_dir = SMOKE_DIR / "sg_lint_0000"
    run_script = (task_dir / "files" / "run_public.sh").read_text()
    # Script should check for sg_shell and produce SKIP message
    assert "sg_shell" in run_script or "SG_CMD" in run_script
    assert "SKIP" in run_script


# --- Integration: Task Loader ---

def test_task_loader_discovers_p7():
    """Task loader discovers P7 tasks."""
    loader = TaskLoader(Path(__file__).resolve().parent.parent / "tasks")
    tasks = loader.discover(track="p7_spyglass_lint_debug")
    assert len(tasks) >= 1, "Should discover at least smoke task"


def test_task_loader_loads_generated():
    """Task loader can load all generated tasks."""
    if not GENERATED_DIR.is_dir():
        pytest.skip("Generated tasks not created")
    loader = TaskLoader(Path(__file__).resolve().parent.parent / "tasks")
    count = 0
    for d in sorted(GENERATED_DIR.iterdir()):
        if not d.is_dir():
            continue
        meta = loader.load(d)
        assert meta["track"] == "p7_spyglass_lint_debug"
        count += 1
    assert count > 0, "Should load at least one generated task"
