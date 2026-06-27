# Task: restore the acc_stage timing sign-off handoff (multi-artifact)

You are handed a downstream **timing sign-off handoff package** for the `acc_stage` block. The
package is internally **inconsistent across several artifacts**: the sign-off flow is signing off
the wrong design on the wrong clock, yet it still reports "clean". Restore one coherent handoff
contract so the flow signs off the **current** design, then confirm sign-off passes.

## What you can do

- Read `spec.md` and `handoff_manifest.json` (the **authority** for the current contract),
  `netlist_v2.v` / `netlist_v1.v`, `constraints.sdc`, `flow_config.json`, `provenance.json`,
  `timing_report.rpt`, and `pt_signoff.tcl`.
- Run `bash run_public.sh` as often as you like for PrimeTime feedback. It models the downstream
  flow: it consumes the netlist named in `flow_config.json`, applies `constraints.sdc`, and reports
  whether the consumed design matches the manifest authority and whether a real, non-empty timing
  graph signs off. The `HANDOFF_PUBLIC:` verdict is on the first line; `PUBLIC_HINT:` lines point at
  what disagrees (not the fix).
- Edit **only** `flow_config.json`, `constraints.sdc`, and `provenance.json`.

## What correct looks like

The handoff is correct only when, end-to-end, the flow consumes the **current v2 netlist** the
manifest names (with matching provenance hash), the SDC **binds the current clock `clk_main`** so the
intended sequential paths are actually constrained, PrimeTime setup sign-off reports **no
negative-slack paths**, and `provenance.json` records that same v2/clk_main run.

## Why one edit is not enough

The consumed selection and the clock binding are **jointly stale**:
- Fix only `constraints.sdc` to `clk_main` → the flow still reads `netlist_v1.v`, which has no
  `clk_main` port → **zero constrained paths** (a meaningless clean report).
- Fix only `flow_config.json` to `netlist_v2.v` → the SDC still binds `clk_old`, absent on v2 →
  **zero constrained paths**.
- Fix only `provenance.json` → the flow still consumes the stale design; the recorded hash will not
  match what is actually consumed.

You must restore them **together**, then reconcile `provenance.json` to the same run.

## What will NOT be accepted

A green PrimeTime report alone is **not** enough — the stale v1/clk_old island signs off clean on the
**wrong design**. Do not edit a netlist, the library, the manifest authority fields, the archived
`timing_report.rpt`, or the runners; do not weaken `constraints.sdc` (no loosened period, no timing
exceptions); do not bypass the selection. The grade checks the restored cross-artifact contract, not
just the PrimeTime status.

When done, briefly state the root cause (which artifacts lagged) and the coordinated repair.
