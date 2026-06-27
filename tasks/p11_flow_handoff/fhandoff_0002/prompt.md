# Task: repair the acc_stage clock binding in the sign-off handoff

You are handed a downstream **timing sign-off handoff** for the `acc_stage` block. The constraints
bind the clock to the **wrong (stale) clock name**, so the design's sequential paths are not
actually constrained. Fix the clock binding so the intended paths are constrained, then confirm
sign-off passes.

## What you can do

- Read `spec.md` (authoritative intent), `design.v` (RTL reference), `design_netlist.v` (gate-level
  netlist), `constraints.sdc`, and `handoff_manifest.json`.
- Run `bash run_public.sh` as often as you like for PrimeTime feedback. It reports whether the
  intended clock is bound and how many sequential paths are actually constrained; the
  `HANDOFF_PUBLIC:` verdict is on the first line.
- Edit **only** `constraints.sdc`.

## What correct looks like

The handoff is correct only when the constraints create the clock on the design's **real** clock
port (see `spec.md` / the netlist), the intended sequential paths are **actually constrained** (a
non-empty timing graph), and PrimeTime setup sign-off reports no negative-slack paths.

## What will NOT be accepted

A green PrimeTime report alone is **not** enough — if the clock name is stale, PT prints a clean
report while constraining **zero** intended paths. Do not weaken timing, delete constraints, rename
the netlist/design to match the stale SDC, edit forbidden netlist/lib artifacts, or fabricate a
report. The grade checks that the intended clock is bound and the intended paths are constrained,
not just the PT status.

When done, briefly state the root cause and the repair.
