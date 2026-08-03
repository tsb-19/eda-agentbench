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

**Budget gate (binding, must be resolved at review):** the Phase-5B **core + pilot ≈ ¥703** (core-48 alone ≈ ¥563) must be **confirmed against the current account balance** before any paid call.
- If the program budget is the **original ¥1000** baseline (memory: `baseline-models-and-budget`), remaining after Phase-4Z ≈ **¥318**, and the core-48 **does not fit** (shortfall ≈ ¥245; core+pilot shortfall ≈ ¥385).
- This is a **budget decision for the user**, not an automatic scope cut. Per the no-adaptive-k rule, **no k reduction is made opportunistically**; the predeclared 2-rep / 48-episode design is the registered intent. If the user confirms a lower ceiling, the registered fallback is **1 rep / 24 episodes ≈ ¥282** (fits within ¥318), with the 2-rep design retained as the declared intent — but this requires explicit re-review and re-freeze, not a mid-run cut.
- If additional budget is confirmed, the full ¥703 core + ¥281 secondary proceeds as predeclared.

The budget table is therefore **honest about a likely shortfall under the original cap** and makes the gate explicit. No paid call occurs in Phase-5A regardless.

## 6. Risk register

| # | Risk | Impact | Likelihood | Mitigation / gate |
|---|---|---|---|---|
| R1 | **Budget shortfall** (core-48 ≈ ¥563 > remaining ≈ ¥318 under original cap) | blocks the predeclared core | Med-High | **#1 GO/NO-GO gate**: confirm current balance at review; if capped, fall back to 1-rep/24 only via explicit re-review; never auto-k-cut. |
| R2 | **Tool-success-≠-semantic fails to hold** for a generated instance (wrong binding causes a violation / implausible number) | instance invalidates the core property | Low (baked per-instance evidence proves it) | per-instance real-tool `wrong_binding_signoff.rpt` (A) / `wrong_tuple_measure.lis` (B); instance rejected at freeze if property fails. |
| R3 | **Independence audit failure** (accidental reuse of p14 signature) | undermines external-validity claim | Low | committed/hashed `scripts/phase5a_independence_check.py` (no `grade_workflow` import; disjoint vocab; no `axis_schema` keys) — fail-closed at freeze. |
| R4 | **Semantic-diff audit failure** (BundleS/TypedContract discloses golden) | invalidates a condition contrast | Low-Med | per-(family,instance,condition) `semantic_diff_audit.json`; fail-closed regenerate at freeze. |
| R5 | **New HSPICE fairness gate** (Family B) introduces a measurement-control gap | masking/distortion of B results | Med | clone of the proven PT sentinel/fullpath pattern; smoke against a known-good and known-wrong tuple before any paid episode; golden must =1.0, wrong-tuple must measure-plausible. |
| R6 | **Small n=3 instances/family** | low power; one-episode/one-instance swings within variance | High (by design) | instance is the unit; primary is paired direction + counts + bootstrap-over-instances; no pooled-episode significance as primary; predeclared thresholds. |
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
