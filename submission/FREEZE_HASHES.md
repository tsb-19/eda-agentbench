# Phase-7C Final Submission Freeze (v6 — main-text expansion)

**Submission HEAD:** the commit that adds this file (v6 expansion over v5 = 3d3e77b, tagged `iclr2027-submission-v1`).
**Experiment freeze HEAD:** a89e084 (immutable; no new experiments — v6 is manuscript-only).

## v6 expansion summary (manuscript-only; no experiments reopened)

v5 used 5 of the 9 permitted main-text pages. Because ICLR reviewers are explicitly *not* required to
read the appendix, load-bearing evidence sitting in appendices was effectively invisible to review.
v6 moves that evidence into the main text and adds exposition. **No experiment was reopened, no
number was changed, and no verdict was altered.** Verified mechanically: every numeric token present
in the v5 PDF is still present in the v6 PDF (nothing dropped or edited); the only new numeric tokens
are the five per-condition ledger cells (`0/3`, `0/4`, `1/4`, `2/3`, `2/4`).

1. **Worked instance + evidence table (§3, new).** One real frozen workflow instance rendered in full:
   the five recoverable constraints, the 294→1 uniqueness, and the four shipped evidence sources with
   the constraint each violates. Source A carries the right netlist *and* clock and **signs off green
   under PrimeTime** while its two role fields are swapped — the paper's *tool-green* concept made
   concrete rather than asserted.
2. **Typed-oracle adjudication (§3, new).** How semantic correctness is decided: typed-membership
   predicates, PVT-descriptor exclusion, exact clock identity, folding into the master evidence gate,
   and the two never-collapsed failure subtypes. Pre-empts the natural objection that the oracle
   defines the result.
3. **Study I per-condition ledger promoted to main text (Table 5, §4).** The full 16-cell
   model × condition ledger, previously a two-line appendix summary. Rows sum exactly to the
   54 classified episodes / 29 correct / 20 axis-binding / 5 value-selection already stated in §4
   (arithmetic re-verified). Machine-derived: `scripts/phase4z_figures_tables.py` regenerates the
   source table byte-identically from the preserved per-episode records.
4. **Reference-standard custody principle (§5, new).** The canonical-source incident restated as a
   general condition on measurement apparatus — *the reference standards of health checks must be
   isolated from the harness whose health they certify* — added as a fourth Layer-4 requirement.
   The monitor's logic was correct and its mismatch real; only the attribution was wrong. Development
   workspace only; no reported measurement derives from it.
5. **Falsifiability section (§7, new).** Per-rung statement of what evidence would overturn or resolve
   each verdict, plus the asymmetry that two measurement results are not contestable by re-analysis.
6. **Reproducibility paragraph relocated.** Moved out of §7 (where it consumed main-text pages) into
   the Reproducibility Statement, which ICLR excludes from the page limit, and expanded.

## SHA-256 hashes (frozen artifacts, v6)
| Artifact | SHA-256 |
|---|---|
| Source (main.tex) | 75b9cca7fc500c579f32a6451455353638800799c4099f3ae0c732a4d4061002 |
| Final PDF (main.pdf, 11 pp: 8 main + refs + appendix) | d09a1f2b3f91305043a08aaa41763e381c9484a695397dec8b1efebca785a1a1 |
| Bibliography (references.bib, 9 entries) | 867562f4be4a6c576bdfd3752e8e7e20ad50885a58214f3cd2dda330b99c9670 |
| Style (iclr2027_conference.sty) | 797deef41724e93761426ac0cbcca46279a91cc650dd1f0ce76a4f08d2098ea6 |
| Bibstyle (iclr2027_conference.bst) | 2d67552db7ed38ccfccb5957b52f95656e25c249724761d3cf5f7922ad1844c5 |
| Claim-evidence matrix (docs/phase7/phase7_synthesis.md) | 9dbecd9fedc65ac19bc5ab1c14589013942f746cf18c2b3900c9627b317f961b |

`references.bib`, the style files and the claim-evidence matrix are **unchanged from v5** (hashes
identical), which is itself evidence that no citation or claim-matrix content moved in this revision.

Source-archive and supplement-archive tarball hashes are recomputed at final OpenReview packaging.

## ICLR 2027 compliance audit
- Main text <=9 pages: **PASS** (8 pp main text, p1–p8; official iclr2027 style; 1 page of headroom
  deliberately retained for the rebuttal phase, where the limit rises to 10).
- References outside page limit: **PASS** (references begin p8, after the Conclusion; run to p9).
- Appendix after references: **PASS** (appendix begins p9, after references; runs to p11).
- Double-blind anonymity: **PASS** (0 infra/path/user/credential/repository leaks in PDF text; re-run
  against the v6 PDF. Public model names Qwen3.7-Max/DeepSeek-V4-Pro retained — they do not reveal
  author identity. The worked instance uses only frozen task content, which carries no identity.)
- PDF metadata anonymous: **PASS** (Title/Author/Subject/Keywords empty).
- AI-use statement: **PASS** (present, outside page limit; ICLR 2027 policy scope).
- Ethics statement: **PASS** (accurately records Study B as preregistered-but-unexecuted).
- Reproducibility statement: **PASS** (present, outside page limit; now also carries the program
  totals and the re-derivation scripts formerly in §7).
- No private endpoint/path/user/credential metadata: **PASS**.
- Citations: **PASS** (9 entries, all verified against arXiv primary source; 0 placeholders; unchanged
  from v5).
- Build: **PASS** (pdflatex+bibtex; 0 undefined refs/citations; 0 errors; bibtex 0 warnings).
- Typesetting: **PASS** (33 overfull/underfull boxes — byte-for-byte the same count as a rebuild of
  the frozen v5 source, i.e. the expansion introduced no net typesetting regression).
- No number changed vs v5: **PASS** (mechanical token diff of both PDFs; see above).
- OpenReview profiles: **HUMAN STEP** — authors must register before abstract deadline (Sept 18, 2026 AOE).

## Provenance of the two frozen points
- `iclr2027-submission-v1` → `3d3e77b` — v5, the earlier submission-ready freeze. **Not moved.**
- This commit → v6. Post-v5 repository-maintenance commits (docs de-staling, archival, the
  `test_fullpath_check` canonical-golden fix) sit between them and touched no scientific artifact.

## Deadlines (official ICLR 2027 site)
- Abstract: September 18, 2026 AOE.
- Full paper: September 25, 2026 AOE.
