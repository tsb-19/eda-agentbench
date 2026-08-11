# Phase-6C Final Mock-Review Packet (post-freeze)

**Manuscript reviewed:** frozen anonymous submission `submission/main.tex` (official ICLR format), compiled to `submission/main.pdf` (main text ends p.8; references p.8; appendix p.9; 10 pp total).
**Method:** five reviewers, each given only `submission/main.tex`, no prior reviews, no target score. Each classified every objection as **[OVERREACH-FIXABLE]** (a claim-overreach fixable by rewording), **[PRESENTATION]** (a presentation/reproducibility/citation problem), or **[IRREDUCIBLE]** (a frozen-experiment limitation no wording can fix).

## Score summary

| Reviewer (lens) | Overall | (a) Problem | (b) Motiv/lit | (c) Claim support | (d) Significance | Net |
|---|---|---|---|---|---|---|
| R1 experimental statistics | 5 | 6 | 4 | 6 | 4 | reject |
| R2 novelty / positioning | 4 | 7 | 7 | 5 | 4 | reject |
| R3 significance / impact | 4 | 6 | 5 | 6 | 4 | reject |
| R4 measurement rigor | 5 | 7 | 6 | 5 | 5 | marginal reject |
| R5 general skeptic | 5 | 7 | 5 | 5 | 5 | marginal reject |
| **Mean** | **4.6** | **6.6** | **5.4** | **5.4** | **4.4** | — |
| **Median** | **5** | **7** | **5** | **5** | **5** | — |

**Change vs Phase-6B:** overall 4.2 → **4.6**; problem/question 5.4 → 6.6; **claim-support/rigor 3.6 → 5.4 (+1.8)**; motivation/lit 5.2 → 5.4; significance 4.0 → 4.4. The large gain is in (c) — exactly the dimension the detectability paragraph, trajectory-stability table, SPICE chronology, and softened protocol language targeted. Not score-gaming: the revisions addressed named Phase-6B weaknesses and the credit lands on the targeted dimension.

---

## Reviewer 1 — experimental statistics
**Overall 5.** (a)6 (b)4 (c)6 (d)4. Conf 4.
*Strengths:* exceptional calibration/self-scoping; L3 execution-validity findings (streaming censoring; config-corruption-as-outage) are genuine, non-obvious; the typed semantic-binding instrument is sharper than aggregate pass@k.
*Weaknesses:* headline rests on n=1 within-family / n=3 external — STA null genuinely "cannot rule out a small effect" **[IRREDUCIBLE]**; cross-family non-transfer partly tautological (families built independent) **[PRESENTATION]**; related-work citations are paraphrased placeholders **[OVERREACH-FIXABLE]**; Model B discovery-vs-counterbalanced inconsistency not reconciled **[PRESENTATION]**; audit-protocol reusability simultaneously asserted and disclaimed **[PRESENTATION]**.
*Net:* reject — headline necessarily weak at these n, positioning unverifiable, most reusable contribution explicitly scoped away.

## Reviewer 2 — novelty / positioning
**Overall 4.** (a)7 (b)7 (c)5 (d)4. Conf 4.
*Strengths:* registration hygiene; clean within-family instrument; real documented measurement threats.
*Weaknesses:* evidential base thin relative to rhetorical weight **[IRREDUCIBLE]**; intro "the community will systematically over-credit" generalizes n=1 into a community-wide failure **[OVERREACH-FIXABLE]**; cross-model tie is a single instance presented as a co-equal pillar **[PRESENTATION]**; RQ3 is apparatus elevated to a research question **[PRESENTATION]**; heavy machinery for a small negative, protocol single-study-validated **[PRESENTATION]**; within-family positive itself small-n **[IRREDUCIBLE]**; SPICE ceiling still occupies a full row **[PRESENTATION]**.
*Net:* reject — claims hedged to evidence but framing ("systematically over-credit") over-sells what n=1+3+ceiling carry.

## Reviewer 3 — significance / impact
**Overall 4.** (a)6 (b)5 (c)6 (d)4. Conf 4.
*Strengths:* tool-green semantic-binding insight; admirable honesty + frozen chronology; cautionary core well-targeted.
*Weaknesses:* evidential base thin at every link **[IRREDUCIBLE]**; effect was already model-contingent before cross-family test, so non-transfer partly expected **[OVERREACH-FIXABLE]**; audit protocol dominated by EDA-specific engineering, only streaming-transport reads as transferable **[PRESENTATION]**; related-work sparse, novelty asserted not argued **[OVERREACH-FIXABLE]**; dense acronym-heavy **[PRESENTATION]**; component decomposition failed, positive is a black-box bundle effect **[IRREDUCIBLE]**.
*Net:* reject — better suited to an evaluation/dataset-methodology venue where strengths need not clear a significance bar the bounded claims cannot reach.

## Reviewer 4 — measurement rigor
**Overall 5.** (a)7 (b)6 (c)5 (d)5. Conf 4.
*Strengths:* registration hygiene; concrete caught-threat episodes (streaming-transport); SPICE repair chronology (no-call forensic re-derivation, separately-frozen 5D) is genuine custody-chain transparency.
*Weaknesses:* **typed-grader construct validity asserted not validated** — no human baseline, no grader logic, no exhaustiveness argument; load-bearing instrument under-defended **[OVERREACH-FIXABLE]**; SPICE step-5 wording ("rates are unchanged") smooths over that all 12 Phase-5C SPICE episodes were zeroed, so SPICE 1.00 comes entirely from 5D **[PRESENTATION]**; L4 artifact-integrity episode attribution hand-wavy/unverifiable **[OVERREACH-FIXABLE]**; thin evidence base **[IRREDUCIBLE]**; protocol coverage (what it misses) not addressed **[PRESENTATION]**.
*Net:* marginal reject — a human-baseline grader check + grader-logic display + cleaner SPICE-5C/5D separation would move to clear accept.

## Reviewer 5 — general skeptic
**Overall 5.** (a)7 (b)5 (c)5 (d)5. Conf 4.
*Strengths:* exemplary self-bounding (detectability paragraph declines small-n bootstrap / trajectory-pooled p-value); clean within-family instrument (BundleD decoy control strong); real documented measurement threats.
*Weaknesses:* headline rests on n=1 cross-model + effectively n=3 discriminative cross-family (STA, where BundleS trends *negative* 0.33<0.50) **[IRREDUCIBLE]**; trajectory-stability "low within-instance variance" inferred from 2-rep agreement (2 obs cannot characterize variance; workflow 3-4-rep rows show disagreement) **[OVERREACH-FIXABLE]**; STA labeled "clean null" when it is null-to-negative **[OVERREACH-FIXABLE]**; related-work thin **[PRESENTATION]**; protocol not externally validated **[IRREDUCIBLE]**; dense jargon **[PRESENTATION]**.
*Net:* marginal reject — paper is not overclaiming, but the headline it foregrounds is its weakest-supported claim (n=1 cross-model, n=3 discriminative cross-family trending negative).

---

## AC Meta-review — do the remaining weaknesses justify rejection despite the bounded claims?

**Verdict: borderline (mean 4.6, median 5 = marginal reject). Rejection is defensible on the small-n grounds; it is no longer defensible on rigor or overclaiming grounds.**

The Phase-6C revisions did exactly what they were designed to do. The detectability paragraph, the trajectory-stability table, the SPICE chronology, and the softened "instantiated and stress-tested in this study" protocol language targeted the Phase-6B weaknesses, and the credit lands where it should: **claim-support/rigor rose 3.6 → 5.4**, and problem/question rose 5.4 → 6.6. Multiple reviewers explicitly praised the self-bounding and the custody-chain transparency. The paper is, by consensus, *not overclaiming*: its "diagnostic, not population-estimating" framing is judged adequate to the evidence.

**What remains is almost entirely [IRREDUCIBLE].** The binding objections are: (i) the headline rests on n=1 (cross-model tie), n=1 (within-family held-out), and n=3 (one discriminating external family, where BundleS trends negative rather than null); (ii) the audit protocol is validated only on the authors' own infrastructure (self-disclaimed as not broadly reusable); (iii) the mechanism was not isolated (component decomposition failed), so the lone positive is a black-box bundle effect for one model. None of these is fixable by writing under the experimental freeze. They are the reason the paper sits below the accept bar.

**The [OVERREACH-FIXABLE] items are cheap and worth doing before camera-ready** (none needs a model call):
1. Soften the intro "the community will systematically over-credit interventions" — generalize from n=1 less aggressively (R2).
2. Relabel the STA result from "clean null" to "null-to-negative" (BundleS 0.33 < Base 0.50 is a small negative direction, not a symmetric null) (R5).
3. Re-caption the trajectory-stability table: 2-rep agreement is *consistent with* but *under-powered to confirm* low within-instance variance (R5).
4. Reconcile the Model B discovery (0/3→3/3 full bundle) vs counterbalanced (3/4=3/4 BundleS) inconsistency explicitly (C6/answer-bearing confound) (R1).
5. Replace the five placeholder related-work citations with verified references (R1, R3, R5) — needs literature access.
6. Add a small human-baseline check on the typed grader for a sample of submissions + show grader logic — R4's named path from marginal-reject to accept, feasible without new model calls.

**Does rejection follow despite the bounded claims?** It is a genuine borderline. The paper is honest, well-bounded, and contributes at least one durable, transferable measurement insight (streaming-transport censoring of thinking models). But its *central* new knowledge — that held-out confirmation did not imply transfer — is demonstrated at n=1–3, which the freeze forbids expanding. A reviewer who weights well-bounded caution + reusable measurement traps above n-density could accept; a reviewer who requires the headline to rest on more than one held-out instance and three external instances will reject. The Phase-6C revisions converted the objection from "overclaiming + under-rigorous" (Phase-6B) to "honestly bounded but empirically thin" (Phase-6C) — a real improvement in the *nature* of the objection, modest in score (4.2→4.6) but clear in substance.

**Recommendation:** apply the six overreach-fixable revisions above (all no-model-call), then submit; expect a split-reviewer borderline outcome hinging on whether the small-n caution is valued as new knowledge.
