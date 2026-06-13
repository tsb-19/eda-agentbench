#!/usr/bin/env python3
"""Generate P6 DC Synthesis QA tasks with deterministic seed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generators.p6_dc_synthesis_qa_gen import DCSynthesisQAGenerator


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate P6 DC Synthesis QA tasks")
    parser.add_argument("--count", type=int, default=50, help="Number of tasks to generate")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="tasks/p6_dc_synthesis_qa/generated")
    args = parser.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    gen = DCSynthesisQAGenerator(seed=args.seed, output_dir=out)
    paths = gen.generate_batch(args.count)
    print(f"Generated {len(paths)} P6 tasks in {out}/")

    # Print distribution
    from collections import Counter
    import json
    types = Counter()
    for p in paths:
        meta = json.loads((p / "metadata.json").read_text())
        types[meta["answer"]["question_type"]] += 1
    print("\nQuestion type distribution:")
    for qtype, count in sorted(types.items()):
        print(f"  {qtype}: {count}")


if __name__ == "__main__":
    main()
