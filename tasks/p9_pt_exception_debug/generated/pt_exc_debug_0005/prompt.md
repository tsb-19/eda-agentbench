# Timing Signoff Debug: `spi_core`

You own static-timing signoff for the `spi_core` block. The constraint file `constraints.sdc`
is failing signoff review.

## Design intent (from the micro-architecture spec)
- `spi_core` runs on a single clock `clk` with period **0.5 ns**.
- The capture register `cap_reg` samples the shift register `shift_reg` at half the core clock rate (every **second** edge), a documented two-cycle path.
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
clk, mosi_in, tick_in, rx_out, flag_out
