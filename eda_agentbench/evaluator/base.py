"""Base evaluator ABC."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from eda_agentbench.types import RunResult, ScoreComponent


class BaseEvaluator(ABC):
    """Evaluates a RunResult for a specific track."""

    def __init__(self, task_dir: Path, metadata: dict):
        self.task_dir = task_dir
        self.metadata = metadata
        self.weights = metadata["scoring"]["weights"]

    @abstractmethod
    def evaluate_component(self, component_name: str, work_dir: Path, run_log: str) -> ScoreComponent:
        """Evaluate a single scoring component. Returns ScoreComponent."""
        ...
