#!/usr/bin/env python3
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
