# ICLR 2027 Final Submission Package (Phase-7C / manuscript v4)

**Title:** Auditing Generalization Claims for LLM Agent Harnesses Semantic Binding, External Validity, and Evaluation Reliability in LLM Agents
**Style:** Official ICLR 2027 (media.iclr.cc/Conferences/ICLR2027/iclr-2027-style-files.zip). **Deadlines:** abstract Sept 18 2026 AOE; full paper Sept 25 2026 AOE.

## Build
```
cd submission && make
```

## Page boundaries
- **Main text: 5 pp** (p1-p7; <=9 limit)
- References: p6
- Appendix A-E: p6-p8
- Ethics/AI-use/Reproducibility: p8
- **Total PDF: 8 pp**

## Contents
| File | Purpose |
|---|---|
| main.tex | v3.1 source (official style; 3-study/RQ; expanded main text) |
| main.pdf | Compiled PDF (anonymous; 0 leaks) |
| references.bib | 7 REAL verified citations (arXiv primary source; no placeholders) |
| iclr2027_conference.sty/.bst | Official ICLR 2027 style |
| natbib.sty / fancyhdr.sty | Bundled (from official style package) |
| math_commands.tex | Optional math macros (from official package) |
| Makefile | One-command build |
| FREEZE_HASHES.md | SHA-256 hashes + compliance audit |
| ANONYMITY_AUDIT.md | Double-blind audit (PASS) |

## Phase-7B content
- Model names restored: Qwen3.7-Max, DeepSeek-V4-Pro (public; not author-identifying).
- All 7 citations real + verified against arXiv.
- Deadlines corrected to Sept 18/25 AOE.
- Main text expanded with: construct worked example, mechanism isolation, three-outcome framework, prospective STA per-instance table (in main), audit-incidents table, TB examples + L2=0 implication, per-work gaps, broader implications, ablation summary.
