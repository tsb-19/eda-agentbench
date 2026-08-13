# ICLR 2027 Submission Package (Phase-7C / manuscript v8)

**Title:** Auditing Generalization Claims for LLM Agent Harnesses: Semantic Binding and Measurement Validity
**Style:** Official ICLR 2027 (media.iclr.cc/Conferences/ICLR2027/iclr-2027-style-files.zip). **Deadlines:** abstract Sept 18 2026 AOE; full paper Sept 25 2026 AOE.

## Build
```
cd submission && make
```
Regenerate derived tables first if the frozen records change:
```
python3 scripts/phase7c_study1_ledger.py       # Table 3 (appendix ledger)
python3 scripts/phase7c_claim_statistics.py    # stat macros + pilot table
```

## Page boundaries
- **Main text: 9 pp** (p1–p9; limit is 9 at submission → **0 pages of headroom**, and 10 at rebuttal/camera-ready → 1 page)
- References: p9, after the Conclusion (outside page limit)
- Appendix A–F: p10–p14 (outside page limit)
- **Total PDF: 14 pp**

## Contents
| File | Purpose |
|---|---|
| main.tex | v8 source (official style; 3-study/RQ; claim-scope **lattice** + 2D framework) |
| main.pdf | Compiled PDF (anonymous; 0 leaks) |
| tables/study1_ledger.tex | Appendix ledger, generated — `\input` directly, never transcribed |
| tables/claim_stats.tex | Generated `\newcommand` macros for every interval/p-value in the prose |
| tables/sta_pilot.tex | Generated three-instance pilot table |
| references.bib | 9 REAL verified citations (arXiv primary source; no placeholders) |
| iclr2027_conference.sty/.bst | Official ICLR 2027 style |
| natbib.sty / fancyhdr.sty | Bundled (from official style package) |
| math_commands.tex | Optional math macros (from official package) |
| Makefile | One-command build |
| FREEZE_HASHES.md | SHA-256 hashes + compliance audit |
| ANONYMITY_AUDIT.md | Double-blind audit (PASS) |

## v8 (reviewer-standard read; no paid calls, no experimental record altered)
Two structural defects were found in v7 and verified against the source. Both are fixed.
- **The "claim-scope ladder" was not a valid order → now a lattice.** v7 asserted that passing a
  lower level is *necessary* for a higher one, but cross-model and cross-family widen **incomparable**
  coordinates — and v7's own Level-3 test held the model fixed at the Level-2 failure. A claim is now
  a point `S=(s_I,s_M,s_F)` under a **partial order**: S0, S1, S2-M, S2-F, and **S3 (joint), which
  this study never measured** and now reports as an empty cell in Table 4 and Figure 1 rather than as
  a failed level.
- **Positive results were held to a looser bar than negative ones → now symmetric.** v7 said the
  effect "is real" and that "Level 0 and Level 1 are established" while the same paragraph conceded
  each rests on one instance (Fisher `p=0.40`). A stated four-tier standard (observed / replicated /
  estimated on a fixed panel / generalized) is now applied to our own results: BundleS is *observed*
  at S0, *replicated* once at S1, and nothing more. **Zero positive uses of "established" remain.**
  New Table 2 maps evidence shapes to licensed and unlicensed wordings.
- **Offline statistics (no new data).** Exact Clopper-Pearson intervals and exact-rational Fisher for
  every headline cell; the STA panel now leads with **+12.5pp (interval −12.5 to +41.7)** instead of
  `p=1.0`, which non-specialists misread as a demonstrated zero. The preregistered test is unchanged
  and still reported.
- **Three-instance pilot published** (−16.7pp vs the prospective +12.5pp), so the claimed direction
  reversal is auditable; the generator asserts the signs differ.
- **Model custody added as a fifth Layer-4 requirement, stated as our own gap:** run windows span 22
  days and no provider-resolved snapshot was retained for any of the 70 episodes, so backend drift
  cannot be excluded from the across-window variation the paper interprets.
- **Table 6 gained its missing Capability row**; "non-answer-bearing" → "instance-answer-independent";
  "independent validity layers" → distinct, interacting dimensions; Study B, family-scope and
  audit-protocol-provenance limitations strengthened; explicit exploratory/confirmatory chronology
  with freeze points (Appendix E).
- **Ledger JSON rule string corrected** — it still carried the one-part rule left over from the v7
  accounting patch. No derived number moved (`study1_ledger.tex` byte-identical).
- **Page cost:** main text 8 pp → 9 pp (at the limit). Figure 2 deleted; the 21-row ledger and the
  worked-instance table moved to the appendix.

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
