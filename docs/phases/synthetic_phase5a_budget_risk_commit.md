# Phase-5A — Budget Table, Risk Register, and Commit Sequence (deliverables 4 + 6 + 7)

**Date:** 2026-08-03 · **Branch:** `synthetic-phase0a` · **Status:** design-only, no paid calls, no implementation, stopped for review (no push).
**Companion:** `…design.md` (master), `…family_specs.md` (2), `…generator_grader_plans.md` (3), `reports/synthetic_phase5a_design.json`.

## 4. Budget table

Per-episode rate is **derived from committed Phase-4 ledgers** (not hand-copied): combined mean **¥11.72/episode** (Qwen ¥12.04 n=16; DeepSeek ¥11.09 n=8), cross-checked against the Phase-4Z freeze-manifest total ¥682.25 / 62 billable episodes = ¥11.00/ep (manifest-authoritative). Episode parameters are the established p14 streaming profile (SSE, inactivity 120 s, hard deadline 300 s, max 1 retry, max-actions 60, timeout 1800 s, temp 0.7, elicit-confidence).

| Component | Episodes | Rate (¥/ep) | Subtotal (¥) | Notes |
|---|---|---|---|---|
| Core primary (Base + BundleS) | **48** | 11.72 | **≈ 562.6** | 2 fam × 3 inst × 2 model × 2 cond × 2 rep |
| — sensitivity at low rate | 48 | 11.00 | 528.0 | manifest-rate floor |
| — sensitivity at high rate | 48 | 12.04 | 577.9 | Qwen-rate ceiling |
| Dev/debug pilot (excluded from analysis) | ~8 | 11.72 | ≈ 93.8 | 2 fam × ~4 ep; smoke golden + wrong-binding feasibility |
| Fairness-gate / arbiter exclusions (budgeted) | ~4 | 11.72 | ≈ 46.9 | measurement-invalid replacements (terminal transport / tool health), per arbiter |
| **Phase-5B core + pilot + exclusions** | **~60** | — | **≈ 703** | the binding Phase-5B scope |
| Secondary TypedContract extension | **24** | 11.72 | ≈ 281.3 | **separately authorized**; NOT executed in Phase-5A or core Phase-5B |
| **All-in (core + secondary)** | ~84 | — | **≈ 984** | if secondary is later authorized |

**Committed-to-date (last known):** Phase-4Z freeze manifest records **¥682.25** for the p14 program (58 primary + 3 excluded + 0 invalid + 1 aborted).

**Budget gate (committed-ledger binding):** the committed ledger is the binding source unless a newer balance is supplied. Phase-4Z committed ¥682.25 of ¥1000 ⇒ **≈ ¥318 remaining**. Under that balance:
- **Binding core = Qwen3.7-Max only, 24 primary episodes** (2 fam × 3 inst × Base+BundleS × 2 reps ≈ **¥282**, fits). Within-task stochastic replication (2 reps) is **preserved**; only the model dimension is cut. This directly tests whether the established **Qwen** BundleS effect generalizes across the two independent families.
- The **full 48-episode** variant (Qwen + DeepSeek ≈ ¥563) is **pre-frozen** and selected **only if ≥ ¥650–700 usable** is confirmed at the next review.
- The **two-model / one-repetition fallback is NOT used** (per directive).
- **DeepSeek** is kept as a **separately-frozen 24-episode extension run across ALL tasks** (≈ ¥281; never selectively on favorable families), authorized later.
- Both core schedules + the DeepSeek extension are **pre-frozen this phase**; **none executed** (no paid calls in Phase-5B). The next review selects Qwen-24 vs full-48 by the actual balance.

No paid call occurs in Phase-5B regardless; all figures are projections from the committed per-episode rate.

## 6. Risk register

| # | Risk | Impact | Likelihood | Mitigation / gate |
|---|---|---|---|---|
| R1 | **Budget shortfall** (full core-48 ≈ ¥563 > committed-ledger remaining ≈ ¥318) | blocks the full two-model core | Med-High | **committed-ledger binding ⇒ Qwen-only 24-ep core (≈¥282, fits)**; full-48 pre-frozen and selected only if ≥¥650–700 confirmed at review; two-model/one-rep fallback NOT used; DeepSeek-24 separately-frozen all-tasks extension; both schedules pre-frozen, none executed. |
| R2 | **Hard feasibility fails** for a generated instance (wrong binding is tool-red / unparsable / NaN / obvious, or not rejected by the grader) | instance ineligible | Med | **hard-feasibility gate (5 criteria)** inside `bake_golden`: wrong binding must be tool-syntax-accepted, execute, produce a plausible signoff/number, remain semantically incorrect, AND be rejected by the typed grader; else regenerate (fail-closed). |
| R3 | **Independence audit failure** (accidental reuse of p14 signature) | undermines external-validity claim | Low | committed/hashed `scripts/phase5a_independence_check.py` (no `grade_workflow` import; disjoint vocab; no `axis_schema` keys) — fail-closed at freeze. |
| R4 | **Semantic-diff audit failure** (BundleS/TypedContract discloses golden) | invalidates a condition contrast | Low-Med | per-(family,instance,condition) `semantic_diff_audit.json`; fail-closed regenerate at freeze. |
| R5 | **New HSPICE fairness gate** (Family B) introduces a measurement-control gap | masking/distortion of B results | Med | clone of the proven PT sentinel/fullpath pattern; smoke against a known-good and known-wrong tuple before any paid episode; golden must =1.0, wrong-tuple must measure-plausible. |
| R6 | **Small n=3 instances/family** | low power; one-instance swings within variance | High (by design) | **task instance is the primary unit; reps are nested observations, not independent instances**; primary = instance-level paired Base-vs-BundleS + family raw counts; bootstrap-over-3 is **descriptive only** (no bootstrap p-value headline); **no pooled trajectory-level test**; **no precise population-level success rate claimed**. |
| R7 | **External-validity confound** (families resemble p14 in some unaccounted way) | over-claim generalization | Med | 5-dimension independence audit + mechanical independence-check; report family-specific effects separately; label claims by family. |
| R8 | **Transport censoring** (non-streaming / thinking-model long reasoning) | false capability failures | Low (mitigated) | SSE streaming mandatory; terminal_valid vs recovered two-dimension telemetry; measurement-invalid episodes replaced, valid-wrong = hard fail. |
| R9 | **Source-tree integrity** (the recurring external writer in the dev workspace) | run contamination | Med (recurring) | mandatory exact-commit isolated worktree; `cig.verify` pre/post; `FAILED_INTEGRITY` stop; dev workspace non-authoritative. |
| R10 | **Provider sampling-seed variance** (Qwen/DeepSeek non-determinism at temp 0.7) | run-to-run noise | High | 2 reps; exact-counterbalanced blocked randomization; never claim a rate from k≤3; report counts + intervals. |
| R11 | **Secondary (TypedContract) mis-timed** | scope creep / budget over-run | Med | secondary is **separately authorized**, not executed in Phase-5A or core Phase-5B; 24-ep budget ring-fenced. |
| R12 | **Provider/tool outage on b04** (PT or HSPICE) | block inadmissible | Med | per-block L1 sentinel + L2 fullpath bookends; block inadmissible if either fails; rerun in a later healthy window; outages recorded, not silently retried. |
| R13 | **b04 SPICE calibration drift** (`.lib`/model differences) | wrong-tuple number leaves plausible range | Low | per-instance `plausible_range` baked from the real tool at generation; recalibrate if drift detected at sentinel. |

## 7. Proposed commit sequence

### 7a. Phase-5A (this phase) — docs-only, no paid calls
1. `docs(phase5a): cross-family external-validity design + predeclared analysis plan` (`synthetic_phase5a_design.md`) + `reports/synthetic_phase5a_design.json` (machine-readable predeclared design).
2. `docs(phase5a): Family A & B task specifications + independence audit` (`synthetic_phase5a_family_specs.md`).
3. `docs(phase5a): generator, grader, and fairness-gate plans` (`synthetic_phase5a_generator_grader_plans.md`).
4. `docs(phase5a): budget table, risk register, commit sequence` (this doc).

(All docs-only; clean tree asserted; **no push**.)

### 7b. Phase-5B (separately authorized; NOT executed in Phase-5A) — gated by budget confirmation (R1) + review
5. `feat(phase5b): Family A generator + grader + evaluator + dev instance` (`p15_sta_handoff`).
6. `feat(phase5b): Family B generator + grader + evaluator + dev instance` (`p16_spice_handoff`).
7. `feat(phase5b): hspice_health_sentinel + SPICE fullpath check` (+ re-point PT gate for A).
8. `feat(phase5b): phase5a_independence_check + semantic-diff audit wiring` (+ tests).
9. `chore(phase5b): smoke both dev instances on b04` (golden=1.0; wrong-binding-green / wrong-tuple-plausible; the fairness fairness-gate analogue).
10. `feat(phase5b): freeze scripts + manifests (cig.freeze) for the 3×2 eval instances` (+ `randomization_manifest`, `frozen_config`, `interpretation_table`, `membership_code_manifest`, `prerun_freeze_manifest`, `canonical_integrity_manifest`).
11. `feat(phase5b): analysis code` (instance-resampling bootstrap; paired Base-vs-BundleS tables; six-dimension separation for B; family/model/interaction descriptive tables) — committed/hashed **before** the first paid episode.
12. `chore(phase5b): pre-run review freeze` (clean tree, `cig.verify`, fairness gates healthy, budget confirmed).
13. `feat(phase5b): guarded execution` (48 core episodes via `run_chain_guarded.py` under the integrity guard) → pipeline + custody → report.
14. *(further, separately authorized)* `feat(phase5b-ext): TypedContract secondary` (24 episodes).

### 7c. Invariants across the sequence
- Separate, topical commits; docs-only for Phase-5A; no push at any step.
- All membership/fairness/integrity code committed and hashed in the pre-run freeze before the first paid episode (step 12 precedes step 13).
- The instance set, wording, and k are frozen at step 12; no change after the first model result (step 13).
- Held-out-family-2 (p14 0024–0027) untouched; no existing p14 task/report modified.
