"""P2 Testbench/SVA Generation evaluator: mutation-based scoring with VCS."""

from __future__ import annotations

import re
from pathlib import Path

from eda_agentbench.evaluator.base import BaseEvaluator
from eda_agentbench.types import ScoreComponent

# Sentinel the CLI uses to pack the golden transcript ahead of a mutant transcript
# in a single mutant_* component payload (see cli.py P2 log_map).
_GOLDEN_MUTANT_SEP = "<<<EDA_P2_GOLDEN_SEP>>>"

# Volatile simulator boilerplate that differs run-to-run (timestamps, binary names,
# the VCS report footer) and would otherwise make every golden/mutant pair "differ".
# Dropping these leaves only the testbench's own $display output for the diff.
_BOILERPLATE_RE = re.compile(
    r"(?:"
    r"^\s*===.*===\s*$"                     # "=== Golden Design ===" / "=== Mutant N ==="
    r"|Chronologic VCS|Contains Synopsys|Compiler version|Runtime version"
    r"|V\s*C\s*S\s+S\s*i\s*m"               # "V C S Simulation Report" (spaced)
    r"|Simulation Report|CPU Time|Data structure size"
    r"|\$finish|\bsimv\w*\b|up to date|UDP read"
    # VCS incremental compile/link noise (appears only when a binary is freshly
    # built vs cached "up to date" — an artifact of the shared workdir, not design
    # behavior). Must be stripped or golden(cached) vs mutant(rebuilt) falsely differ.
    r"|ld -shared|rm -f|_cuarc|\.daidir|\.so\b|objs/|\.o\b"
    r"|^\s*Time:\s*\d"                       # report footer "Time: N"
    r"|^\s*\d+ +modules? "                   # "1 module and 0 UDP read."
    r"|(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) +(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"|Note:|Lic|license"
    r")",
    re.IGNORECASE,
)


def _normalize_transcript(text: str) -> list[str]:
    """Reduce a VCS run log to the testbench's own behavioral output.

    Strips blank lines and known simulator boilerplate (banners, timestamps,
    binary names, the run report) so that two runs of the SAME testbench differ
    only because the design under test behaved differently. Returns the surviving
    lines (stripped) as an ordered list for exact comparison.
    """
    out: list[str] = []
    for line in (text or "").splitlines():
        s = line.strip()
        if not s:
            continue
        if _BOILERPLATE_RE.search(s):
            continue
        out.append(s)
    return out


class TBSVAGenEvaluator(BaseEvaluator):
    """Evaluates testbench/SVA generation tasks using VCS and mutation-based grading."""

    def evaluate_component(self, component_name: str, work_dir: Path, run_log: str,
                           mode: str = "submission") -> ScoreComponent:
        weight = self.weights.get(component_name, 0.0)

        if component_name == "compile":
            return self._eval_compile(weight, run_log)
        elif component_name == "golden_pass":
            return self._eval_golden(weight, run_log)
        elif component_name.startswith("mutant_"):
            return self._eval_mutant(component_name, weight, run_log)
        elif component_name == "explanation":
            return ScoreComponent(
                name=component_name, weight=weight, raw_score=1.0,
                weighted_score=1.0 * weight,
                details="No explanation required in submission mode",
            )
        else:
            return ScoreComponent(
                name=component_name, weight=weight, raw_score=0.0,
                weighted_score=0.0, details=f"Unknown component: {component_name}",
            )

    def _eval_compile(self, weight: float, run_log: str) -> ScoreComponent:
        """Check if VCS compilation succeeded.

        An empty log or a timeout is treated as failure: with no output there is
        no evidence VCS ran, so it must not score as a successful compile.
        (Previously a non-empty log with no explicit ``^Error`` line — e.g. a run
        that timed out — fell through to 1.0, the same false-pass bug fixed in the
        P1 RTL-debug evaluator.)
        """
        text = run_log or ""
        has_error = bool(re.search(r"^Error", text, re.MULTILINE | re.IGNORECASE))
        has_fatal = bool(re.search(r"(compilation aborted|cannot open|not found|timed out)",
                                   text, re.IGNORECASE))
        no_output = not text.strip()

        if no_output or has_error or has_fatal:
            score = 0.0
            details = "Compilation produced no output (did not run)" if no_output else "Compilation failed"
        else:
            score = 1.0
            details = "Compilation succeeded"

        return ScoreComponent(
            name="compile", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=text[:500] if text else None,
        )

    def _eval_golden(self, weight: float, run_log: str) -> ScoreComponent:
        """Precondition: the testbench compiles and *runs to completion* on the
        golden (correct) design without a compile error or simulator crash.

        This intentionally does NOT read any model-printed verdict (no
        ALL_TESTS_PASS): whether a testbench "should" pass the golden is the
        testbench's own judgment and grading it on a self-reported token is
        circular. We only require a clean run so the golden transcript is a valid
        baseline for the differential mutant checks. Bug-finding ability is scored
        by the mutant_* components, not here.
        """
        text = run_log or ""
        has_error = bool(re.search(r"^Error", text, re.MULTILINE | re.IGNORECASE))
        crashed = bool(re.search(r"Segmentation fault|core dumped|Fatal", text, re.IGNORECASE))
        completed = bool(re.search(r"\$finish|V\s*C\s*S\s+S|Simulation Report", text)
                         or _normalize_transcript(text))
        no_output = not text.strip()

        if no_output or has_error or crashed or not completed:
            score = 0.0
            if no_output:
                details = "Testbench produced no output on golden (did not run)"
            elif has_error:
                details = "Testbench failed to compile/run on golden (error)"
            elif crashed:
                details = "Simulator crashed on golden design"
            else:
                details = "Testbench did not run to completion on golden"
        else:
            score = 1.0
            details = "Testbench runs cleanly to completion on golden design"

        return ScoreComponent(
            name="golden_pass", weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=text[-500:] if text else None,
        )

    def _eval_mutant(self, component_name: str, weight: float, run_log: str) -> ScoreComponent:
        """Differential check: a mutant is *caught* iff the testbench's observable
        simulation behavior on the mutant differs from its behavior on the golden.

        ``run_log`` is the golden transcript and this mutant's transcript packed
        together by the CLI (separated by ``_GOLDEN_MUTANT_SEP``). We normalize
        away simulator boilerplate (banners, timestamps, binary names, the run
        report) and compare what remains — the testbench's own ``$display`` output.
        Different ⇒ the stimulus made the bug observable (caught); identical ⇒ this
        testbench fails to expose this bug. No model-printed verdict is consulted.
        """
        golden_raw, sep, mutant_raw = run_log.partition(_GOLDEN_MUTANT_SEP)
        if not sep:
            # No golden baseline available — cannot judge differentially.
            return ScoreComponent(
                name=component_name, weight=weight, raw_score=0.0,
                weighted_score=0.0,
                details="Mutant NOT caught: missing golden baseline for comparison",
            )

        golden_norm = _normalize_transcript(golden_raw)
        mutant_norm = _normalize_transcript(mutant_raw)

        # A mutant that fails to compile/run (empty behavioral output) while the
        # golden produced output is still distinguished by the testbench → caught.
        caught = golden_norm != mutant_norm
        score = 1.0 if caught else 0.0
        if caught:
            details = "Mutant caught: testbench behaves differently on buggy vs golden design"
        elif not golden_norm and not mutant_norm:
            details = "Mutant NOT caught: testbench produced no observable output (no checks)"
        else:
            details = "Mutant NOT caught: identical behavior on buggy and golden design"

        return ScoreComponent(
            name=component_name, weight=weight, raw_score=score,
            weighted_score=score * weight, details=details,
            tool_output_snippet=("\n".join(mutant_norm)[:500]) or None,
        )
