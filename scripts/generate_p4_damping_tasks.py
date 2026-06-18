#!/usr/bin/env python3
"""Generate P4 SPICE damping-design (hard) tasks.

These emit with NULL acceptance thresholds; run scripts/calibrate_p4_damping.py
(with the EDA shim sourced) afterwards to ground the specs in real Spectre sims.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generators.p4_damping_gen import P4DampingGenerator

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "tasks" / "p4_spice_sim" / "generated_damping"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate P4 damping-design tasks")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    gen = P4DampingGenerator(seed=args.seed, output_dir=output_dir)
    paths = gen.generate_batch(args.count)

    print(f"Generated {len(paths)} P4 damping-design tasks in {output_dir}")
    for p in paths:
        print(f"  {p.name}")
    print("\nNEXT: source the EDA shim, then calibrate from real Spectre:")
    print(f"  python3 scripts/calibrate_p4_damping.py {output_dir}/* --apply")


if __name__ == "__main__":
    main()
