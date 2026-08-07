# Phase-6B Mock Reviewer Packet v2 (5 independent reviews + AC meta-review)

**Generated for:** manuscript v2 (`docs/synthetic_phase6_manuscript_v2.md`).
**Method:** five reviewers were dispatched independently. Each was given **only** the manuscript path and instructed to read nothing else (not the v1 reviews, not the claim matrix, not any report), to score honestly with no target, and to apply a distinct deep-read lens while still scoring all four ICLR dimensions. No reviewer saw any other reviewer's text or any prior/target score. Scores are reported as obtained; wording was not optimized to raise them.

**One factual correction triggered by this round (already applied to the manuscript):** Reviewer 4 (generalist) flagged that §4 called `BundleD` "answer-bearing-inclusive" while reporting it *worse* than the non-answer `BundleS` (1/3 vs 3/3), with `BundleD` undefined. The committed evidence shows `BundleD` is in fact **C3/C5 (decoy-disambiguation), itself non-answer-bearing**; the Phase-4W result localizes the effect to the schema/contract components (C1+C2+C4+C7) *versus* the decoy-disambiguation alternative. The manuscript has been corrected.

---

## Score summary

| Reviewer (lens) | Overall | (a) Problem/question | (b) Motivation/lit | (c) Claim support/rigor | (d) Significance | Conf. |
|---|---|---|---|---|---|---|
| R1 — experimental statistics | 4 | 5 | 5 | 3 | 4 | 4 |
| R2 — significance / impact | 5 | 6 | 5 | 4 | 4 | 4 |
| R3 — novelty / positioning | 4 | 6 | 6 | 3 | 4 | 4 |
| R4 — general skeptic | 4 | 5 | 5 | 4 | 4 | 4 |
| R5 — measurement rigor | 4 | 5 | 5 | 4 | 4 | 4 |
| **Mean** | **4.2** | **5.4** | **5.2** | **3.6** | **4.0** | — |
| **Median** | **4** | **5** | **5** | **4** | **4** | — |

Overall mean **4.2 / 10** (borderline reject). v1 was also 4.2; the rewrite improved clarity/positioning (problem/question 5.4, motivation/lit 5.2) but did **not** move the binding scientific weaknesses, which are properties of the frozen experiment and cannot be resolved by prose.

---

## Reviewer 1 — experimental-statistics lens

**Overall: 4.** Sub-scores: (a) 5 (b) 5 (c) 3 (d) 4.

**Summary.** This is an evaluation study of "harness effects" on LLM agents performing tool-grounded EDA workflows. It tests whether a non-answer-bearing "clarity bundle" suppresses a specific tool-green semantic-binding failure, and finds a within-family effect for one model that fails to transfer across a second model and across two structurally independent task families. The paper also contributes a "Harness Effect Audit Protocol" (four layers, nine controls). The central negative result rests on extremely small samples (3–4 instances per cell), and the methodological contribution is largely an operationalization of engineering best practices rather than a new technique.

**Strengths.**
1. Genuine tool grounding on real commercial EDA tools, with the construct that wrong bindings produce tool-green signoffs rejected only by a typed provenance grader — a clean instrument for separating semantic correctness from tool success.
2. Unusual pre-registration discipline (Table 3 tags each result by registration type; exploratory work demoted from the headline). The honesty about scope ("transfer not established" vs. "refuted") is commendable.
3. The audit-protocol "concrete episodes" (streaming-transport censoring; canonical-config corruption masquerading as a tool outage; SPICE action-surface false positive zeroing 12 episodes) are vivid, real threats that were actually caught.

**Weaknesses.**
1. The headline rests on cell sizes of n=3–4. The cross-model null is 3/4 vs 3/4 (one episode); the STA null is 0.50 vs 0.33 over 3 instances; SPICE is at ceiling and uninformative. Even the "established" within-family effect is n=3 plus a held-out n=3. A single different stochastic draw would flip the narrative.
2. Differentiation from prior harness-evolution / leaderboard-critique work is conceptually thin; the negative result is what existing critiques would predict, and the audit protocol is engineering hygiene rigorous work is expected to do silently.
3. Contribution 1 (semantic-binding mechanism + taxonomy) is a counts table (20/5/29 over 54) whose cognitive/behavioral significance is not established; the failure is constructed to be tool-green, not shown to be a naturally occurring real-world failure mode.

**Two strongest reasons to reject.**
1. Sample sizes are fundamentally inadequate for the claims. A "central finding" about non-transfer cannot rest on n=3–4 per cell with no power analysis and no population-level inference.
2. Novelty over prior harness-evolution and protocol-validity work is marginal; the paper reads as a rigorous but narrow experiment log packaged as a methodological contribution.

**Questions for the authors.**
1. Why was per-cell n fixed at 3–4 rather than powered? What is the smallest effect size your design could detect at acceptable power, and how does that bound the headline?
2. Which choices (the two external families, Model A as cross-family model, demoting the C1/C2/C4/C7/C24 decomposition) were pre-registered before any paid call, and which after observing outcomes? Was the STA-null vs SPICE-ceiling framing decided before or after seeing the split?

**Confidence: 4.**

---

## Reviewer 2 — significance / impact lens

**Overall: 5.** Sub-scores: (a) 6 (b) 5 (c) 4 (d) 4.

**Summary.** This evaluation study asks when a measured agent-harness effect is scientifically attributable, whether it transfers across models and structurally independent task families, and which measurement-validity controls make either claim credible. It finds a within-family effect for one frontier model that replicates on a pre-frozen held-out instance, but is not established for a second model under counterbalancing and does not transfer to two external families in a measurable way. Alongside the result it contributes a reusable four-layer, nine-control audit protocol. The paper is unusually disciplined in pre-registration, counterbalancing, and separating clean-null from ceiling results, but its headline rests on extremely small instance counts and its protocol is only demonstrated on this single EDA study.

**Strengths.**
1. Methodological discipline rare in LLM-agent evaluation (pre-declared pairs, pre-frozen held-out, exact counterbalancing, the registration table, validity-only replacement). The careful STA-null vs SPICE-ceiling distinction is exactly the epistemic honesty the area needs.
2. The "tool-green semantic failure" construct is genuinely useful and reusable well beyond this paper.
3. The four-layer audit protocol is the most reusable artifact; the caught-threat episodes (streaming censoring; ~21h false outage from a corrupted golden; the SPICE rule manufacturing 12 false zeros) are real engineering lessons other benchmark builders will recognize.

**Weaknesses.**
1. The headline is dramatically underpowered (1/3 vs 3/3; 3/4 vs 3/4; 3 instances × 2 reps per family). These counts cannot establish an effect size, cannot establish absence of an effect, and cannot distinguish "model/family-specific" from "underpowered." The paper does not report what effect size the design was powered to detect.
2. The audit protocol's reusability is asserted, not demonstrated — every layer is illustrated with a threat from this one infrastructure. To earn "first-class methodological artifact," it needs at least one external application (re-auditing a published harness-effect result, or mapping each control to threats in the cited prior work).
3. Positioning is hard to verify (Table 2's paraphrased prior-work names, no citations) and the EDA framing is narrow; "the semantic-binding failure mode is cognitive and tool-agnostic" is asserted, not demonstrated.

**Two strongest reasons to reject.**
1. Sample size. N=3 per family, k=2–4 reps, one model on cross-family, one on the positive side — this cannot support the headline. Honesty about underpower does not make an underpowered negative publishable; the paper needs roughly an order of magnitude more instances.
2. Audit-protocol generalizability is unproven. Without at least one external benchmark application, "reusable" is a promise, not a demonstration.

**Questions for the authors.**
1. What is the smallest BundleS-vs-Base effect your cross-family design was powered to detect, and what effect sizes remain consistent with your data?
2. Has the audit protocol been applied to any harness-effect study other than this one? If not, why is "reusable" claimable from a single internal demonstration, and what is the minimal external test that would falsify it?

**Confidence: 4.**

---

## Reviewer 3 — novelty / positioning lens

**Overall: 4.** Sub-scores: (a) 6 (b) 6 (c) 3 (d) 4.

**Summary.** This is an evaluation study of whether LLM-agent harness interventions generalize across models and across structurally independent EDA task families, grounded in real commercial tools. It reports a within-family positive (replicating on a frozen held-out instance), a cross-model and cross-family non-transfer, and a four-layer/nine-control audit protocol. The paper is unusually disciplined in hedging. The central empirical claims, however, rest on n=3–4 per cell with no inferential statistics, and the cross-family null is partly a consequence of how the independent families were constructed.

**Strengths.**
1. Honest, near-exemplary calibration ("not established" vs "refuted"; STA clean-null vs SPICE ceiling; exploratory demoted; uncontrolled-seeds disclosed). Section 7 is one of the more honest limitations sections reviewed.
2. A genuinely interesting, underreported measurement threat: non-streaming HTTP censoring long-reasoning models mid-generation, misclassified as a capability failure. The golden-corruption-as-false-outage episode is similarly instructive.
3. Realism of grounding via a transparent remote shim, and a clean instrument for separating semantic correctness from tool success.

**Weaknesses.**
1. Sample sizes are too small to support the headline, with no inferential statistics. The positive within-family is 1/3→3/3 (n=3); the cross-model tie is 3/4=3/4 (n=4); the STA null is driven by one instance moving 0.50→0.00. The alternative to a bad significance test is uncertainty quantification (CIs, bootstrap, Bayesian posterior), not none. For a paper whose thesis is about which conclusions are valid, the absence of any quantitative uncertainty is a sharp internal contradiction.
2. The "central finding" is partly manufactured by the design: the external families were built with independent role vocabularies and family-specific binding structures, and BundleS encodes family-specific role labels/value domains, so non-transfer is close to the expected behavior of the construction rather than a discovery. The cleaner evidence is the same-family cross-model tie — but that rests on n=4.
3. The four-layer protocol is a retrospective experience report, not a validated method: no quantification of how often each threat occurs, no baseline comparison, no demonstration that all nine controls are necessary. A single curated episode per layer, with no denominator, does not support marginal value.

**Two strongest reasons to reject.**
1. The empirical contribution rests on n=3–4 per cell with no CIs, effect sizes, power analysis, or inferential framework. The central claim is at this sample size indistinguishable from "we observed a small-sample null with very low power."
2. Construct-design circularity: because the external families were deliberately built independent with family-specific binding structures, non-transfer across them is close to the intended behavior of the construction, making the result less informative about harness-effect generalization than implied.

**Questions for the authors.**
1. What is the smallest cross-family effect size detectable at n=3 per family? What posterior would a weakly-informed Bayesian model place on "BundleS helps by ≥0.10 on STA"?
2. For the within-family positive (1/3→3/3, n=3): how stable is 3/3 across uncontrolled provider seeds? What fraction of repeats reproduce the split?

**Confidence: 4.**

---

## Reviewer 4 — general-skeptic lens

**Overall: 4.** Sub-scores: (a) 5 (b) 5 (c) 4 (d) 4.

**Summary.** This anonymized evaluation study asks when an LLM-agent harness effect is scientifically attributable and whether it generalizes. On a tool-grounded EDA semantic-handoff task where wrong bindings produce tool-green signoffs, BundleS suppresses a specific axis-binding failure for one model within a family, replicates on a pre-frozen held-out instance, but is not established for a second model under counterbalancing and does not transfer to two structurally independent families (clean null on STA, ceiling on SPICE). A secondary contribution is a four-layer/nine-control audit protocol, each layer illustrated with a concrete threat it allegedly caught. The contribution is explicitly an evaluation study, not a new method.

**Strengths.**
1. Intellectual honesty and study registration (Table 3 typology; refusal to pool into a significance headline; STA-null vs SPICE-ceiling kept distinct).
2. The streaming-transport episode is a genuinely useful, non-obvious finding that stands on its own as a contribution.
3. Construct isolation — the semantic-binding mechanism is a clean, reusable task-design primitive.

**Weaknesses.**
1. Sample sizes are too small to support even the directional claims: within-family positive n=3 (1/3 vs 3/3), held-out n=3 vs n=3, cross-model n=4 (3/4=3/4), STA null driven substantially by one instance declining 0.50→0.00. No bootstrap, exact test, or per-trajectory variance is reported. The asymmetry is striking: "3/3 vs 1/3" is called "established" while the equally tiny "3/4=3/4" is "not established" — both within the same noise band.
2. The audit protocol is self-reported by the infrastructure's own authors, with at least one evidently post-hoc repair. The SPICE Layer-4 integrity rule manufactured 12 false zero-scores; the repair was evidently designed after observing that and produced the desired ceiling. Layer 1's "threat" (a wrong-axis trajectory scoring green) is tautological with the task design.
3. Construct validity of the semantic-binding metric is asserted, not validated — the typed grader is the sole oracle for the very failure subtype it defines, with no inter-rater or external-criterion check.

**Two strongest reasons to reject.**
1. The headline positive and negative directional claims are within the sampling-noise band at n=3–4 with no formal inference or variance reporting; an underpowered evaluation cannot stand on the strength of its caveats alone.
2. The principal methodological contribution is self-reported, partly post-hoc, and in one layer tautological; without an external auditor or independent re-implementation, "we audited our own infrastructure and caught our own bugs" is engineering detail dressed as a first-class artifact.

**Questions for the authors.**
1. Across the 54-episode ledger, what is the per-trajectory axis-binding rate for Model A under Base vs BundleS, and what does a paired bootstrap give for the within-family contrast? How many total trajectories per condition were collected, and what is the variance across repetitions?
2. For the SPICE action-surface false positive: was the immutable-core/derived-deck repair specified *before* or *after* the discovery that all 12 SPICE episodes zeroed? If after, what independent evidence supports it as a principled fix?

**Confidence: 4.**

---

## Reviewer 5 — measurement-rigor lens

**Overall: 4.** Sub-scores: (a) 5 (b) 5 (c) 4 (d) 4.

**Summary.** This is an evaluation study of LLM-agent harness effects on tool-grounded EDA workflows. It introduces a semantic-binding task where a wrong quantity-to-role assignment produces a plausible tool-green signoff rejected only by a typed provenance grader, and tests whether a non-answer-bearing clarity bundle suppresses a specific axis-binding failure. The within-family effect is confirmed on a pre-frozen held-out instance for one model; under exact counterbalancing it is not established for a second model, and on two structurally independent families it is a clean null in one and unmeasurable at ceiling in the other. The paper also contributes a four-layer, nine-control audit protocol, each layer tied to a concrete threat it caught. The central finding is that within-family held-out confirmation did not imply cross-model or cross-family transfer.

**Strengths.**
1. The semantic-binding construct is a genuinely clever measurement instrument other tool-grounded agent benchmarks could borrow.
2. Exemplary registration and self-critique (registration taxonomy, validity-only replacement, pre-frozen held-out truth, willingness to report a failed component-localization as non-headline). The honesty about model contingency and ceiling effects is a strength of the scholarship.
3. Several Study-III threats are real and under-discussed (streaming-transport censoring; canonical-file-corruption-as-false-outage) and argue for pre/post-episode hash verification.

**Weaknesses.**
1. The headline is an absence-of-evidence claim built on n=3 external instances per family, with one family (SPICE) at ceiling providing zero discriminating information. At this n the study cannot distinguish "no transfer" from "underpowered to detect transfer," and it does not commit to a minimum detectable effect.
2. The discovery result (Model B 0/3→3/3 under the *full* bundle) and the counterbalanced result (Model B 3/4=3/4 under BundleS, which excludes C6) are reconciled only loosely: Model B's gain may have been C6 (answer-bearing) driven rather than non-answer clarity. If so, the non-answer localization holds cleanly only for Model A, narrowing the positive evidence. *(Note: this review also flagged the `BundleD` parenthetical, since corrected.)*
3. The three-study structure does not cohere into one strong argument, and the protocol's reusability is asserted, not demonstrated; it is shown catching threats only within this same study, with heavy jargon (BundleS/BundleD/C1–C7/C24/TypedContract) and a lab-report-like voice.

**Two strongest reasons to reject.**
1. The headline contribution is an external-validity null supported by three instances per family (one at ceiling), with no power/detectable-effect analysis to separate "did not transfer" from "could not have detected transfer."
2. The two contributions that could stand alone — the construct and the protocol — are underdeveloped as primary contributions: the construct on one narrow EDA mechanism, the protocol validated only on the authors' own pipeline.

**Questions for the authors.**
1. What evidence distinguishes "Model B's discovery gain was driven by C6 (answer-bearing)" from "it was a sampling artifact that counterbalancing corrected"? If you cannot, does the non-answer framing apply to Model A only?
2. Before collecting Study II, what true effect size was the cross-family comparison powered to detect? Is "transfer not established" better characterized as "not powered to establish or refute transfer," and should the headline be the protocol + construct rather than the transfer null?

**Confidence: 4.**

---

## AC Meta-review

**Assessment: borderline (mean 4.2 / 10; median 4). Leaning reject for the ICLR 2027 main track.** The rewrite is clearer and better-positioned than v1, but it did not move the overall score (4.2 → 4.2), and for a defensible reason: the binding weaknesses the reviewers identify are properties of the *experiment* (frozen, no new data authorized), not of the *exposition*.

**Consensus strengths (≥4 reviewers).**
- *Registration and honesty discipline.* All five reviewers cited Table 3 (study registration), the pre-frozen held-out truth, the validity-only replacement rule, and the STA-null vs SPICE-ceiling distinction as exemplary.
- *The semantic-binding construct.* All five credited the tool-green-but-typed-rejected instrument as a clean, reusable primitive for separating semantic correctness from tool success.
- *The streaming-transport threat.* Three reviewers (R2, R4, R5) singled it out as a genuinely useful, non-obvious finding worth surfacing on its own.

**Consensus weaknesses (≥4 reviewers).**
- *Small n with no inferential statistics (unanimous, 5/5).* This is the dominant objection and the lowest-scoring dimension (claim support / rigor = 3.6). Reviewers object that n=3–4 per cell cannot establish a direction, that the paper reports no CI / bootstrap / power analysis, and that for a paper about validity, the absence of uncertainty quantification is an internal contradiction.
- *Audit-protocol reusability asserted, not demonstrated (3/5: R2, R3, R5).* Every layer is validated only on the authors' own infrastructure; "reusable / first-class methodological artifact" is a promise without an external application.
- *Construct-design circularity (2/5 strongly: R3, R5; touched by R4).* The external families were deliberately built with independent role vocabularies and family-specific binding structures, so cross-family non-transfer is partly the expected behavior of the construction; the cleaner evidence is the same-family cross-model tie (n=4).
- *Construct validity of the metric asserted, not externally validated (2/5: R4, R5).* The typed grader is the sole oracle for the failure subtype it defines; no inter-rater or external-criterion check is reported.

**Single-reviewer concerns worth answering.**
- *Post-hoc SPICE repair (R5).* Whether the immutable-core/derived-deck repair was specified before or after the 12-zero discovery. (Authors' record: the Phase-5D repair was pre-specified and separately frozen *before* the Phase-5D collection that produced 0 trips; the manuscript should state this timing explicitly.)
- *Model B discovery/counterbalance confound (R5, R4).* Whether Model B's full-bundle gain was C6-driven. The data cannot fully separate this, but the manuscript's "not established" framing is already calibrated; it should note that the non-answer localization is established for Model A and is the cleaner case.

**Author-actionable within the no-new-experiments freeze (no new paid calls required).**
1. *Minimum-detectable-effect / power statement* for the cross-family design (a calculation, not an experiment) — directly answers R1/R2/R3/R5 Q1 and is the single most effective revision.
2. *Per-trajectory variance / paired-bootstrap re-analysis* from the 54-episode workflow ledger and the nested repetitions (re-analysis of existing data, no new episodes) — answers R3/R4.
3. *Explicitly acknowledge construct-design circularity* in §7, and re-center the cross-family evidence on the same-family cross-model tie — answers R3.
4. *Soften "reusable / first-class" protocol language* to "a threat catalogue validated on one infrastructure; external re-audit is future work" — answers R2/R3/R5.
5. *State the SPICE repair timing* (pre-specified for Phase-5D before that collection) — answers R5.
6. *(Done.)* Correct the `BundleD` characterization — answers R4.

**Would v2 be accepted at ICLR 2027?** No, not as-is at 4.2. The objections that hold the score down (small n, no inference, single-study protocol validation, construct circularity) cannot be closed by rewriting under the experimental freeze — they require either more instances or an external protocol application, both disallowed. The revisions above (especially the detectable-effect and variance analyses) would tighten the *calibration* of the claims and likely move claim-support/rigor and the overall score modestly upward (toward a high-4s borderline), but clearing the accept bar would need new data the freeze forbids.

**Honest note on the rewrite's value.** The v1→v2 reorganization (three studies, three RQs, the four-layer audit-protocol framing, the lead-with-the-surprise-result intro, the registration table, the novelty table) is credited in the problem/question (5.4) and motivation/lit (5.2) sub-scores and in the consensus on honesty/positioning. It did not, and structurally could not, raise the overall score because the binding weaknesses are experimental. Reporting 4.2 again — rather than a gamed higher number — is the correct outcome.

---

**Summary of v2 reviewer overall scores:** R1=4, R2=5, R3=4, R4=4, R5=4. Mean=4.2, median=4. (v1 mean was also 4.2.)
