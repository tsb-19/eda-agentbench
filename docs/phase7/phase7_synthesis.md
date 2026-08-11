# Phase-7 Synthesis + Claim–Evidence Matrix (authoritative for manuscript v3)

All experimental + benchmark-runtime work is **permanently closed**. This document fixes the
final evidence hierarchy and locked wording for the Phase-7 manuscript (v3). No claim below
rests on pooled n=3+n=12 STA data; the prospective n=12 batch is the authoritative STA result.

## RQ1 — Controlled Harness effect
**Supported claim:** *"Harness information structure can change semantic-binding behavior in a
controlled executable setting."*
- Qwen workflow development pair: Base 1/3 → BundleS 3/3.
- Pre-frozen within-family held-out: Base 1/3 → BundleS 3/3.
- Failure taxonomy: axis-binding failures + role-conditioned value-selection failures.
- **Scope:** controlled workflow family, Qwen only. **Not** a universal Harness-improvement claim.

## RQ2 — Transfer
**Supported claim:** *"Within-family held-out confirmation did not establish cross-model or
cross-family transfer."* The RQ2 headline distinguishes **null/unestablished transfer**,
**ceiling**, and **direction reversal under prospective task expansion**.

STA — historical pilot (n=3, descriptive, NOT pooled): Base 0.50 / BundleS 0.33 / TypedContract 0.33.
STA — prospective preregistered confirmation (n=12, **authoritative**): Base 0.208 / BundleS 0.333 /
TypedContract 0.458; BundleS vs Base 3 improve / 2 decline / 7 tie; exact sign-test p=1.0;
instance-level permutation sensitivity p=0.31.
**Locked wording:** *"Prospective STA confirmation did not establish a transferable BundleS
benefit. The descriptive direction reversed relative to the original three-instance pilot,
illustrating the instability of conclusions drawn from very small task samples."*
**Not claimed:** significant BundleS improvement; significant TypedContract improvement; a stable
STA negative. TypedContract is **descriptively highest** in the prospective batch only.
DeepSeek (exact-counterbalanced): Base 3/4 vs BundleS 3/4 — no detectable BundleS benefit.
SPICE: Base = BundleS = TypedContract = 1.00 semantic-binding ceiling — non-discriminative.

## RQ3 — Evaluation validity
**Framing:** the Harness Effect Audit Protocol is *"an auditable evaluation protocol instantiated
and stress-tested in this study"* (NOT broadly validated / universally reusable). Four layers:
(1) capability validity, (2) sampling validity, (3) execution validity, (4) artifact integrity.
The internal study shows the concrete threat each control family caught.

**Independent Benchmark Repair Audit (Terminal-Bench 2.0→2.1):** 26 officially documented
repairs; rubric frozen before repair coding; **direct 1 / partial 21 / not-covered(Other) 4**;
layers capability 17 / sampling 0 / execution 10 / artifact 1; 6 multi-layer cases. Locked
wording: *"The taxonomy showed broad but predominantly partial correspondence with independently
documented benchmark repairs: 22 of 26 repairs had at least partial correspondence, but only one
was directly captured and four lay outside the taxonomy."* **Explicitly:** not runtime validation;
does not show prediction/prevention; the absence of sampling-layer repairs means the external
audit does not validate every protocol layer.

## Study B — status
**Exact record:** *"Preregistered but unexecuted because qualified independent human annotators
were unavailable."* No LLM substitution. The manuscript does **not** imply the semantic-binding
taxonomy has independent human validation. **Limitations:** construct validity rests on executable
provenance/authority oracles rather than independent blinded human judgment.

## Related-work refresh (add at v3)
- **TAB ("No More, No Less: Task Alignment in Terminal Agents"):** studies selective use of
  necessary environmental cues amid plausible distractors. Our construct = role-conditioned
  semantic binding + provenance/authority attribution, including tool-green wrong bindings after
  evidence is available. **Not** the same failure construct.
- **LongHorizon-Harness:** its cross-benchmark Harness gains sharpen (not contradict) our claim:
  *"Some Harness interventions do transfer across benchmarks; transfer is therefore an empirical
  property that must be demonstrated rather than inferred from within-family confirmation."* We do
  **not** write that Harness improvements generally fail to transfer.

## Abstract / Introduction leads (locked)
- *"A Harness intervention can survive controlled development and a pre-frozen within-family
  held-out evaluation without establishing transfer across models or semantic task families."*
- *"Expanding an external STA evaluation prospectively from three to twelve independently frozen
  task instances reversed the apparent direction of the comparison while still failing to establish
  a stable Harness benefit."*
- Retained: *"Our controlled task instances test existence, recurrence, and transfer direction
  rather than estimate population-level pass rates."* Study-C results are supporting RQ3 evidence,
  not dominant in the abstract.

## Claim–Evidence matrix
| Claim | Status | Evidence | Scope/limit |
|---|---|---|---|
| RQ1: Harness info structure changes semantic-binding in a controlled setting | Supported | Qwen workflow dev 1/3→3/3; frozen held-out 1/3→3/3; taxonomy | Workflow family, Qwen only |
| RQ2: held-out confirmation did not establish transfer | Supported | STA prospective n=12 (0.208/0.333/0.458; 3/2/7; p=1.0/0.31); DeepSeek 3/4=3/4; SPICE ceiling 1.00 | Instance n=12; diagnostic not population |
| RQ2: direction reversal under prospective expansion | Supported (descriptive) | STA pilot n=3 (0.50/0.33) vs prospective n=12 (0.208/0.333) | Small-n illustration |
| RQ3: audit protocol instantiated + stress-tested | Supported | 4 layers; concrete threat per layer caught in-study | Not broadly validated/reusable |
| RQ3: external taxonomy application (TB 2.0→2.1) | Supported (descriptive) | 26 repairs: direct 1/partial 21/Other 4; layers 17/0/10/1 | Retrospective; not prediction/prevention/runtime |
| Construct validity via human annotation | **Not established** | Study B unexecuted | Rests on executable provenance/authority oracles |

## Main-paper organization (3-study/RQ; not phase chronology)
1. Introduction · 2. Related Work and Problem Formulation · 3. Harness Effect Audit Methodology ·
4. Study I — Controlled Semantic-Binding Effects · 5. Study II — Model and Task-Family Transfer ·
6. Study III — Evaluation Validity and Independent Benchmark Repair Audit · 7. Limitations and
Discussion · 8. Conclusion. Appendix: Study-A per-instance table, Study-C 26-repair audit +
source evidence, historical phase chronology, minimal-component ablations, infrastructure details.

## Submission metadata (verified)
- ICLR 2027 official deadlines (iclr.cc/Conferences/2027): **abstract 2026-09-19 11:59 UTC**,
  **full paper 2026-09-26 11:59 UTC**.
- Template: official iclr2027 style not yet posted (Styles URL 404 as of 2026-08-11); compiling
  with the drop-in reconstruction `submission/iclr2027_conference.sty` (drop-in replaceable).
- Anonymous; AI-use + ethics (Study-B status) + reproducibility statements; exact submission HEAD
  + custody hashes captured at freeze.
