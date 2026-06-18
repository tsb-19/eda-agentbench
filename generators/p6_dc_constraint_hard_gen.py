"""P6 DC Constraint Debug — HARD semantic variant (residual-frontier track).

WHY THIS EXISTS
---------------
The base generator (``p6_dc_constraint_debug_gen``) injects EXECUTION-BREAKING
constraint bugs — missing clock, wrong/invalid port name, syntax error,
unsupported command. Design Compiler *reports these as errors* (``Can't find
port``, ``unknown command``, nonzero exit), so the tool's own message reveals
the bug. Frontier models fix them trivially: single-shot ~0.98, and under the
agentic loop the strongest models sweep the track. The difficulty there is
"read the error, fix the typo" — not constraint engineering.

This variant injects SEMANTIC bugs that DC ACCEPTS SILENTLY:
  * wrong clock period (``create_clock -period`` value ≠ spec)
  * wrong IO delay value (``set_input_delay``/``set_output_delay`` ≠ spec)
  * missing IO delay (a port left unconstrained)
DC applies all of these without error, so there is NO tool message to follow.
The model must reason about the design's timing INTENT (stated as an explicit
spec in the prompt) and compare every constraint to it — exactly what a chip
engineer does in SDC review, and exactly the kind of silent-but-dangerous
constraint defect that escapes to silicon. This is real engineering difficulty,
not a contrived trap.

GRADING (continuous, tool-grounded, forge-resistant)
----------------------------------------------------
Same two-phase laundering as the base track: the apply TCL does
``read_sdc constraints.sdc`` (which sandboxes agent Tcl ``proc``/``exit``) then
``write_sdc applied_<section>.sdc`` to launder the genuinely-applied
constraints. The HIDDEN run then scores ``applied_hidden.sdc`` against the spec
with a Python checker, emitting ``CONSTRAINTS_SCORE: <fraction>`` =
(# spec properties satisfied) / (# spec properties). Properties = clock period
+ one per input port + one per output port. K ≈ half are bugged, so an unfixed
deck floors well below a correct one (clean golden/buggy margin) while a
partial fix earns partial credit (continuous discrimination).

Crucially, ``run_public.sh`` reports ONLY whether DC accepted the constraints —
NOT the semantic verdict — so the public tool gives the agent no oracle for
correctness. The agent must self-verify against the stated spec.
"""

from __future__ import annotations

import json
from pathlib import Path

from generators.base import BaseGenerator
from generators.p6_dc_constraint_debug_gen import (
    RTL_TEMPLATES,
    _correct_sdc,
    _make_tcl,
)

# Correct (spec) values used by ``_correct_sdc``.
SPEC_IN_DELAY = 0.5
SPEC_OUT_DELAY = 0.5

# Templates with modest port counts → small property set → K=2..3 bugs gives a
# clean golden/buggy margin without an unwieldy edit. (mux_reg/alu_reg excluded:
# too many ports dilute the bugged fraction.)
_HARD_TEMPLATE_NAMES = [
    "counter", "shift_reg", "fsm_ctrl", "adder_pipe", "accumulator",
    "comparator_reg", "decoder_reg", "updown_counter",
]
_HARD_TEMPLATES = [t for t in RTL_TEMPLATES if t["name"] in _HARD_TEMPLATE_NAMES]


# ---------------------------------------------------------------------------
# Generic semantic checker (written into each task's hidden/ dir, run on the
# laundered applied SDC). Robust to write_sdc canonical form:
#   create_clock [get_ports clk] -period 2 -waveform {0 1}
#   set_input_delay -clock clk  0.5  [get_ports rst_n]      (scalar, unbraced)
#   set_output_delay -clock clk 0.5  [get_ports {dout[7]}]  (bus, per-bit)
# ---------------------------------------------------------------------------
CHECK_PY = r'''#!/usr/bin/env python3
"""Semantic constraint checker (HIDDEN). Scores a laundered applied SDC against
the task spec. Prints CONSTRAINTS_SCORE: <fraction> and a per-property detail.

Usage: check_constraints.py <applied_sdc> <spec_json>
"""
import json, re, sys

def feq(a, b, tol=1e-4):
    return abs(a - b) <= tol + 1e-6 * max(abs(a), abs(b))

def port_base(tok):
    return re.sub(r"\[\d+\]$", "", tok.strip().strip("{}"))

def main():
    applied, specf = sys.argv[1], sys.argv[2]
    spec = json.load(open(specf))
    clk = spec["clk"]
    period = float(spec["period"])
    din = float(spec["input_delay"])
    dout = float(spec["output_delay"])
    try:
        txt = open(applied).read()
    except OSError:
        print("CONSTRAINTS_SCORE: 0.0000")
        print("CONSTRAINTS_DETAIL: no_applied_sdc")
        return

    results = {}
    # Clock period
    m = re.search(r"create_clock[^\n]*?-period\s+([0-9.eE+-]+)", txt)
    results["period"] = bool(m) and feq(float(m.group(1)), period)

    # IO delays: collect base_port -> [(clock, value), ...]
    def collect(kind):
        d = {}
        for line in txt.splitlines():
            if not line.strip().startswith(kind):
                continue
            cm = re.search(r"-clock\s+(\S+)", line)
            vm = re.search(r"-clock\s+\S+\s+([0-9.eE+-]+)", line)
            pm = re.search(r"get_ports\s+\{?([A-Za-z0-9_]+(?:\[\d+\])?)\}?", line)
            if not (cm and vm and pm):
                continue
            d.setdefault(port_base(pm.group(1)), []).append((cm.group(1), float(vm.group(1))))
        return d

    ind = collect("set_input_delay")
    outd = collect("set_output_delay")
    for p in spec["inputs"]:
        lst = ind.get(p, [])
        results["in:" + p] = bool(lst) and all(c == clk and feq(v, din) for c, v in lst)
    for p in spec["outputs"]:
        lst = outd.get(p, [])
        results["out:" + p] = bool(lst) and all(c == clk and feq(v, dout) for c, v in lst)

    total = len(results)
    correct = sum(1 for v in results.values() if v)
    score = correct / total if total else 0.0
    print("CONSTRAINTS_SCORE: %.4f" % score)
    print("CONSTRAINTS_DETAIL: " + " ".join(
        "%s=%s" % (k, "ok" if v else "BAD") for k, v in results.items()))

if __name__ == "__main__":
    main()
'''


def _make_public_sh(rtl: dict) -> str:
    """Public runner: applies the agent's SDC and reports ONLY DC-acceptance.

    Deliberately withholds the semantic verdict (correctness vs spec) — for these
    silent bugs DC always accepts, so a clean apply does NOT mean the constraints
    match the spec. The agent must verify correctness itself; the hidden runner
    computes the real score."""
    top = rtl["top"]
    return f"""\
#!/bin/bash
# DC Constraint Debug (semantic) — PUBLIC runner: reports DC-acceptance only.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
DC_CMD="${{EDA_DC_CMD:-dc_shell}}"
APPLIED="applied_public.sdc"

if ! command -v "$DC_CMD" &>/dev/null; then
    echo "SKIP: dc_shell not found (EDA_DC_CMD=$DC_CMD)"
    exit 0
fi

rm -f "$APPLIED"
APPLY_OUT=$("$DC_CMD" -f run_public.tcl 2>&1)
echo "$APPLY_OUT" | sed 's/^/[apply] /'

# Acceptance = laundered SDC produced AND no hard tool error. NO semantic verdict.
if [ -s "$APPLIED" ] && ! echo "$APPLY_OUT" | grep -Eq "unknown command|Can't find|cannot find|Syntax error"; then
    echo "APPLIED_OK"
    echo "NOTE: DC accepted your constraints. This does NOT verify they match the spec."
    exit 0
else
    echo "APPLIED_FAIL"
    exit 1
fi
"""


def _make_hidden_sh(rtl: dict) -> str:
    """Hidden runner: apply + semantic score over the laundered applied SDC."""
    top = rtl["top"]
    return f"""\
#!/bin/bash
# DC Constraint Debug (semantic) — HIDDEN runner: continuous semantic score.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
DC_CMD="${{EDA_DC_CMD:-dc_shell}}"
APPLIED="applied_hidden.sdc"

if ! command -v "$DC_CMD" &>/dev/null; then
    echo "SKIP: dc_shell not found (EDA_DC_CMD=$DC_CMD)"
    exit 0
fi
if ! command -v python3 &>/dev/null; then
    echo "SKIP: python3 not found"
    exit 0
fi

rm -f "$APPLIED"
APPLY_OUT=$("$DC_CMD" -f run_hidden.tcl 2>&1)
echo "$APPLY_OUT" | sed 's/^/[apply] /'

if [ -s "$APPLIED" ] && ! echo "$APPLY_OUT" | grep -Eq "unknown command|Can't find|cannot find|Syntax error"; then
    python3 check_constraints.py "$APPLIED" spec.json
    exit 0
else
    echo "CONSTRAINTS_SCORE: 0.0000"
    echo "CONSTRAINTS_DETAIL: apply_failed"
    exit 1
fi
"""


# ---------------------------------------------------------------------------
# Semantic bug injection
# ---------------------------------------------------------------------------

def _build_sdc(rtl: dict, period_ns: float, bugs: dict) -> str:
    """Build an SDC for the template, applying the per-property mutations in
    ``bugs``. ``bugs`` maps a property key to a mutation:
        "period"   -> wrong period value (float)
        "in:<p>"   -> ("wrong", value) or ("missing",)
        "out:<p>"  -> ("wrong", value) or ("missing",)
    Absent keys are emitted correctly (spec values)."""
    top = rtl["top"]
    clk = rtl["clk"]
    inputs = [p for p in rtl["inputs"] if p != clk]
    outputs = rtl["outputs"]

    period = bugs.get("period", period_ns)
    lines = [
        f"# SDC constraints for {top}",
        f"create_clock -name {clk} -period {period} [get_ports {{{clk}}}]",
        f"set_clock_uncertainty 0.1 [get_clocks {{{clk}}}]",
        "",
    ]
    for inp in inputs:
        b = bugs.get(f"in:{inp}")
        if b is not None and b[0] == "missing":
            continue
        val = b[1] if (b is not None and b[0] == "wrong") else SPEC_IN_DELAY
        lines.append(f"set_input_delay {val} -clock {clk} [get_ports {{{inp}}}]")
    lines.append("")
    for out in outputs:
        b = bugs.get(f"out:{out}")
        if b is not None and b[0] == "missing":
            continue
        val = b[1] if (b is not None and b[0] == "wrong") else SPEC_OUT_DELAY
        lines.append(f"set_output_delay {val} -clock {clk} [get_ports {{{out}}}]")
    lines.append("")
    lines.append("set_max_area 0")
    lines.append("")
    return "\n".join(lines)


class P6DCConstraintHardGenerator(BaseGenerator):
    """Generates HARD semantic P6 DC Constraint Debug tasks (deterministic)."""

    def generate_one(self, task_index: int) -> Path:
        rtl = _HARD_TEMPLATES[task_index % len(_HARD_TEMPLATES)]
        clk = rtl["clk"]
        inputs = [p for p in rtl["inputs"] if p != clk]
        outputs = rtl["outputs"]
        period_ns = self.rng.choice([2.0, 3.0, 5.0, 10.0])

        # Property set that can be bugged + scored.
        props = ["period"] + [f"in:{p}" for p in inputs] + [f"out:{p}" for p in outputs]
        total = len(props)
        # K ≈ half the properties, in [2, 3]; never exceed available props.
        k = min(max(2, round(0.5 * total)), 3, total)

        chosen = self.rng.sample(props, k)
        wrong_delay_choices = [0.0, 1.0, 2.0, round(period_ns, 2)]
        bugs: dict = {}
        injected = []
        for prop in chosen:
            if prop == "period":
                bugs["period"] = round(period_ns * 2, 3)  # silently-accepted wrong period
                injected.append(f"wrong_period({period_ns}->{bugs['period']})")
            else:
                kind_io, port = prop.split(":", 1)
                spec_val = SPEC_IN_DELAY if kind_io == "in" else SPEC_OUT_DELAY
                mode = self.rng.choice(["wrong", "missing"])
                if mode == "wrong":
                    wv = next(w for w in self.rng.sample(wrong_delay_choices, len(wrong_delay_choices)) if w != spec_val)
                    bugs[prop] = ("wrong", wv)
                    injected.append(f"wrong_{kind_io}_delay:{port}(->{wv})")
                else:
                    bugs[prop] = ("missing",)
                    injected.append(f"missing_{kind_io}_delay:{port}")

        buggy_sdc = _build_sdc(rtl, period_ns, bugs)
        correct_sdc = _build_sdc(rtl, period_ns, {})

        task_id = f"dc_constraint_{9000 + task_index:04d}"
        task_dir = self.output_dir / task_id
        (task_dir / "files").mkdir(parents=True, exist_ok=True)
        (task_dir / "hidden").mkdir(exist_ok=True)
        (task_dir / "solution").mkdir(exist_ok=True)

        # Design + buggy/solution SDC
        (task_dir / "files" / "design.v").write_text(rtl["rtl"])
        (task_dir / "files" / "constraints.sdc").write_text(buggy_sdc)
        (task_dir / "solution" / "constraints.sdc").write_text(correct_sdc)

        # Apply TCL (reused, forge-resistant) + runners
        (task_dir / "files" / "run_public.tcl").write_text(_make_tcl(rtl, "public"))
        (task_dir / "files" / "run_public.sh").write_text(_make_public_sh(rtl))
        (task_dir / "hidden" / "run_hidden.tcl").write_text(_make_tcl(rtl, "hidden"))
        (task_dir / "hidden" / "run_hidden.sh").write_text(_make_hidden_sh(rtl))
        (task_dir / "hidden" / "check_constraints.py").write_text(CHECK_PY)

        # Hidden spec consumed by the checker
        spec = {
            "clk": clk,
            "period": period_ns,
            "input_delay": SPEC_IN_DELAY,
            "output_delay": SPEC_OUT_DELAY,
            "inputs": inputs,
            "outputs": outputs,
        }
        (task_dir / "hidden" / "spec.json").write_text(json.dumps(spec, indent=2) + "\n")

        (task_dir / "files" / "run_public.sh").chmod(0o755)
        (task_dir / "hidden" / "run_hidden.sh").chmod(0o755)
        (task_dir / "hidden" / "check_constraints.py").chmod(0o755)

        in_list = ", ".join(inputs) if inputs else "(none)"
        out_list = ", ".join(outputs) if outputs else "(none)"
        prompt = f"""\
# DC Constraint Debug: {rtl['name']}

## Goal

Constrain `{rtl['name']}` for Design Compiler synthesis so the constraints match
the design's timing spec below. The given `constraints.sdc` contains one or more
bugs: some constraints **deviate from the spec**. Design Compiler may still apply
them **without reporting any error** — a wrong period or delay value is silently
accepted — so you cannot rely on the tool to point out what is wrong. Compare
every constraint to the spec yourself and fix `constraints.sdc` so all of them
match.

## Timing spec (the design intent)

- Clock `{clk}`: period **{period_ns} ns** (50% duty cycle)
- Every input except `{clk}` has an input delay of **{SPEC_IN_DELAY} ns** relative to `{clk}`
- Every output has an output delay of **{SPEC_OUT_DELAY} ns** relative to `{clk}`
- Inputs to constrain: {in_list}
- Outputs to constrain: {out_list}

## Files

- `design.v` — RTL design (do not modify)
- `constraints.sdc` — constraint file (you may edit this file)
- `run_public.sh` — applies your SDC in Design Compiler (do not modify)

## Rules

- Only modify `constraints.sdc`.
- `run_public.sh` reports only whether Design Compiler **accepted** your
  constraints — it does **not** check them against the spec. Acceptance does not
  mean correctness; verify each value yourself.
"""
        (task_dir / "prompt.md").write_text(prompt)

        meta = {
            "task_id": task_id,
            "track": "p6_dc_constraint_debug",
            "tool": ["dc"],
            "difficulty": "hard",
            "data_type": "template_synthetic",
            "resource_preset": "standard",
            "timeout_sec": 300,
            "max_tool_calls": 30,
            "max_patch_attempts": 8,
            "max_output_tokens": 32000,
            "files": {
                "visible": ["design.v", "constraints.sdc", "run_public.sh", "run_public.tcl"],
                "editable": ["constraints.sdc"],
                "hidden": ["run_hidden.sh", "run_hidden.tcl", "check_constraints.py", "spec.json"],
                "forbidden": ["design.v", "run_public.sh", "run_public.tcl",
                              "run_hidden.sh", "run_hidden.tcl", "check_constraints.py", "spec.json"],
            },
            "run_command": "bash run_public.sh && bash run_hidden.sh",
            "scoring": {
                "weights": {
                    "constraint_pass": 0.8,
                    "execution_pass": 0.1,
                    "explanation": 0.1,
                },
                "evaluator": "dc_constraint_debug.DCConstraintDebugEvaluator",
                "explanation_weight": 0.1,
            },
            "sanitizer": {"enabled": True},
            "generator": {
                "script": "p6_dc_constraint_hard_gen.py",
                "seed": self.seed,
                "rtl_template": rtl["name"],
                "period_ns": period_ns,
                "task_index": task_index,
                "injected_bugs": injected,
                "num_properties": total,
                "num_bugs": k,
            },
            "constraint_spec": spec,
            "grading_mode": "semantic_continuous",
            "expected_error_category": "semantic_silent",
            "version": "1.0.0",
        }
        (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
        return task_dir
