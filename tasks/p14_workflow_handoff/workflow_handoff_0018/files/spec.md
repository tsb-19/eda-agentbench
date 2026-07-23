# acc_stage — Workflow / Multi-Stage Evidence-Chain Sign-off Handoff (semantic-role-binding, ambiguous-role spec)

This is a downstream **timing sign-off handoff** for `acc_stage` whose evidence is **out of date** AND whose shipped `flow_config.json` carries a **value-swap** on the signoff axes. You must recover the only globally-consistent package by **resolving the semantic role of each shipped value** (which value belongs on which axis) and intersecting the partially-truthful sources, then regenerate fresh sign-off evidence by rerunning the flow in order.

## Design intent (post-ECO v2 family)

The shipped design family is **netlist v2.x** with interface ports `{clk_main, din, en, dout}`. Legacy **v1** (`{clk_old, din, dout}`) is provenance-only. The exact recovery package is the **unique assignment** satisfying all constraints below -- it is **not** written out as a single tuple anywhere in this handoff.

## Terminology (partial; see glossary.md for examples -- NOT a complete schema)

- The reports carry a **scenario** field (`scenario=`) and a **corner** field (`corner=`). These are DISJOINT typed axes: a value valid on one is invalid on the other.
- A **PVT descriptor** (e.g. `slow_1.0V_125C`) is a string `<process>_<voltage>_<temperature>` that **characterizes** a (scenario, corner) pair but is **never** a valid scenario or corner value.
- The consumed clock is the one that yields non-zero intended-clock path coverage on the design.

**No value-to-axis mapping is provided.** Resolve the role of each label from the evidence.

## Constraints (intersect these; none alone is the answer)

- **C1 netlist family:** the consumed netlist is in the v2.x family with the `{clk_main,din,en,dout}` interface (`netlist_v1.v` is out of family).
- **C2 clock coverage:** the consumed clock is the only one with non-zero intended-clock coverage on the v2 netlist.
- **C3 scenario typed:** the scenario value must be a scenario member (a corner value or PVT label in the scenario role is a type error).
- **C4 corner typed:** the corner value must be a corner member (a scenario value or PVT label in the corner role is a type error).
- **C5 scenario/corner signoff pair:** exactly one `(scenario, corner)` pair is the setup signoff pair.
- **C6/C7 provenance / digest:** the evidence chain must be freshly regenerated from the inferred package (stages ordered); a valid-looking digest bound to a role-mismatched or invalidated stage is rejected.

## Shipped evidence sources (each is LOCALLY plausible, NONE globally correct as-shipped)

- `report_A_role_swap.rpt` — right netlist/clock; the role fields are SWAPPED vs the authority.
- `report_B_role_stale.rpt` — correct role fields; stale netlist (netlist_v1).
- `report_C_role_pvt.rpt` — a PVT descriptor in the corner role (and a generic clock alias).
- `evidence_D_role_mismatch.json` — valid-looking chain; the role fields are swapped inside.
- `glossary.md` — INCOMPLETE terminology examples (NOT a schema).
- `prev_signoff.log` — recent, plausible, NON-authoritative.

**A package with the correct netlist+clock still PrimeTime-signs-off GREEN when the role fields are swapped or a PVT label is substituted** (the report body is corner-independent). Semantic-role binding, not signoff, is what rejects a signoff-green-but-mis-typed package.

## Two-stage evidence chain (evidence_steps=2)

1. **Stage 1** — `bash run_evidence_stage1.sh` regenerates `timing_report.rpt` + `evidence_manifest.json` from the repaired inputs.
2. **Stage 2** — `bash run_evidence_stage2.sh` consumes the **fresh** stage-1 evidence and regenerates `stage2_summary.json`; its `upstream_evidence_digest` must equal the fresh stage-1 report digest.

Run stage 1 **then** stage 2, after the inputs are repaired and role-consistent.

## What correct looks like

1. **Resolve** the semantic role of each report field label from the report intersection.
2. **Infer** the unique assignment by intersecting C1–C5 (reject each pairwise-plausible decoy).
3. **Repair** `flow_config.json` to that netlist + `(scenario, corner)` pair + clock.
4. Run `bash run_evidence_stage1.sh` then `bash run_evidence_stage2.sh` to regenerate fresh evidence.

## What will NOT be accepted

- A **value-swap / role mismatch** on the signoff axes (signoff-green but mis-typed).
- A **PVT descriptor** substituted for a scenario or corner value.
- A **wrong clock** (zero coverage / a generic alias).
- Following any single shipped source; a single-axis repair; a green report alone; hand-edited evidence; a stage-2 from a stale/role-wrong stage 1.
- Editing the netlists, library, manifest, glossary, generators, or runners; weakening `constraints.sdc`.
