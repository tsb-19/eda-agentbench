#!/usr/bin/env python3
"""Generate synthetic project (p10) constraint-drift tasks.

Usage:
    python3 scripts/generate_synthetic_project_tasks.py --count 5 --seed 42 --id-start 2

Emits acc_stage-style timing-constraint tasks (golden -> constraint-drift mutant ->
PrimeTime oracle) into tasks/p10_synthetic_project/. The hand-authored syn_proj_0001
stays as the smoke/reference task; generated tasks start at --id-start (default 2).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from generators.p10_synthetic_project_gen import SyntheticProjectGenerator


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate p10 synthetic constraint-drift tasks")
    parser.add_argument("--count", type=int, default=5, help="Number of tasks to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output-dir", type=str, default="tasks/p10_synthetic_project",
                        help="Output directory")
    parser.add_argument("--id-start", type=int, default=2,
                        help="Starting task ID number (1 is the hand-authored smoke task)")
    args = parser.parse_args()

    out = Path(args.output_dir)
    gen = SyntheticProjectGenerator(seed=args.seed, output_dir=out, id_start=args.id_start)
    paths = gen.generate_batch(args.count)

    print(f"Generated {len(paths)} p10 synthetic-project tasks in {out}")
    for p in paths:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
