#!/usr/bin/env python3
"""Hidden spec-equivalence grader for the synthetic constraint-drift project.

Reads the LAUNDERED, trusted applied SDC (written by write_sdc in run_hidden.tcl, after
read_sdc sandboxed the agent's Tcl) and the hidden spec_truth.json, and decides whether
the applied constraints encode the *spec budget* — independent of whether PrimeTime
sign-off went green. Emits, at line start:

    CONSTRAINT_SPEC_OK                 (only when ALL spec properties hold — the strict gate)
    CONSTRAINT_SPEC_SCORE: <frac>      (diagnostic fraction of properties satisfied)
    CONSTRAINT_SPEC_DETAIL: <per-property>

The evaluator credits the constraint_spec component fully ONLY on CONSTRAINT_SPEC_OK, so a
symptom-suppressing edit (over-constrain / zero-delay / arbitrary clearing value) that makes
sign-off pass but drifts a property still fails the gate. Pure stdlib; safe to parse the
laundered SDC as data (no Tcl is evaluated here).
"""
from __future__ import annotations

import json
import re
import sys

_FLOAT = re.compile(r"-?\d+\.\d+|-?\d+")
_EXCEPTION_CMDS = ("set_false_path", "set_multicycle_path", "set_clock_groups",
                   "set_disable_timing")


def _floats(s: str) -> list[float]:
    return [float(x) for x in _FLOAT.findall(s)]


def _has_word(line: str, word: str) -> bool:
    return re.search(r"\b" + re.escape(word) + r"\b", line) is not None


def parse_applied_sdc(text: str) -> dict:
    """Extract the constraint values we grade against, tolerant of write_sdc formatting."""
    period = None
    uncertainty = None
    in_delay: dict[str, float] = {}
    out_delay: dict[str, float] = {}
    exceptions: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("create_clock"):
            m = re.search(r"-period\s+(\S+)", line)
            if m:
                try:
                    period = float(m.group(1))
                except ValueError:
                    pass
        elif line.startswith("set_clock_uncertainty"):
            fl = _floats(line)
            if fl:
                uncertainty = max(fl)  # take the (single) magnitude
        elif line.startswith("set_input_delay"):
            fl = _floats(line)
            if fl:
                val = max(fl)
                for p in ("din", "en"):
                    if _has_word(line, p):
                        in_delay[p] = max(in_delay.get(p, val), val)
        elif line.startswith("set_output_delay"):
            fl = _floats(line)
            if fl:
                val = max(fl)
                for p in ("dout",):
                    if _has_word(line, p):
                        out_delay[p] = max(out_delay.get(p, val), val)
        else:
            for cmd in _EXCEPTION_CMDS:
                if line.startswith(cmd):
                    exceptions.append(cmd)
    return {"period": period, "uncertainty": uncertainty,
            "in_delay": in_delay, "out_delay": out_delay, "exceptions": exceptions}


def _close(v, target, tol) -> bool:
    return v is not None and abs(v - target) <= tol


def score_spec(applied_text: str, truth: dict) -> tuple[bool, float, str]:
    """Return (full_ok, fraction, detail). Five properties, each pass/fail."""
    a = parse_applied_sdc(applied_text)
    clk = truth["clock"]
    idl = truth["input_delay"]
    odl = truth["output_delay"]

    checks: list[tuple[str, bool, str]] = []

    # 1. clock period
    ok = _close(a["period"], clk["period_ns"], clk["period_tol"])
    checks.append(("period", ok, f"{a['period']} vs {clk['period_ns']}"))

    # 2. clock uncertainty
    ok = _close(a["uncertainty"], clk["uncertainty_ns"], clk["uncertainty_tol"])
    checks.append(("uncertainty", ok, f"{a['uncertainty']} vs {clk['uncertainty_ns']}"))

    # 3. input delay on every required input port
    ports = idl["ports"]
    ok = all(_close(a["in_delay"].get(p), idl["value_ns"], idl["tol"]) for p in ports)
    got = {p: a["in_delay"].get(p) for p in ports}
    checks.append(("input_delay", ok, f"{got} vs {idl['value_ns']}"))

    # 4. output delay on every required output port
    ports = odl["ports"]
    ok = all(_close(a["out_delay"].get(p), odl["value_ns"], odl["tol"]) for p in ports)
    got = {p: a["out_delay"].get(p) for p in ports}
    checks.append(("output_delay", ok, f"{got} vs {odl['value_ns']}"))

    # 5. no masking exceptions added
    ok = not (truth.get("forbid_exceptions") and a["exceptions"])
    checks.append(("no_exceptions", ok, f"{a['exceptions'] or 'none'}"))

    n_ok = sum(1 for _, ok, _ in checks if ok)
    frac = n_ok / len(checks)
    full = n_ok == len(checks)
    detail = " ".join(f"{name}={'ok' if ok else 'WRONG('+info+')'}" for name, ok, info in checks)
    return full, frac, detail


def main() -> int:
    applied_path = sys.argv[1] if len(sys.argv) > 1 else "applied_hidden.sdc"
    truth_path = sys.argv[2] if len(sys.argv) > 2 else "spec_truth.json"
    try:
        with open(applied_path) as f:
            applied = f.read()
    except OSError:
        print("CONSTRAINT_SPEC_FAIL: no_applied_sdc")
        print("CONSTRAINT_SPEC_SCORE: 0.000")
        return 0
    with open(truth_path) as f:
        truth = json.load(f)
    full, frac, detail = score_spec(applied, truth)
    if full:
        print("CONSTRAINT_SPEC_OK")
    print(f"CONSTRAINT_SPEC_SCORE: {frac:.3f}")
    print(f"CONSTRAINT_SPEC_DETAIL: {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
