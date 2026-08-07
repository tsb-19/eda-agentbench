# ICLR 2027 Submission Package

**Title:** When Do Agent Harness Improvements Generalize? Semantic Binding, External Validity, and Evaluation Reliability in LLM Agents

**Status:** anonymized, double-blind. Evaluation study (no new method proposed). Experimentally frozen at commit `a89e084`; this package is repository-hardening only (no new experiments, no model calls).

## Contents

| File | Purpose |
|---|---|
| `main.tex` | Manuscript source (official ICLR entry point). |
| `iclr2027_conference.sty` | ICLR 2027 format package — **offline stand-in reconstruction** (see header). Drop-in replaceable with the official release. |
| `references.bib` | Bibliography (5 related-work entries; metadata flagged VERIFICATION-REQUIRED — see file header). |
| `main.pdf` | Compiled, anonymized PDF. |
| `Makefile` | One-command build. |
| `ANONYMITY_AUDIT.md` | Double-blind anonymity audit result. |

## Build

```
make            # = latexmk -pdf main.tex  (handles bibtex + repeats)
# or manually:
pdflatex main && bibtex main && pdflatex main && pdflatex main
```

## Page boundaries (compiled)

- **Main text ends:** page 8
- **References begin:** page 8
- **Appendix begins:** page 9
- **Total PDF:** 10 pages
- **Main-text length:** 8 pages (<= 9-page ICLR limit; target ~8.5).

## Format caveat (IMPORTANT)

`iclr2027_conference.sty` shipped here is a **faithful offline reconstruction** of
the year-stable ICLR single-column 10pt format (letterpaper, 6.0in x 9.0in text
block, ICLR title block, anonymized). The official `iclr2027_conference.sty` for
the 2027 cycle was not yet published at preparation time and the build host is
offline (web retrieval unavailable). To compile against the official style,
**overwrite this file with the official release and re-run `make`** — no edit to
`main.tex` is required (it loads the package in the standard ICLR way). Because
the ICLR body density is year-stable, the main-text page count is expected to be
unchanged.

## Figures and tables

All data tables are generated from committed ledgers:
- Table 1 (main result) <- `reports/evidence/phase6_data.json`
- Table (trajectory stability) <- per-episode re-grading of `reports/evidence/phase5c_episodes/`, `phase5d_episodes/`, and the p14 stage episode dirs (semantic_binding = submitted==golden on typed axes).
- Figure 2 (taxonomy) counts <- workflow ledger (54 episodes: 29 correct / 20 axis / 5 role-conditioned-value).
Figures 1 and 3 are conceptual (TikZ / tabular).

## Reproducibility

Deterministic generators (fixed seeds), independent per-family graders, exact-commit isolated-worktree execution with pre/post-episode canonical-hash verification, committed sample-membership arbitration, validity-only replacement, per-episode custody byte-matching, sanitized custody evidence. Frozen manifests, treatment mapping, schedules, and provenance in anonymized supplementary material.
