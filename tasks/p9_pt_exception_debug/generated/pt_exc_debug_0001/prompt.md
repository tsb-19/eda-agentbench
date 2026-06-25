# Timing Signoff Debug: `mac_unit`

You own static-timing signoff for the `mac_unit` block. The constraint file `constraints.sdc`
is failing signoff review.

## Design intent (from the micro-architecture spec)
- `mac_unit` runs on a single clock `clk` with period **0.5 ns**.
- The accumulator `acc_reg` latches the product register `prod_reg` on every **second** clock (enabled on alternate cycles), so the architects allow this accumulate transfer two clock periods to settle.
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
clk, a_in, cmd_in, acc_out, stat_out
