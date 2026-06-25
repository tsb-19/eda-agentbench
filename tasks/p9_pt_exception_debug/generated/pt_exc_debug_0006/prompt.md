# Timing Signoff Debug: `dma_eng`

You own static-timing signoff for the `dma_eng` block. The constraint file `constraints.sdc`
is failing signoff review.

## Design intent (from the micro-architecture spec)
- `dma_eng` runs on a single clock `clk` with period **0.5 ns**.
- The configuration register `desc_reg` holds quasi-static settings written once at boot; the path `desc_reg` -> `mode2_reg` (the config sink) is intentionally **excluded** from timing (it never toggles in operation).
- `desc_reg` **also** drives the datapath register `addr_reg`; that transfer is a normal functional path that **must meet timing**.

## Symptom
`report_timing` reports no setup violations. Even so the constraints are believed incorrect: confirm that every transfer the spec requires to be timed is actually being analyzed (not masked by an over-broad exception), and that the quasi-static path remains excluded.

## Rules
- Only `constraints.sdc` is editable; all other files are read-only.
- A clean `report_timing` is **necessary but not sufficient**: signoff also rejects
  *over-constraining*. Any path required to meet timing must stay analyzed — masking, cutting,
  or relaxing a real functional path will be rejected, and so will removing an exception that is
  genuinely required.
- Run `bash run_public.sh` for live `report_timing` / `report_exceptions` feedback. There is no
  answer key; reason about correctness the way an engineer does before signoff.

## Design ports
clk, desc_in, mode2_out, addr_out
