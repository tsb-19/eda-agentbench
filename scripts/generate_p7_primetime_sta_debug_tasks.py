#!/usr/bin/env python3
"""Generate P7 PrimeTime STA Debug tasks.

Usage:
    python3 scripts/generate_p7_primetime_sta_debug_tasks.py --count 20 --seed 42
    python3 scripts/generate_p7_primetime_sta_debug_tasks.py --count 1 --seed 1 --output-dir tasks/p7_primetime_sta_debug/smoke
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from generators.p7_primetime_sta_debug_gen import P7PrimeTimeSTADebugGenerator


def main():
    parser = argparse.ArgumentParser(description="Generate P7 PrimeTime STA Debug tasks")
    parser.add_argument("--count", type=int, default=20, help="Number of tasks to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output-dir", type=str,
                        default="tasks/p7_primetime_sta_debug/generated",
                        help="Output directory")
    args = parser.parse_args()

    out = Path(args.output_dir)
    gen = P7PrimeTimeSTADebugGenerator(seed=args.seed, output_dir=out)
    paths = gen.generate_batch(args.count)

    print(f"Generated {len(paths)} P7 PrimeTime STA Debug tasks in {out}")
    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    main()
