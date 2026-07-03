# acc_stage — Workflow / Multi-Stage Evidence-Chain Sign-off Handoff (constraint-graph spec)

This is a downstream **timing sign-off handoff** for `acc_stage` whose evidence is **out of date** AND whose **correct recovery target is NOT stated in any single file**. You must infer the only globally-consistent package by **intersecting independent constraints**, then regenerate fresh sign-off evidence by rerunning the flow in order.

## Design intent (post-ECO v2 family)

The shipped design family is **netlist v2.x** with interface ports `{clk_main, din, en, dout}`. Legacy **v1** (`{clk_old, din, dout}`) is provenance-only. The exact recovery package is the **unique assignment** satisfying all of the constraints below — it is **not** written out as a single tuple anywhere in this handoff.

## Constraint graph (intersect these; none alone is the answer)

- **C1 — netlist family (interface):** the consumed netlist must be in the **v2.x family** with the `{clk_main, din, en, dout}` interface. The `handoff_manifest.json` declares the allowed family + interface; it does **not** state the full recovery tuple. `netlist_v1.v` (interface `{clk_old, din, dout}`) is **out of family** and cannot be the consumed netlist.
- **C2 — clock coverage:** the consumed clock must be the **intended clock** that yields non-zero path coverage on the v2 netlist. A clock binding that produces **zero constrained paths** (e.g. `clk_old` against the v2 design) is rejected. (Coverage is a tool-derived fact, reported by the public runner.)
- **C3 — scenario/corner signoff pair:** the signoff-mode joint-validity table for `acc_stage` admits **exactly one** (scenario, corner) pair for a setup signoff; the other (scenario, corner) combinations are characterization-only or non-signoff and are rejected by the hidden oracle.
- **C4 — report provenance / C5 upstream digest / C6 stage dependency:** the evidence chain must be freshly regenerated from the inferred package (stages ordered); a valid-looking digest bound to an **invalidated prerequisite stage** (e.g. a stale netlist) is rejected. (Runtime check.)

## Shipped evidence sources (each is LOCALLY / PAIRWISE plausible, NONE globally consistent)

- `report_A_scenario_corner.rpt` — satisfies C1+C2; violates C3 (wrong scenario/corner).
- `report_B_stale_netlist.rpt` — satisfies C3; violates C1 (stale netlist, out of family).
- `report_C_wrong_clock.rpt` — satisfies C1+C3; violates C2 (wrong clock, zero coverage).
- `evidence_D_manifest.json` — valid-looking digest/upstream chain; violates C1+C6 (depends on an invalidated prerequisite stage).
- `prev_signoff.log` — recent, plausible, NON-authoritative.

**No two decoys agree on the same wrong axis** — you cannot majority-vote; you must intersect the constraints.

## Two-stage evidence chain (evidence_steps=2)

Sign-off evidence is a **two-stage chain** and the stages are **ordered**:

1. **Stage 1** — `bash run_evidence_stage1.sh` regenerates `timing_report.rpt` + `evidence_manifest.json` from the repaired inputs.
2. **Stage 2** — `bash run_evidence_stage2.sh` consumes the **fresh** stage-1 evidence and regenerates `stage2_summary.json`; its `upstream_evidence_digest` must equal the fresh stage-1 report digest.

Run stage 1 **then** stage 2, after the inputs are repaired and consistent.

## What correct looks like

1. Infer the **unique** globally-consistent package by intersecting C1 ∧ C2 ∧ C3.
2. Repair `flow_config.json` to consume that netlist at that (scenario, corner) pair (the clock is already the intended clock — do **not** change it).
3. Run `bash run_evidence_stage1.sh` then `bash run_evidence_stage2.sh` to regenerate fresh evidence from the repaired inputs.
4. PrimeTime setup sign-off on the consumed design reports **no negative-slack paths**, with **non-zero intended-clock coverage**.

## What will NOT be accepted

- Following any single shipped source (report_A / report_B / report_C / evidence_D / prev_signoff). Each satisfies only a subset of the constraint graph.
- A **single-axis** repair (fixing only the netlist, or only the clock, or only the scenario/corner).
- A **pairwise-plausible / majority-vote** package (no decoy majority is the global answer).
- A green PrimeTime report alone, or hand-edited evidence, or a stage-2 summary built from a stale/wrong stage 1.
- Editing the netlists, the library, the authority manifest, the generators, or the runners; or weakening `constraints.sdc`.
