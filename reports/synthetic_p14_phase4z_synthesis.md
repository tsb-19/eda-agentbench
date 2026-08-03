# Phase-4Z — Consolidated Evidence Synthesis (p14 workflow-handoff clarity-bundle program)

**Date:** 2026-08-03 · **Branch:** synthetic-phase0a · **Status:** docs-only synthesis, no paid model calls, stopped for review (no push)
**Scope:** consolidates Phase-4V (0009/0010 controlled pair + streaming), Phase-4W (clarity-bundle ablation: Run-1, Run-2, held-out), Phase-4X (DeepSeek cross-model: Stage 1, 1B, 1C), Phase-4Y (decomposition: Stage 1, 2, 3), and the C24 bridge. Model: Qwen3.7-Max (primary) + DeepSeek-V4-Pro (cross-model). One synthetic task family (p14 workflow-handoff).

## Headline scientific conclusion

Stage 3 showed that neither C2-only nor C4-only reproduced the earlier C24 axis-stabilization pattern. However, the independently collected C24 bridge also failed its predeclared replication threshold. The evidence therefore leaves a C2×C4 joint-effect hypothesis **unresolved**; it does not establish a stable super-additive interaction, an irreducible bundle mechanism, or a reliable minimal axis-stabilization component.

## 1. Established findings

1. **Non-streaming long-reasoning censoring was resolved by SSE streaming.** Non-streaming urllib with a 120s inactivity timeout censored thinking models mid-reasoning (apparent "failures" were transport-invalid). Opt-in SSE streaming (`EDA_BENCH_STREAM_RESPONSES=1`, commit `e1c36d2`) separates reasoning time from content delivery; transport validity must be verified before classifying a model response as a capability result. *(Phase-4V; [[llm-streaming-transport-censoring]])*
2. **The full clarity bundle suppressed semantic-binding failures on the controlled pair for Qwen and DeepSeek.** On the 0009 (ambiguous) → 0010 (clear) controlled pair — identical hidden truth and grader, differing only in the visible clarity bundle — the full bundle suppressed the wrong-axis binding failure for both models (Qwen anchor over SSE; DeepSeek 0/3 → 3/3, Phase-4U/4V). This is a bundle-level effect on the controlled pair, established for both providers.
3. **The non-answer-bearing BundleS route was localized and confirmed on a pre-frozen Qwen held-out family.** Phase-4W Run-2 isolated the operative non-answer mechanism to the schema/contract components BundleS = C1 (canonical labels + disjoint-typed-axes declaration) + C2 (PVT-def) + C4 (glossary) + C7 (contract wording): BundleS 3/3 vs decoy BundleD (C3/C5) 1/3 on 0009. Phase-4W held-out confirmed generalization on a pre-frozen second hidden truth (0017 = 0011 + BundleS: 3/3 binding AND artifact vs Base 0011 1/3). BundleS excludes the answer-bearing C6, so this is an inference-aid route, not answer-disclosure. *(Qwen-scoped.)*
4. **The BundleS benefit was not established for DeepSeek under exact counterbalancing.** Phase-4X Stage 1C (DeepSeek, exact-counterbalanced k=4) returned Base 3/4 = BundleS 3/4 (tie; no BundleS improvement), with both failures `axis_binding_failure`. Stage 1 was uninterpretable (position anomaly); Stage 1B audited and refuted cold-start/client-state hypotheses. Across Stage 1 + 1C the DeepSeek development effect is **not established and not refuted**. A clean negative was established: recovered transport degradation does **not** cause binding failures.
5. **Artifact correctness, semantic binding, protocol completion, and transport reliability are distinct evaluation dimensions.** Conflating them masked real signal (e.g., a correctly-bound episode that hit the task wall before evidence regen scores 0.20 on artifact but is binding-correct; a recovered transport degradation is not a terminal failure). The program standardized a 4-dimension reporting convention and a failure taxonomy: parent `semantic_binding_failure` ⊃ {`axis_binding_failure` (value on the wrong typed axis), `role_conditioned_value_selection_failure` (type-valid, wrong value)} — never collapsed into "wrong-axis."

## 2. Directional or model-scoped findings

1. **BundleS is a model-contingent mechanism candidate** with Qwen development (0009) and held-out (0011/0017) support, but no DeepSeek establishment. It must never be presented as a model-robust harness fix.
2. **Schema showed a directional advantage over Contract in Qwen.** Phase-4Y Stage-1 (Schema = C1+C2+C4 vs Contract = C7): a directional mechanistic-localization signal (typed-binding correctness + failure-subtype shift), Qwen only, k=3 — directional, not a component-effect verdict.
3. **C24 showed a directional failure-subtype shift in one Stage-2 window.** Stage-2 C24 (0021, C2+C4) returned 3/4 correct with 0 axis-binding failures (vs C1 2/4 with 2 axis failures). This was the cross-run reference for Stage-3 — and it **did not replicate in-window** (C24 bridge 2/4, 1 axis), so the shift is window-specific, not stable.

## 3. Unresolved or negative findings

1. **No stable minimal C1, C2, C4, or C7 component was identified.** Stage-2 refuted "C1 eliminates axis errors" (C1 2/4, 2 axis). Stage-3 (C2-only 1/4 with 3 axis; C4-only 0/4 with 3 axis) showed neither singleton reproduces C24's axis suppression. No individual non-answer component is a reliable minimal axis-stabilization route at k=4.
2. **C2×C4 interaction was not confirmed by the bridge.** The in-window C24 bridge (2/4, 1 axis) failed its predeclared ≥3/4 + 0-axis replication threshold → `not_established`. Combined with Stage-3's `both_weak`, the C2×C4 joint-effect hypothesis is **unresolved** (not identified, not refuted).
3. **DeepSeek showed residual trajectory variance with no detectable BundleS benefit.** Recurring `axis_binding_failure` (func/slow, and a setup/slow cross-axis value) regardless of the schema/contract bundle; the lever for DeepSeek is unknown (not C1/C2/C4/C7).
4. **Confidence observations remain descriptive rather than calibration evidence.** High-confidence-correct and overconfident-wrong episodes co-occur at these n; abstention is uneven. Reported as descriptive reliability signal only, not a calibrated confidence result.

## 4. Infrastructure and methodology contributions

1. **SSE reasoning/content separation** — streaming opt-in that makes thinking-model responses transport-valid (`EDA_BENCH_STREAM_RESPONSES`).
2. **Terminal validity versus recovered degradation** — two independent transport dimensions; recovered degradation never replaces a terminally-valid episode and is reported separately.
3. **Committed sample-membership arbiter** — `episode_arbiter.py` is the sole membership authority; generalized rule: all code capable of changing primary-sample membership is implemented/tested/committed/hashed in the pre-run freeze before the first paid episode.
4. **Exact counterbalancing and blocked randomization** — seeded, frozen, predeclared; position balance asserted.
5. **Health sentinel and full-path PT measurement control** — Level-1 b04/PT sentinel + Level-2 full-path check (fixed reference through the full PT path) + score-independent block measurement-control (full-path check → candidate subset → full-path check; admissible iff both bookends healthy).
6. **Durable executor state** — `chain_executor` writes atomic RUNNING/COMPLETE/FAILED(/FAILED_INTEGRITY) run-state; orchestration metadata only, never read by membership logic.
7. **Canonical-tree integrity protection and evidence custody** — the canonical-tree integrity guard (commit `d8fb7bd`): exact-commit isolated-worktree execution, frozen SHA-256 manifests, canonical non-writable during runs, per-episode + post-chain verification, atomic `FAILED_INTEGRITY` stop with a sanitized incident sidecar, no silent restore; sanitized per-trial evidence + byte-match custody.

## 5. Threats to validity

1. **Small k per cell** (typically k=3–4). Differences of one episode are within run-to-run variance for a thinking model at temperature 0.7; this is why the program uses predeclared thresholds and reports counts, not inferential rates, at these n.
2. **Sequential adaptive development.** Stages were designed and gated sequentially using prior results (e.g., the C24 bridge was added to test a cross-run reference); this is disclosed but limits the strength of any single contrast.
3. **Model/provider specificity.** Primary model Qwen3.7-Max via one gateway; DeepSeek is the only cross-model check. No claim generalizes across providers beyond what Phase-4X established (which, for BundleS, is "not established").
4. **One synthetic task family.** p14 workflow-handoff only; a single task design (semantic role binding over typed axes). Generalization beyond this family is not tested.
5. **Uncontrolled provider sampling seeds.** The gateway's sampling seed is not fixed by us; temperature is set (0.7) but the provider may inject undetermined variance.
6. **Cross-window comparisons.** Several contrasts (notably the Stage-3 singletons vs the Stage-2 C24 reference) compare across run windows; the C24 bridge showed the reference itself is not stable across windows.
7. **Incomplete FINISH behavior.** Many episodes terminate via task-wall or action-cap rather than a voluntary finish; protocol-completion is reported as a descriptive dimension, not an outcome.
8. **Unresolved external writer in the development workspace.** An unidentified process repeatedly mutated the frozen 0009 golden (`solution/flow_config.json` → `{}`) in the development workspace. It is mitigated (canonical-tree integrity guard for runs; the guard's worktree is isolated) but not root-caused. The development workspace is treated as non-authoritative (see §6).

## 6. Mandatory experiment infrastructure (going forward)

The canonical-tree integrity guard is **mandatory**. All future fairness gates, paid runs, evidence extraction, and custody verification must execute from an **exact-commit integrity-guarded isolated worktree** (`scripts/run_chain_guarded.py`). The repeatedly-modified root development workspace is **non-authoritative** — a development convenience only. `chmod 444` on the 0009 golden is retained as defense-in-depth, not as the authoritative control (the guard is).

## 7. Preserved assets & not-executed next steps

- **Held-out-family-2 (0024–0027, fast/lowpower golden) is preserved as an untouched future-replication asset.** It is not run, not altered, and no variant is selected based on existing outcomes. The C24 bridge's `not_established` verdict means it is not consumed.
- **No opportunistic k-escalation** on C24, C2, or C4 is performed.
- **A future attempt to identify a C2×C4 interaction** would require a newly **preregistered, same-window 2×2 design containing all four cells — Base, C2, C4, C2+C4 — with fixed sample sizes, exact counterbalancing, and a new pre-run review.** This is described as a prerequisite, **not executed** in this program.

## Provenance

Findings trace to: `reports/synthetic_p14_phase4w_run1{,.json}`, `..._phase4w_run2{,.json}`, `..._phase4w_heldout{,.json}`, `..._phase4x_dev{,.json}`, `..._phase4x_stage1b{,.json}`, `..._phase4x_stage1c{,.json}`, `..._phase4y_stage1{,.json}`, `..._phase4y2_stage2{,.json}`, `..._phase4y3_stage3{,.json}`, `..._phase4y3_c24_bridge{,.json}`; evidence under `reports/evidence/p14_phase4*`; guard under `scripts/canonical_integrity.py` + `scripts/run_chain_guarded.py` (commit `d8fb7bd`). No paid model calls in this synthesis.
