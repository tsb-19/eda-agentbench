#!/usr/bin/env python3
"""Generate prompt variants for a sample of tasks."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eda_agentbench.llm.mock import MockLLMProvider
from eda_agentbench.llm.cache import LLMCache
from eda_agentbench.prompt.safety import SafetyChecker
from eda_agentbench.prompt.rewriter import PromptRewriter
from eda_agentbench.prompt.variant_manager import VariantManager


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate prompt variants for sample tasks")
    parser.add_argument("--p1-count", type=int, default=5, help="P1 tasks per bug type")
    parser.add_argument("--p4-count", type=int, default=5, help="P4 tasks per tool")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--variant-name", default="llm_v1")
    parser.add_argument("--cache-dir", default=".cache/llm")
    parser.add_argument("--dry-run", action="store_true", help="Show tasks without generating")
    args = parser.parse_args()

    # Set up components
    provider = MockLLMProvider(seed=args.seed)
    cache = LLMCache(Path(args.cache_dir))
    safety = SafetyChecker()
    rewriter = PromptRewriter(provider=provider, cache=cache, safety=safety)
    manager = VariantManager(rewriter=rewriter)

    # Collect P1 tasks: args.p1_count per bug type
    p1_root = Path("tasks/p1_rtl_debug/generated")
    p1_tasks = []
    if p1_root.exists():
        by_type: dict[str, list[Path]] = {}
        for task_dir in sorted(p1_root.iterdir()):
            if not task_dir.is_dir():
                continue
            meta_path = task_dir / "metadata.json"
            if not meta_path.exists():
                continue
            meta = json.loads(meta_path.read_text())
            bt = meta.get("generator", {}).get("bug_type", "unknown")
            by_type.setdefault(bt, []).append(task_dir)

        for bt, dirs in sorted(by_type.items()):
            p1_tasks.extend(dirs[:args.p1_count])

    # Collect P4 tasks
    p4_tasks = []
    for subdir in ["generated_hspice", "generated_spectre"]:
        p4_root = Path(f"tasks/p4_spice_sim/{subdir}")
        if p4_root.exists():
            dirs = sorted([d for d in p4_root.iterdir() if d.is_dir()])
            p4_tasks.extend(dirs[:args.p4_count])

    all_tasks = p1_tasks + p4_tasks

    if args.dry_run:
        print(f"Would generate variants for {len(all_tasks)} tasks:")
        for t in all_tasks:
            meta = json.loads((t / "metadata.json").read_text())
            gen = meta.get("generator", {})
            bt = gen.get("bug_type", meta["tool"][0])
            print(f"  {t.name} ({bt})")
        return

    print(f"Generating prompt variants for {len(all_tasks)} tasks...")
    print(f"  P1: {len(p1_tasks)} tasks ({args.p1_count} per bug type)")
    print(f"  P4: {len(p4_tasks)} tasks ({args.p4_count} per tool)")
    print(f"  Provider: {provider.name} ({provider.model})")
    print(f"  Cache: {cache.cache_dir}")
    print()

    results = manager.generate_batch(all_tasks, variant_name=args.variant_name)

    passed = sum(1 for _, r in results if r.passed)
    failed = sum(1 for _, r in results if not r.passed)

    print(f"Results: {passed} passed, {failed} failed safety check")
    for path, result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"  {path.parent.parent.name}/{args.variant_name}.md: {status}")
        if not result.passed:
            for v in result.violations:
                print(f"    violation: {v}")

    print(f"\nCache size: {cache.size} entries")


if __name__ == "__main__":
    main()
