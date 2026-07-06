# acc_stage — Workflow / Multi-Stage Evidence-Chain Sign-off Handoff (implicit typed-axis spec)

This is a downstream **timing sign-off handoff** for `acc_stage` whose evidence is **out of date** AND whose shipped `flow_config.json` carries a **value-swap** on the typed axes. The typed axes are **NOT** published as a schema -- you must **infer** axis membership from the report context, the terminology here, PVT notation, and the coverage facts, then recover the only globally-consistent **typed** package and regenerate fresh sign-off evidence.

## Design intent (post-ECO v2 family)

The shipped design family is **netlist v2.x** with interface ports `{clk_main, din, en, dout}`. Legacy **v1** (`{clk_old, din, dout}`) is provenance-only. The setup signoff is taken at the **slow operating point** in the **functional signoff mode**. The exact recovery package is the **unique typed assignment** satisfying all constraints below -- it is **not** written out anywhere.

## Terminology (partial; see glossary.md for examples -- NOT a complete schema)

- The reports carry an **operating-point** field (`op_point=`) and a **signoff-mode** field (`mode=`). These are DISJOINT typed axes: a value valid on one is invalid on the other.
- A **PVT descriptor** (e.g. `slow_1.0V_125C`) is a string `<process>_<voltage>_<temperature>` that **characterizes** an (operating point, signoff mode) pair but is **never** a valid `op_point` or `mode` value.
- The consumed clock is the one yielding **non-zero intended-clock path coverage** on the design.

**No complete value-to-axis table is provided.** Infer membership from how values are used.

## Constraints (intersect these; none alone is the answer)

- **C1 netlist family:** the consumed netlist is in the v2.x family with the `{clk_main,din,en,dout}` interface (`netlist_v1.v` is out of family).
- **C2 clock coverage:** the consumed clock is the only one with non-zero intended-clock coverage on the v2 netlist (a coverage fact).
- **C3 op_point typed:** the `op_point` value is an operating-point member (infer which values are operating points from PVT notation + context).
- **C4 mode typed:** the `mode` value is a signoff-mode member (the OTHER typed axis).
- **C5 signoff pair:** the setup signoff uses the slow operating point in the functional mode.
- **C6/C7 provenance / digest:** the evidence chain must be freshly regenerated from the inferred typed package; a valid-looking digest bound to a typed-mismatched or invalidated stage is rejected.

## Shipped evidence sources (each is LOCALLY plausible, NONE globally correct as-shipped)

- `report_A_context_swap.rpt` — right netlist/clock; `op_point`/`mode` swapped.
- `report_B_context_stale.rpt` — right `op_point`/`mode`; stale netlist.
- `report_C_context_pvt.rpt` — a PVT descriptor used in `mode`.
- `evidence_D_context_mismatch.json` — valid-looking chain; `op_point`/`mode` swapped inside.
- `public_check_summary.json` — pairwise typed/provenance inconsistency symptoms + the coverage fact (verdict-first; never the answer/schema).
- `glossary.md` — INCOMPLETE terminology examples (NOT a schema).
- `prev_signoff.log` — recent, plausible, NON-authoritative.

**A package with the correct netlist+clock still PrimeTime-signs-off GREEN when the typed axes are swapped or a PVT label is substituted** (the report body is corner-independent). Typed binding, not signoff, is what rejects a signoff-green-but-mis-typed package.

## Two-stage evidence chain (evidence_steps=2)

1. **Stage 1** — `bash run_evidence_stage1.sh` regenerates `timing_report.rpt` + `evidence_manifest.json` from the repaired inputs.
2. **Stage 2** — `bash run_evidence_stage2.sh` consumes the **fresh** stage-1 evidence and regenerates `stage2_summary.json`; its `upstream_evidence_digest` must equal the fresh stage-1 report digest.

Run stage 1 **then** stage 2, after the inputs are repaired and typed-consistent.

## What correct looks like

1. **Infer** axis membership from the evidence (op_point→scenario, mode→corner via PVT notation + context + coverage).
2. **Infer** the unique typed package by intersecting C1–C5.
3. **Repair** `flow_config.json` to that netlist + typed (scenario, corner) pair + clock.
4. Run `bash run_evidence_stage1.sh` then `bash run_evidence_stage2.sh` to regenerate fresh evidence.

## What will NOT be accepted

- A **value-swap** on the typed axes (signoff-green but mis-typed).
- A **PVT descriptor** substituted for an `op_point`/`mode` value.
- A **wrong clock** (zero coverage).
- Following any single shipped source; a single-axis repair; a green report alone; hand-edited evidence; a stage-2 from a stale/typed-wrong stage 1.
- Editing the netlists, library, manifest, glossary, generators, or runners; weakening `constraints.sdc`.
