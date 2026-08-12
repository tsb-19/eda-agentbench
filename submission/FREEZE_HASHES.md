# Phase-7C Final Submission Freeze (v7 — principled Study I ledger + review fixes)

**Submission HEAD:** the commit that adds this file (v7 over v6 = 0e82e59; v5 = 3d3e77b, tagged `iclr2027-submission-v1`).
**Experiment freeze HEAD:** a89e084 (immutable; no new experiments — v7 is manuscript + offline re-aggregation only).

## v7 change summary (no paid calls; no experimental record altered)

Review of the v6 PDF surfaced one substantive accounting defect and three wording defects. All four
are fixed. **The Study I ledger totals changed as a direct and intended consequence** — see below.

### 1. Study I episode ledger recomputed under an explicit, enforced inclusion rule (Table 3)

**Defect.** The v6 ledger reported 54 classified episodes (29 correct / 20 axis / 5 value). That set
was not a declared sampling frame. Its generator (`scripts/phase4z_figures_tables.py`, Table 2) keyed
cells by `(label, model)` in a Python dict, so a condition measured in more than one run window
silently overwrote itself. The surviving 54 were an artifact of dict insertion order. Two whole
stages vanished this way (Phase-4X Stage-1, and the Stage-1C Base arm), and Phase-4W Run-1 had never
been included at all. The v6 caption's explanation ("the superseded, position-confounded first
cross-model arm is excluded ... which is why 58 paid primary episodes yield 54 classified ones") was
therefore wrong twice over: the mechanism was dict overwrite, not principled exclusion, and the 54
was not even a subset of the 58 — 12 of it came from the controlled pair, which is not part of the 58.

**Fix.** New `scripts/phase7c_study1_ledger.py` re-derives every cell from the same frozen
per-episode records under a stated rule with two declared parts:

> **(1)** the **program-primary** episodes of the workflow ablation program (Phases 4W / 4X / 4Y and
> the C24 bridge) as declared by the frozen phase manifests — 58 episodes, whose only omissions are
> the ones a manifest marks `excluded`, `invalid` or `aborted` (3, 0 and 1 respectively); plus
> **(2)** the **12 earlier controlled-pair episodes** (Phases 4U / 4V1 / 4V2), which are paid and
> gradeable but predate the phase-matrix accounting. Cells are keyed by
> (stage, condition, model, task); repeat measurements of the same condition in different run
> windows are distinct rows and are **never** deduplicated.

The rule is **mechanically enforced, not merely stated**: the script asserts each stage's derived
episode count against `reports/synthetic_p14_phase4z_freeze_manifest.json` (`phase_matrix[].primary`
and `program_totals.primary`) and aborts on mismatch. Negative-tested: dropping one episode, and
dropping a whole stage (the exact v6 failure mode), both raise.

**Result — the numbers changed, as authorized:**

| | v6 | v7 |
|---|---|---|
| episodes | 54 | **70** |
| correct | 29 | **41** |
| axis-binding | 20 | **24** |
| role-conditioned value-selection | 5 | **5** |
| cells | 16 | **21** |

70 = 58 program primary (frozen manifest) + 12 controlled pair. The 16 added episodes are
Phase-4W Run-1 (6, C6 ablation — never previously included), Phase-4X Stage-1 primary (6), and the
Phase-4X Stage-1C Base arm (4). Each recovered cell independently reproduces its own frozen phase
report's headline (Stage-1 Base 2/3 vs BundleS 1/3; Stage-1C 3/4 = 3/4; Schema 2/3 > Contract 1/3;
C1 2/4; C24 3/4 then 2/4; C2 1/4; C4 0/4), which is a 21-way cross-check of the aggregation.

**No conclusion changed.** These are descriptive taxonomy totals; no verdict on any rung of the
claim-scope ladder depends on them. Table 4 (main results) is unchanged and every one of its cells
remains consistent with the recomputed ledger. Table 3 is now typeset by `\input` from the script's
output, so transcription drift is structurally impossible, and it carries a totals row so a reader
can check the arithmetic without the script.

### 2. Episode-accounting terminology closed across the paper (v7 second pass)

The recomputed ledger (70) and the program totals reported in Appendix D and the reproducibility
statement (`58+24+36+72`) are **different quantities**, and the first v7 pass stated both without
reconciling them — a reader checking the arithmetic would have asked whether Study I has 58 or 70
paid primary episodes, and what the 12 controlled-pair episodes are in that accounting.

Resolved from the frozen manifest rather than by assumption. `program_totals.primary = 58` is
exactly the sum of the ten `phase_matrix` rows (4W-Run1/Run2/Held, 4X-S1/S1B/S1C, 4Y-S1/S2/S3,
4Y-Bridge), and `cost_cny = 682.25` is exactly the sum of those same rows' costs. **No 4U/4V row
exists in that matrix**, so the 12 controlled-pair episodes are paid and gradeable but are *not*
program-primary under this manifest, and their cost is not in ¥682.25 either. The program totals
are therefore correct as printed and were left unchanged; the terminology was made precise instead,
in all three places that carry a count:

- **Table 3 caption** — inclusion rule restated as the two-part universe, with the explicit sentence
  that the 70-episode descriptive ledger is *deliberately broader* than the 58-episode
  program-primary accounting.
- **Appendix D (chronology)** — one sentence stating that the 58 is the program-primary accounting
  of the ablation phases and the 70-episode ledger additionally includes the 12 controlled-pair
  episodes, which predate that accounting and its cost ledger.
- **Reproducibility statement** — parenthetical reconciling `58+24+36+72` with the ledger's 70.
- **Appendix A** and the generator docstring carry the same two-part phrasing.

Costs were **not** recomputed: the committed cost ledger remains authoritative (¥745.29).
The generated table and ledger JSON are byte-identical before and after this pass
(`fdf6c50c…` / `ca8104ac…`) — it changed wording only, not a single derived number.

Also closed in this pass: §4 said three condition–model pairs disagree with themselves but named
only two; BundleS/DeepSeek (1/3 → 3/4) is now named, so the count matches the enumeration.

### 3. Three wording fixes

- **Over-claim removed (§4).** "the conditions that suppress axis errors ... are **exactly** the
  conditions that carry value-domain information" was contradicted by the same table: C2-only and
  C4-only carry value-domain information and retain three axis failures each. Restated as the weaker
  true claim — every axis-suppressing condition carries value-domain information, but neither
  ingredient is sufficient in isolation. This also agrees better with the paper's own "no stable
  minimal mechanism" conclusion.
- **Limitation corrected (§6).** "Level 0 and Level 2 rest on $n$=1" omitted Level 1, which Table 4
  shows is also `#inst.`=1. Now "Levels 0–2 each rest on single-instance cells at their respective
  evaluation stage, with Level 1 using a distinct pre-frozen held-out instance."
- **Two softenings.** Custody principle: "if the standard *is reachable by* the harness, the monitor
  *will* faithfully report ... and assign it to the wrong subsystem" → "if the standard *can be
  mutated by* the harness, the monitor *can* faithfully report a genuine mismatch while
  misattributing the fault" (reachability does not entail mutation). Falsifiability (§7):
  Level 0–1 "would be overturned" → "would be weakened or revised by a preregistered replication
  that fails to reproduce"; the mechanism claim likewise "revised"; Level 3 no longer says a panel
  should detect "the effect size the Level 0–1 result implies" — a within-family effect entails
  nothing about cross-family magnitude — but "distinguish a preregistered, practically meaningful
  effect from zero".

## SHA-256 hashes (frozen artifacts, v7)
| Artifact | SHA-256 |
|---|---|
| Source (main.tex) | f7fc16bde746061b1fdaa17449a7715ebc4331837c2d8caf4a85e162307def82 |
| Final PDF (main.pdf, 11 pp: 8 main + refs + appendix) | f867c1bf8e02822eba5722eb0fb6ce3bbb332dcc29a26147850464a510fe8631 |
| Generated ledger table (tables/study1_ledger.tex) | fdf6c50c2e0c837e96c33c88a1a37bd5a88eb503ed98669de38c4b9fdb99b7c6 |
| Ledger generator (scripts/phase7c_study1_ledger.py) | 1623fbf346fbf2dc7ce0472ca1f8e0e62584e7d95c5062fe4d4783c8a43135e8 |
| Ledger data (reports/synthetic_p14_study1_ledger.json) | ca8104ac6ab9ddf8944978ee31894bbe73b9ddb410289026258b05b37ff574d9 |
| Bibliography (references.bib, 9 entries) | 867562f4be4a6c576bdfd3752e8e7e20ad50885a58214f3cd2dda330b99c9670 |
| Style (iclr2027_conference.sty) | 797deef41724e93761426ac0cbcca46279a91cc650dd1f0ce76a4f08d2098ea6 |
| Bibstyle (iclr2027_conference.bst) | 2d67552db7ed38ccfccb5957b52f95656e25c249724761d3cf5f7922ad1844c5 |
| Claim-evidence matrix (docs/phase7/phase7_synthesis.md) | 9dbecd9fedc65ac19bc5ab1c14589013942f746cf18c2b3900c9627b317f961b |

`references.bib`, the style files and the claim-evidence matrix are **unchanged from v5 and v6**
(hashes identical), which is itself evidence that no citation or claim-matrix content moved.

Source-archive and supplement-archive tarball hashes are recomputed at final OpenReview packaging.

## Change verification (v6 → v7)
- **Numeric token diff of both PDFs** (ICLR margin line numbers stripped). The only semantic numeric
  changes are the ledger ones: `54`, `29`, `20`, `20/54`, `5/54` removed; `70`, `41`, `24`, `41/70`,
  `24/70`, `5/70` and the 21 per-cell values added. All other numbers — Table 4, Table 5, Table 6,
  every rate, cost, $p$-value and instance count — are byte-identical in count.
- **Sentence-level text diff of both PDFs**: the only prose deltas are the four review fixes plus the
  new Table 3 caption/legend. No other sentence changed.
- **Ledger arithmetic re-derived from the rendered PDF** (not from the script): 21 body rows sum to
  41/70 with 24 axis and 5 value, matching the printed totals row and the generated JSON; every row
  satisfies correct+axis+value=$k$.
- **Typesetting: improved.** Overfull hboxes 5 → 4 (the v6 ledger table's 0.77pt overrun is gone);
  the remaining 4 are all pre-existing and unchanged. Underfull \vbox 1 → 4 (page-fill slack from
  the larger float; cosmetic). Underfull hbox unchanged at 27.

## Change verification (v7 first pass → v7 accounting patch)
- **Sentence-level PDF diff**: the only deltas are the four accounting sentences (Table 3 caption
  inclusion rule, Appendix A parenthetical, Appendix D sentence, reproducibility parenthetical) and
  the named third repeat pair in §4. No other sentence changed.
- **No derived number moved**: `tables/study1_ledger.tex` and `reports/synthetic_p14_study1_ledger.json`
  are byte-identical to the first v7 pass; `phase7c_study1_ledger.py --check` reproduces the
  committed JSON exactly (70 / 41 / 24 / 5, 21 cells, 58 + 12).
- **Manifest arithmetic re-verified independently**: sum of `phase_matrix[].primary` = 58 =
  `program_totals.primary`; sum of `phase_matrix[].cost_cny` = 682.25 = `program_totals.cost_cny`;
  `[p for p in phase_matrix if p.phase startswith 4V/4U]` is empty — the basis for keeping
  58/24/36/72 unchanged.
- **Ledger arithmetic re-derived from the rendered PDF again**: 21 body rows sum to 41/70 with 24
  axis and 5 value, matching the printed totals row; every row satisfies correct+axis+value=$k$.
- **Page boundaries unchanged**: main text p1–p8 (Conclusion ends at the foot of p8), references
  begin at the top of p9, appendix p9–p11; 11 pp total. Table 3 remains on p5 as reviewed.
- **Build and gates re-run**: 0 errors, 0 undefined refs, bibtex 0 warnings, overfull hboxes 4
  (unchanged); anonymity 0 hits in PDF text and in the generated `.tex`; PDF metadata empty;
  `scripts/check` 2985/2985; `git status --porcelain -- tasks/` empty.

## ICLR 2027 compliance audit
- Main text <=9 pages: **PASS** (8 pp, p1–p8; Conclusion ends at the foot of p8; 1 page of headroom
  at submission, and 2 at rebuttal/camera-ready, where the limit rises to 10).
- References outside page limit: **PASS** (begin p9, after the Conclusion).
- Appendix after references: **PASS** (p9–p11).
- Double-blind anonymity: **PASS** (0 infra/path/user/credential/repository leaks in PDF text,
  re-scanned on the v7 PDF; the new ledger rows add only frozen task identifiers).
- PDF metadata anonymous: **PASS** (Title/Author/Subject/Keywords empty).
- AI-use statement: **PASS** (present, outside page limit; ICLR 2027 policy scope).
- Ethics statement: **PASS** (records Study B as preregistered-but-unexecuted).
- Reproducibility statement: **PASS** (present, outside page limit).
- Citations: **PASS** (9 entries, all verified against arXiv primary source; 0 placeholders;
  unchanged from v5).
- Build: **PASS** (pdflatex+bibtex; 0 undefined refs/citations; 0 errors; bibtex 0 warnings).
- Repository gate: **PASS** (`scripts/check` 2985/2985; canonical golden hash `c80812cc…` intact
  before and after; `git status --porcelain -- tasks/` empty).
- Ledger self-check: **PASS** (`scripts/phase7c_study1_ledger.py --check` reproduces the committed
  JSON exactly).
- OpenReview profiles: **HUMAN STEP** — authors must register before abstract deadline (Sept 18, 2026 AOE).

## Provenance of the frozen points
- `iclr2027-submission-v1` → `3d3e77b` — v5. **Not moved.**
- `0e82e59` → v6 (main-text expansion, 5 pp → 8 pp).
- This commit → v7.

## Deadlines (official ICLR 2027 site)
- Abstract: September 18, 2026 AOE.
- Full paper: September 25, 2026 AOE.
