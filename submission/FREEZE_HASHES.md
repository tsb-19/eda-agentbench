# Phase-7C Submission Freeze (v8 — claim-scope lattice + symmetric claim calibration)

**Submission HEAD:** the commit that adds this file.
**Experiment freeze HEAD:** a89e084 (immutable). **v8 ran no model calls and altered no experimental record.**
**Previous freeze:** v7 = `5858d843`, pushed, tagged `iclr2027-submission-v2` (lightweight). v5 = `3d3e77b`, tagged `iclr2027-submission-v1`. **Neither tag moves.**

## Why v8 exists

A full read of the v7 PDF against ICLR 2027 reviewer criteria produced two findings that were
verified against the source and are structural rather than cosmetic. Both are fixed here. No
experiment was reopened; every change is framing, calibration, or offline recomputation from
already-frozen records.

### 1. The claim-scope "ladder" was not a valid order (fixed: it is now a lattice)

**Defect.** v7 line 81 stated *"Moving right on the ladder requires evidence at the new level;
passing a lower level is necessary but not sufficient,"* and the abstract called the four levels
*"progressively stronger."* That asserts a total order. But Level 2 (cross-model) and Level 3
(cross-family) intervene on **different, incomparable dimensions**: neither set contains the other.
The paper's own Level-3 experiment held the model fixed at Qwen3.7-Max — i.e. at the Level-2 failure
— while varying the family, so under the paper's own necessity rule that experiment was either
invalid or uninformative by construction. An intervention can cross every family for one model and
fail on a second model; the ladder cannot represent that.

**Fix.** A claim is now a point `S = (s_I, s_M, s_F)` over instance / model / family scope, ordered
**coordinatewise — a partial order, not a chain**. Evidence cells are relabelled:

| old | new | meaning |
|---|---|---|
| Level 0 | **S0** | local: development instance, Qwen3.7-Max, workflow family |
| Level 1 | **S1** | S0 widened in `s_I` (pre-frozen held-out instance) |
| Level 2 | **S2-M** | S0 widened in `s_M` (DeepSeek-V4-Pro) |
| Level 3 | **S2-F** | S0 widened in `s_F` (STA, SPICE) |
| — | **S3** | widened in `s_M` **and** `s_F` — **never measured** |

The relabelling is not cosmetic: it makes S2-M and S2-F explicit siblings (neither prerequisite for
the other) and it exposes **S3 as an empty cell that this study never populated**, which the ladder
formulation could not distinguish from a failed test. S3 now appears as a row in the main result
table (Table 4) and as a column in Figure 1, both marked *not measured*, and has its own entry in
the falsifiability list.

### 2. Positive results were held to a looser standard than negative ones (fixed: symmetric)

**Defect.** v7 stated *"The bundle-level effect is real within-family"* (§4 and §6) and *"Level 0 and
Level 1 are established for Qwen3.7-Max"* (§4) — while the **same** limitations paragraph conceded
that those cells rest on single instances. Each cell is one instance at `k`=3: two-sided Fisher
`p = 0.40`, exact intervals 29.2–100.0% (BundleS) against 0.8–90.6% (Base). Meanwhile every negative
result was scrupulously hedged ("not established", "non-establishment result, not evidence of a zero
effect"). For a paper whose thesis is claim calibration, that asymmetry was the most damaging thing
in it.

**Fix.** A stated four-tier standard (§3.1, `sec:qual`), applied symmetrically:
**observed** → **replicated** → **estimated on a fixed panel** → **generalized**.
Under it, BundleS is *observed* at S0, *replicated* once at S1, *estimated* nowhere in the workflow
family, and *generalized* nowhere at all. **Zero positive uses of "established" remain in the
manuscript** — every surviving occurrence is a negation, an explicit denial, or the definition of the
standard itself. New Table 2 maps each evidence shape to what it does and does not license.

### 3. Offline statistics (no new data)

New `scripts/phase7c_claim_statistics.py` re-reads the frozen records and attaches uncertainty to
numbers previously printed as bare fractions or a lone p-value. Pure standard library; exact
arithmetic where exactness is available.

- **Clopper-Pearson exact intervals** and **two-sided Fisher** (exact rationals) for every headline
  cell: S0 `p=0.40`, S1 `p=0.40`, S2-M `p=1.00`.
- **STA finite-panel estimate** now leads: **+12.5pp**, bootstrap interval **−12.5 to +41.7** over the
  12 instances (10⁵ replicates, fixed seed). The preregistered sign test (`p=1.0`) and permutation
  sensitivity (`p=0.31`) are unchanged and still reported — the interval is labelled post hoc and
  derives **no** second p-value, so no competing inferential channel is introduced. Reason for
  leading with it: `p=1.0` reads to a non-specialist as a demonstrated zero, which it is not.
- **Three-instance pilot published** (Appendix B, generated table): pilot **−16.7pp** (BundleS worse)
  against the prospective **+12.5pp**. The claimed direction reversal is now auditable rather than
  asserted; the script *asserts* the two signs differ and fails the build otherwise.
- **Backend provenance**: run windows span **22 days (2026-07-12 → 2026-08-03)**; the requested alias
  and run date were retained for **66 of 70** ledger episodes, and a provider-resolved snapshot,
  response id or system fingerprint for **none**.

Every derived value is asserted against the frozen report's own declared values (panel means,
improve/decline/tie tally, observed sum, pilot means) and aborts on mismatch.

### 4. Model custody added as a fifth Layer-4 requirement — stated as our own gap

The paper reads across-window variation of the same condition (`0/3, 2/3, 3/4`) as stochastic
instability. With a 22-day span and no resolved snapshot retained, **backend version drift cannot be
excluded** as a contributor. This is now stated at the point the claim is made (§4) and developed in
§6 into a fifth Layer-4 requirement — *record the provider-resolved model identity per episode, not
the requested alias* — explicitly framed as a limitation incurred, not a control exercised.

### 5. Smaller confirmed fixes

- **Table 6 gained its missing Capability row.** The abstract claims each layer caught a concrete
  threat, but the incident table listed only Exec/Samp/Exec/Exec/Art/Art. Added: *tool-success proxy
  → typed provenance/authority oracle → tool-green wrong bindings scored as correct.*
- **"non-answer-bearing" → "instance-answer-independent"**, with an explicit sentence stating that
  BundleS *does* disclose task-level role semantics and only withholds the instance's tuple.
- **"four independent validity layers" → four distinct, interacting audit dimensions**, with the
  canonical-source incident given as the example of a Layer-4 fault presenting as a Layer-3 symptom.
- **Study B limitation strengthened** (§7): the construct validated is a *formal* one; we do not claim
  the typed oracles capture human operational semantics, and we cannot exclude that some Base
  failures reflect underspecification an expert would also judge underspecified.
- **Family scope** restated as cross-generator transfer inside one author-designed universe.
- **Audit-protocol provenance**: the four layers were *derived from* the incidents, so Table 6 is
  framework-construction evidence and the Terminal-Bench coding is its first external evaluation —
  authored by us, with no second coder and no agreement statistic.
- **Exploratory/confirmatory chronology with explicit freeze points** (Appendix E), naming which
  cells are exploratory by construction (S0, the whole component decomposition) and where the two
  freezes fell (intervention + held-out instance; then the cross-family panel, size and analysis).
- **Ledger JSON rule string corrected.** `reports/synthetic_p14_study1_ledger.json` still carried the
  *one-part* inclusion rule left over from the v7 accounting patch, which updated the docstring and
  the paper caption but not this embedded string — so the shipped supplement declared a 58-episode
  rule while containing 70. Now states the two-part universe. **No derived number moved**
  (`tables/study1_ledger.tex` is byte-identical, hash `fdf6c50c…` unchanged).

## Page budget — this is the one regression

| | v7 | v8 |
|---|---|---|
| main text | 8 pp | **9 pp** |
| submission headroom (limit 9) | 1 pp | **0 pp** |
| rebuttal headroom (limit 10) | 2 pp | 1 pp |
| references | p9 | p9 (after the Conclusion) |
| appendix | p9–11 | p10–14 |
| total | 11 pp | 14 pp |

To fit the new framework material, three things moved or went:
- **Figure 2 (failure taxonomy) deleted** — three boxes and two numbers already stated in the prose.
- **Table 3 (21-row Study I ledger) moved to Appendix A.** The three-point analysis stays in the main
  text and is self-contained (it quotes the relevant per-cell numbers inline).
- **The worked-instance evidence table moved to Appendix A.** All of its prose stays in §3; the table
  was illustrative, not load-bearing.

Main text is at the limit with no slack. Any future main-text addition must displace something.

## SHA-256 hashes (frozen artifacts, v8)
| Artifact | SHA-256 |
|---|---|
| Source (main.tex) | 63a2ee9a076570dec3a485b19d099547fb068cae195dbff73595f66c0e34a032 |
| Final PDF (main.pdf, 14 pp: 9 main + refs + appendix) | 9a5f1a694130af6d010a840445d8c487fce4a2f393e220c5526d2d86f8567993 |
| Generated ledger table (tables/study1_ledger.tex) | fdf6c50c2e0c837e96c33c88a1a37bd5a88eb503ed98669de38c4b9fdb99b7c6 |
| Generated stat macros (tables/claim_stats.tex) | dcaa338552ccbf2f2e8711eb053588b8c86f1cc1e94fc33d75d6e864f98474a3 |
| Generated pilot table (tables/sta_pilot.tex) | 95cb8d73b4de9d368b0b986f22fe1c92810c43ab7b358a22f6723b7bf8aaf32b |
| Ledger generator (scripts/phase7c_study1_ledger.py) | 3d7452be5abbe2eb1e39249b4bfa512fcafecf10bd41dbc1aaca3dddc0143615 |
| Statistics generator (scripts/phase7c_claim_statistics.py) | 7fc983298a54f603cb3ddb7eab6e06baff8afce5dc3abb2247566870a733b007 |
| Ledger data (reports/synthetic_p14_study1_ledger.json) | 2a548fce361487384a11b7ab0a59faed520230d32c18075ab1e2609590038e86 |
| Statistics data (reports/synthetic_p14_claim_statistics.json) | b5b08c07ef362cc18d36d78708e22b5c747b886dbbaf0d042c7a53021d30fd6f |
| Bibliography (references.bib, 9 entries) | 867562f4be4a6c576bdfd3752e8e7e20ad50885a58214f3cd2dda330b99c9670 |
| Style (iclr2027_conference.sty) | 797deef41724e93761426ac0cbcca46279a91cc650dd1f0ce76a4f08d2098ea6 |
| Bibstyle (iclr2027_conference.bst) | 2d67552db7ed38ccfccb5957b52f95656e25c249724761d3cf5f7922ad1844c5 |
| Claim-evidence matrix (docs/phase7/phase7_synthesis.md) | 9dbecd9fedc65ac19bc5ab1c14589013942f746cf18c2b3900c9627b317f961b |

`references.bib`, both style files and the claim-evidence matrix are **byte-identical to v5, v6 and
v7** — which is itself the evidence that no citation and no claim-matrix content moved in this
revision. `tables/study1_ledger.tex` is byte-identical to v7: **no derived experimental number
changed in v8.**

## Change verification (v7 → v8)
- **No experimental record touched.** No paid call; `tasks/` clean (`git status --porcelain -- tasks/`
  empty); canonical golden hash intact; the frozen manifests were read, never written.
- **No derived number moved.** `tables/study1_ledger.tex` byte-identical; both generators reproduce
  their committed outputs under `--check`.
- **Ledger arithmetic re-derived from the rendered PDF** (not from the script): 21 body rows sum to
  41/70 with 24 axis and 5 value, matching the printed totals row; every row satisfies
  correct+axis+value=$k$.
- **Statistics independently hand-verified:** Fisher two-sided on [[3,0],[1,2]] = 0.2+0.2 = **0.40**;
  Clopper-Pearson 1/3 = (0.008, 0.906), 3/3 = (0.292, 1.000), 3/4 = (0.194, 0.994); panel mean
  1.5/12 = **+0.125**. All reproduce the script's output exactly.
- **Claim audit:** 0 occurrences of "effect is real", "suppresses the axis", "generalizes to",
  "necessary but not sufficient", "progressively stronger", "claim-scope ladder", "independent
  validity layers", or any stray `Level~N` reference. The single surviving "non-answer-bearing" is
  the explicit contrast in the new wording.
- **Build:** 0 errors, 0 undefined references/citations, bibtex 0 warnings. Overfull hboxes **3**
  (down from 4 in v7). Underfull hbox 30, underfull vbox 1 (cosmetic page-fill slack).
- **Anonymity:** 0 hits in PDF text and 0 in every generated `.tex` for infra/path/user/credential/
  repository patterns. PDF metadata Title/Author/Subject/Keywords all empty.
- **Repository gate:** `scripts/check` **PASSED 2985/2985**.

## ICLR 2027 compliance audit
- Main text ≤9 pages: **PASS** (9 pp, p1–p9; Conclusion ends on p9). **0 pages of headroom at
  submission**, 1 at rebuttal/camera-ready where the limit rises to 10.
- References outside page limit: **PASS** (begin on p9 after the Conclusion).
- Appendix after references: **PASS** (p10–p14).
- Double-blind anonymity: **PASS** (0 leaks in PDF text and generated tables).
- PDF metadata anonymous: **PASS**.
- AI-use statement / Ethics statement / Reproducibility statement: **PASS** (all present, outside the
  page limit).
- Citations: **PASS** (9 entries, arXiv-verified, 0 placeholders; unchanged since v5).
- Build: **PASS**. Repository gate: **PASS** (2985/2985).
- Generator self-checks: **PASS** (both `--check` modes reproduce their committed outputs).
- OpenReview upload: **HUMAN STEP** — abstract Sept 18, 2026 AOE; full paper Sept 25, 2026 AOE.

## Known gaps this revision deliberately does not close
These require new data and the experiment freeze is closed, so each is stated in the manuscript as a
limitation rather than silently omitted:
- **Human construct validity (Study B)** — preregistered, unexecuted; no LLM annotator substituted.
- **Bundle-only leakage control** — flagged in §7 as the single most informative experiment not run.
- **Backend snapshot provenance** — unrecoverable for episodes already collected.
- **Second independent coder for the Terminal-Bench probe** — single-coder, no agreement statistic.
- **S3 (joint model × family)** — never measured; reported as an empty cell.

## Provenance of the frozen points
- `iclr2027-submission-v1` → `3d3e77b` — v5. **Not moved.**
- `iclr2027-submission-v2` → `5858d843` — v7. **Not moved.**
- `0e82e59` → v6. This commit → **v8, untagged pending review.**

## Deadlines (official ICLR 2027 site)
- Abstract: September 18, 2026 AOE. Full paper: September 25, 2026 AOE.
