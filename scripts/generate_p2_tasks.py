#!/usr/bin/env python3
"""Generate P2 Testbench/SVA Generation tasks with deterministic seed."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generators.p2_tb_sva_gen import P2TBGenerator

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate P2 TB/SVA Generation tasks")
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="tasks/p2_rtl_gen/generated")
    args = parser.parse_args()

    out = Path(args.output_dir)
    gen = P2TBGenerator(seed=args.seed, output_dir=out)
    paths = gen.generate_batch(args.count)
    print(f"Generated {len(paths)} tasks in {out}/")
    for p in paths:
        print(f"  {p.name}")

if __name__ == "__main__":
    main()
