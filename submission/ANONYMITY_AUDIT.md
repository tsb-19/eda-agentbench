# Anonymity Audit — manuscript v3.1 (official ICLR 2027 style; double-blind)

**Result: PASS.**

## Checks
| Surface | Result |
|---|---|
| PDF metadata (pdfinfo) | Title/Author/Subject/Keywords empty; Creator/Producer generic. PASS |
| PDF text: infra leaks (tongsb, /data1, /home, b04, eda-agentbench, harbor-framework, laude-institute, 192.168) | **0 matches.** PASS |
| PDF text: model names (Qwen3.7-Max, DeepSeek-V4-Pro) | 14 + 5 occurrences — **intentionally restored** (public models do not reveal author identity per ICLR double-blind policy). PASS |
| LaTeX source | 0 identifying strings. PASS |
| Bibliography | 7 REAL verified citations (arXiv); no author-identifying info. PASS |
| Figures | TikZ/tabular, inline; no metadata. PASS |
| Acknowledgements | none (anonymous). PASS |
| Ethics statement | Study B = preregistered but unexecuted; no author identity. PASS |
