#!/usr/bin/env python3
"""Generate P6 DC Constraint Debug tasks."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generators.p6_dc_constraint_debug_gen import P6DCConstraintDebugGenerator

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "tasks" / "p6_dc_constraint_debug" / "generated"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate P6 DC Constraint Debug tasks")
    parser.add_argument("--count", type=int, default=60, help="Number of tasks to generate (6 bug categories x 10 RTL templates)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR), help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    gen = P6DCConstraintDebugGenerator(seed=args.seed, output_dir=output_dir)
    paths = gen.generate_batch(args.count)

    print(f"Generated {len(paths)} P6 DC Constraint Debug tasks in {output_dir}")
    for p in paths:
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
