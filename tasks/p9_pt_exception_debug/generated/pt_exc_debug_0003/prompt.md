# Timing Signoff Debug: `fir_tap`

You own static-timing signoff for the `fir_tap` block. The constraint file `constraints.sdc`
is failing signoff review.

## Design intent (from the micro-architecture spec)
- `fir_tap` runs on a single clock `clk` with period **0.6 ns**.
- The coefficient register `coef_reg` drives the tap multiplier `mult_reg`, which is clock-enabled to capture once every **two** cycles; this multiply is specified as a two-cycle transfer.
- Every other register transfer is ordinary single-cycle logic and **must meet timing** at `clk`.

## Symptom
`report_timing` reports a setup violation. Resolve it so the constraints reflect the design intent above.

## Rules
- Only `constraints.sdc` is editable; all other files are read-only.
- A clean `report_timing` is **necessary but not sufficient**: signoff also rejects
  *over-constraining*. Any path required to meet timing must stay analyzed — masking, cutting,
  or relaxing a real functional path will be rejected, and so will removing an exception that is
  genuinely required.
- Run `bash run_public.sh` for live `report_timing` / `report_exceptions` feedback. There is no
  answer key; reason about correctness the way an engineer does before signoff.

## Design ports
clk, coef_in, x_in, y_out, y_sum
