"""Tests for benchmark summary export and report artifacts."""

from __future__ import annotations

import csv
import filecmp
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "export_benchmark_summary.py"
REPORTS_DIR = REPO_ROOT / "reports"

# The dataset grows whenever a track is scaled or added, so this gate does NOT freeze the total or
# the per-track counts (which made it go stale on every intended addition, e.g. 2884 -> 2892 when P9
# grew). Instead it derives the count live from the export's own inventory and asserts that:
#   (a) every artifact (distribution, stdout, markdown) agrees with the inventory — the export's
#       real contract — and
#   (b) all known CORE_TRACKS are present (a track silently vanishing is caught; new tracks are not
#       rejected, so additions never break the gate), and
#   (c) the total never collapses below a conservative floor (catches accidental mass task loss).
CORE_TRACKS = {
    "p1_rtl_debug",
    "p2_tb_sva_gen",
    "p3_timing_report_qa",
    "p4_spice_sim",
    "p5_spice_deck_debug",
    "p6_dc_synthesis_qa",
    "p6_dc_constraint_debug",
    "p7_spyglass_lint_debug",
    "p7_primetime_sta_debug",
    "p8_pnr_report_qa",
    "p9_pt_exception_debug",
}
MIN_TOTAL = 2800  # floor only: additions never trip it; a drop below it means tasks were lost


def _inventory() -> list[dict]:
    """The canonical per-task list the export produces — the live source of truth for counts."""
    with open(REPORTS_DIR / "task_inventory.json") as f:
        return json.load(f)


LEADERBOARD_REQUIRED_COLUMNS = [
    "model_name",
    "run_id",
    "date",
    "track",
    "task_count",
    "average_score",
    "pass_rate",
    "compile_rate",
    "tool_run_success_rate",
    "public_score",
    "hidden_score",
    "notes",
    "commit_sha",
    "evaluation_mode",
]


def _run_export(tmp_dir: Path | None = None) -> subprocess.CompletedProcess:
    """Run the export script and return the result."""
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=120,
    )


def _read_csv(path: Path) -> list[dict]:
    with open(path) as f:
        return list(csv.DictReader(f))


def _read_csv_rows(path: Path) -> list[list[str]]:
    with open(path) as f:
        return [row for row in csv.reader(f)]


class TestExportRuns:
    """Test that the export script runs successfully."""

    def test_export_runs_without_error(self):
        result = _run_export()
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        m = re.search(r"Loaded (\d+) tasks", result.stdout)
        assert m, f"missing 'Loaded N tasks' line in stdout:\n{result.stdout}"
        # the reported count must match the inventory it just wrote, and respect the floor
        n = int(m.group(1))
        assert n == len(_inventory()) >= MIN_TOTAL

    def test_all_artifacts_created(self):
        _run_export()
        expected_files = [
            "task_inventory.json",
            "task_inventory.csv",
            "track_distribution.csv",
            "tool_distribution.csv",
            "scoring_summary.csv",
            "p1_bug_distribution.csv",
            "p2_template_mutant_distribution.csv",
            "p3_question_type_distribution.csv",
            "p5_error_category_distribution.csv",
            "leaderboard_template.csv",
            "benchmark_summary.md",
        ]
        for fname in expected_files:
            assert (REPORTS_DIR / fname).exists(), f"Missing artifact: {fname}"


class TestTrackDistribution:
    """Test track distribution correctness."""

    def test_all_core_tracks_present(self):
        _run_export()
        rows = _read_csv(REPORTS_DIR / "track_distribution.csv")
        tracks = {r["track"] for r in rows}
        # superset: every known core track must be present; newly added tracks do not fail the gate
        assert CORE_TRACKS <= tracks, f"missing core tracks: {CORE_TRACKS - tracks}"

    def test_total_task_count(self):
        _run_export()
        rows = _read_csv(REPORTS_DIR / "track_distribution.csv")
        total = sum(int(r["count"]) for r in rows)
        # derived live: the distribution total must equal the inventory and clear the floor
        assert total == len(_inventory()) >= MIN_TOTAL

    def test_per_track_counts_match_inventory(self):
        _run_export()
        rows = _read_csv(REPORTS_DIR / "track_distribution.csv")
        dist = {r["track"]: int(r["count"]) for r in rows}
        inv_counts = dict(Counter(r["track"] for r in _inventory()))
        # the published per-track distribution must agree with the inventory grouping (no frozen
        # numbers to bump), and no track may be empty
        assert dist == inv_counts
        assert all(v > 0 for v in dist.values())


class TestP5Distribution:
    """Test P5 error category distribution."""

    def test_p5_categories_sum_to_100(self):
        _run_export()
        rows = _read_csv(REPORTS_DIR / "p5_error_category_distribution.csv")
        total = sum(int(r["count"]) for r in rows)
        assert total == 100

    def test_p5_has_expected_categories(self):
        _run_export()
        rows = _read_csv(REPORTS_DIR / "p5_error_category_distribution.csv")
        categories = {r["expected_error_category"] for r in rows}
        expected = {
            "missing_model",
            "duplicate_element",
            "wrong_pin_count",
            "unsupported_dialect",
            "missing_subckt",
            "missing_include",
            "invalid_directive",
        }
        assert categories == expected


class TestP3Distribution:
    """Test P3 question type distribution."""

    def test_p3_has_synthetic_and_pt_prototype(self):
        _run_export()
        rows = _read_csv(REPORTS_DIR / "p3_question_type_distribution.csv")
        total_synthetic = sum(int(r["synthetic_count"]) for r in rows)
        total_pt = sum(int(r["pt_prototype_count"]) for r in rows)
        assert total_synthetic > 0, "No synthetic P3 tasks found"
        assert total_pt == 8, f"Expected 8 PT prototype tasks, got {total_pt}"

    def test_p3_total_matches(self):
        _run_export()
        rows = _read_csv(REPORTS_DIR / "p3_question_type_distribution.csv")
        total = sum(int(r["total"]) for r in rows)
        assert total == 1008


class TestDeterminism:
    """Test that outputs are deterministic across runs."""

    def test_json_deterministic(self):
        _run_export()
        first = (REPORTS_DIR / "task_inventory.json").read_text()
        _run_export()
        second = (REPORTS_DIR / "task_inventory.json").read_text()
        assert first == second

    def test_csv_deterministic(self):
        _run_export()
        first = (REPORTS_DIR / "track_distribution.csv").read_text()
        _run_export()
        second = (REPORTS_DIR / "track_distribution.csv").read_text()
        assert first == second

    def test_markdown_deterministic(self):
        _run_export()
        first = (REPORTS_DIR / "benchmark_summary.md").read_text()
        _run_export()
        second = (REPORTS_DIR / "benchmark_summary.md").read_text()
        assert first == second


class TestNoRawLogs:
    """Test that no raw simulator logs are included in reports."""

    def test_no_raw_simulator_files(self):
        _run_export()
        raw_extensions = {".log", ".lis", ".raw", ".trn", ".st0", ".sw0", ".ac0", ".ic0"}
        for f in REPORTS_DIR.iterdir():
            if f.is_file():
                assert f.suffix not in raw_extensions, (
                    f"Raw simulator log found in reports: {f.name}"
                )


class TestLeaderboardTemplate:
    """Test leaderboard template structure."""

    def test_leaderboard_has_required_columns(self):
        _run_export()
        rows = _read_csv_rows(REPORTS_DIR / "leaderboard_template.csv")
        assert len(rows) >= 1
        header = rows[0]
        for col in LEADERBOARD_REQUIRED_COLUMNS:
            assert col in header, f"Missing leaderboard column: {col}"

    def test_leaderboard_empty_body(self):
        _run_export()
        rows = _read_csv_rows(REPORTS_DIR / "leaderboard_template.csv")
        # Header + no data rows
        assert len(rows) == 1


class TestInventoryStructure:
    """Test task inventory JSON/CSV structure."""

    def test_inventory_count(self):
        _run_export()
        data = _inventory()
        rows = _read_csv(REPORTS_DIR / "track_distribution.csv")
        # inventory length must equal the published distribution total and clear the floor
        assert len(data) == sum(int(r["count"]) for r in rows) >= MIN_TOTAL

    def test_inventory_has_required_fields(self):
        _run_export()
        with open(REPORTS_DIR / "task_inventory.json") as f:
            data = json.load(f)
        required = {"task_id", "track", "tool", "difficulty", "data_type"}
        for record in data:
            for field in required:
                assert field in record, f"Missing field {field} in {record.get('task_id')}"

    def test_inventory_sorted_by_task_id(self):
        _run_export()
        with open(REPO_ROOT / "reports" / "task_inventory.json") as f:
            data = json.load(f)
        ids = [r["task_id"] for r in data]
        assert ids == sorted(ids)


class TestScoringSummary:
    """Test scoring summary content."""

    def test_scoring_summary_has_all_tracks(self):
        _run_export()
        rows = _read_csv(REPORTS_DIR / "scoring_summary.csv")
        tracks = {r["track"] for r in rows}
        assert CORE_TRACKS <= tracks, f"missing core tracks: {CORE_TRACKS - tracks}"

    def test_scoring_components_non_empty(self):
        _run_export()
        rows = _read_csv(REPORTS_DIR / "scoring_summary.csv")
        for r in rows:
            assert r["scoring_components"], f"Empty scoring for {r['track']}"


class TestBenchmarkSummaryMd:
    """Test markdown summary content."""

    def test_md_has_total_count(self):
        _run_export()
        md = (REPORTS_DIR / "benchmark_summary.md").read_text()
        assert str(len(_inventory())) in md

    def test_md_has_all_tracks(self):
        _run_export()
        md = (REPORTS_DIR / "benchmark_summary.md").read_text()
        for track_name in ["P1 RTL Debug", "P2 Testbench/SVA Gen", "P3 Timing Report QA", "P4 SPICE Sim", "P5 SPICE Deck Debug", "P6 DC Synthesis QA", "P6 DC Constraint Debug", "P7 SpyGlass Lint Debug", "P7 PrimeTime STA Debug", "P8 PnR Report QA", "P9 PrimeTime Exception Debug"]:
            assert track_name in md, f"Missing track {track_name} in summary"

    def test_md_has_validation_section(self):
        _run_export()
        md = (REPORTS_DIR / "benchmark_summary.md").read_text()
        assert "Validation Status" in md

    def test_md_has_known_limitations(self):
        _run_export()
        md = (REPORTS_DIR / "benchmark_summary.md").read_text()
        assert "Known Limitations" in md
