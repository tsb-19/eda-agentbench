# Phase-7C Submission Freeze (v9 — estimand-aligned uncertainty + formalized scope order)

**Submission HEAD:** the commit that adds this file.
**Experiment freeze HEAD:** a89e084 (immutable). **v9 ran no model calls and altered no experimental record.**
**Previous freezes:** v8 = `83379da4` (committed, never tagged). v7 = `5858d843`, tagged `iclr2027-submission-v2`. v5 = `3d3e77b`, tagged `iclr2027-submission-v1`. **Neither tag moves.**

## Why v9 exists

A second full reviewer-standard read of the v8 PDF upgraded the verdict from Leaning Reject to
Leaning Accept and confirmed that both v8 structural fixes hold. It left **one statistical
objection** that a statistics-trained reviewer would plausibly escalate to a major concern, plus
three definitional tightenings and two positioning additions. All are fixed here. No experiment was
reopened; every change is definition, wording, or relabelling of an already-computed quantity.
**No derived number moved in v9** — the values are identical to v8; what changed is what they are
called and what they are claimed to mean.

### 1. Estimand–resampling mismatch (the load-bearing fix)

**Defect.** v8 declared the S2-F estimand to be the *realized* twelve-instance panel ("inference is
to that panel and no further") while attaching a percentile bootstrap that **resamples instances**.
Those two cannot both be right: a realized panel's composition has no sampling distribution, so
resampling its members does not quantify uncertainty *about* the estimand — it perturbs the panel.
Calling the result an "uncertainty interval" for a fixed-panel estimand is a category error, and
v8 compounded it with a defensive sentence claiming the interval "introduces no second inferential
channel, since no $p$-value is re-derived from it." That defence does not hold either: an interval
is itself an inferential output regardless of whether a $p$-value accompanies it.

**Fix.** The quantity is renamed and re-scoped throughout to an **instance-resampling sensitivity
band**: it reports how far the point estimate moves when panel membership is perturbed, and nothing
else. The numbers are unchanged (+12.5pp; band −12.5 to +41.7).

- §3.1 tier definition rewritten: *"a point estimate over a declared, prospectively frozen panel,
  reported with an explicit account of how far it moves under resampling of that panel's members …
  what accompanies the estimate is a sensitivity band, not a confidence statement about a
  population."*
- §5 now states the reasoning inline rather than asserting the label: *"We report this as an
  instance-resampling sensitivity band and not as a confidence interval, because the declared
  estimand is the realized panel: its composition carries no sampling uncertainty."*
- The defensive sentence is **deleted**. Its replacement makes the weaker, true claim: *"It is not
  used for hypothesis testing, is not used to change the preregistered decision rule, and licenses
  no claim beyond the panel."*
- Generated macros renamed `\StatStaCIlo/\StatStaCIhi` → `\StatStaBandLo/\StatStaBandHi`; the
  shipped supplement's JSON key `bootstrap_ci95` → `instance_resampling_band95`, with an explicit
  `estimand` and `band_interpretation` field; the generator function `bootstrap_mean_ci` →
  `instance_resampling_band` with a docstring stating why it is deliberately *not* named `..._ci`
  (the mechanism is a percentile bootstrap; the reported quantity is not a CI).
- **0 occurrences of "bootstrap interval"** remain in the PDF; the 2 occurrences of "confidence
  interval" are both explicit denials.

### 2. Scope coordinates are now literally nested sets

**Defect.** v8 claimed containment "coordinatewise" but wrote each coordinate as a progression
(*development instance → held-out instance → panel*). A held-out instance does not *contain* a
development instance, so the labels did not instantiate the order the framework asserted.

**Fix.** Each coordinate is now a **set of support points**, widening means **adding** points, and
the order is the product order stated explicitly:
`S ≤ S'` exactly when `s_I ⊆ s_I'`, `s_M ⊆ s_M'` and `s_F ⊆ s_F'`, with
`{i_dev} ⊂ {i_dev, i_held} ⊂` panel `⊂` population, `{Qwen} ⊂ {Qwen, DeepSeek}`,
`{workflow} ⊂ {workflow, STA}`. The paper now says outright: *"a held-out instance does not replace
the development instance — it enlarges `s_I`, which is what makes S1 comparable to S0 at all."*

### 3. "Replicated" no longer counts a new run window

**Defect.** v8 defined *Replicated* as the direction reappearing "at a new instance, **or an
independently collected run window**." Re-running the same support point in a later window is
repeated measurement of the same unit; counting it as replication would let stability evidence
masquerade as scope evidence — and v8's own model-custody limitation shows those windows are not
even guaranteed to measure the same system.

**Fix.** *Replicated* is now tied to the coordinate being claimed: **a newly frozen support point of
that coordinate** (new instance → replication in `s_I`, second backend → `s_M`, independent family →
`s_F`). Re-running the same support point is named **repeated measurement** and is explicitly
excluded. Table 2 gains a row making the distinction operational
(*same support point, new run window* → licenses *stability of the measurement*, does **not**
license *replication at any wider scope*). The one place the paper relies on cross-window agreement
(the mechanism-stability test in §7) is relabelled accordingly. Our own S1 claim survives unchanged
and is now justified in place: S1 **adds an instance**, so it is a replication in `s_I`.

### 4. Model-custody counts stated exactly (0/70, not 66/70)

v8 wrote *"for 66 of the 70 ledger episodes we retained the requested alias and the run date but
never a provider-resolved snapshot,"* which reads as though the other 4 might have retained one.
The retained records were re-inspected. Two distinct counts, both now stated:

- **0 of 70** episodes retained a provider-resolved snapshot, response identifier or system
  fingerprint. The per-episode transport record has **no such field**, and no such field occurs
  anywhere in the retained evidence tree — the gap is total, not partial.
- **66 of 70** retained even the requested alias and run date; the remaining **4** carry no
  per-episode transport record at all.

The generator now **asserts** `resolved_snapshot_present == 0` and fails the build if the evidence
tree ever gains such a field, so the sentence cannot go stale. New macros `\StatSnapshotEpisodes`
(0) and `\StatNoDiagEpisodes` (4).

### 5. S2-F is a coordinate class, not a point

STA and SPICE widen `s_F` to `{workflow, STA}` and `{workflow, SPICE}` — two incomparable sets, not
one cell. The main-result caption now says so, without adding columns.

### 6. Two concurrent references added (verified, not asserted)

| key | title | arXiv | verified |
|---|---|---|---|
| `modelharness` | Model or Harness? An Interaction-Centric Taxonomy for Localizing Agent Failures | 2607.28802 | HTTP 200, title + 7 authors + date 2026-07-30 read from the arXiv record, 2026-08-13 |
| `measvalidity` | Measurement Without Validity: The Compounding Reliability Problem in Agentic AI Evaluation | 2608.00794 | HTTP 200, title + author + date 2026-08-01 read from the arXiv record, 2026-08-13 |

Positioned in §2 against our two axes: `modelharness` localizes *where* a failure originates, where
our layers ask whether the *measurement* of it was valid; `measvalidity` argues the compounding
reliability problem our sampling/execution layers instantiate empirically. Neither indexes a
harness-effect claim by the scope its evidence supports.

**This breaks the v5–v8 `references.bib` byte-identity invariant, deliberately and visibly.** The
diff is **additions only**: all 9 prior entries are byte-identical (verified by entry-level
comparison against `83379da4`), plus 2 new entries and a 1-line header amendment. 11 entries, 11
cited, 0 uncited, 0 placeholders.

### 7. Smaller

- "Five pre-registered structural criteria **establish** family independence" → "Family independence
  is **defined by** five pre-registered structural criteria," removing the last positive use of
  *establish* about our own work anywhere in the manuscript.
- Compressions to buy space (see below): the §5 three-outcomes summary, the Discussion paragraph,
  the Conclusion, and two falsifiability bullets — all restatement, no content dropped.

## Page budget

| | v8 | v9 |
|---|---|---|
| main text | 9 pp (p1–p9) | **9 pp (p1–p9)** |
| submission headroom (limit 9) | 0 pp | **0 pp** |
| rebuttal headroom (limit 10) | 1 pp | 1 pp |
| references | p9 (after Conclusion) | p10 |
| appendix A–F | p10–p14 | p10–p15 |
| total | 14 pp | 15 pp |

The 12-instance per-instance STA table (`tab:sta12`) moved from the main text to Appendix C, which
paid for the framework and definition additions. Its numbers are quoted inline where they are used
(3 improving / 2 declining / 7 tied), and the main-result table carries the panel means. §3.1
(Claim qualification) was preserved intact, as the review asked. Main text remains at the limit with
no slack.

## SHA-256 hashes (frozen artifacts, v9)
| Artifact | SHA-256 |
|---|---|
| Source (main.tex) | 9c1c1450306ee6b7b7947e2a5126f94d18272cec81e3416f01525c43cd0e6a16 |
| Final PDF (main.pdf, 15 pp: 9 main + refs + appendix) | 133578b3d4f81e30c250925e85f3efea97234690a648f501516249840ebd323f |
| Generated ledger table (tables/study1_ledger.tex) | fdf6c50c2e0c837e96c33c88a1a37bd5a88eb503ed98669de38c4b9fdb99b7c6 |
| Generated stat macros (tables/claim_stats.tex) | 5c0b2577d7fb06be9992cf228767e2d5c317065d8dc51f6d679d6de5e5f36615 |
| Generated pilot table (tables/sta_pilot.tex) | 95cb8d73b4de9d368b0b986f22fe1c92810c43ab7b358a22f6723b7bf8aaf32b |
| Ledger generator (scripts/phase7c_study1_ledger.py) | 3d7452be5abbe2eb1e39249b4bfa512fcafecf10bd41dbc1aaca3dddc0143615 |
| Statistics generator (scripts/phase7c_claim_statistics.py) | e406a669dc736359a12417acc9943768ec36d1da92c3327544be644b56be2bc0 |
| Ledger data (reports/synthetic_p14_study1_ledger.json) | 2a548fce361487384a11b7ab0a59faed520230d32c18075ab1e2609590038e86 |
| Statistics data (reports/synthetic_p14_claim_statistics.json) | 67dde79c13041f57c9101b1c5064971a4fdf85f2921f94a18643579a38c06832 |
| Bibliography (references.bib, 11 entries) | 2f4eeb4f113ec0dab3842192af09f5009ac164f57af54656ce9dca7f29d0a27a |
| Style (iclr2027_conference.sty) | 797deef41724e93761426ac0cbcca46279a91cc650dd1f0ce76a4f08d2098ea6 |
| Bibstyle (iclr2027_conference.bst) | 2d67552db7ed38ccfccb5957b52f95656e25c249724761d3cf5f7922ad1844c5 |
| Claim-evidence matrix (docs/phase7/phase7_synthesis.md) | 9dbecd9fedc65ac19bc5ab1c14589013942f746cf18c2b3900c9627b317f961b |

Byte-identical to v8 (and therefore to v5–v7): `tables/study1_ledger.tex`, `tables/sta_pilot.tex`,
both style files, the claim-evidence matrix, and `reports/synthetic_p14_study1_ledger.json`. **No
derived experimental number changed in v9.** `references.bib` changed for the first time since v5,
by addition only.

## Change verification (v8 → v9)
- **No experimental record touched.** No paid call; `git status --porcelain -- tasks/` empty;
  the frozen manifests and evidence tree were read, never written.
- **No derived number moved.** `study1_ledger.tex` and `sta_pilot.tex` byte-identical;
  `claim_stats.tex` changed only in macro *names* (`\StatStaCIlo/hi` → `\StatStaBandLo/Hi`) plus two
  new macros; every numeric value identical. Both generators reproduce their committed outputs under
  `--check` (`{"ok": true, "sta_delta_pp": 12.5, "sta_band_pp": [-12.5, 41.7], …}`).
- **New mechanical assertion:** the statistics generator now aborts if any episode is found carrying
  a provider-resolved model identity, so the "0 of 70" sentence is enforced rather than asserted.
- **Ledger arithmetic re-derived from the rendered PDF** (not from the script): 21 body rows sum to
  41/70 with 24 axis and 5 value, matching the printed totals row; 0 rows violate
  correct+axis+value=$k$.
- **Citation integrity:** 11 entries, 11 cited, 0 uncited, 0 undefined; both new arXiv IDs fetched
  and their titles/authors/dates read from the arXiv record before being written into the bib; the 9
  prior entries verified byte-identical by entry-level comparison against `83379da4`.
- **Claim audit:** 0 occurrences of "effect is real", "suppresses the axis", "generalizes to",
  "necessary but not sufficient", "progressively stronger", "claim-scope ladder", "independent
  validity layers", "bootstrap interval", "unidentified", "external process", or any stray
  `Level~N`. Both "confidence interval" occurrences are explicit denials. Every `establish*`
  occurrence is a negation, an explicit denial, the definition of the standard, a table header
  describing *prior* work, or a citation title — **0 positive uses about our own results**.
- **Build:** 0 errors, 0 undefined references, 0 undefined citations, bibtex 0 warnings.
  **Overfull hboxes 0** (down from 3 in v8). Underfull 31 (cosmetic page-fill slack).
- **Anonymity:** 0 hits in PDF text and 0 in every generated `.tex` for infra/path/user/credential/
  repository patterns. PDF metadata Title/Author/Subject/Keywords all empty.
- **Repository gate:** `scripts/check` **PASSED 2985/2985**.

## ICLR 2027 compliance audit
- Main text ≤9 pages: **PASS** (9 pp, p1–p9; Conclusion ends on p9). **0 pages of headroom at
  submission**, 1 at rebuttal/camera-ready where the limit rises to 10.
- References outside page limit: **PASS** (begin on p10).
- Appendix after references: **PASS** (A–F, p10–p15).
- Double-blind anonymity: **PASS** (0 leaks in PDF text and generated tables).
- PDF metadata anonymous: **PASS**.
- AI-use statement / Ethics statement / Reproducibility statement: **PASS** (all present, outside the
  page limit).
- Citations: **PASS** (11 entries, arXiv-verified, 0 placeholders).
- Build: **PASS**. Repository gate: **PASS** (2985/2985).
- Generator self-checks: **PASS** (both `--check` modes reproduce their committed outputs).
- OpenReview upload: **HUMAN STEP** — abstract Sept 18, 2026 AOE; full paper Sept 25, 2026 AOE.

## Known gaps this revision deliberately does not close
Unchanged from v8; each is stated in the manuscript as a limitation rather than silently omitted:
- **Human construct validity (Study B)** — preregistered, unexecuted; no LLM annotator substituted.
- **Bundle-only leakage control** — flagged in §7 as the single most informative experiment not run.
- **Backend snapshot provenance** — unrecoverable for episodes already collected.
- **Second independent coder for the Terminal-Bench probe** — single-coder, no agreement statistic.
- **S3 (joint model × family)** — never measured; reported as an empty cell.

## Provenance of the frozen points
- `iclr2027-submission-v1` → `3d3e77b` — v5. **Not moved.**
- `iclr2027-submission-v2` → `5858d843` — v7. **Not moved.**
- `0e82e59` → v6. `83379da4` → v8, untagged. This commit → **v9, untagged pending review.**

## Deadlines (official ICLR 2027 site)
- Abstract: September 18, 2026 AOE. Full paper: September 25, 2026 AOE.
