# Task: repair the acc_stage timing sign-off handoff

You are handed a downstream **timing sign-off handoff package** for the `acc_stage` block. The
package is internally **inconsistent**: the sign-off flow is not verifying the design the spec
says is current. Make the handoff consistent so the flow signs off the **current** design, then
confirm sign-off passes.

## What you can do

- Read `spec.md` (authoritative intent), `design.v` (RTL reference), the gate-level netlist
  revisions, `constraints.sdc`, and `handoff_manifest.json`.
- Run `bash run_public.sh` as often as you like for PrimeTime feedback. It reports which netlist
  the manifest currently selects, whether that selection is consistent (provenance hash + the
  interface the constraints expect), and whether sign-off passes. The `HANDOFF_PUBLIC:` verdict
  is on the first line.
- Edit **only** `handoff_manifest.json`.

## What correct looks like

The handoff is correct only when the manifest selects the **current** netlist revision (the one
whose gate-level interface matches `spec.md` — it includes the `en` qualifier), its declared
provenance hash matches that netlist's actual content, and PrimeTime setup sign-off on the
selected netlist reports no negative-slack paths.

## What will NOT be accepted

A green PrimeTime report alone is **not** enough — the legacy revision also signs off clean on its
own, but signing it off verifies the **wrong design**. Do not edit a netlist, weaken
`constraints.sdc`, change the runner to bypass the manifest, or fabricate a report. The grade
checks the restored handoff contract (manifest provenance + consumed interface), not just the PT
status.

When done, briefly state the root cause and the repair.
