"""P1 RTL Debug evaluator: runs VCS compile + public/hidden tests."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent


class VCSRTLEvaluator(BaseEvaluator):
    """Evaluates RTL debug tasks using VCS."""

    def evaluate_component(self, component_name: str, work_dir: Path, run_log: str,
                           mode: str = "submission") -> ScoreComponent:
        weight = self.weights.get(component_name, 0.0)

        if component_name == "compile":
            return self._eval_compile(weight, run_log)
        elif component_name == "public_test":
            return self._eval_test(weight, run_log, "public")
        elif component_name == "hidden_test":
            return self._eval_test(weight, run_log, "hidden")
        elif component_name == "explanation":
            if mode == "submission":
                return ScoreComponent(
                    name=component_name, weight=weight, raw_score=1.0,
                    weighted_score=1.0 * weight,
                    details="No explanation required in submission mode",
                )
            return ScoreComponent(
                name=component_name, weight=weight, raw_score=0.0,
                weighted_score=0.0, details="Explanation scoring not implemented yet",
            )
        else:
            return ScoreComponent(
                name=component_name, weight=weight, raw_score=0.0,
                weighted_score=0.0, details=f"Unknown component: {component_name}",
            )

    def _eval_compile(self, weight: float, run_log: str) -> ScoreComponent:
        """Check if compilation succeeded (no Error in log)."""
        has_error = bool(re.search(r"^Error", run_log, re.MULTILINE | re.IGNORECASE))
        # Also check for "compilation aborted" or similar fatal messages
        has_fatal = bool(re.search(r"(compilation aborted|cannot open|not found)", run_log, re.IGNORECASE))

        if has_error or has_fatal:
            score = 0.0
            details = "Compilation failed"
        else:
            score = 1.0
            details = "Compilation succeeded"

        return ScoreComponent(
            name="compile", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[:500] if run_log else None,
        )

    def _eval_test(self, weight: float, run_log: str, test_type: str) -> ScoreComponent:
        """Parse test output for PASS/FAIL counts. Only matches 'PASS:'/'FAIL:' lines."""
        pass_count = len(re.findall(r"\bPASS:", run_log))
        fail_count = len(re.findall(r"\bFAIL:", run_log))
        total = pass_count + fail_count

        if total == 0:
            score = 0.0
            details = f"No {test_type} test results found in output"
        else:
            score = pass_count / total
            details = f"{pass_count}/{total} {test_type} test cases passed"

        return ScoreComponent(
            name=f"{test_type}_test", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=run_log[-500:] if run_log else None,
        )


def run_vcs_compile(work_dir: Path, env: dict[str, str], source_files: list[str],
                     timeout: int = 120) -> tuple[bool, str]:
    """Run VCS compilation. Returns (success, output)."""
    cmd = ["vcs", "-full64", "-sverilog"] + source_files + ["-o", "simv", "-ntb_opts", "dtm"]
    try:
        result = subprocess.run(
            cmd, cwd=work_dir, env=env,
            capture_output=True, text=True, timeout=timeout,
        )
        output = result.stdout + "\n" + result.stderr
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "VCS compilation timed out"
    except FileNotFoundError:
        return False, "VCS not found in PATH"


def run_vcs_sim(work_dir: Path, env: dict[str, str], simv_name: str = "simv",
                 timeout: int = 60) -> tuple[bool, str]:
    """Run VCS simulation. Returns (success, output)."""
    cmd = [f"./{simv_name}"]
    try:
        result = subprocess.run(
            cmd, cwd=work_dir, env=env,
            capture_output=True, text=True, timeout=timeout,
        )
        output = result.stdout + "\n" + result.stderr
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "Simulation timed out"
    except FileNotFoundError:
        return False, f"Simulator {simv_name} not found"
