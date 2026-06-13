#!/usr/bin/env python3
"""Generate P8 PnR Report QA tasks.

Usage:
    python scripts/generate_p8_pnr_report_qa_tasks.py --count 100 --seed 42
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from generators.p8_pnr_report_qa_gen import (
    DESIGN_NAMES,
    STAGES,
    generate_prompt,
    generate_report,
    generate_task_metadata,
    select_question_types,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate P8 PnR Report QA tasks")
    parser.add_argument("--count", type=int, default=100, help="Number of tasks to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--icc2-ratio", type=float, default=0.5,
                        help="Fraction of ICC2-style tasks (0.0 to 1.0)")
    parser.add_argument("--output-dir", type=str, default="tasks/p8_pnr_report_qa/generated",
                        help="Output directory for generated tasks")
    args = parser.parse_args()

    rng = __import__("random").Random(args.seed)
    output_dir = REPO_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    for i in range(args.count):
        task_id = f"pnr_report_qa_{i:04d}"
        task_dir = output_dir / task_id
        task_dir.mkdir(exist_ok=True)

        # Select tool family
        tool_family = "icc2" if rng.random() < args.icc2_ratio else "innovus"

        # Select design and stage
        design_name = rng.choice(DESIGN_NAMES)
        stage = rng.choice(STAGES)

        # Select question types (3 per task)
        question_types = select_question_types(rng, count=3)

        # Generate report and oracle
        report_text, oracle = generate_report(rng, tool_family, design_name, stage)

        # Filter oracle to only include fields asked about
        asked_fields = set()
        from generators.p8_pnr_report_qa_gen import QUESTION_TYPES
        for qt in question_types:
            asked_fields.update(QUESTION_TYPES[qt])
        filtered_oracle = {k: v for k, v in oracle.items() if k in asked_fields}

        # Generate metadata
        difficulty = "easy" if len(question_types) <= 2 else "medium"
        metadata = generate_task_metadata(task_id, tool_family, difficulty, question_types)

        # Write files
        with open(task_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        with open(task_dir / "report.txt", "w") as f:
            f.write(report_text)

        with open(task_dir / "prompt.md", "w") as f:
            f.write(generate_prompt(question_types, tool_family))

        # Oracle answers go in hidden/
        hidden_dir = task_dir / "hidden"
        hidden_dir.mkdir(exist_ok=True)
        with open(hidden_dir / "answers.json", "w") as f:
            json.dump(filtered_oracle, f, indent=2, sort_keys=True)

        # Solution answers (same as oracle)
        solution_dir = task_dir / "solution"
        solution_dir.mkdir(exist_ok=True)
        with open(solution_dir / "answers.json", "w") as f:
            json.dump(filtered_oracle, f, indent=2, sort_keys=True)

        # Empty answers.json for buggy mode
        buggy_answers = {k: "" for k in filtered_oracle}
        with open(task_dir / "answers.json", "w") as f:
            json.dump(buggy_answers, f, indent=2, sort_keys=True)

    print(f"Generated {args.count} tasks in {output_dir}")


if __name__ == "__main__":
    main()
