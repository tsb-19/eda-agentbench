# ICLR 2027 Submission Package (Phase-8A / manuscript v15 — **current**)

**Title:** Auditing Generalization Claims for LLM Agent Harnesses: Semantic Binding and Measurement Validity
**Style:** Official ICLR 2027 (media.iclr.cc/Conferences/ICLR2027/iclr-2027-style-files.zip).
**Deadlines: no date in this repository is authoritative.** On 2026-08-17 all three official pages
read abstract Sept 18 / full paper Sept 25, 2026 AOE (fetch and AOE↔UTC cross-check in the Deadlines
section of [FREEZE_HASHES.md](FREEZE_HASHES.md)). On 2026-08-20 the pages were reported to disagree
with each other — Author Guidelines Sept 11 / Sept 16, Call for Papers Sept 18 / Sept 25 — and that
divergence could not be independently confirmed from the build host (`iclr.cc` unreachable). v15
therefore states **no deadline in the manuscript at all**; re-check OpenReview and the Author
Guidelines immediately before submitting.

## Build
```
cd submission && make
```
Regenerate derived tables first if the frozen records change:
```
python3 scripts/phase7c_study1_ledger.py       # appendix ledger
python3 scripts/phase7c_claim_statistics.py    # k=2 stat macros + pilot table
python3 scripts/phase8a_claim_statistics.py    # k=6 stat macros + panel and concordance tables
```
**Note:** `make clean` does *not* remove `main.pdf`; use `make distclean` before any build
you intend to measure (a v9 log measurement was taken off a stale PDF — see below).

## Page boundaries
- **Main text: 9 pp** (p1–p9; limit is 9 at submission → **0 pages of headroom**, and 10 at rebuttal/camera-ready → 1 page)
- References: p10 (outside page limit)
- Appendix A–K: p11–p22 (outside page limit)
- **Total PDF: 22 pp**
- **Do not measure the main-text page count by page arithmetic.** The rule is about whether main text
  appears above the `REFERENCES` heading on the heading's own page — during v13 an intermediate state
  reported "9 pp" because references began on p10, with 580 words of main text above them on that same
  page. This is now enforced by code:

  ```bash
  python3 scripts/submission_page_limit_check.py     # PASS: main text ends on page 9 (limit 9)
  ```

  It is fail-closed (missing PDF, missing `pdftotext`, unlocatable heading, empty extraction and
  unexpected top-margin text all fail rather than pass), was proven against a deliberately overflowing
  build, and independently re-confirms the frozen v12 PDF at 9 pp.
- **Layout fact:** cuts made *before* the last float do not shorten the tail — the floats repack and
  absorb the space. Only cuts after the final table (Table 3) move the page-9 boundary.

## Contents
| File | Purpose |
|---|---|
| main.tex | v15 source (official style; 3-study/RQ; **evidence-support** claim lattice + 2D framework) |
| main.pdf | Compiled PDF (anonymous; 0 leaks) |
| tables/study1_ledger.tex | Appendix ledger, generated — `\input` directly, never transcribed |
| tables/claim_stats.tex | Generated `\newcommand` macros for every interval/band/p-value in the prose |
| tables/sta_pilot.tex | Generated three-instance pilot table |
| tables/phase8a_stats.tex | Generated macros for every k=6 number in the prose |
| tables/sta12_k6.tex | Generated primary S2-F panel table (12 instances, k=6) |
| tables/sta_concordance.tex | Generated cross-batch class/sign table (post hoc; not pooling) |
| references.bib | 20 REAL verified citations (arXiv primary source; no placeholders) |
| iclr2027_conference.sty/.bst | Official ICLR 2027 style |
| natbib.sty / fancyhdr.sty | Bundled (from official style package) |
| math_commands.tex | Optional math macros (from official package) |
| Makefile | One-command build |
| FREEZE_HASHES.md | SHA-256 hashes + compliance audit |
| ANONYMITY_AUDIT.md | Double-blind audit (PASS) |

## v15 (Phase-8A: the k=6 STA panel becomes the primary S2-F evidence; **no paid calls in this revision, no experimental record altered**)

v14 reported S2-F from a twelve-instance panel at two repetitions per cell. Two repetitions cannot
resolve a cell's own value, so a separately preregistered batch re-ran the **same twelve frozen
instances at k=6** (216 episodes). v15 makes that batch the primary S2-F evidence and keeps the k=2
batch as the earlier prospective study that motivated raising k.

**The two batches are never pooled.** No quantity is summed, averaged or differenced across them,
their episode counts are not added, and there is no k=8 panel. The stated reason is that they are two
independent executions — the second a preregistered higher-replication follow-up — **not** that their
serving endpoints differed. The endpoint change is disclosed once, under model custody, as a fact and
not as an experimental factor.

| | v14 | v15 |
|---|---|---|
| Primary S2-F evidence | 12 instances, k=2, +12.5 pp, band −12.5 to +41.7 | **12 instances, k=6, −2.8 pp, band −31.9 to +26.4** (216 episodes) |
| k=2 panel | the result | retained as the **earlier batch**, reported separately |
| Instance heterogeneity | 6 floor / 1 ceiling / 5 informative, stated post hoc | same anatomy at k=6, plus **10 of 12 instances identically classified** and 4 of 4 signs agreeing across batches (post hoc) |
| Within-cell stability | invisible at k=2 | **7 of 36 cells** disagree across six identical repetitions |
| S3 | "not measured" (methodological reason) | **"not executed"** — preregistered as a second arm and refused by a preregistered cost gate. Never a negative result |
| Serving endpoint | one endpoint throughout | disclosed change, explicitly **not** an experimental factor |
| Process defects | — | three **accounting requirements** in Appendix J; none in the main text |
| Claim-qualification table | Table 1, main text | moved to Appendix E (page budget; prose standard stays in §3.1) |
| Deadline line in the paper | stated Sept 18 / Sept 25 | **removed** — the official pages disagreed and the repo asserts no date |
| Total PDF | 20 pp | 22 pp (main text 9 pp, unchanged) |

### Page cost

Main text was already exactly 9 pp with zero slack, and the k=6 material is a net addition, so it had
to be paid for. Confirmed again the hard way: cuts made *before* the last main-text float are fully
absorbed by float repacking — two rounds of trimming §1–§4 moved the boundary by exactly zero words.
The budget came from (a) relocating the claim-qualification table to Appendix E, (b) compressing the
three §5 paragraphs whose full versions live in Appendices G and J, and (c) tightening §6–§7. No
result, number, caveat or limitation was dropped; the reference-standard incident narrative moved to
Appendix J and the verdict-pairing detail to Appendix G, both of which already carried them in full.

## v14 (Phase-7E: direct-answer disclosure excluded; **no paid calls, no new episode, no EDA tool run, no previously reported number moved**)

A mock expert review of v13 surfaced the one alternative explanation that could have materially
weakened the paper's only positive result — that BundleS narrows the answer to one rather than
helping the agent reason. v13 had itself flagged this as "the single most informative experiment not
yet run"; it turned out to need no experiment, only deterministic enumeration over already-frozen
files. Reading a condition's own disclosure and never the task evidence, BundleS leaves **9 to 147 of
294** candidate assignments and never one, at S0 and at the pre-frozen held-out instance, while the
deliberately answer-bearing component C6 collapses the sign-off pair to one. Direct answer disclosure
is excluded; softer informational advantage is explicitly **not**, and the Base/BundleS contrast is
deliberately not an equal-information comparison.

Four correctness items travelled with it: task constraints relabelled **K1–K5** to split them from
the clarity components C1–C7 (constraint K5 is what component C6 asserts); S3's absence given its
methodological reason rather than left bare; the prospective panel's **6 floor / 1 ceiling / 5
informative** structure disclosed with its leave-two-out figure of −5.0 pp; and classical
generalizability and validity theory cited, having previously been used in substance and referenced
nowhere. Main text stays at 9 pp — every addition was paid for after the last float.

  ```bash
  python3 scripts/phase7e_answer_identifiability.py --check   # 294 universe; BundleS 9–147, never 1
  ```

## v13 (Phase-7D: measured result promoted ahead of the framework; **no paid calls, no experimental record altered, no derived number moved**)
v12's abstract opened on the claim-scope framework — a method of description — while the paper's
sharpest concrete result sat unquantified in its own grading substrate. Phase-7D quantifies it, and
v13 reorders the paper around it. Two reasons the v12 freeze was reopened deliberately rather than
patched at rebuttal: the result is a result, not infrastructure; and arXiv:2605.10448 was public
*before* the v12 freeze and uncited by it.
- **The measured result.** Pairing each frozen episode's semantic verdict with its family's own
  pre-existing tool-success field, the tool signal is **constant** (accept) across all **169**
  pairing-verified trajectories, accepting all **82** semantically wrong bindings. Against semantic
  correctness it therefore has zero empirical discrimination, and the typed oracle carries the whole
  measurement. SPICE-5D is the negative control (18/18 correct, oracle and tool agreeing).
- **Four load-bearing qualifiers in the abstract's first sentence** — *our*, *deliberately
  tool-green*, *retrospective audit*, *hash-verified pairing*. Do not trim any of them for concision:
  without them the sentence reads as a general claim about agent evaluation, which the data does not
  support.
- **Contributions reordered** to (1) semantically attested evaluation, (2) the two binding-failure
  subtypes, (3) claim-scope framework + qualification standard carrying the transfer study,
  (4) measurement validity as *verdict-to-artifact binding + reference-standard custody*.
- **9 of 58 workflow episodes excluded** because the recorded tool verdict did not attest the final
  submitted artifact; tuple equality would have caught two of nine. Not nine mis-scored episodes —
  the frozen grader already flagged the broken stage chain — but proof that a post hoc paired
  analysis must re-establish pairing rather than assume it.
- **Harness scope stated as a limitation (§7).** "Harness" here is the *task-level information
  structure* of §2, not the agent scaffold. Every episode ran through our own controlled research
  runner and no production coding agent was tested, so the 82-of-169 occupancy rate is a property of
  that scaffold and does not extrapolate. What does not depend on the scaffold: a tool-success field
  cannot discriminate role binding — that is a property of the task and its oracle.
- **Four citations added (12 → 16)**, each verified against arXiv before use. v12's decision not to
  cite concurrent arXiv work is reversed only for these four, which bound what is novel here.
- **Page cost paid by relocation, not deletion.** Main text was at 9 pp with 0 headroom and the
  additions cost ~770 words. Four blocks moved to appendices intact (falsifiability conditions → D;
  four-tier definitions → E; concurrent-works prose → J; Phase-7D accounting → F), one §6 paragraph
  was folded into §7's Discussion, which already carried its point, and duplicated prose was
  compressed to state things once. **No claim was deleted**, and all three generated tables are
  byte-identical to v12 — the mechanical proof no derived number moved.
- **v12 is not rewritten.** Its source and PDF hashes stay in `FREEZE_HASHES.md` as an immutable
  historical snapshot; v13 is a new freeze.

## v12 (fifth reviewer-standard read — **structural audit closed; manuscript frozen**)
No conceptual, statistical or evidence-to-claim objection remains at reject level; the review ended
the defect hunt and recorded that the dominant risk is now over-optimization, not unfound defects.
Three non-decision-critical wording items remained. **`main.tex` is the only artifact changed; a
numeric-token diff of the v11 and v12 PDFs is identical (830 = 830), so no number moved.**
- **`claim` vs `evidence-for-a-claim` shorthand made consistent with v11's E/T split.** Five
  sentences still read "indexes *a claim* by the set of configurations *its evidence* occupies",
  naming the claim as the indexed object — the exact conflation §1 now separates. Abstract, §1
  Contribution (1) and both §2 Positioning occurrences now index **the evidence for** a claim; the
  Conclusion reads "indexes the evidence supporting a claim by its measured configuration support".
  Not a new defect — an inherited shorthand the E/T distinction made conspicuous.
- **The sensitivity band now names what the resampling perturbs.** §5's "how strongly the estimate
  depends on *which* instances the panel happens to contain" → "on the panel's *empirical
  composition*", matching Appendix C's stricter statement that with-replacement draws duplicate and
  omit instances, so what moves is the panel's empirical **weighting**. Two words shorter.
- **One deliberate non-edit, recorded.** Appendix C's "We deliberately do not add a third interval or
  a hierarchical model…" is correct and is **kept**, but is now recorded in `FREEZE_HASHES.md` as the
  head of the page-cost queue for any camera-ready trim, since the factual limitation is fully carried
  by the two preceding sentences.
- **No page cost:** +5 words document-wide (8762 → 8767), no line added. Main text 9 pp, total 15 pp.
- **No citation added** (still 12): ICLR 2027 policy does not require comparison against arXiv-only
  concurrent work and its absence is not a rejection basis, so the newly-surfaced concurrent
  preprints (Harness-IF 2608.11727, ACM 2608.11166, and the five from the v11 round) are not cited.

## v11 (fourth reviewer-standard read; no paid calls, no experimental record altered, **no derived number moved**, **`main.tex` is the only artifact changed**)
The configuration-support formalization held and the scope-lattice line of objection closed. Two
wording-level items remained; no new citation was added (the review advised against spending
main-text space on concurrent arXiv work, and ICLR policy does not require it).
- **Evidence support `E` separated from claim target `T`.** v10 said a claim *is indexed by* the
  measured set, while the top tier (*Generalized*) is inference to a **population** — two different
  objects, since a generalized claim has `E ⊊ T`. The lattice orders `E`, the measured set that
  *audits* a claim; a claim may name a wider target support `T`, and `E = T` only when nothing is
  generalized. §3.1's four tiers now carry their `E`/`T` relation, so *Estimated on a fixed panel* is
  `T = E` and *Generalized* is the one tier asserting `T ⊋ E`.
- **Two BundleS leakage sentences downgraded** to what the design actually shows, since the
  bundle-only leakage control is acknowledged as unrun: "cannot encode any one instance's
  assignment" → "contains no explicitly instance-specific assignment field"; "not attributable to
  disclosing the assignment" → "not attributable to **explicit C6 disclosure** of the assignment".
  No experiment was run — this aligns the claim with the limitation §7 already states.
- **Page cost paid by deleting duplication, not content:** §6's "Why the controls materially
  affected interpretation" was reciting Table 4's own third column in prose; the monitor-custody
  paragraph's closing sentence duplicated the clause before it; a rhetorical closer and a paragraph
  break were removed. §3.1 untouched. Main text stays 9 pp.
- **A v10 miscount corrected:** the v10 record claimed 25 `establish*` occurrences. Hyphenated
  line-breaks in `pdftotext` output hid four of them; the true count is **29**, and the same method
  on the committed v10 PDF also gives 29 — the text did not change, the earlier measurement was low.
  All 29 re-audited: 0 positive uses about our own results.

## v10 (third reviewer-standard read; no paid calls, no experimental record altered, **no derived number moved**)
The v9 statistical fix held and the estimand objection was withdrawn. One structural issue remained,
plus four smaller items.
- **Scope is now a configuration support, not a product of marginals.** v9 wrote a claim as a triple
  `S=(s_I,s_M,s_F)` under the product order, which silently asserts that instance scope and family
  scope are *independent* coordinates. They are not: **instances are family-specific**, so a
  family-widening probe necessarily introduces new instance identities and cannot be a pure move in
  `s_F`. A claim is now indexed by the set of **configurations** `C ⊆ {(f,i,m)}` ordered by
  inclusion, with `s_I = π_I(C)`, `s_M = π_M(C)`, `s_F = π_F(C)` as **projections**. This also makes
  the study's central omission a fact about the support rather than a caveat in prose, because
  `π_F(C) × π_I(C) × π_M(C) ≠ C` in general — a support is *sparse* in the product of its own
  projections, so having widened every projection somewhere is **not** having measured every
  configuration. That is exactly why S3 is unmeasured even though `s_M` and `s_F` were each widened.
  §3.1 now says outright that a cross-family replication is never a replication in `s_F` alone.
- **"Five points" vs "coordinate class" reconciled.** The Introduction claimed the evidence occupied
  *five points* while the main-result caption said S2-F is a *class*, not a point. Both statements
  cannot hold. The Introduction now reads "four of the five named scope regions … across five
  distinct supports", and S2-F is described as a class of two incomparable family-widening supports.
- **The 95% band says what kind of 95% it is.** First occurrence is now spelled out as *the central
  95% of the with-replacement instance-resampling distribution*, then abbreviated "95% sensitivity
  band", with the note that with-replacement draws duplicate some instances and omit others — so
  what is perturbed is the panel's **empirical weighting**, and the 95% is a quantile range of that
  perturbation distribution, **not a coverage probability**.
- **A limitation the band does not cover is now stated.** It does not quantify trajectory-level
  Monte-Carlo uncertainty; at two repetitions per instance–condition cell the latent per-cell success
  probabilities are poorly resolved. We deliberately do **not** add a third interval or a
  hierarchical model for it — that would blur the preregistered/post-hoc boundary — and say so.
- **"The only basis on which anything is decided" → "the sole basis for the confirmatory verdict."**
  The descriptive estimate and the sensitivity band do inform how a reader reads the data; only the
  confirmatory verdict rests solely on the preregistered analysis.
- **The pilot reversal is now in the main text with its number** (`−16.7pp` pilot vs `+12.5pp`
  prospective panel, both from generated macros). Reviewers are not required to read the appendix,
  and the reversal is load-bearing in the abstract, contributions and discussion. The replacement
  sentence is shorter than the one it replaced.
- **AFTER added; novelty repositioned.** arXiv:2606.23127 (Belikova et al., verified 2026-06-22)
  evaluates procedural-skill transfer under separate local / cross-task / cross-role / cross-model
  settings. Reporting several transfer dimensions is therefore **not** claimed as new; the
  contribution is stated as the *indexing* — a claim located by the set of configurations its
  evidence occupies, separating *measured and unestablished* from *never measured*.
- **Page cost paid by moving the positioning table (Table 1) to Appendix G.** Its third column was
  verbatim-equivalent to the §2 prose beside it. Main text stays at 9 pp; §3.1 preserved intact.
  Total stays 15 pp.
- **Correction to the v9 record: v9 did not have 0 overfull hboxes.** The v9 "0" was measured from a
  log produced by a build that never ran (`make clean` leaves `main.pdf` in place, so `make` was a
  no-op). A `make distclean` rebuild of commit `7c2f9c4f` shows **3** overfull hboxes — the same
  three tables and the same magnitudes (4.2 / 10.3 / 4.2 pt) reported for v8. They are fixed here by
  setting `\tabcolsep` to 4pt in those three tables; v10 is **genuinely 0**, verified on a
  distclean build.

## v9 (second reviewer-standard read; no paid calls, no experimental record altered, **no derived number moved**)
The v8 fixes held. One statistical objection and three definitional gaps remained; all are fixed.
- **The fixed-panel estimand and the bootstrap disagreed → reframed as a sensitivity band.** v8
  declared the estimand to be the *realized* 12-instance panel while attaching an interval produced
  by **resampling instances** — which changes the panel rather than quantifying uncertainty about
  it. The quantity (unchanged: +12.5pp, −12.5 to +41.7) is now an **instance-resampling sensitivity
  band**, stated as measuring how far the estimate moves under perturbation of panel membership,
  used for no test and no decision. The defensive claim that it "introduces no second inferential
  channel, since no p-value is re-derived" is **deleted** — an interval is an inferential output
  either way. Macros and the shipped JSON key were renamed to match (`bootstrap_ci95` →
  `instance_resampling_band95`).
- **Lattice coordinates are now literally nested sets.** v8 asserted coordinatewise containment but
  wrote each coordinate as a progression; a held-out instance does not *contain* a development
  instance. Each coordinate became a **set of support points**, widening = adding points.
  *(Superseded in v10: sets of support points per coordinate still over-claimed independence
  between instance and family scope; see the v10 section.)*
- **"Replicated" no longer counts a new run window.** Re-running the *same* support point is
  **repeated measurement** (stability), not scope replication; replication requires a newly frozen
  support point of the coordinate being claimed. Table 2 gains a row making this operational. Our
  own S1 claim is unaffected — S1 adds an instance, so it replicates in `s_I`.
- **Model-custody counts stated exactly.** Not "66 of 70 … but never a snapshot", which implied the
  other 4 might have one: **0 of 70** retained a provider-resolved snapshot (the field does not
  exist in the record), **66 of 70** retained even the alias and run date, **4** carry no transport
  record at all. The generator now asserts the 0 and fails the build if that ever changes.
- **S2-F labelled a coordinate class**, not a point: STA and SPICE widen `s_F` to two incomparable
  support sets.
- **Two concurrent references added** (arXiv 2607.28802 *Model or Harness?*; arXiv 2608.00794
  *Measurement Without Validity*), each fetched and verified before citing. This was the first change
  to `references.bib` since v5 — **additions only**, all 9 prior entries byte-identical.
- **Page cost paid by moving the 12-instance STA table to Appendix C.** Main text stayed at 9 pp;
  §3.1 (Claim qualification) preserved intact. Total 14 → 15 pp.

## v8 (reviewer-standard read; no paid calls, no experimental record altered)
Two structural defects were found in v7 and verified against the source. Both are fixed.
- **The "claim-scope ladder" was not a valid order → now a lattice.** v7 asserted that passing a
  lower level is *necessary* for a higher one, but cross-model and cross-family widen **incomparable**
  coordinates — and v7's own Level-3 test held the model fixed at the Level-2 failure. A claim became
  a point `S=(s_I,s_M,s_F)` under a **partial order**: S0, S1, S2-M, S2-F, and **S3 (joint), which
  this study never measured** and now reports as an empty cell in the main result table and Figure 1
  rather than as a failed level.
- **Positive results were held to a looser bar than negative ones → now symmetric.** v7 said the
  effect "is real" and that "Level 0 and Level 1 are established" while the same paragraph conceded
  each rests on one instance (Fisher `p=0.40`). A stated four-tier standard (observed / replicated /
  estimated on a fixed panel / generalized) is now applied to our own results: BundleS is *observed*
  at S0, *replicated* once at S1, and nothing more. **Zero positive uses of "established" remain.**
  Table 2 maps evidence shapes to licensed and unlicensed wordings.
- **Offline statistics (no new data).** Exact Clopper-Pearson intervals and exact-rational Fisher for
  every headline cell; the STA panel now leads with **+12.5pp** instead of `p=1.0`, which
  non-specialists misread as a demonstrated zero. The preregistered test is unchanged and still
  reported.
- **Three-instance pilot published** (−16.7pp vs the prospective +12.5pp), so the claimed direction
  reversal is auditable; the generator asserts the signs differ.
- **Model custody added as a fifth Layer-4 requirement, stated as our own gap:** run windows span 22
  days and no provider-resolved snapshot was retained, so backend drift cannot be excluded from the
  across-window variation the paper interprets.
- **Incident table gained its missing Capability row**; "non-answer-bearing" →
  "instance-answer-independent"; "independent validity layers" → distinct, interacting dimensions;
  Study B, family-scope and audit-protocol-provenance limitations strengthened; explicit
  exploratory/confirmatory chronology with freeze points (Appendix E).
- **Ledger JSON rule string corrected** — it still carried the one-part rule left over from the v7
  accounting patch. No derived number moved (`study1_ledger.tex` byte-identical).
- **Page cost:** main text 8 pp → 9 pp (at the limit). The taxonomy figure was deleted; the 21-row
  ledger and the worked-instance table moved to the appendix.

## v7 (accounting + review fixes)
- **Study I ledger recomputed under an enforced inclusion rule.** The v6 ledger's 54 episodes were a
  dict-overwrite artifact, not a declared sampling frame; the generator now **asserts each stage's
  count against the frozen program manifest**. Totals 54 → 70 episodes, 29 → 41 correct, 20 → 24
  axis-binding (70 = 58 program primary + 12 controlled pair).
- **Episode accounting closed.** The frozen manifest's `program_totals.primary = 58` is exactly the
  sum of its ten ablation-phase rows and contains no 4U/4V row, so the 12 controlled-pair episodes are
  paid and gradeable but not program-primary; the `58+24+36+72` totals and the ¥745.29 cost ledger
  are unchanged.
- **Over-claim removed (§4):** "*exactly* the conditions that carry value-domain information" was
  contradicted by C2-only and C4-only in the same table.
- **Limitation corrected; two softenings** (custody principle; falsifiability).

## v6 (main-text expansion; manuscript-only, no experiments reopened, no number changed)
v5 used only 5 of the 9 permitted main-text pages while its load-bearing evidence sat in appendices
that ICLR reviewers are explicitly not required to read. v6 moves that evidence forward and adds
exposition; a mechanical token diff confirms every number in the v5 PDF survives unchanged.
- **Worked instance (§3):** one real frozen task rendered in full — five constraints, 294→1 uniqueness,
  and the four shipped evidence sources. Source A has the right netlist *and* clock and signs off
  **green** with its role fields swapped: the paper's *tool-green* concept made concrete.
- **Typed-oracle adjudication (§3):** the membership predicates, PVT-descriptor exclusion, exact clock
  identity, and the two never-collapsed failure subtypes.
- **Study I per-condition ledger promoted to main text (Table 5):** all 16 cells; sums verified against
  the 54/29/20/5 already stated in §4; regenerated byte-identically by a committed script.
  **(Superseded in v7: that 54-episode set turned out to be a dict-overwrite artifact, not a
  declared sampling frame; see the v7 section.)**
- **Reference-standard custody principle (§5):** the canonical-source incident restated as a general
  Layer-4 requirement — health-check reference standards must be isolated from the harness they certify.
- **Falsifiability section (§7):** what evidence would overturn or resolve each rung of the ladder.
- **Reproducibility paragraph relocated** into the page-limit-exempt statement, and expanded.

## v5 (final-review patch)
- Fixed an internal inconsistency the review surfaced: Table 3 (`tab:sta12`) hid instance 0007 (a decline) inside an all-tie aggregate; expanded to all 12 rows so the table matches the prose (3/2/7), the sign-test (p=1.0), and the permutation (Σ=1.5, p=0.31).
- Claim wording: "clean null" → "not established" (abstract/§5/figure).
- Measurement language: "false ceiling" → "spuriously zeroed; semantic-binding ceiling obscured"; "Why the controls are causal" → "materially affected interpretation".
- Removed the L1–L4 (validity) vs Level 0–3 (claim scope) label clash → `Cap./Samp./Exec./Art.`
- AI-use statement expanded to the ICLR 2027 AI-policy scope.
- Appendix B now writes out the frozen sign-test + permutation procedure.
- Added 2 arXiv-verified citations: HarnessAudit (Liu et al. 2026), Safety-or-Capability (Wang et al. 2026).
- Title shortened; Table 2 `n`→`#inst.`; `\hypersetup{hidelinks}`.

## Inherited from Phase-7B/v4
- Model names restored: Qwen3.7-Max, DeepSeek-V4-Pro (public; not author-identifying).
- Official ICLR 2027 style; claim-scope ladder (L0–L3) + 2D scope×validity framework.
- Deadlines Sept 18/25 AOE.
