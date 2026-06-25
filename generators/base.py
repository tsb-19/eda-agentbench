"""Base generator with deterministic seed support."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from pathlib import Path

from eda_agentbench.task.loader import structural_validate


class BaseGenerator(ABC):
    def __init__(self, seed: int, output_dir: Path):
        self.seed = seed
        self.rng = random.Random(seed)
        self.output_dir = output_dir

    @abstractmethod
    def generate_one(self, task_index: int) -> Path:
        """Generate a single task. Returns path to created task directory."""
        ...

    def generate_batch(self, count: int, validate: bool = True) -> list[Path]:
        """Generate multiple tasks.

        Each emitted task is structurally validated (tool-free: schema + required
        files + golden present), so a regeneration can't silently ship a broken task.
        Pass validate=False only for deliberate mid-construction tests.
        """
        paths = []
        for i in range(count):
            p = self.generate_one(i)
            if validate:
                issues = structural_validate(p)
                if issues:
                    raise ValueError(f"generated task {p} is structurally invalid: " + "; ".join(issues))
            paths.append(p)
        return paths
