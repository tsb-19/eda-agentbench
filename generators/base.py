"""Base generator with deterministic seed support."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from pathlib import Path


class BaseGenerator(ABC):
    def __init__(self, seed: int, output_dir: Path):
        self.seed = seed
        self.rng = random.Random(seed)
        self.output_dir = output_dir

    @abstractmethod
    def generate_one(self, task_index: int) -> Path:
        """Generate a single task. Returns path to created task directory."""
        ...

    def generate_batch(self, count: int) -> list[Path]:
        """Generate multiple tasks."""
        paths = []
        for i in range(count):
            p = self.generate_one(i)
            paths.append(p)
        return paths
