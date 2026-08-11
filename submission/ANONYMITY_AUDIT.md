# Anonymity Audit — manuscript v3 (double-blind / ICLR 2027)

**Result: PASS.** Compiled PDF and all sources are free of author-identifying content. Models are Model A / Model B throughout.

## Checks (v3)
| Surface | Result |
|---|---|
| PDF metadata (`pdfinfo`) | Author/Title/Subject/Keywords empty; Creator/Producer generic. PASS |
| PDF text leak scan (`qwen|deepseek|kimi|minimax|glm-|tongsb|/data1|/home/|b04|eda-agentbench|harbor-framework|laude-institute`) | **0 matches.** PASS |
| LaTeX source (`main.tex`, `.sty`, `.bib`) | 0 identifying strings. PASS |
| Bibliography | 7 placeholder entries (`{... authors}`), flagged VERIFICATION-REQUIRED; no real names/affiliations. PASS (finalize before camera-ready) |
| Figures | TikZ/tabular, inline; no metadata/paths. PASS |
| Acknowledgements / funding | none (anonymous). PASS |
| Terminal-Bench references | named as "Terminal-Bench 2 / 2.1" + "PR #53" (public benchmark); no org/repo identity exposed in main text. PASS |

## Fixes applied during the audit
- v3 Study II intro initially named the real model ("DeepSeek"); corrected to "Model B" (re-scan: 0).

## Pre-submission checklist
- Replace the 7 VERIFICATION-REQUIRED bibliography entries with verified canonical citations.
- Drop in the official `iclr2027_conference.sty` when released and re-run the leak scan.
- Confirm the official style adds no identifying metadata.
