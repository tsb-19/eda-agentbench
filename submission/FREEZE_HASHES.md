# Phase-7C Submission Freeze (v11 — evidence support vs claim target)

**Submission HEAD:** the commit that adds this file.
**Experiment freeze HEAD:** a89e084 (immutable). **v11 ran no model calls and altered no experimental record.**
**Previous freezes:** v10 = `ff9b6b44` (committed, never tagged). v9 = `7c2f9c4f` (committed, never tagged). v8 = `83379da4` (committed, never tagged). v7 = `5858d843`, tagged `iclr2027-submission-v2`. v5 = `3d3e77b`, tagged `iclr2027-submission-v1`. **Neither tag moves.**

## Why v11 exists

A fourth reviewer-standard read confirmed the v10 configuration-support formalization and closed the
scope-lattice line of objection. It left **two wording-level items**, both conceptual rather than
numeric, and both fixed here. **v11 touches `main.tex` only.** Every other frozen artifact —
all three generated tables, both generators, both data reports, `references.bib`, both style files,
the claim-evidence matrix — is byte-identical to v10, verified by `git diff`. **No derived number
moved.** No citation was added: the review explicitly advised against spending main-text space on
HarnessCompass / Evo-Bench / AI4AI, and ICLR 2027 policy does not require comparison against
arXiv-only concurrent work.

### 1. Evidence support $E$ separated from claim target $T$ (the load-bearing fix)

**Defect.** v10 wrote that a claim *is indexed by* the set of configurations $C$ at which it was
measured, while the top qualification tier (*Generalized*) is inference to a **population**. Those
are two different objects. If a claim genuinely generalizes then $E\subsetneq T$, and the lattice
orders $E$, not $T$ — two studies with the same measured support can assert different target
populations. The distinction is standard in the external-validity / transportability literature and
was being elided by a single symbol.

**Fix.** Notation hygiene only; no restructuring.

- §1 now names the measured set the **evidence support** $E\subseteq\mathcal{C}$, with
  $s_I=\pi_I(E)$, $s_M=\pi_M(E)$, $s_F=\pi_F(E)$.
- §1 adds the separation explicitly: *"$E$ is what **audits** a claim, not what the claim asserts:
  a claim may name a wider **target support** $T$, and $E=T$ only when nothing is generalized. The
  lattice orders $E$; the standard of §3.1 governs which relations between $E$ and $T$ a design
  licenses."*
- §3 restates the lattice paragraph as *"The evidence auditing a harness-effect claim is indexed by
  the support $E$…"*
- §3.1's four tiers now carry their $E$/$T$ relation, which gives the standard a formal reading:
  *Observed* — *"no target beyond $E$"*; *Replicated* — $E$ enlarged; *Estimated on a fixed panel* —
  *"Inference is to the realized panel and no further ($T=E$)"*; *Generalized* — *"the one tier
  asserting $T\supsetneq E$"*.

### 2. Two BundleS leakage sentences downgraded to what the design shows

**Defect.** Both sentences asserted an absolute negative that the **unrun bundle-only leakage
control** cannot support. That a schema is shared across instances shows there is no explicit
instance-indexed answer field; it does not show that schema and generator structure *jointly* cannot
permit recovering an assignment. §7 already flags the bundle-only solve as the single most
informative experiment not run, so the two claims were in tension with our own limitation.

| location | v10 | v11 |
|---|---|---|
| §4 Conditions | "so it **cannot encode any one instance's assignment**" | "so it **contains no explicitly instance-specific assignment field**; whether schema and generator structure *jointly* permit recovering an assignment is a separate question, and §7 gives the leakage check that would settle it" |
| §5 Study I | "the effect is **not attributable to disclosing the assignment**" | "the effect is **not attributable to explicit C6 disclosure** of the assignment" |

**0 occurrences** of "cannot encode" or "not attributable to disclosing" remain in the PDF.
No experiment was run for this; it is a claim-strength correction.

### 3. Page cost, paid by removing duplication

The additions cost ~6 lines and pushed the main text to 10 pp. Recovered without touching §3.1
(claim qualification) or any result, by deleting text that restated other text:

- §6 *"Why the controls materially affected interpretation"* recited, in prose, the same three
  entries already printed in Table 4's *"Conclusion that would have been wrong"* column. Replaced by
  one sentence asserting the claim without the recitation.
- §6 monitor-custody: the closing *"silent by construction"* sentence duplicated the preceding
  clause's content; merged into it.
- §6 model-custody: dropped the rhetorical closer *"Artifact custody without model custody secures
  only half of what reproducibility requires."*
- §7: *"Two results are not contestable by re-analysis at all…"* folded into the Discussion
  paragraph as its opening (saves a paragraph break; text preserved).

| | v10 | v11 |
|---|---|---|
| main text | 9 pp (p1–p9) | **9 pp (p1–p9)** |
| submission headroom (limit 9) | 0 pp | **0 pp** |
| rebuttal headroom (limit 10) | 1 pp | 1 pp |
| references | p10 | p10 |
| appendix | A–G, p10–p15 | A–G, p10–p15 |
| total | 15 pp | 15 pp |

### 4. A miscount in the v10 record, corrected

The v10 record stated **"25 `establish*` occurrences, all audited"**. The audit verdict was right but
the count was wrong: the grep ran on `pdftotext` output in which hyphenated line-breaks split the
word, so occurrences rendered as `estab-\nlished` were missed. Counting on newline-flattened text
gives **29**, and the identical method applied to the committed v10 PDF *also* gives 29 — so nothing
changed between versions; only the earlier measurement was low. All 29 were re-audited individually
in v11 (list below) and **0 are positive uses about our own results**.

## SHA-256 hashes (frozen artifacts, v11)
| Artifact | SHA-256 |
|---|---|
| Source (main.tex) | 22d6b4437f1c8eab7b0e2b087ffffc48e3fa1c8e4361b7b6b6c3dbe3ef4a0082 |
| Final PDF (main.pdf, 15 pp: 9 main + refs + appendix) | a11470806dbafaa229fdaf35eea71f196dc399fdfe798a9fef28731bb909c42e |
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

Byte-identical to v10 (and to v5–v9 where applicable): **every artifact above except `main.tex` and
`main.pdf`**. **No derived experimental number changed in v11.** `references.bib` unchanged —
12 entries, no addition.

## Change verification (v10 → v11)
- **No experimental record touched.** No paid call; `git status --porcelain -- tasks/` empty; the
  frozen manifests and evidence tree were read, never written.
- **No derived number moved.** `git diff HEAD -- submission/tables submission/references.bib
  submission/*.sty submission/*.bst scripts/ reports/` is empty. Both generators reproduce their
  committed outputs under `--check`
  (`{"ok": true, "sta_delta_pp": 12.5, "sta_band_pp": [-12.5, 41.7], "pilot_delta_pp": -16.7,
  "fisher": {"S0": 0.4, "S1": 0.4, "S2-M": 1.0}, "resolved_snapshot_retained": false}` and
  `{"ok": true, "episodes": 70, "correct": 41, "axis_binding_failure": 24,
  "role_conditioned_value_selection_failure": 5, "cells": 21, "total": 70}`).
- **Ledger arithmetic re-derived from the rendered PDF** (not from the script): 21 body rows sum to
  41/70 with 24 axis and 5 value, matching the printed totals row exactly; **0** rows violate
  correct+axis+value=$k$.
- **Citation integrity:** 12 entries, 12 cited, 0 uncited, 0 undefined, 12 rendered. No entry added
  or changed in v11.
- **Claim audit:** 0 occurrences of "cannot encode", "not attributable to disclosing", "five points",
  "coordinate class", "effect is real", "suppresses the axis", "generalizes to", "necessary but not
  sufficient", "claim-scope ladder", "bootstrap interval", "unidentified", "external process", or
  any stray `Level~N`. Both "confidence interval" occurrences are explicit denials. All **29**
  `establish*` occurrences (see §4 above for why 29 and not the 25 recorded in v10) are a negation,
  an explicit denial, the definition of the standard, the *not-licensed* column of Table 1, a cited
  work's title, or the *"What it establishes"* header of the prior-work table — **0 positive uses
  about our own results**.
- **Build:** 0 errors, 0 undefined references, 0 undefined citations, 0 real bibtex warnings
  (`Warning--` count 0). **Overfull hboxes 0**, on a distclean build (log confirmed to contain 3
  `This is pdfTeX` banners, i.e. the build actually ran). Underfull 34 (cosmetic page-fill slack).
- **PDF reproducibility:** two consecutive `make distclean && make` runs produce byte-identical PDFs
  (`a1147080…`).
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
Unchanged from v8–v10; each is stated in the manuscript as a limitation rather than silently omitted:
- **Human construct validity (Study B)** — preregistered, unexecuted; no LLM annotator substituted.
- **Bundle-only leakage control** — flagged in §7 as the single most informative experiment not run.
  v11 aligns the two BundleS sentences with this gap rather than closing it.
- **Backend snapshot provenance** — unrecoverable for episodes already collected.
- **Second independent coder for the Terminal-Bench probe** — single-coder, no agreement statistic.
- **S3 (joint model × family)** — never measured; reported as an empty cell.
- **Trajectory-level Monte-Carlo uncertainty** — not quantified anywhere; stated as a limit on what
  the sensitivity band may be read to mean.

## Provenance of the frozen points
- `iclr2027-submission-v1` → `3d3e77b` — v5. **Not moved.**
- `iclr2027-submission-v2` → `5858d843` — v7. **Not moved.**
- `0e82e59` → v6. `83379da4` → v8, untagged. `7c2f9c4f` → v9, untagged. `ff9b6b44` → v10, untagged.
  This commit → **v11, untagged pending review.**

## Deadlines (official ICLR 2027 site)
- Abstract: September 18, 2026 AOE. Full paper: September 25, 2026 AOE.
