#!/usr/bin/env python3
"""Generate P4 op-amp SIZING (hard) tasks — two-stage Miller OTA, gain/GBW/PM tradeoff.

These emit with NULL acceptance floors (calibrated:False); run
scripts/calibrate_p4_amp.py (with the EDA shim sourced) afterwards to ground the
specs in real Spectre AC sims. See generators/p4_amp_sizing_gen.py and
docs/benchmark_hardening_plan.md §9 for the residual-recipe rationale.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generators.p4_amp_sizing_gen import P4AmpSizingGenerator

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "tasks" / "p4_spice_sim" / "generated_ota_sizing"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate P4 op-amp sizing tasks")
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    gen = P4AmpSizingGenerator(seed=args.seed, output_dir=output_dir)
    paths = gen.generate_batch(args.count)

    print(f"Generated {len(paths)} P4 op-amp-sizing tasks in {output_dir}")
    for p in paths:
        print(f"  {p.name}")
    print("\nNEXT: source the EDA shim, then calibrate from real Spectre:")
    print(f"  python3 scripts/calibrate_p4_amp.py {output_dir}/* --apply")


if __name__ == "__main__":
    main()
