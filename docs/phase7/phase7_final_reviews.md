# Phase-7 Final Mock-Review Packet (manuscript v3; 5 fresh reviews + AC meta-review)

**Manuscript:** frozen v3 (`submission/main.tex` + appendix), 9 pp (main text 6 pp ≤ 9), anonymous (0 leaks).
**Method:** five reviewers, each given ONLY the frozen manuscript; no prior reviews, no target scores. Each criticism classified **[FIXABLE]** (claim/presentation, fixable by rewording/restructuring), **[IRREDUCIBLE]** (frozen-evidence limitation no writing can fix), or **[NOVELTY/SIGNIFICANCE]** (value disagreement). Not optimized for score; reported as obtained.

## Score summary
| Reviewer (lens) | Overall | (a) Problem | (b) Motiv/lit | (c) Claim support | (d) Significance | Net |
|---|---|---|---|---|---|---|
| R1 stats/rigor | 6 | 8 | 6 | 6 | 5 | marginal accept |
| R2 novelty | 4 | 6 | 5 | 4 | 4 | reject |
| R3 significance | 4 | 6 | 5 | 4 | 4 | reject |
| R4 measurement | 4 | (2/4 sound) | (2/4 sig) | (2/4 orig) | (3/4 clar) | reject |
| R5 general | 5 | (2/4 sound) | (3/4 pres) | (2/4 contr) | (3/4 conf) | reject |
| **Mean** | **4.6** | — | — | — | — | median 4 |

(R4/R5 used the OpenReview 1–4 sub-scale; their Overall is 1–10. v2 Phase-6C mean was 4.6; v3 is unchanged in score but the binding objections are now cleanly separable into frozen-irreducible vs fixable.)

## Consensus by classification
- **[IRREDUCIBLE] (unanimous, the binding objections):** (i) the within-family (Study I) and cross-model headlines rest on **n=1 task instance** per cell (5/5); (ii) **construct validity rests on executable provenance/authority oracles, not human judgment** — Study B is unexecuted (5/5); (iii) the audit protocol's **external validation is weak** (Terminal-Bench 1/26 direct, L2/sampling 0/26) (4/5); (iv) **narrow scope** (2 models, 2 families, EDA-only) (4/5); (v) the n=12 STA batch is underpowered (floor effects; ~5 discriminating instances) (3/5).
- **[FIXABLE] (addressable in revision):** placeholder/uncited Table~1 related work (3/5); direction-reversal framed as a finding rather than expected sampling noise on a near-zero effect (2/5); model-selection unjustified (2/5); cross-family tested with only the one within-family-positive model (3/5); no mechanism isolated (2/5); the three studies don't cohere tightly (1/5); TypedContract dominance (11/12 ≥ BundleS) dismissed in one sentence (1/5); cost not normalized per instance (1/5).
- **[NOVELTY/SIGNIFICANCE] (value disagreement):** the cautionary thesis (held-out confirmation ≠ transfer; small pilots unstable) is well-established methodological territory (4/5).

---

## Reviewer 1 — statistics/rigor
**Overall 6** (marginal accept). (a)8 (b)6 (c)6 (d)5. Conf 4.
*Strengths:* exemplary statistical hygiene (no trajectory pooling, no small-n bootstrap, exact sign + instance permutation; pilot not pooled with prospective); the n=3→n=12 direction-reversal is a powerful methodological demonstration; the audit protocol is instantiated (each layer caught a real threat), not merely proposed.
*Weaknesses:* [IRREDUCIBLE] Studies I/cross-model headlines rest on n=1 instance per cell; [IRREDUCIBLE] n=12 powered only for large effects, can't resolve small-to-moderate; [IRREDUCIBLE] floor effects (~5 discriminating instances); [FIXABLE] construct validity via oracles only (Study B unexecuted); [FIXABLE] external protocol validation weak (1/26, L2=0); [FIXABLE] narrow scope; [FIXABLE] mixed unit (trajectory vs instance); [NOVELTY/SIGNIFICANCE] cautionary null + partially-validated protocol = modest advance.
*Net:* does not justify rejection — the prospective n=12 direction-reversal + instantiated protocol + exemplary honesty tip a borderline case to marginal accept.

## Reviewer 2 — novelty
**Overall 4** (reject, borderline). (a)6 (b)5 (c)4 (d)4. Conf 4.
*Strengths:* disciplined claim bounding/registration (Table 2); the four-layer protocol with concrete named threats is reusable (L3 streaming-transport finding alone valuable); the prospective direction-reversal is the single most convincing demonstration.
*Weaknesses:* [IRREDUCIBLE] n=1 cells in Studies I/II; [FIXABLE] headline near-tautological, undersells the protocol + reversal; [NOVELTY/SIGNIFICANCE] TB audit 1/26 direct weakens external validity; [FIXABLE] Table 1 placeholder citations; [IRREDUCIBLE] construct validity via oracles (Study B unexecuted); [FIXABLE] TypedContract dominance (11/12) dismissed in one sentence; [FIXABLE] studies don't cohere; [FIXABLE] model selection unjustified.
*Net:* reject — honesty/infrastructure excellent, but n=1 superstructure + well-trodden caution + 1/26 external capture underpowered for ICLR. Needs scaled within-family (k≥5 instances) or predictive (not post-hoc) protocol validation.

## Reviewer 3 — significance
**Overall 4** (reject). (a)6 (b)5 (c)4 (d)4. Conf 4.
*Strengths:* genuinely reframes the question (claim validity/attribution, not "harnesses matter"); best-in-class methodological honesty; L3 transport catch is community-relevant.
*Weaknesses:* [NOVELTY/SIGNIFICANCE] direction reversal is sampling noise on two non-significant estimates; [IRREDUCIBLE] taxonomy rests on executable oracles only (Study B unexecuted); [IRREDUCIBLE] powered to find nulls (n=1 cells, SPICE ceiling, STA floor); [FIXABLE] Table 1 placeholder citations; [NOVELTY/SIGNIFICANCE] protocol self-admittedly not broadly validated, only external test 1/26 (undercuts the "external validity must be demonstrated" thesis); [FIXABLE] TAB/LongHorizon distinctions asserted thinly; [FIXABLE] no mechanism isolated; [FIXABLE] EDA-only + 2 models.
*Net:* reject — does what it advertises (no inflated claims) but the bounded claims are individually weak; needs a powered prospective family or completed human construct-validity pass.

## Reviewer 4 — measurement
**Overall 4** (reject). Soundness 2/4, Significance 2/4, Originality 2/4, Clarity 3/4. Conf 4.
*Strengths:* exceptional scholarly honesty (registration ledger, no pooling, no LLM substitute); real-tool engineering rigor (exact-commit worktrees, custody, SSE streaming); the tool-green/typed-rejected taxonomy isolates a real under-reported validity problem.
*Weaknesses:* [IRREDUCIBLE] RQ1 effect = one model/pair/instance, k=3 (transfer-failure only as load-bearing as the thin original effect); [FIXABLE] direction reversal framed as a finding (it's expected sampling noise on a near-zero effect); [IRREDUCIBLE] protocol is an existence proof, not a validated instrument (TB 1/26, L2=0); [IRREDUCIBLE] construct validity via single-source oracles (Study B unexecuted); [FIXABLE] cross-family single-model (can't separate "no transfer" from "no transfer for this model"); [NOVELTY/SIGNIFICANCE] message statistically well-known; [IRREDUCIBLE] EDA-only caps the contribution.
*Net:* reject — honesty/rigor commendable, but the n=3→n=12 reversal is sampling noise and the protocol is explicitly unvalidated beyond the authors' pipeline; needs a second model/instance or predictive external validation.

## Reviewer 5 — general
**Overall 5** (borderline reject). Soundness 2/4, Presentation 3/4, Contribution 2/4, Confidence 3/4.
*Strengths:* exemplary self-limitation + registration (Table 2); concrete verifiable infrastructure (real tools, exact-commit worktrees, arbiter, custody); the direction-reversal is a useful cautionary artifact.
*Weaknesses:* [IRREDUCIBLE] taxonomy zero independent validation (Study B unexecuted); [IRREDUCIBLE] TB audit weak (1/26 direct, L2=0); [FIXABLE] TB retrospective not prospective prediction; [IRREDUCIBLE] diagnostic-only sample sizes; [FIXABLE] minimal-component ablation failed (black-box bundle); [FIXABLE] single-primary-model cross-family; [FIXABLE] Table 1 placeholder citations; [NOVELTY/SIGNIFICANCE] thesis well-established; [FIXABLE] cost not normalized.
*Net:* reject — bounded claims defensible but rest on two under-validated pillars (taxonomy, protocol); needs Study B executed or a prospective TB application to clear the bar.

---

## AC Meta-review

**Verdict: borderline-reject (mean 4.6, median 4).** The question posed — *do the remaining weaknesses justify rejection despite the explicitly bounded claims?* — answers **yes, on scientific grounds, but narrowly and entirely on [IRREDUCIBLE] frozen-evidence limitations.**

The v3 is the most honestly-bounded version of this work: the prospective n=12 STA batch is primary (pilot not pooled), the direction reversal is reported as a small-sample caution rather than a mechanism finding, Study B is openly unexecuted, the audit protocol is explicitly "not broadly validated," and the Terminal-Bench audit is framed strictly as retrospective taxonomy application (1/26 direct, L2=0). Reviewers unanimously praise the registration discipline, the real-tool custody infrastructure, and the L3 streaming-transport catch; one (R1) finds this tips the paper to marginal accept.

The binding objections are all **[IRREDUCIBLE]** and cluster on three frozen limitations no revision can remove: (1) the within-family effect and cross-model null rest on **n=1 task instances**; (2) **construct validity rests on executable oracles, not human judgment** (Study B unexecuted); (3) the protocol's **only external test captures 1/26 repairs and validates the L2 sampling layer zero times.** These are precisely the gaps that a powered within-family study, a completed human construct-validity pass, or a predictive (not retrospective) benchmark application would close — all of which the experimental freeze forbids. The **[FIXABLE]** items (real citations for Table 1; justifying model selection; reframing the reversal as expected sampling noise; tightening Study III's coherence; normalizing cost) would improve the paper but cannot move the core scientific objection.

**Honest assessment for submission:** as frozen, this is a rigorously bounded, infrastructure-rich evaluation study whose individual scientific conclusions are thin (underpowered nulls, a self-validated taxonomy, 1/26 external protocol capture). Acceptance would require a reviewer to weight the methodological infrastructure + honesty + the direction-reversal caution above the thin positive yield — a defensible but minority position (R1). The default outcome at ICLR 2027 is a borderline reject on significance/rigor grounds that the freeze does not permit resolving. **Per the directive, no experiments are reopened in response to these scores.** The most leveraged no-experiment revisions before camera-ready (if a further round is available) are: replace the placeholder citations; reframe the direction-reversal explicitly as an expected consequence of estimating a near-zero effect at small n (not a mechanism finding); justify model selection; and consider whether the TypedContract descriptive dominance (11/12 ≥ BundleS) deserves a foregrounded sentence given it is the one non-null directional signal in the prospective batch.
