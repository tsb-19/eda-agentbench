#!/usr/bin/env python3
"""Generate P4 SPICE Sim tasks with deterministic seed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generators.p4_spice_gen import P4SPICEGenerator

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate P4 SPICE Sim tasks")
    parser.add_argument("--count", type=int, default=10, help="Total tasks (5 HSPICE + 5 Spectre)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="tasks/p4_spice_sim")
    args = parser.parse_args()

    out = Path(args.output_dir)
    gen = P4SPICEGenerator(seed=args.seed, output_dir=out)
    paths = gen.generate_batch(args.count)
    print(f"Generated {len(paths)} tasks in {out}/")
    for p in paths:
        print(f"  {p.name}")

if __name__ == "__main__":
    main()
