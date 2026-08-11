# ICLR 2027 Submission Package (Phase-7 / manuscript v3)

**Title:** When Do Agent Harness Improvements Generalize? Semantic Binding, External Validity, and Evaluation Reliability in LLM Agents
**Status:** anonymized, double-blind. All experimental + benchmark-runtime work permanently closed. Experimentally frozen earlier; this package is the Phase-7 synthesis + manuscript v3.

## Build
```
cd submission && make      # pdflatex + bibtex + 2x pdflatex
```

## Page boundaries (compiled)
- **Main text (§1–8) ends: page 6**
- **References begin: page 6**
- **Appendix begins: page 6 (A–E through page 8)**
- **Ethics/AI-use/Reproducibility: pages 8–9**
- **Total PDF: 9 pages** — main text 6 pp (≤ 9-page ICLR limit).

## Format caveat
`iclr2027_conference.sty` is an offline stand-in reconstruction (the official 2027 style was not yet posted as of 2026-08-11; `iclr.cc/Conferences/2027/Styles` returns 404). Drop-in replaceable: overwrite with the official release and re-run `make`. ICLR 2027 deadlines verified from the official site: **abstract 2026-09-19, full paper 2026-09-26 (11:59 UTC)**.

## Contents
| File | Purpose |
|---|---|
| `main.tex` | v3 source: 3-study/RQ structure; Phase-7 evidence hierarchy. |
| `iclr2027_conference.sty` | ICLR 2027 format (offline reconstruction; drop-in). |
| `references.bib` | Bibliography (7 entries; 2 new = TAB, LongHorizon; all VERIFICATION-REQUIRED placeholders). |
| `main.pdf` | Compiled, anonymized (0 identifying strings). |
| `Makefile` | One-command build. |
| `ANONYMITY_AUDIT.md` | Double-blind audit (PASS). |

## Key Phase-7 content (vs v2)
- **Main result table:** prospective STA n=12 batch is the authoritative STA row (Base 0.208 / BundleS 0.333 / TypedContract 0.458; transfer not established); historical n=3 pilot reported separately, not pooled.
- **Experimental-status table** (7 registration types incl. "preregistered but unexecuted").
- **Study III** adds the Independent Benchmark Repair Audit (Terminal-Bench 2.0→2.1): direct 1 / partial 21 / not-covered 4 of 26.
- **Related work:** TAB (distinct construct) + LongHorizon-Harness (transfer is empirical).
- **Ethics statement:** Study B = preregistered but unexecuted; construct validity rests on executable provenance/authority oracles.
- **Appendix:** Study-A 12-instance table, Study-C full 26-task audit + source evidence, minimal-component ablation, phase chronology, infrastructure + custody.

## Reproducibility / supplement
Frozen manifests, deterministic generators, per-family graders, schedules, custody hashes, and sanitized episode evidence are in the anonymized supplement. Exact submission HEAD is recorded at freeze (Phase-7 manuscript-freeze commit).
