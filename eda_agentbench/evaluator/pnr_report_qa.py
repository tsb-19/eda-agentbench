"""P8 PnR Report QA evaluator: parser-based answer matching.

Scoring model:
  - answer_match: exact match for strings/ints, tolerance for floats
  - explanation: low-weight auxiliary (defaults to 1.0 in submission mode)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent

# Tolerance for floating-point comparisons (relative)
FLOAT_TOLERANCE = 0.02  # 2% relative tolerance

# Fields that should be compared as strings (exact match)
STRING_FIELDS = {
    "tool_family", "design_name", "stage", "worst_endpoint", "worst_startpoint",
    "worst_congestion_layer",
}

# Fields that should be compared as integers (exact match)
INT_FIELDS = {
    "setup_violations", "hold_violations", "instance_count", "sequential_count",
    "buffer_count", "congested_bins", "drc_total", "shorts", "opens",
    "antenna_violations",
}

# Fields that should be compared as booleans (exact match)
BOOL_FIELDS = {
    "timing_met", "congestion_pass", "route_completed",
}

# Fields that should be compared as floats (tolerance)
FLOAT_FIELDS = {
    "setup_wns", "setup_tns", "hold_wns", "hold_tns",
    "core_utilization", "placement_density", "cell_area", "macro_area",
    "total_cell_area", "total_wirelength", "max_horizontal_overflow",
    "max_vertical_overflow", "total_overflow", "internal_power",
    "switching_power", "leakage_power", "total_power",
}


def _compare_values(expected: str, actual: str, field: str) -> tuple[bool, str]:
    """Compare expected and actual answer strings.

    Returns (match: bool, details: str).
    """
    exp_clean = expected.strip()
    act_clean = actual.strip()

    if field in STRING_FIELDS:
        match = exp_clean.lower() == act_clean.lower()
        return match, f"string match: expected={exp_clean!r}, actual={act_clean!r}"

    if field in BOOL_FIELDS:
        exp_bool = exp_clean.lower() in ("true", "1", "yes")
        act_bool = act_clean.lower() in ("true", "1", "yes")
        match = exp_bool == act_bool
        return match, f"bool match: expected={exp_clean!r}, actual={act_clean!r}"

    if field in INT_FIELDS:
        try:
            exp_int = int(exp_clean)
            act_int = int(act_clean)
            match = exp_int == act_int
            return match, f"int match: expected={exp_int}, actual={act_int}"
        except ValueError:
            return False, f"int parse error: expected={exp_clean!r}, actual={act_clean!r}"

    if field in FLOAT_FIELDS:
        try:
            exp_float = float(exp_clean)
            act_float = float(act_clean)
            if exp_float == 0:
                match = abs(act_float) < 0.001
            else:
                match = abs(exp_float - act_float) / abs(exp_float) <= FLOAT_TOLERANCE
            return match, f"float match: expected={exp_float:.4f}, actual={act_float:.4f}, tol={FLOAT_TOLERANCE}"
        except ValueError:
            return False, f"float parse error: expected={exp_clean!r}, actual={act_clean!r}"

    # Default: exact string match
    match = exp_clean == act_clean
    return match, f"exact match: expected={exp_clean!r}, actual={act_clean!r}"


class PnRReportQAEvaluator(BaseEvaluator):
    """Evaluates P8 PnR Report QA tasks using parser-based answer matching."""

    def __init__(self, task_dir: Path, metadata: dict):
        super().__init__(task_dir, metadata)

    def evaluate_component(self, component_name: str, work_dir: Path, run_log: str,
                           mode: str = "submission") -> ScoreComponent:
        weight = self.weights.get(component_name, 0.0)

        if component_name == "answer_match":
            return self._eval_answer_match(weight, work_dir)
        elif component_name == "explanation":
            if mode == "submission":
                return ScoreComponent(
                    name=component_name, weight=weight, raw_score=1.0,
                    weighted_score=1.0 * weight,
                    details="No explanation required in submission mode",
                )
            return ScoreComponent(
                name=component_name, weight=weight, raw_score=0.0,
                weighted_score=0.0, details="Explanation scoring not implemented",
            )
        else:
            return ScoreComponent(
                name=component_name, weight=weight, raw_score=0.0,
                weighted_score=0.0, details=f"Unknown component: {component_name}",
            )

    def _eval_answer_match(self, weight: float, work_dir: Path) -> ScoreComponent:
        """Check submitted answers against oracle answers."""
        # Load oracle answers from solution/answer.txt
        oracle_path = self.task_dir / "solution" / "answer.txt"
        if not oracle_path.exists():
            return ScoreComponent(
                name="answer_match", weight=weight, raw_score=0.0,
                weighted_score=0.0, details="Oracle answer.txt not found in solution/",
            )

        try:
            with open(oracle_path) as f:
                oracle = json.load(f)
        except json.JSONDecodeError:
            return ScoreComponent(
                name="answer_match", weight=weight, raw_score=0.0,
                weighted_score=0.0, details="Oracle answer.txt is not valid JSON",
            )

        # Load submitted answers from work_dir/answer.txt
        submission_path = work_dir / "answer.txt"
        if not submission_path.exists():
            return ScoreComponent(
                name="answer_match", weight=weight, raw_score=0.0,
                weighted_score=0.0, details="Submitted answer.txt not found",
            )

        try:
            with open(submission_path) as f:
                submission = json.load(f)
        except json.JSONDecodeError:
            return ScoreComponent(
                name="answer_match", weight=weight, raw_score=0.0,
                weighted_score=0.0, details="Submitted answer.txt is not valid JSON",
            )

        # Compare each oracle answer
        total = len(oracle)
        if total == 0:
            return ScoreComponent(
                name="answer_match", weight=weight, raw_score=0.0,
                weighted_score=0.0, details="No oracle answers defined",
            )

        correct = 0
        details_list = []
        for field, expected in oracle.items():
            actual = submission.get(field)
            if actual is None:
                details_list.append(f"{field}: MISSING")
                continue

            match, detail = _compare_values(str(expected), str(actual), field)
            if match:
                correct += 1
            details_list.append(f"{field}: {detail}")

        score = correct / total
        details = f"{correct}/{total} correct. " + "; ".join(details_list[:5])
        if len(details_list) > 5:
            details += f" ... and {len(details_list) - 5} more"

        return ScoreComponent(
            name="answer_match", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
        )
