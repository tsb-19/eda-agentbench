#!/usr/bin/env python3
"""Generate P1 RTL Debug tasks with deterministic seed."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generators.p1_rtl_debug_gen import P1RTLDebugGenerator

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate P1 RTL Debug tasks")
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="tasks/p1_rtl_debug/generated")
    args = parser.parse_args()

    out = Path(args.output_dir)
    gen = P1RTLDebugGenerator(seed=args.seed, output_dir=out)
    paths = gen.generate_batch(args.count)
    print(f"Generated {len(paths)} tasks in {out}/")
    for p in paths:
        print(f"  {p.name}")

if __name__ == "__main__":
    main()
