"""P4 SPICE — HARD variant #2: op-amp SIZING for a multi-objective AC tradeoff.

WHY THIS EXISTS (generalizing the residual recipe — see docs/phases/benchmark_hardening_plan.md §9)
-------------------------------------------------------------------------------------------
P4 damping (p4_damping_gen.py) proved the recipe: make the agent tune a knob to satisfy
COUPLED, COMPETING specs scored by continuous closeness, calibrated on real sims. This
track applies the SAME recipe to the canonical ANALOG design problem — sizing a two-stage
Miller-compensated OTA — where three specs genuinely compete:

  * DC gain        A0   >= gain_min   (loop accuracy)
  * gain-bandwidth GBW  >= gbw_min    (speed)
  * phase margin   PM   >= pm_min     (stability; ~60 deg is the textbook target)

They trade through the device sizes / bias / Miller cap: GBW ~ gm1/Cc, the non-dominant
pole ~ gm2/CL, PM falls as GBW approaches that pole, and the Miller RHP zero (~gm2/Cc)
eats more phase as Cc shrinks. So pushing GBW up (more gm1, smaller Cc) costs phase
margin; buying phase margin back (bigger Cc) costs GBW. There is no single monotonic knob
that helps all three — the model must reason about the pole/zero tradeoff, exactly what an
analog designer does. Real engineering, not a gimmick; the §9.1 contract holds.

GRADING (continuous, tool-grounded) — identical philosophy to p4_damping:
the HIDDEN run does an AC analysis, dumps |H|(dB) and phase(deg) vs frequency to a plain
ac.csv, and measure_ac.py computes A0/GBW/PM in pure Python and scores each with a graded
closeness ramp (1.0 if the spec is met, ramping to 0 as it is missed). SPEC_SCORE = mean.
The PUBLIC run reports the measured A0/GBW/PM but NOT pass/fail vs spec, so the agent sees
realistic diagnostic output and must judge sizing itself (the §3 protocol).

GROUNDING: caps are NOT analytic — scripts/calibrate_p4_amp.py runs the golden sizing
through real Spectre, measures the real A0/GBW/PM, and writes mins with margin. Until
calibrated a task scores 0 (the settling-bug lesson, baked in).

STATUS: measurement core + analytic self-test (tests/test_p4_amp_sizing.py) first; the
netlist generator + calibration are built once the measurement is proven offline.
"""

from __future__ import annotations

import json
from pathlib import Path

from generators.base import BaseGenerator

# ---------------------------------------------------------------------------
# AC spec-scoring script (written into each task dir; standalone on b04).
# Pure Python (no numpy). Reads ac.csv (freq gain_db phase_deg) + spec.json.
# Load-bearing measurement — unit-tested in tests/test_p4_amp_sizing.py against
# an ANALYTIC two-stage-OTA transfer function (two poles + a Miller RHP zero).
# ---------------------------------------------------------------------------
MEASURE_AC_PY = r'''#!/usr/bin/env python3
"""Compute op-amp AC specs (DC gain, gain-bandwidth, phase margin) from a Bode
sweep and score them against a spec. Pure Python, robust to a coarse sweep.

Usage: measure_ac.py <ac.csv> <spec.json> [--mode public|hidden]

ac.csv: lines "freq_hz gain_db phase_deg" (whitespace; '#' comments ok), ascending freq.
spec.json: {"specs": {"gain_db":{"min":..,"ramp":..},
                      "gbw_hz" :{"min":..,"ramp":..},
                      "pm_deg" :{"min":..,"ramp":..}}}

Prints:
  SPEC_MEASURED: gain_db=<dB> gbw_hz=<Hz> pm_deg=<deg>
  SPEC_SCORE: <fraction 0..1>                          (hidden mode)
  SPEC_DETAIL: gain_db=<g> gbw_hz=<g> pm_deg=<g>        (per-spec graded 0..1)
"""
import json, sys

def _read_ac(path):
    f_, g_, p_ = [], [], []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            q = line.split()
            if len(q) < 3:
                continue
            try:
                f_.append(float(q[0])); g_.append(float(q[1])); p_.append(float(q[2]))
            except ValueError:
                continue
    # ensure ascending in frequency
    if len(f_) >= 2 and f_[0] > f_[-1]:
        f_, g_, p_ = f_[::-1], g_[::-1], p_[::-1]
    return f_, g_, p_

def _interp(x, x0, x1, y0, y1):
    if x1 == x0:
        return y0
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)

def measure(freq, gdb, pdeg):
    """DC gain (dB), unity-gain freq GBW (Hz), phase margin (deg)."""
    n = len(freq)
    if n < 3:
        return {"gain_db": None, "gbw_hz": None, "pm_deg": None}
    # DC gain: mean of the lowest-decade samples (flat region).
    lo = [gdb[i] for i in range(n) if freq[i] <= freq[0] * 10.0] or [gdb[0]]
    gain_db = sum(lo) / len(lo)
    # GBW: first downward crossing of 0 dB (unity gain). Interpolate in log10(f).
    import math
    gbw = None
    for i in range(1, n):
        if gdb[i-1] >= 0.0 > gdb[i]:
            lf = _interp(0.0, gdb[i-1], gdb[i], math.log10(freq[i-1]), math.log10(freq[i]))
            gbw = 10.0 ** lf
            break
    # Phase margin: phase at GBW + 180. Interpolate phase in log10(f).
    pm = None
    if gbw is not None:
        for i in range(1, n):
            if freq[i-1] <= gbw <= freq[i]:
                ph = _interp(math.log10(gbw), math.log10(freq[i-1]), math.log10(freq[i]),
                             pdeg[i-1], pdeg[i])
                pm = 180.0 + ph
                break
    return {"gain_db": gain_db, "gbw_hz": gbw, "pm_deg": pm}

def _graded(actual, target, ramp, kind):
    """kind 'min': want actual>=target (1.0 at/above, ->0 at target*(1-ramp)).
       kind 'max': want actual<=target (1.0 at/below, ->0 at target*(1+ramp)).
       actual None/NaN/inf -> 0.0; target<=0 guarded."""
    if actual is None:
        return 0.0
    try:
        if actual != actual or actual in (float("inf"), float("-inf")):
            return 0.0
    except TypeError:
        return 0.0
    if ramp <= 0:
        ramp = 1.0
    if kind == "min":
        if actual >= target:
            return 1.0
        floor = target * (1.0 - ramp)
        if target <= floor:
            return 0.0
        return max(0.0, min(1.0, (actual - floor) / (target - floor)))
    else:  # max
        if actual <= target:
            return 1.0
        if target <= 0:
            return 0.0
        over = (actual - target) / (target * ramp)
        return max(0.0, min(1.0, 1.0 - over))

# which way each spec is "good": gain/gbw/pm are floors (>=), anything else a ceiling.
_KIND = {"gain_db": "min", "gbw_hz": "min", "pm_deg": "min"}

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mode = "hidden"
    if "--mode" in sys.argv:
        mode = sys.argv[sys.argv.index("--mode") + 1]
    ac_path, spec_path = args[0], args[1]
    spec = json.load(open(spec_path))
    try:
        freq, gdb, pdeg = _read_ac(ac_path)
    except OSError:
        print("SPEC_MEASURED: no_ac")
        if mode == "hidden":
            print("SPEC_SCORE: 0.0000")
            print("SPEC_DETAIL: no_ac")
        return
    m = measure(freq, gdb, pdeg)
    try:
        json.dump({k: m[k] for k in ("gain_db", "gbw_hz", "pm_deg") if m[k] is not None},
                  open("metrics.json", "w"), indent=2)
    except OSError:
        pass
    def fmt(x):
        return "None" if x is None else ("%.6g" % x)
    print("SPEC_MEASURED: gain_db=%s gbw_hz=%s pm_deg=%s" % (
        fmt(m["gain_db"]), fmt(m["gbw_hz"]), fmt(m["pm_deg"])))
    if mode != "hidden":
        return
    specs = spec["specs"]
    graded = {}
    uncalibrated = False
    # A valid amplifier must close the loop: if it never crosses unity gain (GBW
    # unmeasurable) it is not a working amp, so every spec scores 0 (a flat/dead
    # response must not earn credit for "infinite phase margin").
    functional = m["gbw_hz"] is not None and m["gain_db"] is not None and m["gain_db"] > 0.0
    for name in ("gain_db", "gbw_hz", "pm_deg"):
        cfg = specs.get(name)
        if not cfg:
            continue
        target = cfg.get("min", cfg.get("max"))
        if target is None:                      # not yet calibrated from a real golden sim
            uncalibrated = True
            graded[name] = 0.0
            continue
        graded[name] = (_graded(m[name], float(target), float(cfg.get("ramp", 1.0)),
                                _KIND.get(name, "min")) if functional else 0.0)
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
# data lives in circuit.scs / spec.json, never in the scripts). cwd = workspace.
#
# NOTE (b04-PENDING): the AC raw->csv extraction below parses Spectre nutascii
# COMPLEX output. The measurement core (measure_ac.py) is already unit-tested
# offline against an analytic OTA; this raw parser is the one piece that must be
# confirmed against real `spectre -format nutascii` AC output on b04 (the exact
# complex token layout — "re,im" vs "re<tab>im" — is version-dependent; the
# parser flattens all floats per point to be robust to either).
# ---------------------------------------------------------------------------
_PUBLIC_SH = r'''#!/bin/bash
# P4 op-amp sizing - PUBLIC runner: run the AC analysis, then REPORT the measured
# DC gain / gain-bandwidth / phase margin. It does NOT tell you pass/fail vs the
# spec -- compare the numbers to the spec in the prompt and size ibias/cc yourself.
set -e
spectre circuit.scs +escchars +log spectre_public.out -format nutascii 2>&1 | tee spectre_public.log

python3 - <<'PY'
import math, os
raw = "circuit.raw"
def dump_empty():
    open("ac.csv", "w").close()
if not os.path.isfile(raw):
    dump_empty(); raise SystemExit
content = open(raw).read()
# Variable order: find the index of node 'out' among the saved variables.
out_idx = 1
vsec = content.split("Variables:")
if len(vsec) >= 2:
    head = vsec[1].split("Values:")[0]
    for line in head.strip().splitlines():
        p = line.replace("\t", " ").split()
        # lines look like: "<k> <name> <type>"
        if len(p) >= 2 and p[0].isdigit() and p[1].lower() in ("out", "v(out)", "out2"):
            out_idx = int(p[0]); break
sec = content.split("Values:")
if len(sec) < 2:
    dump_empty(); raise SystemExit
# Group the Values section into per-point blocks. A new point starts at a line
# whose first token is the integer point index; collect every float in the block.
points = []
cur = None
for line in sec[1].strip().splitlines():
    toks = line.replace(",", " ").replace("\t", " ").split()
    if not toks:
        continue
    if toks[0].isdigit() and cur is not None and len(cur) > 0:
        # heuristic: a bare leading integer that indexes a NEW point (block already has data)
        # only treat as a new block boundary if we already saw >= one full var
        pass
    # simpler: detect block start by a leading integer index token AND that we expect a new freq
    if toks[0].isdigit() and (cur is None or len(cur) >= 2 * (out_idx + 1)):
        if cur:
            points.append(cur)
        cur = []
        toks = toks[1:]
    if cur is None:
        cur = []
    for t in toks:
        try:
            cur.append(float(t))
        except ValueError:
            pass
if cur:
    points.append(cur)
with open("ac.csv", "w") as f:
    f.write("# freq_hz gain_db phase_deg\n")
    for fl in points:
        # var k complex = (fl[2k], fl[2k+1]); var0 = frequency (imag ~ 0)
        if len(fl) < 2 * (out_idx + 1):
            continue
        freq = fl[0]
        re, im = fl[2 * out_idx], fl[2 * out_idx + 1]
        mag = math.hypot(re, im)
        gdb = 20.0 * math.log10(mag) if mag > 0 else -300.0
        ph = math.degrees(math.atan2(im, re))
        f.write("%.9e %.9e %.9e\n" % (freq, gdb, ph))
PY

python3 measure_ac.py ac.csv spec_public.json --mode public
'''

_HIDDEN_SH = r'''#!/bin/bash
# P4 op-amp sizing - HIDDEN runner: enforce the locked devices/load (only ibias
# and cc may be tuned), then score the AC response against the spec (continuous).
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
def inst_param(inst, key):
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
# Locked: the load cap cl and the gm-defining device widths (w of m1, m6). These
# fix the "physics"; the design must be met through ibias and cc, not by resizing.
for inst, key in (("cl", "c"), ("m1", "w"), ("m6", "w")):
    want = lock.get(inst + "_" + key)
    if want is None:
        continue
    got = inst_param(inst, key)
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

python3 measure_ac.py ac.csv spec.json --mode hidden
'''

_PROMPT = """\
# Task: Size a Two-Stage Miller OTA for Gain / Bandwidth / Phase Margin

## Problem

`circuit.scs` is a two-stage Miller-compensated operational transconductance
amplifier (OTA): an NMOS differential pair with a PMOS current-mirror load, a
common-source second stage, and a Miller compensation capacitor `cc`. It is wired
in the standard open-loop AC test rig (an ideal feedback inductor sets the DC
operating point; the loop is open at AC), so `bash run_public.sh` runs an AC
analysis and reports the **DC gain**, **gain-bandwidth (GBW)**, and **phase
margin (PM)** of the open-loop response.

The amplifier is currently **under-compensated**: `cc` is too small, so it is fast
but has poor phase margin (it would ring / be unstable in feedback). Re-size the
two design knobs so the response meets ALL THREE specs at once:

- DC gain: at least __GAINMIN__
- Gain-bandwidth (unity-gain frequency): at least __GBWMIN__
- Phase margin (at the unity-gain frequency): at least __PMMIN__

These specs trade off against each other:
- raising the **tail bias current `ibias`** increases transconductance -> higher
  GBW, but lowers the DC gain (output resistance drops) and pushes GBW toward the
  non-dominant pole, eroding phase margin;
- raising the **Miller capacitor `cc`** buys phase margin (pole splitting) but
  lowers GBW, and moves the right-half-plane zero down (which also costs phase).

There is no single knob direction that helps all three — find the sizing that
balances them.

## Your Task

1. Inspect `circuit.scs` and run `bash run_public.sh`. It reports the measured DC
   gain, GBW, and phase margin (it does NOT report pass/fail) — judge those numbers
   against the specs above yourself.
2. Change ONLY the values of `ibias` and `cc` (the `parameters` line). Keep the
   device sizes, the load capacitor `cl`, the topology, and the test rig fixed.
3. Iterate until all three specs are met at once.

## Constraints

- You may only edit `circuit.scs`, and within it only the `ibias` and `cc` values.
- Do not change the device widths/lengths, the load `cl`, the topology, the models,
  or the test rig (changing the locked devices/load is detected and scores zero).
- Do not modify `run_public.sh`, `measure_ac.py`, or any other file.

## Files

- `circuit.scs` — Spectre netlist (editable: `ibias` and `cc` values only)
- `run_public.sh` — run the AC analysis + report measured gain/GBW/PM (read-only)
- `measure_ac.py` — how those values are measured (read-only)
"""


def _spectre_ota_netlist(ibias: float, cc: float, *, w1: float, w3: float,
                         w6: float, w7: float, lch: float, cl: float,
                         vb: float, vdd: float = 3.3, vcm: float = 1.2) -> str:
    """Two-stage Miller OTA in the open-loop AC test rig (self-contained mos1
    models). `ibias` (tail current) and `cc` (Miller cap) are the tunable knobs;
    everything else is fixed per task. Lfb/Cfb form the ideal DC-bias / AC-open
    rig so the operating point is well defined and the sim converges."""
    return f"""\
// Two-stage Miller OTA - sizing task (open-loop AC gain test rig)
simulator lang=spectre
global 0

// --- TUNABLE KNOBS (edit ONLY these two values) ---
parameters ibias={ibias:.6g} cc={cc:.6g}

// Supplies and bias
vdd   (vdd 0)   vsource dc={vdd:.6g}
itail (tail 0)  isource dc=ibias
vbias (vb 0)    vsource dc={vb:.6g}

// Open-loop AC rig: lfb shorts DC (sets bias point), cfb grounds inn at AC
vin (inp 0) vsource dc={vcm:.6g} mag=1
lfb (out inn) inductor l=1e9
cfb (inn 0)   capacitor c=1e9

// Stage 1: NMOS diff pair (m1/m2) + PMOS mirror load (m3/m4).
// inn (feedback node) drives m1 (mirror/diode side) and the AC input inp drives
// m2 (output side): with the CS stage inverting, this makes `out` INVERTING w.r.t.
// inn, so the open-loop rig's out->inn feedback is NEGATIVE (stable DC bias). The
// opposite assignment latches the bias (positive feedback -> zero measured gain).
m1 (n1   inn tail tail) nch w={w1:.6g} l={lch:.6g}
m2 (out1 inp tail tail) nch w={w1:.6g} l={lch:.6g}
m3 (n1   n1  vdd  vdd)  pch w={w3:.6g} l={lch:.6g}
m4 (out1 n1  vdd  vdd)  pch w={w3:.6g} l={lch:.6g}

// Stage 2: CS NMOS (m6) + PMOS current-source load (m7) + Miller cap + load cap
m6 (out out1 0   0)   nch w={w6:.6g} l={lch:.6g}
m7 (out vb   vdd vdd) pch w={w7:.6g} l={lch:.6g}
cc1 (out1 out) capacitor c=cc
cl  (out 0)    capacitor c={cl:.6g}

// Self-contained generic level-1 MOS models (no PDK dependency)
model nch mos1 type=n vto=0.7  kp=120u lambda=0.04 gamma=0.4 phi=0.7
model pch mos1 type=p vto=-0.8 kp=40u  lambda=0.06 gamma=0.5 phi=0.7

ac1 ac start=1 stop=1e10 dec=30
save out
"""


class P4AmpSizingGenerator(BaseGenerator):
    """Generates P4 op-amp-sizing (hard) tasks (Spectre AC, deterministic).

    Each task emits an under-compensated (buggy) deck + a golden (balanced) deck +
    generic run scripts + the measure_ac.py scorer. The acceptance MINIMUMS
    (gain/GBW/PM floors) are left NULL: scripts/calibrate_p4_amp.py runs the golden
    through real Spectre, measures the real gain/GBW/PM, and writes the floors (with
    margin) into spec.json + the prompt. An uncalibrated task scores 0 by design
    (no analytic windows -- the P4 settling-bug lesson, same as p4_damping).

    Two knobs (ibias, cc) create a genuine three-spec tradeoff (see module docstring
    and benchmark_hardening_plan.md §9). The buggy start is under-compensated (cc too
    small -> poor PM); the golden balances all three.
    """

    # Per-task variety: load cap (sets the speed regime) and second-stage bias.
    _CL_CHOICES = [0.5e-12, 1e-12, 2e-12, 5e-12]
    _LCH_CHOICES = [1e-6, 2e-6]

    def generate_one(self, task_index: int) -> Path:
        cl = self.rng.choice(self._CL_CHOICES)
        lch = self.rng.choice(self._LCH_CHOICES)
        # Fixed device geometry (the locked "physics"); modest per-task jitter.
        w1 = round(self.rng.choice([20e-6, 30e-6, 40e-6]), 12)
        w3 = round(w1 * 0.5, 12)
        w6 = round(self.rng.choice([60e-6, 80e-6, 100e-6]), 12)
        w7 = round(w6 * 1.0, 12)
        vb = round(self.rng.uniform(2.0, 2.3), 4)   # PMOS load gate bias (sets stage-2 I)

        ibias_golden = round(self.rng.uniform(20e-6, 40e-6), 12)
        # Golden Miller cap: a sane fraction of CL (pole-splitting target ~ PM 60 deg).
        cc_golden = round(self.rng.uniform(0.4, 0.8) * cl, 15)
        # Buggy start perturbs BOTH knobs so the task is genuinely 2-dimensional (not a
        # 1-knob cc fix that hands the agent the golden ibias for free): over-biased
        # (ibias too high -> pushes the unity-gain crossing past the non-dominant pole,
        # eroding PM and lowering gain) AND under-compensated (cc too small -> poor PM).
        # Recovering all three specs needs lowering ibias AND raising cc, which pull GBW
        # in opposite directions -- the real pole/zero tradeoff an analog designer makes.
        ibias_buggy = round(ibias_golden * self.rng.uniform(1.6, 2.2), 12)
        cc_buggy = round(cc_golden * self.rng.uniform(0.08, 0.18), 15)  # badly under-compensated

        task_id = f"task_{9100 + task_index:06d}"
        task_dir = self.output_dir / f"spectre_ota_sizing_{task_index:06d}"
        (task_dir / "files").mkdir(parents=True, exist_ok=True)
        (task_dir / "hidden").mkdir(exist_ok=True)
        (task_dir / "solution").mkdir(exist_ok=True)

        nl = dict(w1=w1, w3=w3, w6=w6, w7=w7, lch=lch, cl=cl, vb=vb)
        (task_dir / "files" / "circuit.scs").write_text(
            _spectre_ota_netlist(ibias_buggy, cc_buggy, **nl))
        (task_dir / "solution" / "circuit.scs").write_text(
            _spectre_ota_netlist(ibias_golden, cc_golden, **nl))

        (task_dir / "files" / "run_public.sh").write_text(_PUBLIC_SH)
        (task_dir / "files" / "measure_ac.py").write_text(MEASURE_AC_PY)
        (task_dir / "hidden" / "run_hidden.sh").write_text(_HIDDEN_SH)
        (task_dir / "files" / "run_public.sh").chmod(0o755)
        (task_dir / "hidden" / "run_hidden.sh").chmod(0o755)
        (task_dir / "files" / "measure_ac.py").chmod(0o755)

        (task_dir / "files" / "spec_public.json").write_text(json.dumps(
            {"specs": {}}, indent=2) + "\n")

        hidden_spec = {
            "specs": {
                "gain_db": {"min": None, "ramp": 0.5},
                "gbw_hz": {"min": None, "ramp": 0.5},
                "pm_deg": {"min": None, "ramp": 0.6},
            },
            "lock": {"cl_c": cl, "m1_w": w1, "m6_w": w6, "tol": 0.02},
            "design": {
                "ibias_golden": ibias_golden, "cc_golden": cc_golden,
                "ibias_buggy": ibias_buggy, "cc_buggy": cc_buggy,
                "w1": w1, "w3": w3, "w6": w6, "w7": w7, "lch": lch,
                "cl": cl, "vb": vb,
            },
        }
        (task_dir / "hidden" / "spec.json").write_text(json.dumps(hidden_spec, indent=2) + "\n")
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
                "visible": ["circuit.scs", "run_public.sh", "measure_ac.py", "spec_public.json"],
                "editable": ["circuit.scs"],
                "hidden": ["run_hidden.sh", "spec.json"],
                "forbidden": ["run_public.sh", "run_hidden.sh", "measure_ac.py",
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
                "script": "p4_amp_sizing_gen.py",
                "seed": self.seed,
                "task_index": task_index,
                "circuit_type": "ota_sizing",
                "ibias_golden": ibias_golden,
                "cc_golden": cc_golden,
                "ibias_buggy": ibias_buggy,
                "cc_buggy": cc_buggy,
                "cl": cl,
            },
            "grading_mode": "spec_continuous",
            "calibrated": False,
            "version": "1.0.0",
        }
        (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
        return task_dir
