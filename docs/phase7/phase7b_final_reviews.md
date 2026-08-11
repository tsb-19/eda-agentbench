# Phase-7B Final Review Packet (manuscript v3.1; official ICLR 2027 style; 5 fresh reviews + AC)

**Manuscript:** frozen v3.1 (official style, 7pp main, expanded, real citations, model names restored). 5 reviewers, each given ONLY the manuscript; no prior reviews/targets.

## Score summary
| R | Lens | Overall | Net | Resolves? |
|---|---|---|---|---|
| R1 | construct | 5 | reject | Worked example helps inspectability; human validation (Study B) still needed |
| R2 | small-n | 4 | reject | STA n=12 table + three-outcome handle the STA concern; Studies I/cross-model n=1 not rescued |
| R3 | protocol sig | 4 | reject | Clears "engineering detail" bar; not yet "significant methodological" (1/26 direct, L2=0, co-evolved) |
| R4 | prior work | 4 | reject | Structurally adequate; delta = instantiation (EDA threat log), not a new validity concept |
| R5 | general | 3 | reject | Thin cumulative; honest but insufficient for ICLR bar |
| **Mean** | | **4.0** | | median 4 |

v3.1 vs v3: 4.0 vs 4.6. The expansions improved clarity + positioning but let reviewers identify the binding weaknesses more precisely. The decline is honesty, not regression: the paper is clearer, so the irreducible limitations are sharper.

## Per-reviewer key findings (condensed)

**R1 (construct):** The worked example genuinely converts "trust the oracle" to "inspect the evidence" (a reader can read the coverage matrix and judge). Cross-family instantiation rules out a single-grader quirk. But all three oracles share authorial provenance and Study B (human validation) is unexecuted → cannot confirm human–oracle agreement on borderline value-selection cases. The construct-circularity concern is **partially but not fully resolved.**

**R2 (small-n):** The per-instance table + three-outcome framework + reversal-as-instability are "exactly the right moves" for the STA n=12 concern — the STA null is the paper's most defensible claim. But n=1 in Studies I and cross-model is not rescued: "a skeptic can grant every STA-methodological virtue and still deny that the paper has established a within-family effect worth testing for transfer." The headline "held-out confirmation did not survive external validity" dissolves into "a single held-out instance did not predict an n=12 null."

**R3 (protocol sig):** The incidents table with per-row counterfactual conclusions clears the "engineering detail dressed as science" bar — genuine scientific argument. But 1/26 direct external capture + L2=0 + the protocol's co-evolution with the incidents it catches ("discovery → transport repair → controlled pair → ... → prospective") mean it is a "well-documented candidate framework with thin external validation, not an established method."

**R4 (prior work):** The per-work gap paragraph + TAB/LongHorizon distinctions + 7 real citations are "structurally adequate." The TAB distinction (cue selection vs role-conditioned binding) is "a genuine conceptual line." But the novelty statement reduces to "the standard external-validity + protocol-validity triad" and the delta over ABC/Protocol Validity is "an instantiation (a per-control threat log on EDA) plus a fine-grained specialization," not a new validity concept.

**R5 (general):** "A paper may be both honest and insufficient." The only positive (RQ1) is n=1×k=3; the negative (RQ2) is a known external-validity principle re-observed in a new domain; the protocol has 1/26 external capture. "Reads as a careful negative-results report that would fit a workshop or position-paper track."

## AC Meta-review

**Verdict: reject (mean 4.0, median 4).** The v3.1 expansions (worked example, per-instance table, incidents table, real citations, three-outcome framework, model-selection rationale, broader implications) demonstrably improved the paper's clarity and let reviewers engage the evidence more substantively. But the binding objections are all [IRREDUCIBLE] frozen-evidence limitations, now identified with greater precision:

1. **n=1 in Studies I and cross-model** (all 5 reviewers): the headline "RQ1 supported, effect does not transfer" rests on a single held-out instance + a single cross-model instance. The STA n=12 expansion is well-designed and the paper's strongest segment, but it cannot rescue the foundational RQ1 claim from n=1.

2. **Construct validity via executable oracles only** (R1, R5): the worked example + cross-family instantiation partially resolve inspectability, but without Study B (human validation, unexecuted), the taxonomy rests on author-built oracles over author-built tasks with no external ground truth.

3. **Audit protocol: 1/26 direct, L2=0** (R3, R4): clears the engineering bar but not the significant-contribution bar. The causality argument (each control changed the headline) is genuine but internal; the only external test (Terminal-Bench) mostly fails to match.

4. **Novelty = instantiation** (R4): the delta over ABC/Protocol Validity is a per-control threat log on EDA, not a new validity concept.

These are the same limitations identified in v3 (mean 4.6), now sharper due to the expanded evidence making the paper's scope and claims more transparent. The expansions did not (and structurally could not) resolve frozen limitations; they improved exposition. **Per the directive, no experiments are reopened.** The paper is as strong as it can be without new data: a rigorously honest, infrastructure-rich evaluation study whose scientific yield is bounded by the frozen design.

**Recommendation:** submit as-is (the honesty + infrastructure + L3 transport finding + prospective direction-reversal caution are genuine contributions) with the understanding that the frozen limitations (n=1, unvalidated construct, 1/26 external) are the likely grounds for rejection. A workshop or methods-focused venue is a reasonable alternative if the main-track rejection risk is unacceptable.
