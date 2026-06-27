# acc_stage — Handoff Sign-off Package (authoritative spec)

This is a downstream **timing sign-off handoff** for the `acc_stage` block. Your job is to make the
handoff package internally consistent so the sign-off flow verifies the **current** design on the
**current** clock, then confirm sign-off passes. This document, together with
`handoff_manifest.json`, is the **authority** for what the current design is; if a *consumed*
artifact in the package disagrees with this spec/manifest, the spec/manifest wins.

## Current design intent (post-ECO v2)

Two engineering changes have already landed and are recorded in the spec and the manifest:

1. **Re-synthesis v1 → v2.** The current handoff netlist is the **v2** revision. It is
   **enable-qualified**: it has a qualifier input **`en`** in addition to the data input `din` and
   the output `dout`. An earlier **v1** revision predates the `en` qualifier and exists in the
   package for provenance history only — it must **not** be the one the flow consumes.
2. **Clock rename `clk_old` → `clk_main`.** The current clock port is **`clk_main`**. The legacy
   `clk_old` name belongs to the stale v1 revision.

So the **current contract** the flow must sign off is: netlist **v2** (port list
`{clk_main, din, en, dout}`), clock **`clk_main`**, scenario **func**, corner/library **typ**
(`tiny.db`).

## What the package contains

- `handoff_manifest.json` — the handoff **contract / authority**: which netlist revision, clock,
  scenario, and corner the downstream flow is *supposed* to consume, plus the v2 provenance hash.
  Its `netlist` / `clock` / `scenario` / `corner` / provenance fields are **correct and frozen**
  (read-only authority).
- `flow_config.json` — the downstream selection the sign-off flow **actually consumes**: it names
  the netlist file the flow reads. This is one of the drifted artifacts.
- `constraints.sdc` — the SDC the flow applies (clock binding + I/O budget). This is the other
  drifted artifact.
- `netlist_v2.v` (current) and `netlist_v1.v` (legacy, provenance history only).
- `timing_report.rpt` — an archived sign-off report shipped with the package. **Read-only evidence**
  — its provenance stamp records which design/clock it was generated against. (It is stale; see
  below. Do not hand-edit it.)
- `provenance.json` — the **machine-readable provenance pointer** the flow maintains to record what
  the *current* sign-off evidence corresponds to (netlist revision + content hash + clock + corner).
  Editable. It currently still records the **stale v1/clk_old** run and must be reconciled to the
  current v2/clk_main contract once you restore the consumed design.
- `pt_signoff.tcl` — a reference description of how the downstream flow consumes `flow_config.json`
  and `constraints.sdc` (documentation; the grader runs the real flow itself).
- `tiny.lib` / `tiny.db` — the typ-corner library.
- `run_public.sh` / `run_public.tcl` — the public sign-off feedback runner.

## The defect

The manifest and this spec say **v2 / clk_main**. But the **downstream consumers lag**: the
selection in `flow_config.json` still names the **stale v1** netlist, the `constraints.sdc` still
binds the **stale `clk_old`** clock, and the archived `timing_report.rpt` is the **old v1/clk_old**
report. Those three downstream artifacts form a self-consistent **stale island** that signs off
green on the *wrong* design — a silent false pass.

## The sign-off requirement

The handoff is correct only when, end-to-end:

1. the flow **consumes the v2 netlist** the manifest names (selection + provenance integrity),
2. the SDC **binds `clk_main`** and the intended sequential paths are actually constrained
   (a clean report on zero constrained paths is meaningless), and
3. PrimeTime setup sign-off on the consumed design reports **no negative-slack paths**.

For **full** credit, also reconcile `provenance.json` so the recorded sign-off evidence matches the
restored v2/clk_main run (revision + content hash + clock + corner). Restoring the consumed design
without reconciling the provenance record signs off the right design but leaves stale evidence — a
correct-but-incomplete handoff.

## What will NOT be accepted

- A green PrimeTime report **alone** is not enough — the stale v1/clk_old island signs off clean on
  its own but verifies the **wrong design**.
- **One edit is not enough.** The selection and the SDC are *jointly* stale: fixing only the SDC to
  `clk_main` leaves the flow reading v1 (which has no `clk_main` port) → zero constrained paths;
  fixing only the selection to v2 leaves the SDC on `clk_old` (absent on v2) → zero constrained
  paths. You must restore **both** consistently.
- Do **not** edit a netlist, the library, the manifest authority fields, the archived report, or the
  runners; do **not** weaken `constraints.sdc` with timing exceptions or a loosened period; do
  **not** bypass the selection. Such symptom-suppression is rejected by the grader regardless of the
  PrimeTime status.

When done, briefly state the root cause (which artifacts lagged) and the coordinated repair.
