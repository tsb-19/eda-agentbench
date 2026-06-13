#!/usr/bin/env python3
"""Generate P7 SpyGlass Lint Debug prototype tasks.

Usage:
    python scripts/generate_p7_spyglass_lint_debug_tasks.py [--count N] [--seed S]

Default: 32 tasks (4 per bug category × 8 categories), seed=42.
Smoke task is always generated as sg_lint_0000.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from generators.p7_spyglass_lint_debug_gen import P7SpyGlassLintDebugGenerator

TASKS_DIR = REPO_ROOT / "tasks" / "p7_spyglass_lint_debug"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate P7 SpyGlass Lint Debug tasks")
    parser.add_argument("--count", type=int, default=15, help="Number of tasks to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output-dir", type=Path, default=TASKS_DIR / "generated",
                        help="Output directory for generated tasks")
    args = parser.parse_args()

    # Ensure output directory exists
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Generate smoke task
    smoke_dir = TASKS_DIR / "smoke"
    smoke_dir.mkdir(parents=True, exist_ok=True)
    smoke_gen = P7SpyGlassLintDebugGenerator(seed=args.seed, output_dir=smoke_dir)
    smoke_path = smoke_gen.generate_one(0)
    print(f"Smoke task: {smoke_path}")

    # Generate batch
    gen = P7SpyGlassLintDebugGenerator(seed=args.seed, output_dir=args.output_dir)
    paths = gen.generate_batch(args.count)
    print(f"Generated {len(paths)} tasks in {args.output_dir}")

    # Print distribution
    from collections import Counter
    import json
    dist = Counter()
    for p in paths:
        meta = json.loads((p / "metadata.json").read_text())
        dist[meta["generator"]["bug_type"]] += 1
    print("\nBug type distribution:")
    for bt, count in sorted(dist.items()):
        print(f"  {bt}: {count}")


if __name__ == "__main__":
    main()
