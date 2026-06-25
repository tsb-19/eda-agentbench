#!/usr/bin/env python3
"""Generate P9 PrimeTime Exception Debug tasks (timing-exception diagnosis).

Usage:
    python3 scripts/generate_p9_pt_exception_debug_tasks.py --count 8 --seed 42
    python3 scripts/generate_p9_pt_exception_debug_tasks.py --count 1 --seed 1 \
        --output-dir tasks/p9_pt_exception_debug/smoke --id-start 0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from generators.p9_pt_exception_debug_gen import P9PrimeTimeExceptionDebugGenerator


def main():
    parser = argparse.ArgumentParser(description="Generate P9 PrimeTime Exception Debug tasks")
    parser.add_argument("--count", type=int, default=8, help="Number of tasks to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output-dir", type=str,
                        default="tasks/p9_pt_exception_debug/generated",
                        help="Output directory")
    parser.add_argument("--id-start", type=int, default=1,
                        help="Starting task ID number (0 for smoke, 1 for generated)")
    args = parser.parse_args()

    out = Path(args.output_dir)
    gen = P9PrimeTimeExceptionDebugGenerator(seed=args.seed, output_dir=out, id_start=args.id_start)
    paths = gen.generate_batch(args.count)

    print(f"Generated {len(paths)} P9 PrimeTime Exception Debug tasks in {out}")
    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    main()
