"""P4 SPICE simulation evaluator: parses HSPICE .mt0/.lis measurement results."""

from __future__ import annotations

import re
from pathlib import Path

from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent


def _parse_hspice_value(val_str: str) -> float | None:
    """Parse a HSPICE value with engineering suffixes (e.g., 8.3984n, 1.2k, 10p)."""
    suffixes = {"t": 1e12, "g": 1e9, "meg": 1e6, "k": 1e3, "m": 1e-3,
                "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15, "a": 1e-18}
    val_str = val_str.strip().lower()
    # Try engineering suffix
    for suffix, mult in sorted(suffixes.items(), key=lambda x: -len(x[0])):
        if val_str.endswith(suffix):
            try:
                return float(val_str[:-len(suffix)]) * mult
            except ValueError:
                pass
    # Try plain float / scientific notation
    try:
        return float(val_str)
    except ValueError:
        return None


def parse_hspice_measurements(lis_path: Path) -> dict[str, float]:
    """Parse measurement values from HSPICE .lis output file.

    Handles formats like:
      tdrise = 7.1234E-09    (scientific notation)
      tdrise=   8.3984n      (engineering suffix)

    Returns dict of {measure_name: value}.
    """
    if not lis_path.is_file():
        return {}

    text = lis_path.read_text(errors="replace")
    results: dict[str, float] = {}

    # Pattern: "name = value" or "name= value" (with optional engineering suffix)
    # Use word boundary to find name=value pairs anywhere on a line
    for m in re.finditer(r"\b(\w+)\s*=\s*([0-9eE.+\-]+[a-zA-Z]*)\b", text):
        name = m.group(1).lower()
        val = _parse_hspice_value(m.group(2))
        if val is not None:
            results[name] = val

    # Pattern: measurement name on one line, value on next line (mt0 format)
    lines = text.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("*") and "=" not in stripped:
            if re.match(r"^[a-zA-Z_]\w*$", stripped) and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                val = _parse_hspice_value(next_line)
                if val is not None:
                    results[stripped.lower()] = val

    return results


class SPICESimEvaluator(BaseEvaluator):
    """Evaluates SPICE simulation tasks using parsed measurement results."""

    def evaluate_component(self, component_name: str, work_dir: Path, run_log: str,
                           mode: str = "submission") -> ScoreComponent:
        weight = self.weights.get(component_name, 0.0)

        if component_name == "tool_run":
            return self._eval_tool_run(weight, run_log)
        elif component_name == "output_generated":
            return self._eval_output_generated(weight, work_dir)
        elif component_name == "public_metric":
            return self._eval_metric(weight, work_dir, "public", run_log)
        elif component_name == "hidden_metric":
            return self._eval_metric(weight, work_dir, "hidden", run_log)
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

    def _eval_tool_run(self, weight: float, run_log: str) -> ScoreComponent:
        """Check if HSPICE ran without fatal errors."""
        has_abort = bool(re.search(r"job aborted", run_log, re.IGNORECASE))
        has_concluded = bool(re.search(r"job concluded", run_log, re.IGNORECASE))

        if has_abort and not has_concluded:
            score = 0.0
            details = "HSPICE run aborted"
        else:
            score = 1.0
            details = "HSPICE run completed"

        return ScoreComponent(
            name="tool_run", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[:500] if run_log else None,
        )

    def _eval_output_generated(self, weight: float, work_dir: Path) -> ScoreComponent:
        """Check if .lis output file exists and has content."""
        lis_files = list(work_dir.glob("*.lis"))
        if not lis_files:
            return ScoreComponent(
                name="output_generated", weight=weight, raw_score=0.0,
                weighted_score=0.0, details="No .lis output file found",
            )

        lis = lis_files[0]
        content = lis.read_text(errors="replace")
        if len(content) < 100:
            return ScoreComponent(
                name="output_generated", weight=weight, raw_score=0.0,
                weighted_score=0.0, details=".lis file is empty or too small",
            )

        return ScoreComponent(
            name="output_generated", weight=weight, raw_score=1.0,
            weighted_score=1.0 * weight, details=f"Output file {lis.name} generated ({len(content)} bytes)",
        )

    def _eval_metric(self, weight: float, work_dir: Path, metric_type: str,
                      run_log: str) -> ScoreComponent:
        """Evaluate a measurement metric (public or hidden)."""
        # Get metric config from metadata
        metrics_config = self.metadata.get("scoring", {}).get("metrics", {})
        metric_cfg = metrics_config.get(metric_type)

        if not metric_cfg:
            # No metric config — try to parse from run_log
            return ScoreComponent(
                name=f"{metric_type}_metric", weight=weight, raw_score=0.0,
                weighted_score=0.0, details=f"No {metric_type} metric configuration",
            )

        measure_name = metric_cfg.get("measure", "").lower()
        target = metric_cfg.get("target")
        tolerance = metric_cfg.get("tolerance", 0.1)
        min_val = metric_cfg.get("min")
        max_val = metric_cfg.get("max")

        # Parse measurements from all .lis files
        lis_files = list(work_dir.glob("*.lis"))
        if not lis_files:
            return ScoreComponent(
                name=f"{metric_type}_metric", weight=weight, raw_score=0.0,
                weighted_score=0.0, details="No .lis file to parse",
            )

        measurements: dict[str, float] = {}
        for lis in lis_files:
            measurements.update(parse_hspice_measurements(lis))
        actual = measurements.get(measure_name)

        if actual is None:
            return ScoreComponent(
                name=f"{metric_type}_metric", weight=weight, raw_score=0.0,
                weighted_score=0.0, details=f"Measurement '{measure_name}' not found in output",
            )

        # Check if within range
        in_range = True
        if min_val is not None and actual < min_val:
            in_range = False
        if max_val is not None and actual > max_val:
            in_range = False
        if target is not None:
            if abs(actual - target) > tolerance * abs(target):
                in_range = False

        score = 1.0 if in_range else 0.0
        details = f"{measure_name}={actual:.4e}"
        if target is not None:
            details += f" (target={target:.4e}, tol={tolerance})"
        if min_val is not None:
            details += f" range=[{min_val:.4e}, {max_val:.4e}]"
        details += " PASS" if in_range else " FAIL"

        return ScoreComponent(
            name=f"{metric_type}_metric", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=f"{measure_name} = {actual}",
        )
