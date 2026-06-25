#!/usr/bin/env python3
"""Generate P9 ExceptionDebug INFERRED-INTENT falsification tasks.

These strip the stated timing intent and force the model to recover it from a behavioral
`design_rtl.v`. Used for the make-or-break frontier probe (if the frontier-3 still collapse,
ExceptionDebug is retired). Output defaults to tasks/p9_pt_exception_debug/infer.

Usage:
    python3 scripts/generate_p9_infer_tasks.py --count 8 --seed 42
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from generators.p9_pt_exception_debug_infer_gen import P9InferGenerator


def main():
    parser = argparse.ArgumentParser(description="Generate P9 inferred-intent falsification tasks")
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=str, default="tasks/p9_pt_exception_debug/infer")
    parser.add_argument("--id-start", type=int, default=2001)
    args = parser.parse_args()

    out = Path(args.output_dir)
    gen = P9InferGenerator(seed=args.seed, output_dir=out, id_start=args.id_start)
    paths = gen.generate_batch(args.count)
    print(f"Generated {len(paths)} P9 inferred-intent tasks in {out}")
    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    main()
