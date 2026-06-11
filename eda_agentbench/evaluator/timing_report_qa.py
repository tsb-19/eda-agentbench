"""P3 Timing Report QA evaluator: exact/tolerance-based answer matching."""

from __future__ import annotations

import re
from pathlib import Path

from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent


def _parse_numeric(val_str: str) -> float | None:
    """Try to parse a string as a float."""
    try:
        return float(val_str.strip())
    except (ValueError, TypeError):
        return None


def _normalize_string(s: str) -> str:
    """Normalize a string for comparison: lowercase, strip, collapse whitespace."""
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _read_answer_file(path: Path) -> str:
    """Read the answer from a file, stripping whitespace."""
    if not path.is_file():
        return ""
    return path.read_text(errors="replace").strip()


class TimingReportQAEvaluator(BaseEvaluator):
    """Evaluates P3 Timing Report QA tasks using answer comparison."""

    def __init__(self, task_dir: Path, metadata: dict):
        super().__init__(task_dir, metadata)
        self.answer_config = metadata.get("answer", {})

    def evaluate_component(self, component_name: str, work_dir: Path, run_log: str,
                           mode: str = "submission") -> ScoreComponent:
        weight = self.weights.get(component_name, 0.0)

        if component_name == "answer_match":
            return self._eval_answer_match(weight, work_dir)
        else:
            return ScoreComponent(
                name=component_name, weight=weight, raw_score=0.0,
                weighted_score=0.0, details=f"Unknown component: {component_name}",
            )

    def _eval_answer_match(self, weight: float, work_dir: Path) -> ScoreComponent:
        """Compare submission answer against expected answer."""
        expected_answer = self.answer_config.get("expected", "")
        answer_type = self.answer_config.get("type", "string")
        tolerance = self.answer_config.get("tolerance", 0.01)

        # Read submission answer
        submission_answer = _read_answer_file(work_dir / "answer.txt")

        if not submission_answer:
            return ScoreComponent(
                name="answer_match", weight=weight, raw_score=0.0,
                weighted_score=0.0, details="No answer.txt found in submission",
            )

        # Compare based on answer type
        if answer_type == "numeric":
            score = self._compare_numeric(submission_answer, expected_answer, tolerance)
        else:
            score = self._compare_string(submission_answer, expected_answer)

        details = f"expected={expected_answer!r}, got={submission_answer!r}"
        if score == 1.0:
            details += " PASS"
        else:
            details += " FAIL"

        return ScoreComponent(
            name="answer_match", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=submission_answer[:200],
        )

    def _compare_numeric(self, submission: str, expected: str, tolerance: float) -> float:
        """Compare numeric answers with tolerance."""
        sub_val = _parse_numeric(submission)
        exp_val = _parse_numeric(expected)

        if sub_val is None or exp_val is None:
            # Fall back to string comparison if parsing fails
            return 1.0 if _normalize_string(submission) == _normalize_string(expected) else 0.0

        if exp_val == 0.0:
            # Absolute tolerance for zero
            return 1.0 if abs(sub_val) <= max(abs(tolerance), 1e-9) else 0.0

        # Relative tolerance
        rel_diff = abs(sub_val - exp_val) / abs(exp_val)
        return 1.0 if rel_diff <= tolerance else 0.0

    def _compare_string(self, submission: str, expected: str) -> float:
        """Compare string answers with normalization."""
        sub_norm = _normalize_string(submission)
        exp_norm = _normalize_string(expected)
        return 1.0 if sub_norm == exp_norm else 0.0
