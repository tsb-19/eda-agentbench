"""Tests for the P1 RTL Debug generator."""

import json
from pathlib import Path

import pytest

from generators.p1_rtl_debug_gen import P1RTLDebugGenerator, BUG_TYPES
from eda_agentbench.schema import validate_metadata


def test_generator_deterministic(tmp_path):
    """Same seed produces identical output."""
    gen1 = P1RTLDebugGenerator(seed=42, output_dir=tmp_path / "a")
    gen2 = P1RTLDebugGenerator(seed=42, output_dir=tmp_path / "b")
    p1 = gen1.generate_one(0)
    p2 = gen2.generate_one(0)
    meta1 = json.loads((p1 / "metadata.json").read_text())
    meta2 = json.loads((p2 / "metadata.json").read_text())
    assert meta1["generator"]["bug_type"] == meta2["generator"]["bug_type"]
    assert (p1 / "files" / "design.sv").read_text() == (p2 / "files" / "design.sv").read_text()
    assert (p1 / "solution" / "design.sv").read_text() == (p2 / "solution" / "design.sv").read_text()


def test_generator_different_seeds(tmp_path):
    """Different seeds may produce different bug types."""
    gen1 = P1RTLDebugGenerator(seed=1, output_dir=tmp_path / "a")
    gen2 = P1RTLDebugGenerator(seed=99, output_dir=tmp_path / "b")
    p1 = gen1.generate_one(0)
    p2 = gen2.generate_one(0)
    meta1 = json.loads((p1 / "metadata.json").read_text())
    meta2 = json.loads((p2 / "metadata.json").read_text())
    valid_names = {bt()["name"] for bt in BUG_TYPES}
    assert meta1["generator"]["bug_type"] in valid_names
    assert meta2["generator"]["bug_type"] in valid_names


def test_generator_metadata_valid(tmp_path):
    """Generated task metadata passes schema validation."""
    gen = P1RTLDebugGenerator(seed=42, output_dir=tmp_path)
    p = gen.generate_one(0)
    meta = json.loads((p / "metadata.json").read_text())
    errors = validate_metadata(meta)
    assert errors == [], f"Metadata validation errors: {errors}"


def test_generator_files_exist(tmp_path):
    """All required files are created."""
    gen = P1RTLDebugGenerator(seed=42, output_dir=tmp_path)
    p = gen.generate_one(0)
    assert (p / "metadata.json").is_file()
    assert (p / "prompt.md").is_file()
    assert (p / "files" / "design.sv").is_file()
    assert (p / "files" / "tb_public.sv").is_file()
    assert (p / "files" / "run_public.sh").is_file()
    assert (p / "hidden" / "tb_hidden.sv").is_file()
    assert (p / "hidden" / "run_hidden.sh").is_file()
    assert (p / "solution" / "design.sv").is_file()


def test_generator_buggy_differs_from_solution(tmp_path):
    """Buggy design is different from solution."""
    gen = P1RTLDebugGenerator(seed=42, output_dir=tmp_path)
    p = gen.generate_one(0)
    buggy = (p / "files" / "design.sv").read_text()
    solution = (p / "solution" / "design.sv").read_text()
    assert buggy != solution, "Buggy and solution should differ"


def test_generator_batch_creates_count(tmp_path):
    """generate_batch creates the requested number of tasks."""
    gen = P1RTLDebugGenerator(seed=42, output_dir=tmp_path)
    paths = gen.generate_batch(5)
    assert len(paths) == 5
    for p in paths:
        assert (p / "metadata.json").is_file()


def test_generator_distribution_balanced(tmp_path):
    """20 tasks should cover all 10 bug types, 2 each."""
    from collections import Counter
    gen = P1RTLDebugGenerator(seed=42, output_dir=tmp_path)
    paths = gen.generate_batch(20)
    types = Counter()
    for p in paths:
        meta = json.loads((p / "metadata.json").read_text())
        types[meta["generator"]["bug_type"]] += 1
    expected = {
        "sensitivity_list", "blocking_nonblocking", "reset_polarity",
        "width_truncation", "comparison_boundary", "wrong_mux_select",
        "priority_order", "fsm_transition_error", "counter_off_by_one",
        "enable_condition",
    }
    assert set(types.keys()) == expected, f"Bug types mismatch: got {set(types.keys())}"
    for bt in expected:
        assert types[bt] == 2, f"{bt}: expected 2, got {types[bt]}"


def test_generator_validate_sample_tasks(tmp_path):
    """Sample generated tasks pass structural validation."""
    gen = P1RTLDebugGenerator(seed=42, output_dir=tmp_path)
    from eda_agentbench.task.loader import TaskLoader
    loader = TaskLoader(tmp_path)
    paths = gen.generate_batch(3)
    for p in paths:
        meta = loader.load(p)  # raises on failure
        assert meta["track"] == "p1_rtl_debug"
