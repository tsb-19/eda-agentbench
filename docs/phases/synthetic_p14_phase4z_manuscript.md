# Harness Information Structure and Model-Contingent Semantic Execution: A Controlled Decomposition of a Workflow-Handoff EDA Task

**Manuscript v0** · 2026-08-03 · branch `synthetic-phase0a` · **source of truth: `docs/synthetic_p14_phase4z_paper_outline.md` (15-row claim–evidence matrix).** Where prose and the matrix disagree, the matrix is authoritative. No claim below is absent from the matrix.

> **Scope note (this is not a harness-leaderboard paper).** This paper does not propose a higher-scoring harness. It studies **how harness information structure changes semantic execution behavior** on a controlled task, shows that the resulting effects can be **model-contingent**, and argues that **benchmark measurement validity** depends on transport, sampling-membership, tool health, termination, orchestration, and artifact integrity — each reported as an independent dimension.

## Abstract

We study a workflow-handoff task in which an agent must bind a timing signoff to a canonical (scenario, corner) role from heterogeneous, role-misleading evidence (PVT descriptors, role-swapped timing reports, stale decoys). On a controlled pair — identical hidden truth and grader, differing only in a visible "clarity bundle" — the full bundle suppresses a semantic-axis binding failure for both Qwen3.7-Max and DeepSeek-V4-Pro (confirmatory; Tier 1). Decomposing the bundle, a non-answer-bearing schema/contract subset (BundleS) suffices on the development pair and generalizes to a pre-frozen held-out family for Qwen (frozen held-out confirmation; Tier 2), but its benefit is **not established** for DeepSeek under exact counterbalancing (null). A further component decomposition (Qwen) finds no stable minimal component: C1 does not eliminate axis errors, neither C2-only nor C4-only reproduces the bundle pattern, and an independently collected in-window bridge of the C2+C4 bundle **failed its predeclared replication threshold** (null/inconclusive replication). The C2×C4 joint-effect hypothesis therefore remains **unresolved** (unresolved component attribution; Tier 3). We report four orthogonal evaluation dimensions and a seven-layer reliability accounting, and we introduce a canonical-tree integrity guard that runs every paid episode from an exact-commit isolated worktree. The contribution is a measurement-valid decomposition showing a bundle-level effect that is model-contingent and an unresolved component-interaction question — not a minimal mechanism.

## 1. Introduction

EDA agent benchmarks increasingly evaluate multi-artifact workflows where the agent must reconcile conflicting, role-misleading evidence rather than search for a single fault. A natural question is whether **harness-level information structure** — how a task presents its evidence and disambiguating context — changes the *semantic* execution behavior of a frontier model, and whether any such effect is a property of the model or of the task. This is distinct from asking whether a harness scores higher.

We ask three questions on a controlled workflow-handoff family (p14):
- **Q1.** Does the full clarity bundle change semantic-binding behavior on the controlled pair, and for whom?
- **Q2.** Is the effect answer-disclosure or inference-aid, and does it generalize off the development pair?
- **Q3.** Which component(s) carry it, and is the effect model-robust?

We deliberately separate three claim tiers that are easy to conflate: (1) the **full clarity bundle** (the original clear condition, including an answer-bearing component); (2) the **non-answer BundleS** (excluding the answer-bearing component); and (3) **minimal components** (individual non-answer components and their interactions). The central negative result lives in Tier 3: no minimal component or two-component bundle is established as a stable mechanism.

## 2. Task and grader

The p14 workflow-handoff task presents a handoff: prior timing signoff artifacts (a stale signoff log, role-swapped reports A/B/C, a PVT-descriptor report, a decoy evidence chain) that each *characterize* but never *correctly name* the canonical signoff pair. The agent edits a `flow_config.json` to bind a `scenario` ∈ {slow, typ, fast} and `corner` ∈ {func, test, lowpower}. The controlled pair is 0009 (ambiguous evidence) vs 0010 (the same task plus a "clarity bundle" of seven components C1–C7), with **identical hidden truth and grader**; they differ only in visible content.

The grader is execution-based (real PrimeTime via a remote b04 shim): a typed-binding oracle checks the (scenario, corner, netlist) tuple against the hidden truth, and an 8-component score (signoff, final_state, evidence_generation, stage_chain, provenance, authority_consistency, hazard_recovery, explanation) measures artifact correctness. We report **four orthogonal dimensions**: semantic binding (the (scenario,corner) tuple), artifact correctness (total score), protocol completion (voluntary FINISH), and transport reliability. Failures use a two-subtype taxonomy: `semantic_binding_failure/axis_binding_failure` (a value placed on the wrong typed axis, e.g. func/slow) and `.../role_conditioned_value_selection_failure` (type-valid slots, wrong value, e.g. typ/func).

## 3. Methods

**Models & transport.** Qwen3.7-Max (primary) and DeepSeek-V4-Pro (cross-model) via one gateway, SSE streaming (`EDA_BENCH_STREAM_RESPONSES=1`; per-operation inactivity timeout 120 s, hard deadline 300 s, max 1 retry). We first establish (Phase-4V) that **non-streaming transport censors thinking-model long reasoning** — apparent "failures" were transport-invalid — so streaming is a measurement prerequisite, not a harness choice.

**Design.** Each phase uses a predeclared interpretation table, seeded exact-counterbalanced blocked randomization (frozen pre-run), and a real-PrimeTime fairness gate with score-independent block measurement-control (Level-1 b04/PT sentinel + Level-2 full-path check; a block is admissible only if both bookend checks are healthy; a valid but unfavorable score is a hard failure, never retried). Sample sizes are small (k=3–4 per cell) by design and budget; we report counts, not inferential rates.

**Integrity.** Every paid episode in the program's final stage (the C24 bridge) executed under a **canonical-tree integrity guard** from an exact-commit isolated git worktree: frozen SHA-256 manifests of canonical task trees, graders, generators, membership code, and evidence inputs; canonical directories non-writable during the run; hashes verified pre-run, after every episode, and post-chain; any mutation atomically marks the run `FAILED_INTEGRITY` and stops, with a sanitized incident sidecar and no silent restore. The repeatedly-modified development workspace is treated as non-authoritative; `chmod 444` is defense-in-depth only.

**Membership.** A committed `episode_arbiter` is the sole membership authority; all code capable of changing primary-sample membership is implemented, tested, committed, and hashed in the pre-run freeze before the first paid episode.

## 4. Results

Numerical results are generated from committed report JSON and preserved episode ledgers (Table 2 / Figure 2–3 in `docs/synthetic_p14_phase4z_figures_tables.md`); nothing here is hand-copied.

### 4.1 Tier 1 — Full clarity bundle on the controlled pair *(confirmatory)*

The full bundle (0010, C1–C7 including the answer-bearing C6) suppressed the axis-binding failure on the controlled pair for **both** models: Qwen 0009 1/3 → 0010 3/3 (0 axis); DeepSeek 0009 0/3 (3 axis) → 0010 3/3 (0 axis) (matrix_2x2_k3). This is evidence for a **complete-bundle effect on the original pair**, not isolated cross-model evidence for BundleS (Tier 2) — the two tiers must not be conflated.

### 4.2 Tier 2 — Non-answer BundleS *(frozen held-out confirmation; null for DeepSeek)*

Excluding the answer-bearing C6, BundleS (C1+C2+C4+C7) suffices on the development pair: Phase-4W Run-2 BundleS 3/3 (0 axis) vs decoy-disambiguation BundleD (C3/C5) 1/3 (2 axis). The Phase-4W Run-1 C6 ablation showed C6 is sufficient but **answer-bearing**, so its effect is answer-disclosure, not inference-aid; the BundleS route is the non-answer mechanism. BundleS **generalizes** to a pre-frozen second hidden truth: held-out Base 0011 1/3 (1 axis) vs Held 0017 (= 0011 + BundleS) 3/3 (0 axis). *(Qwen only.)*

**DeepSeek (null).** Under exact counterbalancing (Phase-4X Stage 1C), Base 3/4 (1 axis) = BundleS 3/4 (1 axis): a tie, no BundleS improvement. Stage 1 was uninterpretable (a position anomaly), audited in Stage 1B (cold-start/client-state hypotheses refuted). Across Stage 1 + 1C, the DeepSeek effect is **not established and not refuted**. BundleS is therefore a **model-contingent mechanism candidate** (Qwen development + held-out support; no DeepSeek establishment) — never a model-robust harness fix. A clean negative was also established: recovered transport degradation does **not** cause binding failures.

### 4.3 Tier 3 — Minimal components *(sequential exploratory localization; null/inconclusive replication; unresolved attribution)*

Phase-4Y decomposes BundleS for Qwen:
- **Stage 1 (directional):** Schema (C1+C2+C4) 2/3 (0 axis, 1 value-selection) vs Contract (C7) 1/3 (2 axis) — a directional localization signal, not a component verdict.
- **Stage 2 (refutes a hypothesis):** C1-only 2/4 (2 axis) vs C24 (C2+C4) 3/4 (0 axis, 1 value-selection). C1 does **not** eliminate axis errors (a prior hypothesis is refuted).
- **Stage 3:** C2-only 1/4 (3 axis) vs C4-only 0/4 (3 axis, 1 value-selection). Neither singleton reproduces the C24 pattern.

The Stage-2/3 bundle reference (C24, 3/4, 0 axis) was cross-run. The **C24 bridge** re-measured C24 in-window under the integrity guard: **2/4 (1 axis, 1 value-selection)** — failing the predeclared ≥3/4 + 0-axis replication threshold (verdict `not_established`). 

**Unresolved attribution.** Stage 3 showed that neither C2-only nor C4-only reproduced the earlier C24 axis-stabilization pattern, and the independently collected C24 bridge also failed its predeclared replication threshold. The evidence therefore leaves a **C2×C4 joint-effect hypothesis unresolved**; it does not establish a stable super-additive interaction, an irreducible bundle mechanism, or a reliable minimal axis-stabilization component. We do **not** imply that C24 is a confirmed interaction or minimal mechanism.

### 4.4 Reliability dimensions *(descriptive)*

Across the program (Figure 3): the four evaluation dimensions are distinct — e.g., correctly-bound episodes can score below 1.0 on artifact (evidence-regen/task-wall after a correct binding), and recovered transport degradation is not terminal failure. Protocol completion (voluntary FINISH) is incomplete for many episodes (task-wall/action-cap terminations) and is descriptive. Confidence elicitation is descriptive only — high-confidence-correct and overconfident-wrong co-occur — not calibration evidence.

## 5. Discussion

The results separate cleanly into what is established and what is not. **Established:** a bundle-level effect on the controlled pair for both providers (Tier 1); a non-answer BundleS route for Qwen on development and held-out (Tier 2); and several measurement-validity infrastructure facts (streaming, two-dimension transport, the integrity guard). **Model-contingent:** BundleS helps Qwen but is not established for DeepSeek. **Unresolved:** no minimal component (C1, C2, C4, C7) is a stable mechanism, and the C2×C4 interaction is not confirmed — the in-window bridge failed to replicate the cross-run bundle reference.

The methodological lesson is that a bundle-level effect and a component-level mechanism are different objects, and that cross-window references are fragile: the C24 reference that motivated the Stage-3 decomposition did not replicate in-window, which is exactly why a same-window design is required to resolve the interaction. The measurement-validity dependencies (transport, sampling membership, tool health, termination, orchestration, artifact integrity) are not incidental — each can manufacture or mask a result, and we report them as independent layers rather than collapsing them into a single score.

## 6. Threats to validity

(1) Small k per cell (k=3–4); one-episode swings are within run-to-run variance at temperature 0.7 — hence predeclared thresholds and counts, not rates. (2) Sequential adaptive development — stages were gated on prior results (e.g., the bridge was added to test a cross-run reference), limiting the strength of any single contrast. (3) Model/provider specificity — Qwen primary, DeepSeek the only cross-model check. (4) One synthetic task family (p14 workflow-handoff). (5) Uncontrolled provider sampling seeds. (6) Cross-window comparisons — the C24 reference is itself not stable across windows. (7) Incomplete FINISH behavior. (8) An unresolved external writer in the development workspace (mitigated by the integrity guard for runs, not root-caused).

## 7. Infrastructure contributions

(1) SSE reasoning/content separation (transport validity for thinking models). (2) Terminal validity vs recovered degradation as two independent transport dimensions. (3) A committed sample-membership arbiter as the sole membership authority. (4) Exact counterbalancing and seeded blocked randomization, frozen pre-run. (5) Health sentinel + full-path PT measurement control + score-independent block measurement-control. (6) Durable executor state. (7) Canonical-tree integrity protection (isolated worktree, frozen hashes, non-writable canonical, per-episode verification, `FAILED_INTEGRITY` stop) and sanitized evidence custody with byte-match.

## 8. Conclusion

Stage 3 showed that neither C2-only nor C4-only reproduced the earlier C24 axis-stabilization pattern. However, the independently collected C24 bridge also failed its predeclared replication threshold. The evidence therefore leaves a C2×C4 joint-effect hypothesis **unresolved**; it does not establish a stable super-additive interaction, an irreducible bundle mechanism, or a reliable minimal axis-stabilization component. The bundle-level effect on the controlled pair is established for both providers; the non-answer BundleS mechanism is established for Qwen and is model-contingent; no minimal component or two-component bundle is established as a stable mechanism.

## 9. Future work (declared, not executed)

A future attempt to identify a C2×C4 interaction would require a **newly preregistered, same-window 2×2 design** containing all four cells — **Base, C2, C4, C2+C4** — with fixed sample sizes, exact counterbalancing, and a new pre-run review, executed under the canonical-tree integrity guard. This is a prerequisite, not an executed experiment. No opportunistic k-escalation on C24/C2/C4 is performed.

## 10. Preserved assets

**Held-out-family-2** (tasks 0024–0027; golden fast/lowpower) is preserved as an **untouched future-replication asset**: not run, not altered, and no variant selected on existing outcomes. The C24 bridge's `not_established` verdict means it is not consumed.

## Appendix A — Claim–evidence matrix (authoritative)

The 15-row matrix in `docs/synthetic_p14_phase4z_paper_outline.md` is authoritative. Summary by tier:

- **Tier 1 (full bundle):** controlled-pair effect for Qwen + DeepSeek — **established** (scoped to the original pair; not cross-model BundleS evidence).
- **Tier 2 (BundleS):** Qwen dev + held-out — **established (Qwen)**; DeepSeek under exact counterbalancing — **negative**; described as a model-contingent candidate.
- **Tier 3 (minimal components):** no stable minimal C1/C2/C4/C7 — **negative/unresolved**; C2×C4 interaction — **unresolved** (bridge failed the threshold); C24 is **not** claimed as a confirmed interaction or minimal mechanism.

## Appendix B — Provenance

Findings trace to `reports/synthetic_p14_phase4{w,x,y}*` and `reports/synthetic_p14_phase4y3_c24_bridge.*`; generated figures/tables to `docs/synthetic_p14_phase4z_figures_tables.md` (`scripts/phase4z_figures_tables.py`); the experiment freeze to `reports/synthetic_p14_phase4z_freeze_manifest.{md,json}` (HEAD, commit chain, SHA-256, task/model matrix, episode counts, costs; 58 primary / 3 excluded / 0 invalid / 1 aborted episodes; ¥682.25; SSE). No paid model calls were made for this manuscript.
