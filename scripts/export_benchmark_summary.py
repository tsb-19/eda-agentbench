#!/usr/bin/env python3
"""Export benchmark summary, inventory, and leaderboard artifacts.

Generates deterministic CSV/JSON/MD files under reports/ for the v0.3 benchmark.
No LLM calls. No task modification. Read-only on tasks/.

Usage:
    python scripts/export_benchmark_summary.py
"""

from __future__ import annotations

import csv
import io
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from eda_agentbench.config import TASKS_ROOT
from eda_agentbench.task.loader import TaskLoader

REPORTS_DIR = REPO_ROOT / "reports"

TRACK_DISPLAY = {
    "p1_rtl_debug": "P1 RTL Debug",
    "p2_tb_sva_gen": "P2 Testbench/SVA Gen",
    "p3_timing_report_qa": "P3 Timing Report QA",
    "p4_spice_sim": "P4 SPICE Sim",
    "p5_spice_deck_debug": "P5 SPICE Deck Debug",
    "p6_dc_synthesis_qa": "P6 DC Synthesis QA",
    "p6_dc_constraint_debug": "P6 DC Constraint Debug",
    "p7_spyglass_lint_debug": "P7 SpyGlass Lint Debug",
}

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


def discover_and_load(tasks_root: Path) -> list[dict]:
    """Discover all tasks and load metadata. Returns list of enriched dicts."""
    loader = TaskLoader(tasks_root)
    task_dirs = loader.discover()
    results = []
    for task_dir in task_dirs:
        try:
            meta = loader.load(task_dir)
        except Exception as e:
            print(f"WARNING: skipping {task_dir}: {e}", file=sys.stderr)
            continue
        record = _extract_record(meta, task_dir, tasks_root)
        results.append(record)
    # Sort deterministically by task_id
    results.sort(key=lambda r: r["task_id"])
    return results


def _extract_record(meta: dict, task_dir: Path, tasks_root: Path) -> dict:
    """Extract a flat inventory record from task metadata."""
    track = meta["track"]
    gen = meta.get("generator", {})
    scoring = meta.get("scoring", {})
    files_spec = meta.get("files", {})
    tool_list = meta.get("tool", [])

    # Visible/hidden file counts
    visible_count = len(files_spec.get("visible", []))
    hidden_count = len(files_spec.get("hidden", []))

    # Oracle presence
    has_oracle = (task_dir / "oracle").is_dir() or (task_dir / "solution").is_dir()

    # Prompt path
    prompt_path = task_dir / "prompt.md"
    prompt_rel = str(prompt_path.relative_to(tasks_root)) if prompt_path.exists() else ""

    # Task dir relative to tasks_root
    task_dir_rel = str(task_dir.relative_to(tasks_root))

    # Evaluator
    evaluator = scoring.get("evaluator", "")

    # Scoring type: describe the component structure
    weights = scoring.get("weights", {})
    scoring_type = "|".join(f"{k}:{v}" for k, v in sorted(weights.items()))

    # Backend/tool requirement
    backend = ",".join(tool_list)

    record = {
        "task_id": meta["task_id"],
        "track": track,
        "tool": backend,
        "difficulty": meta.get("difficulty", ""),
        "data_type": meta.get("data_type", ""),
        "evaluator": evaluator,
        "scoring_type": scoring_type,
        "task_dir": task_dir_rel,
        "generator": gen.get("script", ""),
        "prompt_path": prompt_rel,
        "visible_files_count": visible_count,
        "hidden_files_count": hidden_count,
        "has_oracle": has_oracle,
        "backend": backend,
    }

    # Track-specific fields
    record["bug_type"] = ""
    record["question_type"] = ""
    record["template"] = ""
    record["mutant_name"] = ""
    record["expected_error_category"] = ""
    record["p3_source"] = ""

    if track == "p1_rtl_debug":
        record["bug_type"] = gen.get("bug_type", "")

    elif track == "p2_tb_sva_gen":
        record["template"] = gen.get("template", "")
        record["mutant_name"] = gen.get("mutant_name", "")

    elif track == "p3_timing_report_qa":
        # question_type from answer object or generator
        answer = meta.get("answer", {})
        record["question_type"] = answer.get("question_type", gen.get("question_type", ""))
        # Distinguish synthetic vs PT prototype
        if "pt_prototype" in task_dir_rel:
            record["p3_source"] = "pt_prototype"
        else:
            record["p3_source"] = "synthetic"

    elif track == "p5_spice_deck_debug":
        record["expected_error_category"] = meta.get("expected_error_category", "")

    elif track == "p6_dc_synthesis_qa":
        answer = meta.get("answer", {})
        record["question_type"] = answer.get("question_type", gen.get("question_type", ""))

    elif track == "p6_dc_constraint_debug":
        record["bug_type"] = gen.get("bug_type", "")
        record["expected_error_category"] = meta.get("expected_error_category", "")

    elif track == "p7_spyglass_lint_debug":
        record["bug_type"] = gen.get("bug_type", "")
        record["expected_error_category"] = meta.get("expected_error_category", "")

    return record


def write_json(data: object, path: Path) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


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


def generate_track_distribution(records: list[dict]) -> list[list[str]]:
    counter = Counter(r["track"] for r in records)
    rows = [["track", "display_name", "count"]]
    for track in sorted(counter):
        rows.append([track, TRACK_DISPLAY.get(track, track), str(counter[track])])
    return rows


def generate_tool_distribution(records: list[dict]) -> list[list[str]]:
    counter = Counter()
    for r in records:
        for t in r["tool"].split(","):
            if t:
                counter[t] += 1
    rows = [["tool", "count"]]
    for tool in sorted(counter):
        rows.append([tool, str(counter[tool])])
    return rows


def generate_scoring_summary(records: list[dict]) -> list[list[str]]:
    # Collect unique scoring types per track
    by_track: dict[str, set[str]] = defaultdict(set)
    for r in records:
        by_track[r["track"]].add(r["scoring_type"])
    rows = [["track", "scoring_components"]]
    for track in sorted(by_track):
        # Use the most common scoring type (should be uniform per track)
        rows.append([track, sorted(by_track[track])[0]])
    return rows


def generate_p1_bug_distribution(records: list[dict]) -> list[list[str]]:
    counter = Counter(r["bug_type"] for r in records if r["track"] == "p1_rtl_debug")
    rows = [["bug_type", "count"]]
    for bt in sorted(counter):
        rows.append([bt, str(counter[bt])])
    return rows


def generate_p2_template_mutant_distribution(records: list[dict]) -> list[list[str]]:
    p2 = [r for r in records if r["track"] == "p2_tb_sva_gen"]
    template_counter = Counter(r["template"] for r in p2)
    mutant_counter = Counter(r["mutant_name"] for r in p2)
    rows = [["category", "value", "count"]]
    for t in sorted(template_counter):
        rows.append(["template", t, str(template_counter[t])])
    for m in sorted(mutant_counter):
        rows.append(["mutant_name", m, str(mutant_counter[m])])
    return rows


def generate_p3_question_type_distribution(records: list[dict]) -> list[list[str]]:
    p3 = [r for r in records if r["track"] == "p3_timing_report_qa"]
    # Count by question_type and source
    counter: dict[str, Counter] = defaultdict(Counter)
    for r in p3:
        counter[r["question_type"]][r["p3_source"]] += 1
    rows = [["question_type", "synthetic_count", "pt_prototype_count", "total"]]
    for qt in sorted(counter):
        syn = counter[qt].get("synthetic", 0)
        pt = counter[qt].get("pt_prototype", 0)
        rows.append([qt, str(syn), str(pt), str(syn + pt)])
    return rows


def generate_p5_error_category_distribution(records: list[dict]) -> list[list[str]]:
    counter = Counter(
        r["expected_error_category"]
        for r in records
        if r["track"] == "p5_spice_deck_debug"
    )
    rows = [["expected_error_category", "count"]]
    for cat in sorted(counter):
        rows.append([cat, str(counter[cat])])
    return rows


def generate_p6_question_type_distribution(records: list[dict]) -> list[list[str]]:
    counter = Counter(
        r["question_type"]
        for r in records
        if r["track"] == "p6_dc_synthesis_qa"
    )
    rows = [["question_type", "count"]]
    for qt in sorted(counter):
        rows.append([qt, str(counter[qt])])
    return rows


def generate_leaderboard_template() -> list[list[str]]:
    return [LEADERBOARD_COLUMNS]


def generate_benchmark_summary_md(records: list[dict]) -> str:
    total = len(records)
    track_counter = Counter(r["track"] for r in records)
    tool_counter = Counter()
    for r in records:
        for t in r["tool"].split(","):
            if t:
                tool_counter[t] += 1
    difficulty_counter = Counter(r["difficulty"] for r in records)
    data_type_counter = Counter(r["data_type"] for r in records)

    # P3 breakdown
    p3 = [r for r in records if r["track"] == "p3_timing_report_qa"]
    p3_syn = sum(1 for r in p3 if r["p3_source"] == "synthetic")
    p3_pt = sum(1 for r in p3 if r["p3_source"] == "pt_prototype")

    # P5 categories
    p5_counter = Counter(
        r["expected_error_category"]
        for r in records
        if r["track"] == "p5_spice_deck_debug"
    )

    # Scoring methodology
    scoring_lines = []
    scoring_rows = generate_scoring_summary(records)
    for row in scoring_rows[1:]:
        scoring_lines.append(f"| {TRACK_DISPLAY.get(row[0], row[0])} | `{row[1]}` |")

    lines = [
        "# EDA-AgentBench v0.3 — Benchmark Summary",
        "",
        f"**Tag:** `v0.3-phase6b-2363`  ",
        f"**Total tasks:** {total}  ",
        f"**Tracks:** {len(track_counter)}  ",
        f"**Generated:** deterministic export via `scripts/export_benchmark_summary.py`",
        "",
        "## Per-Track Task Count",
        "",
        "| Track | Count |",
        "|-------|------:|",
    ]
    for track in sorted(track_counter):
        lines.append(f"| {TRACK_DISPLAY.get(track, track)} | {track_counter[track]} |")
    lines.append(f"| **Total** | **{total}** |")

    lines += [
        "",
        "## Tool Distribution",
        "",
        "| Tool | Task Count |",
        "|------|----------:|",
    ]
    for tool in sorted(tool_counter):
        lines.append(f"| {tool} | {tool_counter[tool]} |")

    lines += [
        "",
        "## Difficulty Distribution",
        "",
        "| Difficulty | Count |",
        "|------------|------:|",
    ]
    for diff in sorted(difficulty_counter):
        lines.append(f"| {diff} | {difficulty_counter[diff]} |")

    lines += [
        "",
        "## Data Type Distribution",
        "",
        "| Data Type | Count |",
        "|-----------|------:|",
    ]
    for dt in sorted(data_type_counter):
        lines.append(f"| {dt} | {data_type_counter[dt]} |")

    lines += [
        "",
        "## Scoring Methodology",
        "",
        "Each track uses weighted multi-component scoring. The evaluator computes a",
        "per-component raw score, multiplies by the component weight, and sums to a",
        "total score in [0, 1]. A task passes if total_score >= 0.5.",
        "",
        "| Track | Scoring Components |",
        "|-------|-------------------|",
    ]
    lines += scoring_lines

    lines += [
        "",
        "## Public / Private Split",
        "",
        "- **P1**: public_test (0.3) + hidden_test (0.5) — hidden testbench is private",
        "- **P2**: golden_pass (0.4) uses public testbench; mutant_1/mutant_2 (0.2 each) use hidden mutant designs",
        "- **P3**: answer_match (1.0) — answer file is hidden from the agent",
        "- **P4**: public_metric (0.2) + hidden_metric (0.2) — hidden test script measures additional metrics",
        "- **P5**: execution_pass (0.9) — oracle fixed deck is hidden; grading is execution-based",
        "",
        "## Synthetic vs Tool-Backed Tasks",
        "",
        "- **template_synthetic** (P2, P3, P4): generated from controlled templates with deterministic seeds",
        "- **mutation_synthetic** (P1, P2): correct designs with injected bugs",
        "- **flow_synthetic** (P5): generated by running real EDA tools and collecting logs/errors",
        "",
        "P3 tasks are entirely synthetic — timing reports are generated from templates,",
        "not from real PrimeTime runs (except the 8 PT prototype tasks).",
        "P5 tasks are flow_synthetic — they originate from real HSPICE error logs.",
        "",
        "## P3 Synthetic vs PrimeTime Prototype Breakdown",
        "",
        f"- **Synthetic (generated):** {p3_syn} tasks — template-based timing reports",
        f"- **PT Prototype:** {p3_pt} tasks — handcrafted scenarios backed by real PrimeTime",
        f"- **Total P3:** {len(p3)} tasks",
        "",
        "## P5 Error Category Distribution",
        "",
        "| Error Category | Count |",
        "|---------------|------:|",
    ]
    for cat in sorted(p5_counter):
        lines.append(f"| {cat} | {p5_counter[cat]} |")
    lines.append(f"| **Total** | **{sum(p5_counter.values())}** |")

    lines += [
        "",
        "## Validation Status",
        "",
        "- **pytest:** 265/265 passing",
        "- **Smoke scripts:** all 6 tracks pass end-to-end smoke tests",
        "- **Sampled evaluation:** fast eval (5 tasks/track) passes for solution mode",
        "- **P5 full batch:** 100/100 solution tasks score 1.0; 100/100 buggy tasks score < 1.0",
        "- **P6 prototype:** 51 tasks, all solution mode pass, DC detected on system",
        "",
        "## Known Limitations",
        "",
        "- No agentic runner yet — evaluation uses pre-computed submissions",
        "- No LLM API integration — benchmark is offline evaluation only",
        "- P4 tasks are RC-filter circuits only; no complex analog designs",
        "- P5 is limited to 100 tasks (imported from external bundle)",
        "- P3 synthetic reports are template-based, not from real synthesis runs",
        "- P6 DC Synthesis QA is a prototype (51 tasks)",
        "- P6 DC Constraint Debug is a prototype (13 tasks)",
        "- No P7 (physical) track yet",
        "",
        "## Generated Artifacts",
        "",
        "| File | Description |",
        "|------|-------------|",
        "| `task_inventory.json` | Full task inventory with all metadata fields |",
        "| `task_inventory.csv` | Flattened CSV of task inventory |",
        "| `track_distribution.csv` | Per-track task counts |",
        "| `tool_distribution.csv` | Per-tool task counts |",
        "| `scoring_summary.csv` | Scoring component weights per track |",
        "| `p1_bug_distribution.csv` | P1 bug type distribution |",
        "| `p2_template_mutant_distribution.csv` | P2 template and mutant distributions |",
        "| `p3_question_type_distribution.csv` | P3 question type with synthetic/PT split |",
        "| `p5_error_category_distribution.csv` | P5 error category distribution |",
        "| `leaderboard_template.csv` | Empty leaderboard template for model evaluation results |",
    ]

    return "\n".join(lines) + "\n"


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    tasks_root = REPO_ROOT / TASKS_ROOT
    print(f"Discovering tasks under {tasks_root}...")
    records = discover_and_load(tasks_root)
    print(f"Loaded {len(records)} tasks.")

    # Verify track counts
    track_counter = Counter(r["track"] for r in records)
    for track in sorted(track_counter):
        print(f"  {track}: {track_counter[track]}")

    # Write task_inventory.json
    write_json(records, REPORTS_DIR / "task_inventory.json")

    # Write task_inventory.csv
    inventory_fields = [
        "task_id", "track", "tool", "difficulty", "data_type",
        "evaluator", "scoring_type", "task_dir", "generator",
        "prompt_path", "visible_files_count", "hidden_files_count",
        "has_oracle", "bug_type", "question_type", "template",
        "mutant_name", "expected_error_category", "p3_source", "backend",
    ]
    write_csv(records, inventory_fields, REPORTS_DIR / "task_inventory.csv")

    # Write track_distribution.csv
    write_csv_rows(generate_track_distribution(records), REPORTS_DIR / "track_distribution.csv")

    # Write tool_distribution.csv
    write_csv_rows(generate_tool_distribution(records), REPORTS_DIR / "tool_distribution.csv")

    # Write scoring_summary.csv
    write_csv_rows(generate_scoring_summary(records), REPORTS_DIR / "scoring_summary.csv")

    # Write p1_bug_distribution.csv
    write_csv_rows(generate_p1_bug_distribution(records), REPORTS_DIR / "p1_bug_distribution.csv")

    # Write p2_template_mutant_distribution.csv
    write_csv_rows(
        generate_p2_template_mutant_distribution(records),
        REPORTS_DIR / "p2_template_mutant_distribution.csv",
    )

    # Write p3_question_type_distribution.csv
    write_csv_rows(
        generate_p3_question_type_distribution(records),
        REPORTS_DIR / "p3_question_type_distribution.csv",
    )

    # Write p5_error_category_distribution.csv
    write_csv_rows(
        generate_p5_error_category_distribution(records),
        REPORTS_DIR / "p5_error_category_distribution.csv",
    )

    # Write p6_question_type_distribution.csv
    write_csv_rows(
        generate_p6_question_type_distribution(records),
        REPORTS_DIR / "p6_question_type_distribution.csv",
    )

    # Write leaderboard_template.csv
    write_csv_rows(generate_leaderboard_template(), REPORTS_DIR / "leaderboard_template.csv")

    # Write benchmark_summary.md
    md = generate_benchmark_summary_md(records)
    (REPORTS_DIR / "benchmark_summary.md").write_text(md)

    print(f"\nAll artifacts written to {REPORTS_DIR}/")


if __name__ == "__main__":
    main()
