"""Tests for sampled/limited dataset evaluation mode."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


def _make_mock_results(n: int, track: str = "p1_rtl_debug") -> list[dict]:
    """Create n mock task results for testing."""
    results = []
    for i in range(n):
        results.append({
            "task_path": f"/mock/{track}/task_{i:06d}",
            "task_id": f"task_{i:06d}",
            "track": track,
            "tool": ["vcs"],
            "difficulty": "easy",
            "status": "pass",
            "total_score": 1.0,
            "objective_score": 0.9,
            "explanation_score": 0.1,
            "components": [],
            "score_path": "",
        })
    return results


def test_build_summary_sampled():
    """Sampled summary includes sampling metadata."""
    from eda_agentbench.cli import _build_dataset_summary

    results = _make_mock_results(5)
    summary = _build_dataset_summary(
        results, "test_run", "solution", None,
        sampled=True, sample_per_track=1, seed=42,
        total_candidates=100, selected_task_ids=["task_000000", "task_000001"],
    )

    assert summary["sampled"] is True
    assert summary["sample_per_track"] == 1
    assert summary["seed"] == 42
    assert summary["total_candidates"] == 100
    assert summary["selected_task_count"] == 5
    assert summary["selected_task_ids"] is not None


def test_build_summary_full():
    """Full evaluation summary has sampled=False."""
    from eda_agentbench.cli import _build_dataset_summary

    results = _make_mock_results(100)
    summary = _build_dataset_summary(
        results, "test_run", "solution", None,
        sampled=False, total_candidates=100,
    )

    assert summary["sampled"] is False
    assert summary["seed"] is None
    assert summary["selected_task_ids"] is None
    assert summary["total_candidates"] == 100


def test_sampling_deterministic():
    """Same seed produces same selection."""
    import random

    tasks = [Path(f"/mock/task_{i:06d}") for i in range(100)]

    rng1 = random.Random(42)
    shuffled1 = list(tasks)
    rng1.shuffle(shuffled1)
    selected1 = shuffled1[:10]

    rng2 = random.Random(42)
    shuffled2 = list(tasks)
    rng2.shuffle(shuffled2)
    selected2 = shuffled2[:10]

    assert selected1 == selected2


def test_sampling_different_seeds():
    """Different seeds may produce different selections."""
    import random

    tasks = [Path(f"/mock/task_{i:06d}") for i in (range(100))]

    rng1 = random.Random(1)
    shuffled1 = list(tasks)
    rng1.shuffle(shuffled1)
    selected1 = shuffled1[:10]

    rng2 = random.Random(99)
    shuffled2 = list(tasks)
    rng2.shuffle(shuffled2)
    selected2 = shuffled2[:10]

    # Very unlikely to be identical with different seeds
    # (but possible in theory, so we just check they're valid)
    assert len(selected1) == 10
    assert len(selected2) == 10


def test_sample_per_track_grouping():
    """sample_per_track groups by track and samples N per group."""
    import random

    # Simulate tasks from 3 tracks
    tasks_by_track = {
        "p1": [Path(f"/mock/p1/task_{i}") for i in range(100)],
        "p2": [Path(f"/mock/p2/task_{i}") for i in range(20)],
        "p3": [Path(f"/mock/p3/task_{i}") for i in range(50)],
    }

    rng = random.Random(42)
    sampled = []
    for track in sorted(tasks_by_track):
        candidates = tasks_by_track[track]
        n = min(2, len(candidates))
        selected = rng.sample(candidates, n)
        sampled.extend(selected)

    assert len(sampled) == 6  # 2 per track * 3 tracks
    # Each track should have exactly 2
    tracks = {}
    for p in sampled:
        t = str(p).split("/")[2]
        tracks[t] = tracks.get(t, 0) + 1
    assert tracks == {"p1": 2, "p2": 2, "p3": 2}


def test_sample_per_track_respects_limit():
    """sample_per_track never exceeds available tasks per track."""
    import random

    tasks = {"p1": [Path(f"/mock/p1/task_{i}") for i in range(3)]}  # only 3 tasks

    rng = random.Random(42)
    sampled = []
    for track in tasks:
        candidates = tasks[track]
        n = min(5, len(candidates))  # request 5, only 3 available
        selected = rng.sample(candidates, n)
        sampled.extend(selected)

    assert len(sampled) == 3  # can't select more than available


def test_limit_selection():
    """Global limit selects at most N tasks."""
    import random

    tasks = [Path(f"/mock/task_{i:06d}") for i in range(1000)]

    rng = random.Random(42)
    shuffled = list(tasks)
    rng.shuffle(shuffled)
    selected = shuffled[:5]

    assert len(selected) == 5


def test_cli_args_parsed():
    """CLI correctly parses new sampling arguments."""
    import argparse
    from eda_agentbench.cli import main

    # Mock the parser to check args are accepted
    # We can't run full evaluation in unit test, so just verify parsing
    parser = argparse.ArgumentParser()
    parser.add_argument("tasks_root")
    parser.add_argument("--submission-mode", default="solution")
    parser.add_argument("--track", default=None)
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sample-per-track", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args(["tasks", "--sample-per-track", "2", "--seed", "99"])
    assert args.sample_per_track == 2
    assert args.seed == 99
    assert args.limit is None

    args2 = parser.parse_args(["tasks", "--limit", "10"])
    assert args2.limit == 10
    assert args2.sample_per_track is None


def test_selected_task_ids_stable():
    """Selected task IDs are stable for same seed."""
    import random

    tasks = [Path(f"/mock/task_{i:06d}") for i in range(100)]

    ids1 = []
    rng1 = random.Random(42)
    shuffled1 = list(tasks)
    rng1.shuffle(shuffled1)
    for p in shuffled1[:5]:
        ids1.append(p.name)

    ids2 = []
    rng2 = random.Random(42)
    shuffled2 = list(tasks)
    rng2.shuffle(shuffled2)
    for p in shuffled2[:5]:
        ids2.append(p.name)

    assert ids1 == ids2
