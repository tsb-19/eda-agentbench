# acc_stage — Handoff Sign-off Package (authoritative spec)

This is a downstream **timing sign-off handoff** for the `acc_stage` block. Your job is to make
the handoff package internally consistent so the sign-off flow verifies the **current** design,
then confirm sign-off passes. This document is the **authority** for what the current design is;
if an artifact in the package disagrees with this spec, the spec wins.

## Current design intent

`acc_stage` is a registered datapath stage on a single clock `clk`. After the most recent
engineering change, the block is **enable-qualified**: it has a qualifier input **`en`** in
addition to the data input `din` and the output `dout`. The behavioural RTL in `design.v` is the
reference — note its port list `{clk, rst_n, en, din, dout}` and that the datapath only updates
`when (en)`. The handoff netlist that the flow signs off **must be the current revision whose
gate-level interface matches this design** (it must contain the `en` input path). An earlier
revision of the netlist exists in the package for provenance history only; it predates the `en`
qualifier and must **not** be the one the flow consumes.

## Handoff scenario

- Scenario: **func** (functional sign-off).
- Corner / library: **typ** (`tiny.db`).
- Clock: **clk**, period **3.0 ns**, uncertainty **0.15 ns**.
- Constraints: the frozen `constraints.sdc` (already correct — do not edit it).

## What the package contains

- `handoff_manifest.json` — the handoff contract: which netlist/constraints/scenario/corner the
  downstream flow consumes, plus the selected netlist's **provenance hash**.
- the gate-level netlist revisions shipped with the package (one current, one legacy).
- `constraints.sdc`, `tiny.lib` / `tiny.db`, `design.v` (RTL reference).
- `run_public.sh` / `run_public.tcl` — the manifest-driven public sign-off feedback runner.

## The sign-off requirement

The downstream flow consumes **the manifest-selected netlist**. The handoff is correct only when:

1. the manifest selects the **current** revision (the one whose interface matches this spec),
2. the manifest's declared provenance hash matches that netlist's actual content, and
3. PrimeTime setup sign-off on the selected netlist reports **no negative-slack paths**.

A green PrimeTime report alone is **not** sufficient: the legacy revision also signs off clean on
its own, but signing it off verifies the **wrong design**. Do **not** "fix" the handoff by editing
a netlist, weakening `constraints.sdc`, editing the runner to bypass the manifest, or faking a
report. The only correct repair is to make the **handoff mapping** point at the current revision
with a matching provenance hash.
