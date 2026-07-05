# acc_stage — Workflow / Multi-Stage Evidence-Chain Sign-off Handoff (axis-binding spec)

This is a downstream **timing sign-off handoff** for `acc_stage` whose evidence is **out of date** AND whose shipped `flow_config.json` carries a **value-swap** on scenario/corner. The typed-axis vocabulary is **published** in `axis_schema.json` -- the challenge is correct **binding**, not vocabulary hiding. You must infer the only globally-consistent **typed** package, bind each value to its own axis, then regenerate fresh sign-off evidence by rerunning the flow in order.

## Design intent (post-ECO v2 family)

The shipped design family is **netlist v2.x** with interface ports `{clk_main, din, en, dout}`. Legacy **v1** (`{clk_old, din, dout}`) is provenance-only. The exact recovery package is the **unique typed assignment** satisfying all constraints below -- it is **not** written out anywhere.

## Typed axes (vocabulary published in `axis_schema.json`)

- **scenario_axis:** `{slow, typ, fast}` -- may occupy ONLY the scenario field.
- **corner_axis:** `{func, test, lowpower}` -- may occupy ONLY the corner field.
- **clock_axis:** `{clk_old, clk_main}` -- exact identity required (`clk_main`).
- **pvt_label_axis:** `{slow_1.0V_125C, typ_1.0V_25C, fast_0.8V_0C}` -- DESCRIPTIVE METADATA mapping to a `(scenario, corner)` pair; **never** a valid scenario or corner value.

**A value valid on one axis is invalid on another.** A corner value in the scenario slot, a scenario value in the corner slot, or a PVT label in either slot is a **type error**.

## Constraint graph (intersect these; none alone is the answer)

- **C1 — netlist family (interface):** the consumed netlist must be in the **v2.x family** with the `{clk_main, din, en, dout}` interface (`netlist_v1.v` is out of family).
- **C2 — clock identity:** the consumed clock must be the exact intended clock (`clk_main`); a generic/aliased name (e.g. `clk`) is rejected.
- **C3 — scenario typed:** the scenario field must be a `scenario_axis` member.
- **C4 — corner typed:** the corner field must be a `corner_axis` member.
- **C5 — scenario/corner signoff pair:** the signoff-mode joint-validity table admits **exactly one** `(scenario, corner)` pair for a setup signoff.
- **C6/C7 — report provenance / upstream digest / stage dependency:** the evidence chain must be freshly regenerated from the inferred typed package (stages ordered); a valid-looking digest bound to a typed-mismatched or invalidated prerequisite is rejected. (Runtime check.)

## Shipped evidence sources (each is LOCALLY plausible, NONE type-correct)

- `report_A_value_swap.rpt` — right netlist/clock; scenario/corner SWAPPED (violates C3+C4).
- `report_B_pvt_corner.rpt` — a PVT label used as the corner (violates C4).
- `report_C_wrong_clock.rpt` — a generic clock alias `clk` (violates C2).
- `evidence_D_typed_mismatch.json` — valid-looking chain with swapped scenario/corner fields (violates C3+C4).
- `prev_signoff.log` — recent, plausible, NON-authoritative.

**A package with the correct netlist+clock still PrimeTime-signs-off GREEN when scenario/corner are swapped or a PVT label is substituted** -- because the report body is corner-independent. Type binding (C3/C4), not signoff, is what rejects a signoff-green-but-mis-typed package.

## Two-stage evidence chain (evidence_steps=2)

Sign-off evidence is a **two-stage chain** and the stages are **ordered**:

1. **Stage 1** — `bash run_evidence_stage1.sh` regenerates `timing_report.rpt` + `evidence_manifest.json` from the repaired inputs.
2. **Stage 2** — `bash run_evidence_stage2.sh` consumes the **fresh** stage-1 evidence and regenerates `stage2_summary.json`; its `upstream_evidence_digest` must equal the fresh stage-1 report digest.

Run stage 1 **then** stage 2, after the inputs are repaired and typed-consistent.

## What correct looks like

1. Infer the **unique typed** package by intersecting C1 ∧ C2 ∧ C3 ∧ C4 ∧ C5.
2. **Bind** each value to its own typed axis (scenario-axis value in the scenario field; corner-axis value in the corner field; `clk_main` as the clock).
3. Repair `flow_config.json` to consume that netlist at that typed `(scenario, corner)` pair.
4. Run `bash run_evidence_stage1.sh` then `bash run_evidence_stage2.sh` to regenerate fresh evidence from the repaired inputs.
5. PrimeTime setup sign-off on the consumed design reports **no negative-slack paths**, with **non-zero intended-clock coverage**.

## What will NOT be accepted

- A **value-swap** (a corner value in the scenario slot / a scenario value in the corner slot) -- signoff-green but mis-typed.
- A **PVT label** substituted for a scenario or corner value.
- A **generic clock alias** (`clk`) instead of `clk_main`.
- Following any single shipped source (report_A / report_B / report_C / evidence_D / prev_signoff).
- A **single-axis** repair (fixing only the netlist, or only the clock, or only scenario/corner).
- A green PrimeTime report alone, or hand-edited evidence, or a stage-2 summary built from a stale/wrong/typed-mismatched stage 1.
- Editing the netlists, the library, the manifest, `axis_schema.json`, the generators, or the runners; or weakening `constraints.sdc`.
