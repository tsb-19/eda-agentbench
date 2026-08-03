# Phase-5 Treatment Mapping (FROZEN before eval-instance generation)

**Amendment 3 freeze.** This directory is the authoritative source for the BundleS/TypedContract treatment in Phase-5A/5B. It is **frozen before any primary evaluation instance is generated**, so no instance content can retroactively reshape the treatment.

## Contents

- `abstract_components.json` — **family-independent** abstract definitions of the non-answer-bearing BundleS components **C1** (canonical labels + disjoint-axis declaration), **C2** (value-domain definitions), **C4** (glossary + references), **C7** (procedural contract). Documents what is excluded (C3 coverage, C5 pairwise-conflict, **C6** answer-bearing — none are in BundleS).
- `sta_mapping.json` — the **deterministic STA mapping** (abstract components → Family-A roles `intent_class`/`target_partition`/`check_mode`, files, authority precedence). Tool: PrimeTime. Track: `p15_sta_handoff`.
- `spice_mapping.json` — the **deterministic SPICE mapping** (abstract components → Family-B roles `corner`/`load_condition`/`metric`, files, authority precedence). Tool: HSPICE. Track: `p16_spice_handoff`.

## How generators use it

Each instance generator derives the instance's **Base / BundleS / TypedContract** disclosure mechanically from this mapping + the instance's value domains (the per-instance enums). The BundleS prose and the TypedContract JSON Schema carry the **same semantic facts** (information-equivalent; checked by `info_equiv_audit.json`). **No per-instance wording optimization is permitted**, and **no wording is optimized on model performance** (there are no model calls in Phase-5B; the dev instance may expose implementation/tool-path defects only — amendment 3).

## Freeze integrity

The mapping is immutable in git history at its commit; `canonical_integrity.freeze` hash-pins these three files into the pre-run freeze manifest (Task: integrity manifests) before the first paid episode. The downstream generators record this directory's commit SHA in their own `metadata.generator` block so any instance's treatment is traceable to a frozen mapping.
