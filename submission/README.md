# ICLR 2027 Final Submission Package (Phase-7C / manuscript v5)

**Title:** Auditing Generalization Claims for LLM Agent Harnesses: Semantic Binding and Measurement Validity
**Style:** Official ICLR 2027 (media.iclr.cc/Conferences/ICLR2027/iclr-2027-style-files.zip). **Deadlines:** abstract Sept 18 2026 AOE; full paper Sept 25 2026 AOE.

## Build
```
cd submission && make
```

## Page boundaries
- **Main text: 5 pp** (p1–p5; <=9 limit)
- References: p6 (outside page limit)
- Appendix A–E: p7–p8 (outside page limit)
- Ethics/AI-use/Reproducibility: p8
- **Total PDF: 8 pp**

## Contents
| File | Purpose |
|---|---|
| main.tex | v5 source (official style; 3-study/RQ; claim-scope ladder + 2D framework) |
| main.pdf | Compiled PDF (anonymous; 0 leaks) |
| references.bib | 9 REAL verified citations (arXiv primary source; no placeholders) |
| iclr2027_conference.sty/.bst | Official ICLR 2027 style |
| natbib.sty / fancyhdr.sty | Bundled (from official style package) |
| math_commands.tex | Optional math macros (from official package) |
| Makefile | One-command build |
| FREEZE_HASHES.md | SHA-256 hashes + compliance audit |
| ANONYMITY_AUDIT.md | Double-blind audit (PASS) |

## v5 (final-review patch; manuscript-only, no experiments reopened)
- Fixed an internal inconsistency the review surfaced: Table 3 (`tab:sta12`) hid instance 0007 (a decline) inside an all-tie aggregate; expanded to all 12 rows so the table matches the prose (3/2/7), the sign-test (p=1.0), and the permutation (Σ=1.5, p=0.31).
- Claim wording: "clean null" → "not established" (abstract/§5/figure).
- Measurement language: "false ceiling" → "spuriously zeroed; semantic-binding ceiling obscured"; "Why the controls are causal" → "materially affected interpretation".
- Removed the L1–L4 (validity) vs Level 0–3 (claim scope) label clash → `Cap./Samp./Exec./Art.`
- AI-use statement expanded to the ICLR 2027 AI-policy scope.
- Appendix B now writes out the frozen sign-test + permutation procedure.
- Added 2 arXiv-verified citations: HarnessAudit (Liu et al. 2026), Safety-or-Capability (Wang et al. 2026).
- Title shortened; Table 2 `n`→`#inst.`; `\hypersetup{hidelinks}`.

## Inherited from Phase-7B/v4
- Model names restored: Qwen3.7-Max, DeepSeek-V4-Pro (public; not author-identifying).
- Official ICLR 2027 style; claim-scope ladder (L0–L3) + 2D scope×validity framework.
- Deadlines Sept 18/25 AOE.
