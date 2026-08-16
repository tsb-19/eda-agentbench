"""A trivially scorable evaluator, used only to test the harness contract.

The three task families this repository studies (workflow / STA / SPICE semantic handoff) all
require commercial EDA tools, so none of them can exercise the agentic runner in a tool-free
unit test. Before the slim, `tests/test_agentic_runner.py` borrowed a benchmark QA evaluator for
that job; those benchmark tracks are not part of the paper and were removed, so the runner's
contract -- workspace isolation, hidden-file isolation, artifact emission, timeout handling, CLI
wiring -- is tested against this stub instead.

The stub deliberately implements the *smallest* thing an evaluator can be: compare a submitted
`answer.txt` against `metadata["answer"]["expected"]`. It scores 1.0 on an exact or
tolerance-matching answer and 0.0 otherwise, which is all the runner tests assert. It is not
part of the shipped package and no reported measurement derives from it.

Referenced from task metadata as:
    "evaluator": "tests.support.qa_stub_evaluator:AnswerMatchStub"
"""

from __future__ import annotations

from pathlib import Path

from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent


class AnswerMatchStub(BaseEvaluator):
    """Scores `answer.txt` against the expected answer declared in metadata."""

    def evaluate_component(self, component_name: str, work_dir: Path, run_log: str,
                           mode: str = "submission") -> ScoreComponent:
        weight = self.weights.get(component_name, 0.0)
        spec = self.metadata.get("answer", {})
        expected = str(spec.get("expected", "")).strip()
        submitted_file = work_dir / "answer.txt"

        if not submitted_file.exists():
            return self._component(component_name, weight, 0.0, "answer.txt not submitted")

        submitted = submitted_file.read_text(errors="ignore").strip()
        if spec.get("type") == "numeric":
            ok, detail = self._numeric_match(submitted, expected, float(spec.get("tolerance", 0.0)))
        else:
            ok = submitted == expected
            detail = f"exact match: {submitted!r} vs {expected!r}"

        return self._component(component_name, weight, 1.0 if ok else 0.0, detail)

    @staticmethod
    def _numeric_match(submitted: str, expected: str, tolerance: float) -> tuple[bool, str]:
        try:
            got, want = float(submitted), float(expected)
        except ValueError:
            return False, f"non-numeric answer: {submitted!r}"
        delta = abs(got - want)
        return delta <= tolerance, f"|{got} - {want}| = {delta} (tolerance {tolerance})"

    @staticmethod
    def _component(name: str, weight: float, raw: float, detail: str) -> ScoreComponent:
        return ScoreComponent(
            name=name,
            weight=weight,
            raw_score=raw,
            weighted_score=raw * weight,
            details=detail,
        )
