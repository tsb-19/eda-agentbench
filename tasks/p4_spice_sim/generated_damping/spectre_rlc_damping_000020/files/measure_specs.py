#!/usr/bin/env python3
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
