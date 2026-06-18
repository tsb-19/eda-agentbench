"""P4 SPICE — HARD variant: second-order step-response DAMPING DESIGN (residual track).

WHY THIS EXISTS
---------------
The base P4 track is a single-knob, single-window fix: "change R so one delay lands
in [min,max]". Under the agentic loop a model just runs the deck, reads the one
measurement, nudges the one knob, and re-runs — 4/5 frontier models sweep it. The
difficulty is "bisect one number", not analog engineering.

This variant makes the difficulty IRREDUCIBLE analog reasoning. A series RLC driven
by a voltage step (output across C) must satisfy THREE COUPLED, COMPETING specs at
once:
  * propagation delay  t_pd      <= Td      (fast enough)
  * overshoot          OS%       <= OSmax   (not ringing)
  * settling time      t_settle  <= Ts      (settles quickly, +/-2% band)
These trade off against each other through the damping ratio zeta = (R/2)*sqrt(C/L):
low R is underdamped (fast rise but large overshoot + long ringing settle), high R is
overdamped (clean but slow). The feasible region is a band near critical damping
(zeta ~ 0.7, the classic maximally-flat / best-compromise point). There is no single
monotonic knob direction that helps every spec, so naive single-metric bisection
fails: pushing R to kill overshoot blows the delay budget. The model must reason
about the second-order tradeoff — exactly what an analog / signal-integrity engineer
does for interconnect termination and filter damping. Real engineering, not a gimmick.

GRADING (continuous, tool-grounded, forge-resistant)
----------------------------------------------------
The HIDDEN run re-simulates the model's deck, dumps the transient waveform to a plain
3-column ``wave.csv`` (t, v_in, v_out), and ``measure_specs.py`` computes the three
specs from the waveform in pure Python (robust to ringing — no fragile .measure) and
scores each with a graded closeness ramp (1.0 within budget, linearly to 0 at 2x the
budget). SPEC_SCORE = mean of the three. Partial designs (meet 1-2 of 3, or land close)
earn partial credit -> continuous discrimination. The PUBLIC run reports the three
measured values but NOT the pass/fail verdict against spec, so the agent sees realistic
diagnostic output and must judge correctness itself (the section-3 protocol).

GROUNDING (avoids the analytic-window root cause)
-------------------------------------------------
The acceptance thresholds are NOT analytic. The generator emits a golden deck at the
target damping; ``scripts/calibrate_p4_damping.py`` runs that golden through REAL
HSPICE/Spectre, measures the three real quantities, and writes thresholds with margin
around the real golden values. A task is only finalized once its golden really meets
its own (real-sim-derived) specs.
"""

from __future__ import annotations

from __future__ import annotations

import json
import math
from pathlib import Path

from generators.base import BaseGenerator

# ---------------------------------------------------------------------------
# Spec-scoring script (written into each task's dir; runs standalone on b04).
# Pure Python (no numpy) — b04 python may be bare. Reads wave.csv + spec.json.
# This is the load-bearing measurement; it is unit-tested in tests/test_p4_damping.py
# by running THIS exact source against analytic RLC step responses.
# ---------------------------------------------------------------------------
MEASURE_PY = r'''#!/usr/bin/env python3
"""Compute second-order step-response specs (t_pd, overshoot, settling) from a
plain waveform and score them against a spec. Robust to ringing (waveform-based,
not .measure-based).

Usage: measure_specs.py <wave.csv> <spec.json> [--mode public|hidden]

wave.csv: lines "t v_in v_out" (whitespace-separated; '#' comments ok).
spec.json: {"v_final": <float|null>, "t_edge": <float|null>,
            "specs": {"t_pd":{"max":..,"ramp":1.0},
                      "overshoot":{"max":..,"ramp":1.0},
                      "t_settle":{"max":..,"ramp":1.0}}}

Prints (public mode prints measured values only; hidden prints the score too):
  SPEC_MEASURED: t_pd=<s> overshoot=<pct> t_settle=<s> v_final=<V>
  SPEC_SCORE: <fraction 0..1>            (hidden mode)
  SPEC_DETAIL: t_pd=<g> overshoot=<g> t_settle=<g>   (per-spec graded 0..1)
"""
import json, sys

def _read_wave(path):
    t, vin, vout = [], [], []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            p = line.split()
            if len(p) < 3:
                continue
            try:
                t.append(float(p[0])); vin.append(float(p[1])); vout.append(float(p[2]))
            except ValueError:
                continue
    return t, vin, vout

def _cross_rising(t, v, level, t_start=None):
    """First time v crosses `level` going up (linear interp). None if never."""
    for i in range(1, len(v)):
        if t_start is not None and t[i] < t_start:
            continue
        if v[i-1] < level <= v[i]:
            if v[i] == v[i-1]:
                return t[i]
            frac = (level - v[i-1]) / (v[i] - v[i-1])
            return t[i-1] + frac * (t[i] - t[i-1])
    return None

def _graded(actual, cap, ramp):
    """1.0 if actual<=cap; linearly to 0 at actual = cap*(1+ramp); 0 beyond.
    `actual` None or inf -> 0.0 (spec not achievable / not measurable)."""
    if actual is None:
        return 0.0
    try:
        if actual != actual or actual in (float("inf"), float("-inf")):  # NaN/inf
            return 0.0
    except TypeError:
        return 0.0
    if actual <= cap:
        return 1.0
    if cap <= 0:
        return 0.0
    over = (actual - cap) / (cap * ramp)
    return max(0.0, min(1.0, 1.0 - over))

def measure(t, vin, vout, v_final, t_edge):
    """Return dict(t_pd, overshoot, t_settle, v_final). Times relative to t_edge."""
    n = len(vout)
    if n < 5:
        return {"t_pd": None, "overshoot": None, "t_settle": None, "v_final": v_final}
    # Final value: measure from the tail unless pinned.
    if v_final is None:
        tail = vout[int(0.9 * n):] or vout[-1:]
        v_final = sum(tail) / len(tail)
    half = 0.5 * v_final
    # Input edge: first rising 50% crossing of v_in unless pinned.
    if t_edge is None:
        t_edge = _cross_rising(t, vin, half)
    if t_edge is None:
        t_edge = t[0]
    # Propagation delay: output reaches 50% of final, measured from the edge.
    t_out50 = _cross_rising(t, vout, half, t_start=t_edge)
    t_pd = (t_out50 - t_edge) if t_out50 is not None else None
    # Overshoot: peak of v_out after the edge, vs final.
    peak = None
    for i in range(n):
        if t[i] >= t_edge:
            peak = vout[i] if peak is None else max(peak, vout[i])
    overshoot = max(0.0, (peak - v_final) / v_final * 100.0) if (peak is not None and v_final) else None
    # Settling (+/-2%): last time the output is OUTSIDE the band, measured from edge.
    band = 0.02 * abs(v_final)
    last_out = None
    for i in range(n):
        if t[i] < t_edge:
            continue
        if abs(vout[i] - v_final) > band:
            last_out = i
    if last_out is None:
        t_settle = t_pd if t_pd is not None else 0.0   # already settled at the edge
    elif last_out + 1 < n:
        t_settle = t[last_out + 1] - t_edge
    else:
        t_settle = float("inf")                        # never settles within the window
    return {"t_pd": t_pd, "overshoot": overshoot, "t_settle": t_settle, "v_final": v_final}

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mode = "hidden"
    if "--mode" in sys.argv:
        mode = sys.argv[sys.argv.index("--mode") + 1]
    wave_path, spec_path = args[0], args[1]
    spec = json.load(open(spec_path))
    try:
        t, vin, vout = _read_wave(wave_path)
    except OSError:
        print("SPEC_MEASURED: no_waveform")
        if mode == "hidden":
            print("SPEC_SCORE: 0.0000")
            print("SPEC_DETAIL: no_waveform")
        return
    m = measure(t, vin, vout, spec.get("v_final"), spec.get("t_edge"))
    # Persist measured values so the output_generated check (and any downstream
    # tooling) sees a metrics.json, and the agent can inspect numbers it computed.
    try:
        json.dump({k: m[k] for k in ("t_pd", "overshoot", "t_settle", "v_final")
                   if m[k] is not None}, open("metrics.json", "w"), indent=2)
    except OSError:
        pass
    def fmt(x):
        return "None" if x is None else ("%.6g" % x)
    print("SPEC_MEASURED: t_pd=%s overshoot=%s t_settle=%s v_final=%s" % (
        fmt(m["t_pd"]), fmt(m["overshoot"]), fmt(m["t_settle"]), fmt(m["v_final"])))
    if mode != "hidden":
        return
    specs = spec["specs"]
    graded = {}
    uncalibrated = False
    # All three specs presuppose a working step response. If the output never even
    # reaches 50% of final (t_pd unmeasurable — e.g. the model broke the deck or
    # killed the response), every spec scores 0; otherwise a dead/flat output would
    # earn full "0% overshoot" credit, which is nonsense.
    functional = m["t_pd"] is not None
    for name in ("t_pd", "overshoot", "t_settle"):
        cfg = specs.get(name)
        if not cfg:
            continue
        cap = cfg.get("max")
        if cap is None:                      # not yet calibrated from a real golden sim
            uncalibrated = True
            graded[name] = 0.0
            continue
        graded[name] = (_graded(m[name], float(cap), float(cfg.get("ramp", 1.0)))
                        if functional else 0.0)
    score = sum(graded.values()) / len(graded) if graded else 0.0
    print("SPEC_SCORE: %.4f" % score)
    detail = " ".join("%s=%.3f" % (k, v) for k, v in graded.items())
    if uncalibrated:
        detail += " UNCALIBRATED"
    print("SPEC_DETAIL: " + detail)

if __name__ == "__main__":
    main()
'''


# ---------------------------------------------------------------------------
# Run-script templates (GENERIC — identical for every task; all task-specific
# data lives in circuit.scs / spec.json, never in the scripts). Run with
# cwd = evaluator workspace (all files are siblings there).
# ---------------------------------------------------------------------------
_PUBLIC_SH = r'''#!/bin/bash
# P4 damping design - PUBLIC runner: simulate, then REPORT the measured
# delay / overshoot / settling. It does NOT tell you pass/fail vs the spec --
# compare the numbers to the spec in the prompt and size R1 yourself.
set -e
spectre circuit.scs +escchars +log spectre_public.out -format nutascii 2>&1 | tee spectre_public.log

python3 - <<'PY'
import os
raw = "circuit.raw"
def dump_empty():
    open("wave.csv", "w").close()
if not os.path.isfile(raw):
    dump_empty(); raise SystemExit
content = open(raw).read()
sec = content.split("Values:")
if len(sec) < 2:
    dump_empty(); raise SystemExit
rows = {}
for line in sec[1].strip().split(chr(10)):
    p = line.split()
    if len(p) >= 4:
        try:
            rows[int(p[0])] = [float(x) for x in p[1:]]
        except ValueError:
            pass
with open("wave.csv", "w") as f:
    f.write("# t v_in v_out" + chr(10))
    for i in sorted(rows):
        r = rows[i]
        f.write("%.9e %.9e %.9e%s" % (r[0], r[1], r[2], chr(10)))
PY

python3 measure_specs.py wave.csv spec_public.json --mode public
'''

_HIDDEN_SH = r'''#!/bin/bash
# P4 damping design - HIDDEN runner: enforce the locked L1/C1 (only R1 may be
# tuned), then score the simulated waveform against the spec (continuous).
set -e

VIOL=$(python3 - <<'PY'
import json, re
try:
    spec = json.load(open("spec.json"))
except Exception:
    print(""); raise SystemExit
lock = spec.get("lock", {})
try:
    txt = open("circuit.scs").read()
except OSError:
    print("deck_missing"); raise SystemExit
def getval(inst, key):
    for line in txt.splitlines():
        s = line.strip().lower()
        if s.startswith(inst + " ") or s.startswith(inst + "("):
            m = re.search(r"\b" + key + r"\s*=\s*([0-9.eE+\-]+)", s)
            if m:
                try:
                    return float(m.group(1))
                except ValueError:
                    return None
    return None
viol = ""
for inst, key in (("l1", "l"), ("c1", "c")):
    want = lock.get(key)
    if want is None:
        continue
    got = getval(inst, key)
    tol = lock.get("tol", 0.02)
    if got is None or abs(got - want) > tol * abs(want):
        viol = "%s_%s(%s->%s)" % (inst, key, want, got)
        break
print(viol)
PY
)

if [ -n "$VIOL" ]; then
    echo "SPEC_SCORE: 0.0000"
    echo "SPEC_DETAIL: modified_locked_component:$VIOL"
    exit 0
fi

python3 measure_specs.py wave.csv spec.json --mode hidden
'''

_PROMPT = """\
# Task: Damping Design for a Series RLC Step Response

## Problem

The series RLC network in `circuit.scs` is driven by a fast voltage step on `in`
(0 -> 1.8 V). The output is taken across the capacitor (`out`). With the current
resistor value the response is **under-damped**: it rises quickly but RINGS — large
overshoot and a long settling tail.

Re-size the damping resistor `R1` so the step response on `out` meets ALL THREE of
these specs at the same time:

- Propagation delay (in -> out, 50% = 0.9 V crossing): at most __TD__
- Overshoot above the 1.8 V final value: at most __OSMAX__
- Settling time into a +/-2% band (1.764 .. 1.836 V): at most __TS__

These specs trade off through the damping ratio: too little resistance rings (fails
overshoot and settling); too much resistance is sluggish (fails the delay). There is
a window of R near critical damping that satisfies all three — find it.

## Your Task

1. Inspect `circuit.scs` and run `bash run_public.sh`. It reports the measured
   delay, overshoot, and settling time (it does NOT report pass/fail) — judge those
   numbers against the specs above yourself.
2. Change ONLY the value of `R1`. Keep `L1`, `C1`, the topology, and the input fixed.
3. Iterate until all three specs are met.

## Constraints

- You may only edit `circuit.scs`, and within it only the value of `R1`.
- Do not change `L1`, `C1`, the topology, or the input source (changing `L1`/`C1`
  is detected and scores zero).
- Do not modify `run_public.sh`, `measure_specs.py`, or any other file.

## Files

- `circuit.scs` — Spectre netlist (editable: R1 value only)
- `run_public.sh` — simulate + report measured delay/overshoot/settling (read-only)
- `measure_specs.py` — how those values are measured (read-only)
"""


def _spectre_step_netlist(r: float, l: float, c: float, delay: float, rise: float,
                          width: float, period: float, stop: float, maxstep: float,
                          vdd: float = 1.8) -> str:
    return f"""\
// RLC damping design - Spectre netlist (output across C)
simulator lang=spectre
global 0

// Fast voltage step on `in` (edge << circuit natural period -> ideal step)
vin (in 0) vsource type=pulse val0=0 val1={vdd} delay={delay:.6g} rise={rise:.6g} fall={rise:.6g} width={width:.6g} period={period:.6g}

// Series RLC. R1 is the damping resistor to size; L1 and C1 are FIXED.
l1 (in mid) inductor l={l:.6g}
r1 (mid out) resistor r={r:.6g}
c1 (out 0) capacitor c={c:.6g}

// Transient: maxstep resolves the ring, stop captures the settling tail
tran tran stop={stop:.6g} errpreset=conservative maxstep={maxstep:.6g}

save in out
"""


class P4DampingGenerator(BaseGenerator):
    """Generates P4 SPICE damping-design (hard) tasks (Spectre, deterministic).

    Each task emits a buggy (under-damped) deck + a golden (near-critical) deck +
    generic run scripts + the measure_specs.py scorer. The acceptance thresholds
    are left NULL: scripts/calibrate_p4_damping.py runs the golden through real
    Spectre, measures the real delay/overshoot/settling, and writes the caps (with
    margin) into spec.json + the prompt. An uncalibrated task scores 0 by design
    (no analytic windows -- the P4 settling-bug lesson).
    """

    # Reuse the base generator's component value pools for timescale variety.
    _L_CHOICES = [1e-6, 2.2e-6, 4.7e-6, 1e-5, 2.2e-5, 4.7e-5, 1e-4, 2.2e-4]
    _C_CHOICES = [1e-12, 2.2e-12, 4.7e-12, 1e-11, 2.2e-11, 4.7e-11, 1e-10, 2.2e-10]

    def generate_one(self, task_index: int) -> Path:
        l = self.rng.choice(self._L_CHOICES)
        c = self.rng.choice(self._C_CHOICES)
        z0 = math.sqrt(l / c)
        w0 = 1.0 / math.sqrt(l * c)
        t0 = 2.0 * math.pi / w0

        zeta_golden = round(self.rng.uniform(0.62, 0.78), 4)   # near-critical: clean + fast
        zeta_buggy = round(self.rng.uniform(0.15, 0.30), 4)    # under-damped: rings
        r_golden = 2.0 * zeta_golden * z0
        r_buggy = 2.0 * zeta_buggy * z0

        # Sim window: long enough for the worst (buggy) ring-down to settle (~4/(zeta*w0)),
        # with margin; fine enough to resolve the ringing period. (Analytics used ONLY to
        # size the simulation, never for the acceptance thresholds.)
        stop = max(40.0 * t0, 10.0 * 4.0 / (zeta_buggy * w0))
        maxstep = t0 / 200.0
        delay = 0.5 * t0
        rise = t0 / 500.0
        width = stop * 2.0
        period = stop * 4.0

        task_id = f"task_{9000 + task_index:06d}"
        task_dir = self.output_dir / f"spectre_rlc_damping_{task_index:06d}"
        (task_dir / "files").mkdir(parents=True, exist_ok=True)
        (task_dir / "hidden").mkdir(exist_ok=True)
        (task_dir / "solution").mkdir(exist_ok=True)

        # Decks: buggy (under-damped) is the start; golden (near-critical) is the answer.
        (task_dir / "files" / "circuit.scs").write_text(
            _spectre_step_netlist(r_buggy, l, c, delay, rise, width, period, stop, maxstep))
        (task_dir / "solution" / "circuit.scs").write_text(
            _spectre_step_netlist(r_golden, l, c, delay, rise, width, period, stop, maxstep))

        # Generic scripts + scorer.
        (task_dir / "files" / "run_public.sh").write_text(_PUBLIC_SH)
        (task_dir / "files" / "measure_specs.py").write_text(MEASURE_PY)
        (task_dir / "hidden" / "run_hidden.sh").write_text(_HIDDEN_SH)
        (task_dir / "files" / "run_public.sh").chmod(0o755)
        (task_dir / "hidden" / "run_hidden.sh").chmod(0o755)
        (task_dir / "files" / "measure_specs.py").chmod(0o755)

        # Public spec: just enough for measure_specs to report values (no caps).
        (task_dir / "files" / "spec_public.json").write_text(json.dumps(
            {"v_final": 1.8, "t_edge": None, "specs": {}}, indent=2) + "\n")

        # Hidden spec: caps NULL until calibrated; lock L/C so only R may move.
        hidden_spec = {
            "v_final": 1.8,
            "t_edge": None,
            "specs": {
                "t_pd": {"max": None, "ramp": 1.0},
                "overshoot": {"max": None, "ramp": 1.0},
                "t_settle": {"max": None, "ramp": 1.0},
            },
            "lock": {"l": l, "c": c, "tol": 0.02},
            "design": {
                "zeta_golden": zeta_golden, "zeta_buggy": zeta_buggy,
                "r_golden": r_golden, "r_buggy": r_buggy,
                "l": l, "c": c, "z0": z0, "w0": w0, "t0": t0,
                "stop": stop, "maxstep": maxstep,
            },
        }
        (task_dir / "hidden" / "spec.json").write_text(json.dumps(hidden_spec, indent=2) + "\n")

        # Prompt with placeholders the calibrator fills from the real golden sim.
        (task_dir / "prompt.md").write_text(_PROMPT)

        meta = {
            "task_id": task_id,
            "track": "p4_spice_sim",
            "tool": ["spectre"],
            "difficulty": "hard",
            "data_type": "flow_synthetic",
            "resource_preset": "standard",
            "timeout_sec": 300,
            "max_tool_calls": 30,
            "max_patch_attempts": 8,
            "max_output_tokens": 32000,
            "files": {
                "visible": ["circuit.scs", "run_public.sh", "measure_specs.py", "spec_public.json"],
                "editable": ["circuit.scs"],
                "hidden": ["run_hidden.sh", "spec.json"],
                "forbidden": ["run_public.sh", "run_hidden.sh", "measure_specs.py",
                              "spec_public.json", "spec.json"],
            },
            "run_command": "bash run_public.sh",
            "scoring": {
                "weights": {
                    "tool_run": 0.2,
                    "output_generated": 0.1,
                    "spec_score": 0.6,
                    "explanation": 0.1,
                },
                "evaluator": "spice_sim.SPICESimEvaluator",
                "explanation_weight": 0.1,
            },
            "sanitizer": {"enabled": True},
            "generator": {
                "script": "p4_damping_gen.py",
                "seed": self.seed,
                "task_index": task_index,
                "circuit_type": "rlc_damping",
                "zeta_golden": zeta_golden,
                "zeta_buggy": zeta_buggy,
                "r_golden": r_golden,
                "r_buggy": r_buggy,
                "l": l,
                "c": c,
            },
            "grading_mode": "spec_continuous",
            "calibrated": False,
            "version": "1.0.0",
        }
        (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
        return task_dir
