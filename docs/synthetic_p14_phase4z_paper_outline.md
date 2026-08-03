# Phase-4Z — Paper Outline & Claim–Evidence Matrix (p14 workflow-handoff clarity-bundle program)

**Date:** 2026-08-03 · **Branch:** synthetic-phase0a · **Status:** docs-only, no paid model calls, stopped for review (no push)
**Companion:** `reports/synthetic_p14_phase4z_synthesis.{md,json}` (the evidence synthesis this outline draws on).

This document (1) proposes a paper outline and (2) gives a **claim–evidence matrix** that records, for every claim the program could make, its status (Established / Directional·model-scoped / Unresolved / Negative) and the exact evidence for/against it. The matrix is the single source of truth for what the data does and does not support; the prose must not outrun it.

## Guiding constraint

Every paper claim must map to a matrix row at or below its evidence status. The headline is **unresolved**, not "interaction found" or "bundle works generally."

---

## 1. Paper outline (proposed)

**Working title.** *When clarity helps and when it doesn't: a controlled decomposition of a semantic-role-binding EDA task across two frontier models.* (Or, more conservative: *A model-contingent clarity-bundle effect and an unresolved component-interaction question on a workflow-handoff EDA task.*)

1. **Introduction.** EDA agent benchmarks; why semantic role binding over typed axes is a useful, search-resistant probe; the gap between "the full bundle works" and "which part matters, for whom." State the three questions: (Q1) does the full clarity bundle help on the controlled pair? (Q2) is the effect answer-disclosure or inference-aid, and does it generalize? (Q3) which component(s) carry it, and is the effect model-robust?
2. **Task & grader.** p14 workflow-handoff: bind a signoff scenario/corner from heterogeneous, role-misleading evidence (PVT descriptors, role-swapped reports, stale decoys). Controlled pair 0009 (ambiguous) / 0010 (clear), identical hidden truth + grader, differ only in visible clarity. Typed-binding oracle + 8-component score; the `semantic_binding_failure` taxonomy (axis vs value-selection).
3. **Methods.** Models (Qwen3.7-Max primary, DeepSeek-V4-Pro cross-model); SSE streaming (transport validity); k=3–4 per cell with seeded exact-counterbalanced blocked randomization; predeclared interpretation tables; the fairness gate (real-PrimeTime, score-independent block measurement-control); the canonical-tree integrity guard (isolated worktree, frozen hashes, per-episode verification). Four evaluation dimensions reported separately: artifact correctness, semantic binding, protocol completion, transport reliability.
4. **Results.**
   - **R1 — Full bundle on the controlled pair (Qwen + DeepSeek).** Established: the full bundle suppresses the wrong-axis binding failure for both providers.
   - **R2 — Non-answer localization + Qwen held-out.** Established (Qwen): BundleS (C1+C2+C4+C7), excluding the answer-bearing C6, suffices on 0009 and generalizes to a pre-frozen second hidden truth.
   - **R3 — DeepSeek cross-model.** Negative/unresolved: BundleS benefit not established under exact counterbalancing (tie); DeepSeek axis-binding variance unrelated to the schema/contract bundle.
   - **R4 — Component decomposition (Qwen).** Directional→unresolved: Schema > Contract (directional); C1 does not eliminate axis errors (refutes a prior hypothesis); neither C2-only nor C4-only reproduces the C24 pattern; the in-window C24 bridge fails its replication threshold → **C2×C4 interaction unresolved**.
   - **R5 — Reliability (descriptive).** Transport 2-dim (terminal vs recovered); confidence/abstention descriptive, not calibration.
5. **Discussion.** Model-contingent mechanisms; the difference between a bundle-level effect (R1, robust) and a component-level mechanism (R4, Qwen-scoped and unresolved); why the C2×C4 question needs a same-window 2×2; what "not established ≠ refuted" means for the field.
6. **Threats to validity** (the 8 from the synthesis: small k; sequential adaptive development; model/provider specificity; one task family; uncontrolled sampling seeds; cross-window comparisons; incomplete FINISH; unresolved dev-workspace writer).
7. **Infrastructure contributions** (the §4 list; emphasize the integrity guard + custody as reproducibility infrastructure).
8. **Conclusion.** Verbatim headline: the C2×C4 joint-effect hypothesis is unresolved; no stable super-additive interaction, irreducible bundle mechanism, or reliable minimal axis-stabilization component is established.
9. **Declared next step (not executed).** A preregistered same-window 2×2 (Base, C2, C4, C2+C4) with fixed n and exact counterbalancing, behind a new review + the integrity guard.

---

## 2. Claim–Evidence Matrix

Status legend: **E** = Established · **D** = Directional / model-scoped · **U** = Unresolved · **N** = Negative (clean). Each row cites the phase + report + the decisive numbers.

| # | Claim | Status | Supporting evidence | Against / caveat |
|---|---|---|---|---|
| 1 | Non-streaming transport censors thinking-model long reasoning; SSE streaming resolves it. | **E** | Phase-4V: apparent Qwen "failures" were transport-invalid under non-streaming urllib+120s; SSE (`EDA_BENCH_STREAM_RESPONSES=1`, `e1c36d2`) made them terminal-valid. `reports/synthetic_p14_qwen_0009_stream_anchor` | Provider-specific transport; convention, not a model-capability claim. |
| 2 | The full clarity bundle suppresses semantic-binding failures on the controlled 0009/0010 pair. | **E** | Qwen anchor over SSE; DeepSeek 0/3 → 3/3 (Phase-4U/4V); `reports/synthetic_p14_balanced_controlled_pair`, `..._qwen_0009_*` | Bundle-level only (see #3–#7 for components); controlled pair, one task design. |
| 3 | The operative non-answer mechanism is the schema/contract bundle BundleS (C1+C2+C4+C7), not decoy-disambiguation (C3/C5) and not only the answer-bearing C6. | **E (Qwen)** | Phase-4W Run-1 (C6 sufficient but answer-bearing → disclosure, not inference-aid); Run-2 BundleS 3/3 vs BundleD 1/3 on 0009; `..._phase4w_run1/run2` | Qwen only; 0009 only at this stage. |
| 4 | BundleS generalizes to a pre-frozen second hidden truth. | **E (Qwen)** | Phase-4W held-out: 0017 (0011+BundleS) 3/3 binding AND artifact vs Base 0011 1/3; `..._phase4w_heldout` | Qwen only; one held-out family; revealed a new value-selection failure mode. |
| 5 | BundleS benefit is established for DeepSeek. | **N** | Phase-4X Stage 1C: Base 3/4 = BundleS 3/4 (tie, exact counterbalance); both failures axis_binding_failure; `..._phase4x_stage1c` | Stage 1 uninterpretable (position anomaly); "not established," not refuted. |
| 6 | Recovered transport degradation causes binding failures. | **N (clean)** | Phase-4X Stage 1C/1B: episodes WITH recovered degradation were terminally valid AND correct; failing episodes had ZERO recovered degradation; `..._phase4x_stage1b/1c` | DeepSeek session-window specific; a correlate, not a cause. |
| 7 | Artifact correctness, semantic binding, protocol completion, transport reliability are distinct dimensions that must be reported separately. | **E** | Throughout: e.g., correctly-bound episodes scoring 0.20 on artifact (evidence-regen/task-wall) but binding-correct; recovered≠terminal. Standardized 4-dim convention. | Convention/methodology, not a model claim. |
| 8 | Schema (C1+C2+C4) has a directional advantage over Contract (C7) in Qwen. | **D** | Phase-4Y Stage-1 typed-binding + failure-subtype shift; `..._phase4y_stage1` | k=3; directional localization signal, not a component-effect verdict. |
| 9 | C1 (canonical labels + disjoint-axis declaration) specifically eliminates axis-binding errors. | **N** | Phase-4Y Stage-2: C1 2/4 with 2 axis_binding_failure (refuted); C24 (C2+C4) 3/4 with 0 axis; `..._phase4y2_stage2` | Prior hypothesis, now refuted. |
| 10 | A single non-answer component (C1, C2, C4, or C7) is a reliable minimal axis-stabilization route. | **N/U** | Phase-4Y Stage-3: C2-only 1/4 (3 axis), C4-only 0/4 (3 axis); `..._phase4y3_stage3` | k=4; no singleton reproduces C24's axis suppression. |
| 11 | The C24 (C2+C4) axis-stabilization pattern replicates across run windows. | **N** | C24 bridge: in-window 2/4, 1 axis → predeclared `not_established`; `..._phase4y3_c24_bridge` | Cross-run Stage-2 C24 was 3/4 + 0 axis; did not replicate. |
| 12 | A stable C2×C4 super-additive interaction / irreducible bundle mechanism exists. | **U** | Stage-3 `both_weak` + bridge `not_established`; neither singleton reproduces C24 AND the C24 reference itself did not replicate | Not refuted either; unresolved. Requires a same-window 2×2 (Base/C2/C4/C2+C4) to resolve. |
| 13 | DeepSeek's residual axis-binding variance is reduced by the schema/contract bundle. | **N/U** | Phase-4X Stage 1/1C: axis_binding_failure recurs regardless of bundle; `..._phase4x_*` | Lever unknown (not C1/C2/C4/C7). |
| 14 | Confidence elicitation yields calibrated probability. | **U (descriptive)** | High-confidence-correct and overconfident-wrong co-occur; abstention uneven; Phase-4Y reliability rows | Descriptive only, not calibration evidence. |
| 15 | The integrity guard + isolated-worktree execution protects canonical-task integrity for paid runs. | **E (infra)** | `scripts/canonical_integrity.py` + `run_chain_guarded.py` (`d8fb7bd`); C24 bridge ran 0 incidents under per-episode verification; regression tests | The dev-workspace external writer is mitigated, not root-caused. |

### How to use this matrix

- **Claim 1, 2, 7, 15** may be stated as established (with their scope caveats).
- **Claims 3, 4** are established **for Qwen only**; always scoped, never "the bundle works."
- **Claims 5, 6, 9, 11** are clean negatives — state them as such.
- **Claims 8** is directional; phrase as "a directional signal, not a verdict."
- **Claims 10, 12, 13, 14** are unresolved/descriptive — never present as findings. Claim 12 (the C2×C4 interaction) is the headline unresolved question and requires the declared 2×2 to address.
- **No claim** may outrun its row. If a reviewer asks "does the bundle work for DeepSeek," the answer is row 5 (not established), not row 2.

---

## 3. Declared (not-executed) next experiment

A future attempt to identify a C2×C4 interaction would require a **newly preregistered, same-window 2×2 design** with all four cells — **Base, C2, C4, C2+C4** — fixed sample sizes, exact counterbalancing, and a new pre-run review, executed under the canonical-tree integrity guard. This is stated as a prerequisite, **not executed** in this program. No opportunistic k-escalation on C24/C2/C4; held-out-family-2 remains untouched.
