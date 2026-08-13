# Phase-7C Submission Freeze (v12 — notation cleanup; framework frozen)

**Submission HEAD:** the commit that adds this file.
**Experiment freeze HEAD:** a89e084 (immutable). **v12 ran no model calls and altered no experimental record.**
**Previous freezes:** v11 = `95128e11` (committed, never tagged). v10 = `ff9b6b44`. v9 = `7c2f9c4f`. v8 = `83379da4`. v7 = `5858d843`, tagged `iclr2027-submission-v2`. v5 = `3d3e77b`, tagged `iclr2027-submission-v1`. **Neither tag moves.**

## Why v12 exists

The fifth reviewer-standard read closed the structural line entirely: **no conceptual, statistical or
evidence-to-claim objection remains at reject level**, and the reviewer stopped hunting for defects.
What remained was **three wording items, all non-decision-critical**, plus an explicit instruction to
freeze afterwards. Two were applied; the third was a deliberate *non*-edit.

**v12 touches `main.tex` only.** Every other frozen artifact — all three generated tables, both
generators, both data reports, `references.bib`, the `Makefile`, both style files, the claim-evidence
matrix — is byte-identical to v11, verified by `git diff --quiet`. **No derived number moved:** a
numeric-token diff of the v11 and v12 rendered PDFs gives 830 tokens on both sides, **identical**.

### 1. `claim` / `evidence-for-a-claim` shorthand made consistent with the v11 E/T split

**Defect.** v11 introduced the evidence support $E$ and the target support $T$, and made the point
that $E$ is what *audits* a claim rather than what the claim asserts. But five sentences elsewhere
still carried the pre-v11 shorthand "indexes **a claim** by the set of configurations **its evidence**
occupies" — which names the claim as the indexed object, exactly the conflation §1 now separates.
Not a new conceptual problem; an inconsistency that the E/T distinction made conspicuous.

| location | v11 | v12 |
|---|---|---|
| Abstract | "index **a harness-effect claim** by the set of (family, instance, model) configurations **its evidence** occupies" | "index **the *evidence* for** a harness-effect claim by the set of (family, instance, model) configurations **it** occupies" |
| §1 Contribution (1) | "indexes **a harness-effect claim** by the set of configurations **its evidence** occupies" | "indexes **the *evidence* for** a harness-effect claim by the set of configurations **it** occupies" |
| §2 Positioning (prior work) | "None of the three indexes **a harness-effect claim** by the scope **its evidence supports**." | "None of the three indexes **the evidence for** a harness-effect claim by the **support it occupies**." |
| §2 Positioning (our contribution) | "locating **a claim** by the set of configurations **its evidence** occupies" | "locating **the *evidence* for a claim** by the set of configurations **it** occupies" |
| §8 Conclusion | "indexes **a claim** by the set of configurations **its evidence** occupies" | "indexes **the evidence supporting a claim** by its **measured configuration support**" |

The reviewer named the Contribution (1) and Conclusion occurrences. The Abstract and the two §2
occurrences are the *same* shorthand and were fixed for the stated reason — full-text notation
consistency — rather than left to read against §1. **0 occurrences of "its evidence occupies" remain.**

### 2. The sensitivity band now says what the resampling actually perturbs

**Defect.** §5 described the band as measuring "how strongly the estimate depends on **which**
instances the panel happens to contain", while Appendix C states the stricter and correct thing: a
with-replacement draw duplicates some instances and omits others, so what is perturbed is the panel's
**empirical weighting**, not its membership list.

| location | v11 | v12 |
|---|---|---|
| §5 S2-F | "how strongly the estimate depends on *which* instances the panel happens to contain" | "how strongly the estimate depends on the panel's *empirical composition*" |

More accurate and two words shorter. **0 occurrences of "happens to contain" remain.**

### 3. A deliberate non-edit, recorded so it is not re-litigated

Appendix C's *"We deliberately do not add a third interval or a hierarchical model to absorb it…"*
was flagged as **correct but the first line to cut** if a future revision needs space — the factual
limitation is fully carried by the two sentences before it. It is **kept in v12** and is hereby the
head of the page-cost queue for any camera-ready trimming. No other reserved cut exists.

### 4. Page budget

The two applied edits are net +5 words across the whole document (8762 → 8767) and cost no line:
main text stays 9 pp, Conclusion still ends on p9, References still begin on p10.

| | v11 | v12 |
|---|---|---|
| main text | 9 pp (p1–p9) | **9 pp (p1–p9)** |
| submission headroom (limit 9) | 0 pp | **0 pp** |
| rebuttal headroom (limit 10) | 1 pp | 1 pp |
| references | p10 | p10 |
| appendix | A–G, p10–p15 | A–G, p10–p15 |
| total | 15 pp | 15 pp |

## SHA-256 hashes (frozen artifacts, v12)
| Artifact | SHA-256 |
|---|---|
| Source (main.tex) | 82cb22da00f74fa751f008060abebc419de29f599a560fc0d49fa07c2c95b473 |
| Final PDF (main.pdf, 15 pp: 9 main + refs + appendix) | bbf948bfc533e3162eef4a299a1215b2664b0d3189bccc51ed65d257aba7a2e1 |
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

Byte-identical to v11 (and to v5–v10 where applicable): **every artifact above except `main.tex` and
`main.pdf`**. **No derived experimental number changed in v12.** `references.bib` unchanged — 12
entries, no addition, per the reviewer's explicit advice and ICLR 2027 policy (comparison against
arXiv-only concurrent work is not required and its absence is not a rejection basis).

## Change verification (v11 → v12)
- **No experimental record touched.** No paid call; `git status --porcelain -- tasks/` empty; the
  frozen manifests and evidence tree were read, never written.
- **Change scope proved, not asserted.** `git status --porcelain` lists exactly
  `submission/main.tex` and `submission/main.pdf`. `git diff --quiet HEAD -- submission/tables
  submission/references.bib submission/*.sty submission/*.bst submission/Makefile scripts/ reports/
  docs/` returns clean.
- **Word-level diff of the rendered text** (hyphenated line-breaks rejoined, ICLR margin numbers and
  page headers stripped) yields **18 change regions: 13 belong to the six intended edits and 5 are
  pure reflow** (a hyphenation point or an em-dash line break moving). **No unintended text change.**
- **Numeric-token diff: 830 vs 830, identical.** No number, interval, p-value, count or date moved.
- **Ledger arithmetic re-derived from the rendered PDF** (not from the script): 21 body rows sum to
  41/70 with 24 axis and 5 value, matching the printed totals row exactly; **0** rows violate
  correct+axis+value=$k$.
- **Generator self-checks** reproduce their committed outputs under `--check`
  (`{"ok": true, "sta_delta_pp": 12.5, "sta_band_pp": [-12.5, 41.7], "pilot_delta_pp": -16.7,
  "fisher": {"S0": 0.4, "S1": 0.4, "S2-M": 1.0}, "resolved_snapshot_retained": false}` and
  `{"ok": true, "episodes": 70, "correct": 41, "axis_binding_failure": 24,
  "role_conditioned_value_selection_failure": 5, "cells": 21, "total": 70}`).
- **Citation integrity:** 12 entries, 12 cited, 0 uncited, 0 undefined, 12 rendered.
- **Claim audit:** 0 occurrences of "its evidence occupies", "happens to contain", "cannot encode",
  "not attributable to disclosing", "five points", "coordinate class", "effect is real",
  "unidentified", "external process", or any stray `Level~N`. Both "confidence interval"
  occurrences are explicit denials. All **29** `establish*` occurrences (counted on
  newline-flattened text — see the v11 record for why 29 and not 25) are a negation, an explicit
  denial, the definition of the standard, the *not-licensed* column of Table 1, a cited work's
  title, or the *"What it establishes"* header of the prior-work table — **0 positive uses about our
  own results**.
- **Build:** 0 errors, 0 undefined references, 0 undefined citations, 0 real bibtex warnings
  (`Warning--` count 0). **Overfull hboxes 0**; underfull 34 (cosmetic page-fill slack). Counts read
  from the **final pass only** of a `distclean` build whose log was confirmed to contain 3
  `This is pdfTeX` banners, i.e. the build actually ran.
- **PDF reproducibility:** two consecutive `make distclean && make` runs produce byte-identical PDFs
  (`bbf948bf…`).
- **Anonymity:** 0 hits in PDF text for infra/path/user/credential/repository patterns; PDF metadata
  Title/Author/Subject/Keywords all empty.
- **Repository gate:** `scripts/check` **PASSED 2985/2985**.
- **Tags unmoved:** `iclr2027-submission-v1` → `3d3e77b7…`, `iclr2027-submission-v2` → `5858d843…`.

## ICLR 2027 compliance audit
- Main text ≤9 pages: **PASS** (9 pp, p1–p9; Conclusion ends on p9). **0 pages of headroom at
  submission**, 1 at rebuttal/camera-ready where the limit rises to 10.
- References outside page limit: **PASS** (begin on p10).
- Appendix after references: **PASS** (A–G, p10–p15). Reviewers are not required to read it, which is
  why every load-bearing claim, the E/T distinction, §3.1, the main results, the pilot reversal, the
  measurement incidents and the limitations all sit in p1–p9.
- Double-blind anonymity: **PASS** (0 leaks in PDF text and generated tables).
- PDF metadata anonymous: **PASS**.
- AI-use statement / Ethics statement / Reproducibility statement: **PASS** (all present, outside the
  page limit).
- Citations: **PASS** (12 entries, arXiv-verified, 0 placeholders). No comparison against arXiv-only
  concurrent work is required by ICLR 2027 policy, and its absence cannot be a rejection basis.
- Build: **PASS**. Repository gate: **PASS** (2985/2985).
- Generator self-checks: **PASS** (both `--check` modes reproduce their committed outputs).
- OpenReview upload: **HUMAN STEP** — abstract Sept 18, 2026 AOE; full paper Sept 25, 2026 AOE.

## Known gaps this revision deliberately does not close
Unchanged from v8–v11; each is stated in the manuscript as a limitation rather than silently omitted:
- **Human construct validity (Study B)** — preregistered, unexecuted; no LLM annotator substituted.
- **Bundle-only leakage control** — flagged in §7 as the single most informative experiment not run.
  v11 aligned the two BundleS sentences with this gap; v12 changes nothing here.
- **Backend snapshot provenance** — unrecoverable for episodes already collected.
- **Second independent coder for the Terminal-Bench probe** — single-coder, no agreement statistic.
- **S3 (joint model × family)** — never measured; reported as an empty cell.
- **Trajectory-level Monte-Carlo uncertainty** — not quantified anywhere; stated as a limit on what
  the sensitivity band may be read to mean.

## Freeze status
**The manuscript is frozen at v12.** The review that produced v12 explicitly ended the structural
audit, and recorded that the dominant risk has shifted from *unfound defects* to *over-optimization
reintroducing inconsistency*. Further edits should be made only for a concrete external reason
(OpenReview formatting, a reviewer request during rebuttal), not for further polish.

## Provenance of the frozen points
- `iclr2027-submission-v1` → `3d3e77b` — v5. **Not moved.**
- `iclr2027-submission-v2` → `5858d843` — v7. **Not moved.**
- `0e82e59` → v6. `83379da4` → v8. `7c2f9c4f` → v9. `ff9b6b44` → v10. `95128e11` → v11. All untagged.
  This commit → **v12, untagged pending review.**

## Deadlines (official ICLR 2027 site)
- Abstract: September 18, 2026 AOE. Full paper: September 25, 2026 AOE.
