"""Manages prompt variant generation and storage."""

from __future__ import annotations

import json
from pathlib import Path

from eda_agentbench.prompt.rewriter import PromptRewriter
from eda_agentbench.prompt.safety import SafetyResult


class VariantManager:
    """Manages prompt variants for tasks.

    Writes variants to prompt_variants/ subdirectory within each task.
    Keeps original prompt.md unchanged.
    """

    def __init__(self, rewriter: PromptRewriter):
        self.rewriter = rewriter

    def generate_variant(
        self,
        task_dir: Path,
        variant_name: str = "llm_v1",
        policy: str = "default",
    ) -> tuple[Path, SafetyResult]:
        """Generate a single prompt variant for a task.

        Args:
            task_dir: Path to the task directory.
            variant_name: Name for the variant (e.g., "llm_v1").
            policy: Rewrite policy identifier.

        Returns:
            Tuple of (variant_path, safety_result).
        """
        prompt_path = task_dir / "prompt.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"No prompt.md in {task_dir}")

        meta_path = task_dir / "metadata.json"
        metadata = None
        if meta_path.exists():
            metadata = json.loads(meta_path.read_text())

        original = prompt_path.read_text()
        rewritten, safety = self.rewriter.rewrite(
            original_prompt=original,
            metadata=metadata,
            policy=policy,
        )

        # Write variant
        variants_dir = task_dir / "prompt_variants"
        variants_dir.mkdir(exist_ok=True)

        variant_path = variants_dir / f"{variant_name}.md"
        variant_path.write_text(rewritten)

        # Write variant metadata
        meta_out = {
            "variant_name": variant_name,
            "provider": self.rewriter.provider.name,
            "model": self.rewriter.provider.model,
            "policy": policy,
            "safety_passed": safety.passed,
            "safety_violations": safety.violations,
            "original_length": len(original),
            "variant_length": len(rewritten),
        }
        meta_path_out = variants_dir / f"{variant_name}_meta.json"
        meta_path_out.write_text(json.dumps(meta_out, indent=2) + "\n")

        return variant_path, safety

    def generate_batch(
        self,
        task_dirs: list[Path],
        variant_name: str = "llm_v1",
        policy: str = "default",
    ) -> list[tuple[Path, SafetyResult]]:
        """Generate variants for multiple tasks.

        Returns list of (variant_path, safety_result) for each task.
        """
        results = []
        for task_dir in task_dirs:
            try:
                result = self.generate_variant(task_dir, variant_name, policy)
                results.append(result)
            except Exception as e:
                results.append((
                    task_dir / "prompt_variants" / f"{variant_name}.md",
                    SafetyResult(passed=False, violations=[str(e)]),
                ))
        return results
