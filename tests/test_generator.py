"""Tests for the P1 RTL Debug and P4 SPICE generators."""

import json
from pathlib import Path

import pytest

from generators.p1_rtl_debug_gen import P1RTLDebugGenerator, BUG_TYPES
from generators.p4_spice_gen import P4SPICEGenerator, _RC_CONFIGS
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
    """100 tasks should cover all 10 bug types, 10 each."""
    from collections import Counter
    gen = P1RTLDebugGenerator(seed=42, output_dir=tmp_path)
    paths = gen.generate_batch(100)
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
        assert types[bt] == 10, f"{bt}: expected 10, got {types[bt]}"


def test_generator_validate_sample_tasks(tmp_path):
    """Sample generated tasks pass structural validation."""
    gen = P1RTLDebugGenerator(seed=42, output_dir=tmp_path)
    from eda_agentbench.task.loader import TaskLoader
    loader = TaskLoader(tmp_path)
    paths = gen.generate_batch(3)
    for p in paths:
        meta = loader.load(p)  # raises on failure
        assert meta["track"] == "p1_rtl_debug"


# --- P4 SPICE generator tests ---

def test_p4_generator_deterministic(tmp_path):
    """Same seed produces identical P4 output."""
    gen1 = P4SPICEGenerator(seed=42, output_dir=tmp_path / "a")
    gen2 = P4SPICEGenerator(seed=42, output_dir=tmp_path / "b")
    p1 = gen1.generate_one(0)
    p2 = gen2.generate_one(0)
    meta1 = json.loads((p1 / "metadata.json").read_text())
    meta2 = json.loads((p2 / "metadata.json").read_text())
    assert meta1["task_id"] == meta2["task_id"]
    assert meta1["tool"] == meta2["tool"]


def test_p4_generator_metadata_valid(tmp_path):
    """Generated P4 task metadata passes schema validation."""
    gen = P4SPICEGenerator(seed=42, output_dir=tmp_path)
    for i in range(10):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        errors = validate_metadata(meta)
        assert errors == [], f"Task {i} metadata errors: {errors}"


def test_p4_generator_files_exist(tmp_path):
    """All required P4 files are created."""
    gen = P4SPICEGenerator(seed=42, output_dir=tmp_path)
    for i in range(10):
        p = gen.generate_one(i)
        assert (p / "metadata.json").is_file()
        assert (p / "prompt.md").is_file()
        assert (p / "solution").is_dir()


def test_p4_generator_tool_split(tmp_path):
    """10 tasks: first 5 HSPICE, last 5 Spectre."""
    gen = P4SPICEGenerator(seed=42, output_dir=tmp_path)
    tools = []
    for i in range(10):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        tools.append(meta["tool"][0])
    assert tools[:5] == ["hspice"] * 5
    assert tools[5:] == ["spectre"] * 5


def test_p4_generator_unique_task_ids(tmp_path):
    """All P4 tasks have unique task IDs."""
    gen = P4SPICEGenerator(seed=42, output_dir=tmp_path)
    ids = set()
    for i in range(10):
        p = gen.generate_one(i)
        meta = json.loads((p / "metadata.json").read_text())
        assert meta["task_id"] not in ids, f"Duplicate task_id: {meta['task_id']}"
        ids.add(meta["task_id"])
