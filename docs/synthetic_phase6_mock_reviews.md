# Phase-6 Mock Reviewer Packet (5 skeptical reviews + AC meta-review)

**Note:** these are simulated reviews for manuscript improvement. Each identifies the two strongest rejection reasons, the existing evidence that rebuts them, any remaining fatal gap, and proposed manuscript-only changes (no new experiments).

---

## Reviewer 1: "This is only a synthetic EDA benchmark."

**Overall: 4/10 (borderline reject).**

**Strongest rejection reasons:**
1. The tasks are hand-constructed synthetic EDA workflows (tiny.db, macro-amplifier decks), not real industrial signoff flows. External validity to real chip design is untested.
2. The semantic-handoff abstraction may not reflect how real engineers interact with agents.

**Rebutting evidence (existing):**
- The tasks run on **real commercial tools** (PrimeTime V-2023.12, HSPICE S-2023.09) through a transparent b04 shim — not simulations of tools. The golden/wrong evidence is baked by real tool execution.
- The semantic-binding failure (placing a value on the wrong typed axis) is a *cognitive* failure mode that is tool-agnostic; it occurs whether the tool is PT, HSPICE, or anything else.
- The *measurement-validity* framework (9 layers) generalizes beyond EDA — it's about agent evaluation, not chip design.

**Remaining fatal gap:** the paper does not test on a real (non-synthetic) multi-artifact EDA workflow. This is a genuine scope limitation.

**Proposed manuscript changes:** (a) Reframe: "The contribution is the evaluation-validity framework and the external-validity-failure finding, not the EDA domain." (b) Add a paragraph in §3 explaining the scalar-delay / macro-amplifier abstractions are deliberate (they isolate the semantic-binding mechanism from analog-design difficulty). (c) Acknowledge in §8 that real-industrial-flow validation is future work.

---

## Reviewer 2: "There is no positive general method contribution."

**Overall: 3/10 (reject).**

**Strongest rejection reasons:**
1. The paper does not propose a method that improves agent performance; BundleS doesn't generalize; TypedContract adds nothing. The result is entirely negative.
2. An "evaluation study" without a positive contribution is below the ICLR bar.

**Rebutting evidence (existing):**
- The paper DOES have a positive within-family result (RQ1: the clarity bundle suppresses axis-binding for Qwen, confirmed held-out). The negative results are about *generalization*, which is the contribution: **external-validity failure after held-out confirmation** is a novel finding that the community needs.
- The nine-layer measurement-validity stack IS a methodological contribution (each layer caught a real threat that manufactured or masked a result).
- ICLR 2024–2026 accepted evaluation-study papers (e.g., BIG-Bench, HELM). The "no positive method = reject" heuristic is outdated.

**Remaining fatal gap:** none fatal. The framing change (§1: evaluation study, not improved harness) addresses this.

**Proposed manuscript changes:** (a) Title/abstract lead with the evaluation framework + the external-validity-failure finding. (b) §6 (measurement reliability) as a standalone contribution (not just "limitations"). (c) Cite ICLR evaluation-study precedents.

---

## Reviewer 3: "Sequential adaptation invalidates the conclusions."

**Overall: 5/10 (borderline).**

**Strongest rejection reasons:**
1. The p14 phases (4U/4V/4W/4X/4Y) were developed sequentially, each gated on prior results. This is garden-of-forking-paths: the design adapted to favorable outcomes.
2. The component decomposition (C1/C2/C4/C7/C24) was exploratory; the "no stable minimal component" result could be an artifact of the specific decomposition order.

**Rebutting evidence (existing):**
- The Phase-5 cross-family study (5C/5D) is **pre-registered**: the frozen schedule, budget, and conditions were committed BEFORE any paid call. The cross-family null is not garden-of-forking-paths.
- The p14 sequential phases are explicitly labeled "sequential exploratory localization" (not headline). The headline results are the confirmatory controlled pair + the pre-frozen held-out (both predeclared).
- The C24 bridge was a predeclared replication threshold (≥3/4 + 0 axis); its failure (`not_established`) is a clean negative, not a post-hoc rationalization.

**Remaining fatal gap:** the p14 BundleS-vs-DeepSeek null IS somewhat underpowered (k=3-4 per cell). But it's labeled "not established" (not "refuted").

**Proposed manuscript changes:** (a) Add a table showing which results are confirmatory (predeclared) vs sequential exploratory. (b) §4: explicitly state the sequential adaptation is a limitation that the predeclared Phase-5 cross-family study is designed to address.

---

## Reviewer 4: "The sample size is too small."

**Overall: 4/10 (borderline reject).**

**Strongest rejection reasons:**
1. n=3 instances per family × 2 reps = 6-8 episodes per condition. This cannot support significance testing.
2. One-episode swings (e.g., STA 0001: Base 0.5 → BundleS 0.0) could be within run-to-run variance.

**Rebutting evidence (existing):**
- The paper explicitly does NOT use significance testing as a headline. The instance is the unit; results are reported as paired directions + raw counts + descriptive bootstrap-over-3 (clearly labeled descriptive).
- The Phase-5C/5D result is a **consistent null** (0/3 improve in STA; 0 improve across all 6 instances in the contrasts). This directional consistency across instances is the evidence — not a p-value.
- The 0.33 vs 0.50 difference (STA BundleS vs Base) is small and within noise; the paper says "no improving instance" (directional), not "BundleS significantly hurts."

**Remaining fatal gap:** the small n limits the STA null's power. A reviewer could argue "with more instances, BundleS might help STA." But the paper scopes this as "lack of evidence," not "proof of no effect."

**Proposed manuscript changes:** (a) §8: state explicitly that n=3 is insufficient to rule out small effects; the claim is "transfer not established," not "transfer refuted." (b) Report the descriptive bootstrap interval for the STA contrast.

---

## Reviewer 5: "Harness-Bench / Harness evolution work already establishes the same point."

**Overall: 5/10 (borderline).**

**Strongest rejection reasons:**
1. Harness-Bench already shows harness variation affects agent performance. This paper rediscovers that.
2. "Rethinking the Evaluation of Harness Evolution" already critiques harness-leaderboard conflation. The measurement-validity stack overlaps.

**Rebutting evidence (existing):**
- Harness-Bench shows harnesses MATTER; this paper shows *which specific semantic-binding mechanism* changes, *which evaluation controls are necessary*, and *that a discovered effect can fail to transfer after held-out confirmation*. These are distinct contributions.
- The typed failure taxonomy (axis_binding vs role_conditioned_value_selection + family-specific subtypes) is novel — prior work does not decompose the failure mode.
- The external-validity-failure-after-held-out-confirmation finding is novel: prior harness work does not construct independent families + test transfer.

**Remaining fatal gap:** none fatal if the novelty statement is sharpened.

**Proposed manuscript changes:** (a) §7: sharpen the novelty statement — "controlled semantic-binding mechanisms, external-validity failure after within-family held-out confirmation, and measurement-validity auditing." (b) A direct comparison table: "Harness-Bench shows X; we show X+Y+Z." (c) Note that prior work does not report a nine-layer evaluation-validity stack or test cross-family transfer.

---

## AC Meta-review

**Assessment: borderline (5/10). Leaning weak reject for ICLR 2027 main track; potential accept with revisions.**

**Why borderline:**
- The paper has a genuine, novel finding (harness-effect-within-family vs not-established-cross-family-after-held-out). This is valuable for the community.
- The measurement-validity stack is a substantive methodological contribution (each layer caught a real threat).
- BUT the sample size (n=3/family) and the sequential adaptation within p14 are legitimate concerns that limit the strength of the conclusions.
- The framing as "evaluation study" (not "improved harness") is correct but may not satisfy reviewers expecting a positive method.

**Path to accept:**
1. Sharpen the novelty statement (§7) to distinguish from Harness-Bench / HarnessOpt-Bench.
2. Add a confirmatory-vs-exploratory table (§4) to address Reviewer 3.
3. Strengthen §6 (measurement reliability) as a standalone contribution, not just limitations.
4. Add the descriptive bootstrap interval for the STA contrast (§5).
5. Frame the SPICE ceiling as a design lesson (the SPICE Base instance is too easy — future work should increase ambiguity).
6. Acknowledge n=3 explicitly in §8 as a scope limitation; the claim is "transfer not established," not "no effect."

**Would the current paper be accepted?** Unlikely at ICLR 2027 without revision (borderline → reject due to small-n + sequential adaptation). With the above revisions + a stronger measurement-validity framing, it could clear the bar. The negative results are honest and the infrastructure is real, but reviewers will demand more instances or a stronger methodological contribution claim.

---

**Summary of reviewer scores:** R1=4, R2=3, R3=5, R4=4, R5=5. Mean=4.2. Borderline.
