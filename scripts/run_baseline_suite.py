#!/usr/bin/env python3
"""Run baseline suite and produce leaderboard artifacts.

Runs evaluate-dataset in solution and buggy modes, collects results,
and writes CSV/MD artifacts under reports/.

No external model APIs. No task modification. No scoring logic changes.

Usage:
    python scripts/run_baseline_suite.py
    python scripts/run_baseline_suite.py --sample-per-track 1 --seed 123
    python scripts/run_baseline_suite.py --modes solution,buggy --seed 42
    python scripts/run_baseline_suite.py --track p1_rtl_debug --sample-per-track 2
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
TASKS_ROOT = REPO_ROOT / "tasks"

VALID_MODES = ("solution", "buggy")

LEADERBOARD_COLUMNS = [
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

TRACK_DISPLAY = {
    "p1_rtl_debug": "P1 RTL Debug",
    "p2_tb_sva_gen": "P2 Testbench/SVA Gen",
    "p3_timing_report_qa": "P3 Timing Report QA",
    "p4_spice_sim": "P4 SPICE Sim",
    "p5_spice_deck_debug": "P5 SPICE Deck Debug",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run baseline suite and produce leaderboard artifacts"
    )
    parser.add_argument(
        "--modes",
        default="solution,buggy",
        help="Comma-separated baseline modes (default: solution,buggy)",
    )
    parser.add_argument("--track", default=None, help="Filter by track")
    parser.add_argument(
        "--sample-per-track", type=int, default=None,
        help="Sample N tasks per track (fast mode)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Sampling seed")
    parser.add_argument("--timeout", type=int, default=None, help="Timeout per task")
    parser.add_argument(
        "--tasks-root", default=None,
        help="Override tasks root (default: tasks/)",
    )
    return parser.parse_args(argv)


def get_git_sha() -> str:
    """Get current git commit SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def run_evaluate_dataset(
    tasks_root: Path,
    mode: str,
    track: str | None = None,
    sample_per_track: int | None = None,
    seed: int = 42,
    timeout: int | None = None,
) -> dict:
    """Run eda-bench evaluate-dataset and return parsed summary.

    Calls the CLI main() directly (in-process) to avoid subprocess
    output buffering issues with `python -m`.
    """
    import io
    import contextlib

    argv = ["evaluate-dataset", str(tasks_root), "--submission-mode", mode]
    if track:
        argv += ["--track", track]
    if sample_per_track is not None:
        argv += ["--sample-per-track", str(sample_per_track)]
    argv += ["--seed", str(seed)]
    if timeout is not None:
        argv += ["--timeout", str(timeout)]

    # Capture stdout to extract the summary path
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured):
            from eda_agentbench.cli import main as cli_main
            cli_main(argv)
    except SystemExit as e:
        if e.code and e.code != 0:
            raise RuntimeError(
                f"evaluate-dataset failed (mode={mode}): exit code {e.code}\n"
                f"output: {captured.getvalue()[-2000:]}"
            )

    output = captured.getvalue()

    # Find the summary.json path from captured output
    summary_path = None
    for line in output.splitlines():
        if "Summary written to:" in line:
            summary_path = Path(line.split("Summary written to:", 1)[1].strip())
            break

    if summary_path is None or not summary_path.is_file():
        raise RuntimeError(f"Could not find summary.json in output:\n{output[-1000:]}")

    return json.loads(summary_path.read_text())


def summary_to_leaderboard_rows(
    summary: dict,
    model_name: str,
    commit_sha: str,
    date: str,
    mode: str,
) -> list[dict]:
    """Convert a dataset summary to leaderboard CSV rows."""
    rows = []

    # Overall row
    evaluated = summary.get("evaluated", 0)
    passed = summary.get("passed", 0)
    avg_score = summary.get("avg_score", 0.0)
    pass_rate = round(passed / evaluated, 4) if evaluated > 0 else 0.0

    rows.append({
        "model_name": model_name,
        "run_id": summary.get("run_id", ""),
        "date": date,
        "track": "all",
        "task_count": str(evaluated),
        "average_score": f"{avg_score:.4f}",
        "pass_rate": f"{pass_rate:.4f}",
        "compile_rate": "",
        "tool_run_success_rate": "",
        "public_score": "",
        "hidden_score": "",
        "notes": f"baseline mode={mode}",
        "commit_sha": commit_sha,
        "evaluation_mode": mode,
    })

    # Per-track rows
    for track, stats in sorted(summary.get("per_track", {}).items()):
        t_total = stats.get("total", 0)
        t_passed = stats.get("passed", 0)
        t_avg = stats.get("avg_score", 0.0)
        t_pass_rate = round(t_passed / t_total, 4) if t_total > 0 else 0.0

        rows.append({
            "model_name": model_name,
            "run_id": summary.get("run_id", ""),
            "date": date,
            "track": track,
            "task_count": str(t_total),
            "average_score": f"{t_avg:.4f}",
            "pass_rate": f"{t_pass_rate:.4f}",
            "compile_rate": "",
            "tool_run_success_rate": "",
            "public_score": "",
            "hidden_score": "",
            "notes": f"baseline mode={mode}",
            "commit_sha": commit_sha,
            "evaluation_mode": mode,
        })

    return rows


def write_csv(rows: list[dict], fieldnames: list[str], path: Path) -> None:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    path.write_text(buf.getvalue())


def write_csv_rows(rows: list[list[str]], path: Path) -> None:
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in rows:
        writer.writerow(row)
    path.write_text(buf.getvalue())


def collect_per_task_results(
    summary: dict,
    model_name: str,
    mode: str,
    commit_sha: str,
    date: str,
) -> list[dict]:
    """Extract per-task result rows from a summary."""
    rows = []
    for r in summary.get("results", []):
        if r.get("status") not in ("pass", "fail"):
            continue
        rows.append({
            "model_name": model_name,
            "mode": mode,
            "task_id": r.get("task_id", ""),
            "track": r.get("track", ""),
            "difficulty": r.get("difficulty", ""),
            "total_score": f"{r.get('total_score', 0.0):.4f}",
            "objective_score": f"{r.get('objective_score', 0.0):.4f}",
            "explanation_score": f"{r.get('explanation_score', 0.0):.4f}",
            "status": r.get("status", ""),
            "commit_sha": commit_sha,
            "date": date,
        })
    return rows


def generate_baseline_summary_md(
    mode_summaries: dict[str, dict],
    commit_sha: str,
    date: str,
    sample_per_track: int | None,
    seed: int,
) -> str:
    """Generate baseline_summary.md content."""
    lines = [
        "# EDA-AgentBench — Baseline Results",
        "",
        f"**Date:** {date}  ",
        f"**Commit:** `{commit_sha}`  ",
        f"**Sampling:** {'sample_per_track=' + str(sample_per_track) + ', seed=' + str(seed) if sample_per_track else 'full'}",
        "",
        "## Overview",
        "",
        "| Mode | Tasks Evaluated | Avg Score | Pass Rate |",
        "|------|----------------|-----------|-----------|",
    ]

    for mode in VALID_MODES:
        if mode not in mode_summaries:
            continue
        s = mode_summaries[mode]
        evaluated = s.get("evaluated", 0)
        avg = s.get("avg_score", 0.0)
        passed = s.get("passed", 0)
        pr = round(passed / evaluated, 4) if evaluated > 0 else 0.0
        lines.append(f"| {mode} | {evaluated} | {avg:.4f} | {pr:.4f} |")

    lines += [
        "",
        "## Per-Track Breakdown",
        "",
    ]

    for mode in VALID_MODES:
        if mode not in mode_summaries:
            continue
        lines.append(f"### {mode.capitalize()} Mode")
        lines.append("")
        lines.append("| Track | Tasks | Avg Score | Pass Rate |")
        lines.append("|-------|------:|----------:|----------:|")

        for track, stats in sorted(mode_summaries[mode].get("per_track", {}).items()):
            t_total = stats.get("total", 0)
            t_avg = stats.get("avg_score", 0.0)
            t_passed = stats.get("passed", 0)
            t_pr = round(t_passed / t_total, 4) if t_total > 0 else 0.0
            display = TRACK_DISPLAY.get(track, track)
            lines.append(f"| {display} | {t_total} | {t_avg:.4f} | {t_pr:.4f} |")

        lines.append("")

    # Score distribution
    lines += ["## Score Distribution", ""]
    for mode in VALID_MODES:
        if mode not in mode_summaries:
            continue
        dist = mode_summaries[mode].get("score_distribution", {})
        lines.append(f"### {mode.capitalize()}")
        lines.append("")
        lines.append("| Bucket | Count |")
        lines.append("|--------|------:|")
        for bucket, count in dist.items():
            lines.append(f"| {bucket} | {count} |")
        lines.append("")

    # Baseline interpretation
    lines += [
        "## Interpretation",
        "",
        "- **solution mode** (oracle baseline): expected avg=1.00, pass_rate=1.00. "
        "Verifies that the evaluation pipeline correctly rewards perfect submissions.",
        "- **buggy mode** (weak baseline): expected avg<1.00. Uses unmodified editable "
        "files (or wrong answers for QA tracks) to verify that evaluators distinguish "
        "correct from incorrect submissions.",
        "",
        "These baselines establish floor and ceiling scores for the benchmark.",
        "Any real LLM submission should score between the buggy and solution baselines.",
        "",
        "## Artifacts",
        "",
        "| File | Description |",
        "|------|-------------|",
        "| `baseline_results_solution.csv` | Per-task results for solution mode |",
        "| `baseline_results_buggy.csv` | Per-task results for buggy mode |",
        "| `leaderboard_baseline_filled.csv` | Leaderboard template filled with baseline rows |",
        "| `baseline_summary.md` | This summary file |",
    ]

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    modes = [m.strip() for m in args.modes.split(",")]
    for m in modes:
        if m not in VALID_MODES:
            print(f"ERROR: unknown mode '{m}'. Valid: {VALID_MODES}", file=sys.stderr)
            return 1

    tasks_root = Path(args.tasks_root) if args.tasks_root else TASKS_ROOT
    commit_sha = get_git_sha()
    date = datetime.now().strftime("%Y-%m-%d")
    model_name = "baseline"

    print(f"=== EDA-AgentBench Baseline Suite ===")
    print(f"  Modes:          {modes}")
    print(f"  Track:          {args.track or 'all'}")
    print(f"  Sample:         {args.sample_per_track or 'full'}")
    print(f"  Seed:           {args.seed}")
    print(f"  Commit:         {commit_sha}")
    print()

    mode_summaries: dict[str, dict] = {}
    all_leaderboard_rows: list[dict] = []
    all_per_task: dict[str, list[dict]] = {}

    for mode in modes:
        print(f"--- Running {mode} mode ---")
        try:
            summary = run_evaluate_dataset(
                tasks_root=tasks_root,
                mode=mode,
                track=args.track,
                sample_per_track=args.sample_per_track,
                seed=args.seed,
                timeout=args.timeout,
            )
        except Exception as e:
            print(f"ERROR running {mode} mode: {e}", file=sys.stderr)
            return 1

        mode_summaries[mode] = summary

        # Leaderboard rows
        lb_rows = summary_to_leaderboard_rows(
            summary, model_name, commit_sha, date, mode,
        )
        all_leaderboard_rows.extend(lb_rows)

        # Per-task results
        per_task = collect_per_task_results(
            summary, model_name, mode, commit_sha, date,
        )
        all_per_task[mode] = per_task

        evaluated = summary.get("evaluated", 0)
        avg = summary.get("avg_score", 0.0)
        passed = summary.get("passed", 0)
        print(f"  Evaluated: {evaluated}, Avg: {avg:.4f}, Passed: {passed}")
        print()

    # Write per-task CSVs
    task_fields = [
        "model_name", "mode", "task_id", "track", "difficulty",
        "total_score", "objective_score", "explanation_score",
        "status", "commit_sha", "date",
    ]
    for mode in modes:
        csv_path = REPORTS_DIR / f"baseline_results_{mode}.csv"
        write_csv(all_per_task.get(mode, []), task_fields, csv_path)
        print(f"Wrote {csv_path}")

    # Write leaderboard CSV
    write_csv(all_leaderboard_rows, LEADERBOARD_COLUMNS, REPORTS_DIR / "leaderboard_baseline_filled.csv")
    print(f"Wrote {REPORTS_DIR / 'leaderboard_baseline_filled.csv'}")

    # Write baseline summary markdown
    md = generate_baseline_summary_md(
        mode_summaries, commit_sha, date,
        args.sample_per_track, args.seed,
    )
    (REPORTS_DIR / "baseline_summary.md").write_text(md)
    print(f"Wrote {REPORTS_DIR / 'baseline_summary.md'}")

    print("\n=== Baseline suite complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
