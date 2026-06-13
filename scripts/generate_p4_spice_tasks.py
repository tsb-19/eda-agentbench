#!/usr/bin/env python3
"""Generate P4 SPICE Sim tasks with deterministic seed."""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generators.p4_spice_gen import P4SPICEGenerator

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate P4 SPICE Sim tasks")
    parser.add_argument("--count", type=int, default=300,
                        help="Total tasks (150 HSPICE + 150 Spectre across 3 circuit types)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="tasks/p4_spice_sim")
    parser.add_argument("--split", action="store_true",
                        help="Split into generated_hspice/ and generated_spectre/")
    args = parser.parse_args()

    out = Path(args.output_dir)

    if args.split:
        # Generate all tasks to a temp dir, then split
        tmp_dir = out / "_tmp_gen"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        gen = P4SPICEGenerator(seed=args.seed, output_dir=tmp_dir)
        paths = gen.generate_batch(args.count)
        print(f"Generated {len(paths)} tasks, splitting...")

        hspice_dir = out / "generated_hspice"
        spectre_dir = out / "generated_spectre"
        hspice_dir.mkdir(parents=True, exist_ok=True)
        spectre_dir.mkdir(parents=True, exist_ok=True)

        for p in paths:
            meta_file = p / "metadata.json"
            if meta_file.exists():
                import json
                meta = json.loads(meta_file.read_text())
                tool = meta["tool"][0]
                if tool == "hspice":
                    dest = hspice_dir / p.name
                else:
                    dest = spectre_dir / p.name
                shutil.move(str(p), str(dest))

        shutil.rmtree(tmp_dir, ignore_errors=True)

        hspice_count = len(list(hspice_dir.iterdir()))
        spectre_count = len(list(spectre_dir.iterdir()))
        print(f"  HSPICE: {hspice_count} tasks in {hspice_dir}/")
        print(f"  Spectre: {spectre_count} tasks in {spectre_dir}/")
    else:
        gen = P4SPICEGenerator(seed=args.seed, output_dir=out)
        paths = gen.generate_batch(args.count)
        print(f"Generated {len(paths)} tasks in {out}/")
        for p in paths:
            print(f"  {p.name}")

if __name__ == "__main__":
    main()
