"""P6 DC Synthesis QA evaluator: robust structure-aware answer matching."""

from __future__ import annotations

from pathlib import Path

from eda_agentbench.evaluator.answer_match import match_answer
from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent


def _read_answer_file(path: Path) -> str:
    """Read the answer from a file, stripping whitespace."""
    if not path.is_file():
        return ""
    return path.read_text(errors="replace").strip()


class DCSynthesisQAEvaluator(BaseEvaluator):
    """Evaluates P6 DC Synthesis QA tasks using answer comparison."""

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

        # Compare using the robust, structure-aware matcher.
        matched, match_detail = match_answer(
            expected_answer, submission_answer, answer_type, tolerance)
        score = 1.0 if matched else 0.0

        details = f"expected={expected_answer!r}, got={submission_answer!r} " \
                  + ("PASS" if matched else "FAIL") + f" [{match_detail}]"

        return ScoreComponent(
            name="answer_match", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=submission_answer[:200],
        )
