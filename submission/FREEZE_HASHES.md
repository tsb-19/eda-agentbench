# Phase-7C Submission Freeze (v10 — configuration-support scope lattice)

**Submission HEAD:** the commit that adds this file.
**Experiment freeze HEAD:** a89e084 (immutable). **v10 ran no model calls and altered no experimental record.**
**Previous freezes:** v9 = `7c2f9c4f` (committed, never tagged). v8 = `83379da4` (committed, never tagged). v7 = `5858d843`, tagged `iclr2027-submission-v2`. v5 = `3d3e77b`, tagged `iclr2027-submission-v1`. **Neither tag moves.**

## Why v10 exists

A third full reviewer-standard read confirmed the v9 statistical fix and withdrew the
estimand objection. It left **one structural issue** in the scope formalization, plus four
smaller items and one citation. All are fixed here. No experiment was reopened; every change is
definition, wording, relabelling or placement. **No derived number moved in v10** — all three
generated tables are byte-identical to v9, verified by diff.

### 1. Scope is a configuration support, not a product of marginals (the load-bearing fix)

**Defect.** v9 wrote a claim as a triple $S=(s_I,s_M,s_F)$ under the product order, which asserts
that instance scope and family scope are *independent* coordinates. They are not. **Instances are
family-specific**: an STA instance is not a workflow instance evaluated elsewhere. So the move
S0 → S2-F(STA) does not widen $s_F$ alone — it necessarily introduces twelve new instance
identities at the same time, and no purely marginal formulation can say so.

**Fix.** A claim is now indexed by the set of **configurations** at which it was measured,

`C ⊆ 𝒞 = {(f,i,m)}`, ordered by inclusion,

with `s_I = π_I(C)`, `s_M = π_M(C)`, `s_F = π_F(C)` as **projections** of that support. Two
consequences are now stated rather than assumed:

- §1: *"instances are family-specific … so a family-widening probe necessarily brings its own new
  instance identities and $s_I$ and $s_F$ are not free coordinates of a product."*
- §1: `π_F(C) × π_I(C) × π_M(C) ≠ C` in general — *"a support is typically **sparse** in the
  product of its own projections, so having widened every projection somewhere is not the same as
  having measured every configuration. That gap is precisely where this study's central omission
  lives."*
- §3.1 concedes the fibered structure at the point where it bites: *"a probe that enlarges $s_F$
  necessarily enlarges $s_I$ too, so a cross-family replication is never a replication in $s_F$
  alone."*
- §3 adds that this is a property of the design space rather than a confound.
- The S3 falsifiability bullet is now an argument about coverage, not about verdicts: *"No
  combination of the projections fills it — even had S2-M and S2-F both succeeded, no configuration
  in S3 would have been run."*
- §7 Discussion now names **three** errors a ladder invites (was two); the new one is *"reading
  separately widened projections as joint coverage."*
- Abstract, Contributions, Figure 1 caption, Table 3 caption, Table 2 row, and the Conclusion are
  all restated in the same vocabulary.

### 2. "Five points" vs "coordinate class" reconciled

**Defect.** The Introduction said the evidence occupies *five points of this lattice* while the
main-result caption said *S2-F is a coordinate class, not a point*. Both cannot hold.

**Fix.** The Introduction now reads *"four of the five named scope regions below, and does so across
five distinct supports"* — S0, S1, S2-M realize one support each, S2-F realizes two incomparable
ones (STA, SPICE), and S3 realizes none. The caption calls S2-F *a class of supports, not one*;
Figure 1 calls S3 a *region*. **0 occurrences of "five points" or "coordinate class" in the PDF.**

### 3. The 95% band now says what kind of 95% it is

First occurrence is spelled out as *the central 95% of that instance-resampling distribution*, then
abbreviated *95% sensitivity band*. Added: because the draws are **with replacement**, each replicate
duplicates some instances and omits others, so what is perturbed is the panel's **empirical
weighting**; the band is a panel-composition sensitivity and *"the 95% names a quantile range of
that perturbation distribution, not a coverage probability."*

### 4. A limitation the band does not cover

New Appendix-C paragraph: the band *"does not quantify trajectory-level Monte-Carlo uncertainty:
with two repetitions per instance–condition cell, each cell's latent success probability is itself
poorly resolved."* It also records the deliberate decision **not** to fix it: *"We deliberately do
not add a third interval or a hierarchical model to absorb it — that would blur the
preregistered/post-hoc boundary this appendix exists to keep sharp."*

### 5. "Sole basis for the confirmatory verdict"

v9's *"is the only basis on which anything is decided"* over-claimed: the descriptive estimate and
the sensitivity band legitimately inform how a reader reads the data. Narrowed to the claim that is
actually true — the preregistered analysis is the sole basis for the **confirmatory verdict**.

### 6. The pilot reversal moved into the main text

ICLR reviewers are not required to read the appendix, but the pilot reversal is load-bearing in the
abstract, contributions and discussion, and only the appendix carried its number. §5 now reads
*"The three-instance pilot (\StatPilotDelta pp) and the prospectively frozen twelve-instance panel
(\StatStaDelta pp) reversed direction"* — both from generated macros, and shorter than the sentence
it replaced.

### 7. One concurrent reference added (verified, not asserted)

| key | title | arXiv | verified |
|---|---|---|---|
| `after` | Managing Procedural Memory in LLM Agents: Control, Adaptation, and Evaluation | 2606.23127 | HTTP 200, title + 7 authors + date 2026-06-22 read from the arXiv record, 2026-08-13 |

AFTER evaluates procedural-skill transfer under separate **local / cross-task / cross-role /
cross-model** settings. Reporting several transfer dimensions is therefore **not** claimed as novel.
§2 restates the contribution as the *indexing*: *"locating a claim by the set of configurations its
evidence occupies, which separates a hypothesis measured and left unestablished from one never
measured at all."* Appendix G's table gains a matching row.

Two further recent works (Evo-Bench 2608.09096; AI4AI at Test-Time 2608.12307) were fetched and
verified but deliberately **not** cited: both are concurrent evidence that harness effects sometimes
do transfer, an argument `longhorizon` already carries, and neither is worth main-text space at zero
page headroom.

**`references.bib`:** 11 → 12 entries, **additions only**; all 11 prior entries byte-identical,
verified by entry-level comparison against `7c2f9c4f`. 12 entries, 12 cited, 0 uncited.

### 8. Two false claims in the v9 record, corrected

- **v9 did not have 0 overfull hboxes.** The v9 measurement came from a log produced by a build that
  never ran: `make clean` does not delete `main.pdf`, so `make` was a no-op. A `make distclean`
  rebuild of `7c2f9c4f` shows **3** overfull boxes — the same three tables and the same magnitudes
  (4.2 / 10.3 / 4.2 pt) reported for v8. Nothing had regressed; the claim was unearned. Fixed here by
  setting `\tabcolsep` to 4pt in those three tables. **v10 is genuinely 0**, on a distclean build.
  The Makefile now carries a comment warning about the `clean`/`distclean` trap.
- **The PDF was not reproducible across rebuilds.** v9's recorded hash is correct for the committed
  artifact, but pdfTeX embeds a wall-clock `/CreationDate`, so a rebuild produced a different hash
  and the recorded value could not be re-verified by anyone building from source. The Makefile now
  pins `SOURCE_DATE_EPOCH`/`FORCE_SOURCE_DATE`; two consecutive distclean builds now produce
  **byte-identical PDFs**, so the hash below is a real freeze artifact.

### 9. Page cost

The positioning table (formerly Table 1) moved to **Appendix G**. Its "what this paper additionally
does" column was verbatim-equivalent to the §2 prose sentence that referenced it, and §2 now
positions ten works in prose. §3.1 (Claim qualification) was preserved intact, as the review asked.

| | v9 | v10 |
|---|---|---|
| main text | 9 pp (p1–p9) | **9 pp (p1–p9)** |
| submission headroom (limit 9) | 0 pp | **0 pp** |
| rebuttal headroom (limit 10) | 1 pp | 1 pp |
| references | p10 | p10 |
| appendix | A–F, p10–p15 | A–G, p10–p15 |
| total | 15 pp | 15 pp |

## SHA-256 hashes (frozen artifacts, v10)
| Artifact | SHA-256 |
|---|---|
| Source (main.tex) | 1857b5f54115b1a1dd79e8de57e4ea271e98543b187c7b6c1d229158f442b411 |
| Final PDF (main.pdf, 15 pp: 9 main + refs + appendix) | 8b7db3cc6bb7904d81b43bb8233ca39592bce8e85a0d52a6d5d0409266b5f333 |
| Generated ledger table (tables/study1_ledger.tex) | fdf6c50c2e0c837e96c33c88a1a37bd5a88eb503ed98669de38c4b9fdb99b7c6 |
| Generated stat macros (tables/claim_stats.tex) | 5c0b2577d7fb06be9992cf228767e2d5c317065d8dc51f6d679d6de5e5f36615 |
| Generated pilot table (tables/sta_pilot.tex) | 95cb8d73b4de9d368b0b986f22fe1c92810c43ab7b358a22f6723b7bf8aaf32b |
| Ledger generator (scripts/phase7c_study1_ledger.py) | 3d7452be5abbe2eb1e39249b4bfa512fcafecf10bd41dbc1aaca3dddc0143615 |
| Statistics generator (scripts/phase7c_claim_statistics.py) | e406a669dc736359a12417acc9943768ec36d1da92c3327544be644b56be2bc0 |
| Ledger data (reports/synthetic_p14_study1_ledger.json) | 2a548fce361487384a11b7ab0a59faed520230d32c18075ab1e2609590038e86 |
| Statistics data (reports/synthetic_p14_claim_statistics.json) | 67dde79c13041f57c9101b1c5064971a4fdf85f2921f94a18643579a38c06832 |
| Bibliography (references.bib, 12 entries) | 7939a80c45fe78d6af4879d4d1279e2cd0e2653be39062e6ca04b6cfb1135f15 |
| Style (iclr2027_conference.sty) | 797deef41724e93761426ac0cbcca46279a91cc650dd1f0ce76a4f08d2098ea6 |
| Bibstyle (iclr2027_conference.bst) | 2d67552db7ed38ccfccb5957b52f95656e25c249724761d3cf5f7922ad1844c5 |
| Claim-evidence matrix (docs/phase7/phase7_synthesis.md) | 9dbecd9fedc65ac19bc5ab1c14589013942f746cf18c2b3900c9627b317f961b |

Byte-identical to v9 (and therefore to v5–v7 where applicable): **all three generated tables**, both
generators, both data reports, both style files, and the claim-evidence matrix. **No derived
experimental number changed in v10.** `references.bib` changed by addition only.

## Change verification (v9 → v10)
- **No experimental record touched.** No paid call; `git status --porcelain -- tasks/` empty; the
  frozen manifests and evidence tree were read, never written.
- **No derived number moved.** `study1_ledger.tex`, `claim_stats.tex` and `sta_pilot.tex` are all
  byte-identical to `7c2f9c4f`, verified by `diff`. Both generators reproduce their committed
  outputs under `--check`
  (`{"ok": true, "sta_delta_pp": 12.5, "sta_band_pp": [-12.5, 41.7], "pilot_delta_pp": -16.7,
  "resolved_snapshot_retained": false}` and `{"ok": true, "episodes": 70, "correct": 41, …}`).
- **Ledger arithmetic re-derived from the rendered PDF** (not from the script): 21 body rows sum to
  41/70 with 24 axis and 5 value, matching the printed totals row; **0** rows violate
  correct+axis+value=$k$.
- **Citation integrity:** 12 entries, 12 cited, 0 uncited, 0 undefined, 12 rendered in the
  bibliography; the new arXiv ID was fetched and its title/authors/date read from the arXiv record
  before being written into the bib; the 11 prior entries verified byte-identical by entry-level
  comparison against `7c2f9c4f`.
- **Claim audit:** 0 occurrences of "effect is real", "suppresses the axis", "generalizes to",
  "necessary but not sufficient", "progressively stronger", "claim-scope ladder", "independent
  validity layers", "bootstrap interval", "unidentified", "external process", "five points",
  "coordinate class", or any stray `Level~N`. Both "confidence interval" occurrences are explicit
  denials. All **25** `establish*` occurrences are a negation, an explicit denial, the definition of
  the standard, the *not-licensed* column of Table 2, or a header describing *prior* work —
  **0 positive uses about our own results**.
- **Build:** 0 errors, 0 undefined references, 0 undefined citations, 0 real bibtex warnings
  (`Warning--` count 0). **Overfull hboxes 0**, on a distclean build. Underfull 34 (cosmetic
  page-fill slack).
- **PDF reproducibility:** two consecutive `make distclean && make` runs produce byte-identical
  PDFs (`8b7db3cc…`).
- **Anonymity:** 0 hits in PDF text and 0 in every generated `.tex` for infra/path/user/credential/
  repository patterns. PDF metadata Title/Author/Subject/Keywords all empty.
- **Repository gate:** `scripts/check` **PASSED 2985/2985**.
- **Tags unmoved:** `iclr2027-submission-v1` → `3d3e77b7…`, `iclr2027-submission-v2` → `5858d843…`.

## ICLR 2027 compliance audit
- Main text ≤9 pages: **PASS** (9 pp, p1–p9; Conclusion ends on p9). **0 pages of headroom at
  submission**, 1 at rebuttal/camera-ready where the limit rises to 10.
- References outside page limit: **PASS** (begin on p10).
- Appendix after references: **PASS** (A–G, p10–p15).
- Double-blind anonymity: **PASS** (0 leaks in PDF text and generated tables).
- PDF metadata anonymous: **PASS**.
- AI-use statement / Ethics statement / Reproducibility statement: **PASS** (all present, outside the
  page limit).
- Citations: **PASS** (12 entries, arXiv-verified, 0 placeholders).
- Build: **PASS**. Repository gate: **PASS** (2985/2985).
- Generator self-checks: **PASS** (both `--check` modes reproduce their committed outputs).
- OpenReview upload: **HUMAN STEP** — abstract Sept 18, 2026 AOE; full paper Sept 25, 2026 AOE.

## Known gaps this revision deliberately does not close
Unchanged from v8/v9; each is stated in the manuscript as a limitation rather than silently omitted:
- **Human construct validity (Study B)** — preregistered, unexecuted; no LLM annotator substituted.
- **Bundle-only leakage control** — flagged in §7 as the single most informative experiment not run.
- **Backend snapshot provenance** — unrecoverable for episodes already collected.
- **Second independent coder for the Terminal-Bench probe** — single-coder, no agreement statistic.
- **S3 (joint model × family)** — never measured; reported as an empty cell.
- **Trajectory-level Monte-Carlo uncertainty** — not quantified anywhere; stated as a limit on what
  the sensitivity band may be read to mean (new in v10).

## Provenance of the frozen points
- `iclr2027-submission-v1` → `3d3e77b` — v5. **Not moved.**
- `iclr2027-submission-v2` → `5858d843` — v7. **Not moved.**
- `0e82e59` → v6. `83379da4` → v8, untagged. `7c2f9c4f` → v9, untagged.
  This commit → **v10, untagged pending review.**

## Deadlines (official ICLR 2027 site)
- Abstract: September 18, 2026 AOE. Full paper: September 25, 2026 AOE.
