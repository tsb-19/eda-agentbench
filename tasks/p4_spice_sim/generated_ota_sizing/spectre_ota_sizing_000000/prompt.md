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

- DC gain: at least 79.9 dB
- Gain-bandwidth (unity-gain frequency): at least 191 MHz
- Phase margin (at the unity-gain frequency): at least 54.6 deg

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
