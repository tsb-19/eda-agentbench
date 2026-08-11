# Auditing Harness Effects in LLM Agents: Semantic Binding, External Validity, and Measurement Reliability

**Phase-6 manuscript v1** · ICLR 2027 submission draft · 9-page main text · numbers from `reports/evidence/phase6_data.json` + `docs/synthetic_phase6_figures_tables.md` + `docs/synthetic_phase6_claim_matrix.md`.

## Abstract

We study how the *information structure* of an agent harness—the way a task presents its evidence and disambiguating context—changes the *semantic execution behavior* of frontier LLMs on tool-grounded EDA workflows. On a controlled semantic-handoff task (p14), a non-answer-bearing "clarity bundle" (BundleS) suppresses a specific semantic-axis binding failure for Qwen3.7-Max, confirmed on a pre-frozen held-out instance (confirmatory + frozen held-out). Under exact counterbalancing this benefit is **not established** for DeepSeek-V4-Pro (cross-model null). When we construct two **structurally independent** semantic-handoff families (STA/PrimeTime and SPICE/HSPICE) sharing none of p14's signature structures, **cross-family transfer of the BundleS benefit is not established**: the STA family shows a clean null (Base 0.50 ≥ BundleS 0.33), and the SPICE family is non-discriminative at ceiling (Base = BundleS = TypedContract = 1.00). A machine-readable typed representation of the same non-answer-bearing information produced **no measurable advantage** over either Base or BundleS. We argue that harness-effect studies require a nine-layer evaluation-validity stack (semantic binding, artifact correctness, protocol completion, terminal transport validity, recovered degradation, tool health, sample-membership arbitration, action-surface integrity, canonical-tree integrity), each reported independently. The contribution is an **evaluation study** of harness effects—not a proposal of an improved harness.

## 1. Introduction

A harness intervention can appear robust under repeated development and frozen within-family held-out evaluation yet fail to transfer across task families or models. This paper does not propose a universally better harness. It asks three questions:
- **RQ1:** Can harness information structure change semantic execution behavior?
- **RQ2:** Do discovered harness effects transfer across models and task families?
- **RQ3:** Which evaluation controls are necessary to make those conclusions valid?

On p14 (a timing-signoff semantic-handoff task), a "clarity bundle" of non-answer-bearing disclosure components (canonical labels, value-domain definitions, a glossary, a procedural contract) suppresses a specific failure: the agent places a PVT descriptor on the wrong typed axis (e.g., `scenario=func` instead of `corner=func`). We show this effect is **real** within p14 for Qwen (Tier-1 confirmatory; Tier-2 held-out confirmation) but **model-contingent** (DeepSeek null under exact counterbalancing) and **does not transfer** to two structurally independent families (STA null, SPICE ceiling). A typed machine-readable schema adds nothing.

The measurement-validity lesson is that harness-effect studies depend on transport, tool health, sample membership, protocol completion, action surfaces, and canonical-artifact integrity—each of which we report as an independent dimension. We contribute: (a) a controlled semantic-binding mechanism + failure taxonomy; (b) the external-validity-failure-after-held-out-confirmation finding; (c) the nine-layer measurement-validity auditing framework.

## 2. Harness effects and evaluation validity

We define a **harness** as the task-level information structure visible to the agent: the prompt, the visible task files, the disclosure bundle, the public tool feedback, and the action surface (what the agent can edit). A **harness effect** is a change in agent behavior (specifically, semantic-binding correctness) attributable to a change in harness information content, holding the hidden truth and grader fixed.

The **evaluation-validity stack** (Figure 3) comprises nine independent layers: semantic binding (primary), artifact correctness, protocol completion, terminal transport validity, recovered degradation, tool health, sample-membership arbitration, action-surface integrity, and canonical-tree integrity. We report each separately and never collapse them into a single score.

## 3. Controlled semantic-handoff benchmark methodology

**Tasks.** Each task presents a *semantic handoff*: the agent must bind a tuple to canonical typed roles from heterogeneous, role-misleading evidence. p14 binds `(scenario, corner)` ∈ typed axes from PVT descriptors, role-swapped reports, and stale decoys. Family A (STA) binds `(intent_class, target_partition, check_mode)` from an authority DAG. Family B (SPICE) binds `(corner, load_condition, metric)` from a request-authority relational join. The families share **none** of p14's signature structures (independent text template, role vocabulary, hidden-truth representation, grader implementation, decoy-generation logic; operational independence verified under five preregistered criteria).

**Tool grounding.** p14 runs on real PrimeTime (tiny.db); Family A on PrimeTime; Family B on HSPICE. All through a transparent remote shim to b04. A wrong binding produces a **plausible green signoff or plausible numeric output**—so tool success is necessary but not sufficient for semantic correctness. Only the typed provenance/authority grader distinguishes correct from wrong.

**Conditions.** Base (ambiguous natural-language handoff; no answer-bearing disclosure). BundleS (canonical labels + disjoint-axis declaration, value-domain definitions, glossary+references, procedural contract—mapped mechanically; no C6 answer assertion; no golden values). TypedContract (same information content as BundleS in a machine-readable JSON Schema; no golden values; no post-submission verifier feedback; matched budgets). The three differ only in disclosure representation.

**Design.** Seeded exact-counterbalanced blocked randomization (frozen pre-run); position-balance asserted; instance is the primary experimental unit; stochastic repetitions are nested observations. No pooled trajectory-level significance test is used as a headline. Predeclared interpretation tables.

**Budget.** ¥315 ceiling (Phase-5C) and ¥50.76 ceiling (Phase-5D, recomputed from the Phase-5C slot-cost distribution). Replacement only for terminal measurement-invalid episodes; recovered degradation in a gradeable episode does not trigger replacement.

## 4. Discovery and within-family mechanism study *(p14; confirmatory + sequential exploratory + frozen held-out)*

**Discovery.** On the p14 controlled pair (0009 ambiguous / 0010 clear), the full clarity bundle suppressed the axis-binding failure for both Qwen and DeepSeek *(confirmatory; Tier-1)*: Qwen 0009 1/3 (2 axis) → 0010 3/3 (0 axis); DeepSeek 0/3 (3 axis) → 3/3 (0 axis).

**Non-answer localization.** Excluding the answer-bearing C6, BundleS (C1+C2+C4+C7) suffices on the development pair for Qwen: Phase-4W Run-2 BundleS 3/3 vs BundleD 1/3 *(confirmatory)*. BundleS generalizes to a **pre-frozen held-out** hidden truth: held-out 0017 (= 0011 + BundleS) 3/3 vs Base 0011 1/3 *(frozen held-out confirmation; Qwen)*.

**Model contingency.** Under exact counterbalancing, BundleS is **not established** for DeepSeek: Stage-1C Base 3/4 (1 axis) = BundleS 3/4 (1 axis) *(cross-model null)*.

**Component decomposition (sequential exploratory).** No stable minimal component is identified: C1 does not eliminate axis errors (2/4 with 2 axis); neither C2-only (1/4) nor C4-only (0/4) reproduces the C24 pattern; the in-window C24 bridge fails the predeclared ≥3/4 + 0-axis threshold (2/4, 1 axis) → `not_established` *(unresolved)*. The C2×C4 joint-effect hypothesis remains **unresolved**, not refuted.

## 5. Cross-model and cross-family external validity *(cross-model null + cross-family null + ceiling)*

**Cross-model (p14):** the BundleS benefit is model-contingent—established for Qwen, not for DeepSeek.

**Cross-family (Phase-5C/5D):** we construct Family A (STA/PrimeTime) and Family B (SPICE/HSPICE), structurally independent from p14 and from each other. Phase-5C (Qwen-only, 24 episodes): **STA Base 0.50 / BundleS 0.33** (0/3 instances improve; one declines, one at ceiling, one at floor) — a clean null. **SPICE Base 1.00 / BundleS 1.00** (ceiling; non-discriminative — the Base instance is already solved). Phase-5D (Qwen-only, 36 episodes, 3 conditions including TypedContract): **TypedContract produces no measurable advantage** over Base (0 improve/1 decline/5 tie) or BundleS (0/0/6 tie). **Cross-family transfer of the P14 BundleS benefit was not established.**

The STA null is clean primary evidence. The SPICE ceiling means the effect is unmeasurable there (not that it was refuted). The SPICE artifact dimension was compromised in Phase-5C by a deck-editability conflict (forbearance false-positive anti-cheat; forensically audited 0/12 protocol_compromised) and repaired in Phase-5D (0 trips; clean artifact data).

## 6. Measurement-reliability findings *(infrastructure contributions)*

Each of these was a real threat that manufactured or masked a result, caught by the corresponding evaluation-validity layer:
1. **Transport:** non-streaming HTTP censors thinking-model long reasoning (apparent Qwen "failures" were transport-invalid); SSE streaming is a measurement prerequisite.
2. **Sample-membership:** a committed `episode_arbiter` is the sole membership authority; `measurement_valid = terminal_transport_valid ∧ workspace_gradeable`.
3. **Tool health:** real-PrimeTime/HSPICE Level-1 sentinel + Level-2 full-path bookends; block admissible iff both healthy.
4. **Action-surface integrity:** immutable integrity-hashed circuit core + derived deck (the Phase-5C false-positive anti-cheat fix); regressions prove core-modification is detected.
5. **Canonical-tree integrity:** exact-commit isolated worktree; frozen SHA-256 manifests; per-episode verification; `FAILED_INTEGRITY` stop (0 incidents in the guarded runs).
6. **Custody:** byte-match per-episode evidence; sanitized agentlogs; no credential leakage (verified).

## 7. Related work

**Harness-Bench** benchmarks harness variation but does not isolate semantic-binding mechanisms or audit external validity after held-out confirmation. **Rethinking the Evaluation of Harness Evolution** critiques harness-leaderboard conflation but does not construct controlled semantic-handoff families or a measurement-validity stack. **HarnessOpt-Bench** optimizes harnesses via search but does not study cross-family transfer failure. Our novelty: (a) controlled semantic-binding mechanisms with a typed failure taxonomy; (b) the external-validity-failure-after-held-out-confirmation finding (the BundleS effect appears robust within p14 yet does not transfer); (c) measurement-validity auditing as a first-class contribution (nine independent layers). We do not claim "harnesses matter" generically; we show *how* and *when* a harness effect can be measured reliably, and when it fails to generalize.

## 8. Limitations and conclusion

**Limitations:** (1) small k per cell (n=3 instances per family; descriptive, not population); (2) sequential adaptive development within p14 (stages gated on prior results); (3) one gateway/provider; (4) the STA null could reflect insufficient Base ambiguity (two of three instances at ceiling/floor); (5) SPICE non-discriminative at ceiling; (6) Qwen-only cross-family (DeepSeek cross-family not run); (7) TypedContract scoped to the tested model + families.

**Conclusion:** A harness intervention can appear robust under repeated development and frozen within-family held-out evaluation yet fail to transfer across task families or models. The BundleS effect is real within p14 for Qwen but model-contingent and not established cross-family. A machine-readable typed representation produced no measurable advantage on the tested external families. Evaluation validity depends on transport, tool health, sample membership, protocol completion, action surfaces, and canonical-artifact integrity—each of which can manufacture or mask a result, and each of which we report independently.

---

**Study-type labels used:** confirmatory (p14 controlled pair; Phase-5C Qwen-24 core) · sequential exploratory localization (p14 4W/4X/4Y; not headline) · frozen held-out (p14 0017) · cross-model null (DeepSeek Stage-1C) · cross-family null (Phase-5 STA) · ceiling (SPICE; p14 STA-0002) · unresolved (C2×C4). **Program totals:** 58 (p14) + 24 (5C) + 36 (5D) = 118 paid primary episodes (beyond p14: 60); total cost ¥701.72. **No push.**
