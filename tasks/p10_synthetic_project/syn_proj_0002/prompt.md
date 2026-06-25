# Timing Constraint Sign-off Debug: `acc_stage`

You own static-timing sign-off for the `acc_stage` datapath stage. The constraint file
`constraints.sdc` is failing sign-off review.

## What to do

Edit **`constraints.sdc`** so that:
1. PrimeTime setup sign-off reports no negative-slack paths, **and**
2. the constraints encode the **interface budget defined in `spec.md`** (the authority).

`spec.md` gives the clock target and the neighbouring blocks' budgets. The clock, input, and
output constraints must all match the spec; the I/O delays are **not** stated literally —
derive them from the budget arithmetic in the spec.

## Symptom

`report_timing` reports a setup **violation**. The violation is real, but its cause is that a
constraint no longer matches the spec budget. Making the violation disappear is **necessary
but not sufficient**: over-constraining (tightening the period, inflating uncertainty, zeroing
or padding a delay) is rejected at sign-off review — the constraints must match the spec, not
merely silence the symptom.

## Files

- `spec.md` — the authoritative timing contract (read-only)
- `design.v` — RTL of `acc_stage` (read-only)
- `design_netlist.v` — gate-level netlist timed by PrimeTime (read-only)
- `tiny.lib`, `tiny.db` — scalar timing library (read-only)
- `constraints.sdc` — the constraint file (**you may edit only this file**)
- `run_public.sh`, `run_public.tcl` — live sign-off feedback (read-only)

## Feedback

Run `bash run_public.sh` for live `report_timing` and a sign-off pass/fail indication. There
is no answer key in the feedback — reason about the spec budget the way an engineer does
before sign-off.

## Rules

- Only `constraints.sdc` is editable; every other file is read-only.
- The design has a single clock `clk`. Design ports: `clk`, `din`, `en`, `dout`.
