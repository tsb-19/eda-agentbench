# Timing Signoff Debug: `rf_front`

You own static-timing signoff for the `rf_front` block. The constraint file `constraints.sdc` is
failing signoff review.

## What you are given
- `design_netlist.v` — the synthesized gate-level datapath PrimeTime times (one clock `clk`,
  period **0.8 ns**).
- `design_rtl.v` — the behavioral RTL spec. Its capture-enable logic defines the cadence of each
  register transfer: some registers update on every clock, others only once every few clocks (or
  only at boot). **The timing intent is not stated in words — you must infer it from this RTL.**
- `constraints.sdc` — the constraints under review (the only editable file).

## Symptom
`report_timing` reports no setup violations. The constraints are nonetheless under suspicion: from `design_rtl.v`, determine which transfers are genuinely quasi-static (safe to exclude) and which are functional paths that must remain analyzed and meet timing.

## Your task
From `design_rtl.v`, determine which register transfers are genuinely multi-cycle or quasi-static
and which must meet timing every cycle, then correct `constraints.sdc` so every transfer is
constrained according to its real cadence — no broader, no narrower.

## Rules
- Only `constraints.sdc` is editable; all other files are read-only.
- A clean `report_timing` is **necessary but not sufficient**. Signoff rejects *over-constraining*
  (relaxing, cutting, or masking a path that must meet timing every cycle) and *under-constraining*
  (failing to relax a genuine multi-cycle path or exclude a genuine quasi-static one). Applying an
  exception too broadly is as wrong as omitting it.
- Run `bash run_public.sh` for live `report_timing` / `report_exceptions` feedback. There is no
  answer key; reason about correctness the way an engineer does before signoff.

## Design ports
clk, gain_in, band_out, samp_out
