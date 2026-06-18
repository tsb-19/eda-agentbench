# Task: Damping Design for a Series RLC Step Response

## Problem

The series RLC network in `circuit.scs` is driven by a fast voltage step on `in`
(0 -> 1.8 V). The output is taken across the capacitor (`out`). With the current
resistor value the response is **under-damped**: it rises quickly but RINGS — large
overshoot and a long settling tail.

Re-size the damping resistor `R1` so the step response on `out` meets ALL THREE of
these specs at the same time:

- Propagation delay (in -> out, 50% = 0.9 V crossing): at most 13.2 ns
- Overshoot above the 1.8 V final value: at most 3.26 %
- Settling time into a +/-2% band (1.764 .. 1.836 V): at most 48.3 ns

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
