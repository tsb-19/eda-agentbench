# Anonymity Audit — manuscript v5 (official ICLR 2027 style; double-blind)

**Result: PASS.** Re-scanned on the v5 PDF (final-review patch over v4 = bd18973).

## Checks
| Surface | Result |
|---|---|
| PDF metadata (pdfinfo) | Title/Author/Subject/Keywords empty; Creator/Producer generic. PASS |
| PDF text: infra leaks (tongsb, /data1, /home, b04, eda-agentbench, harbor-framework, laude-institute, 192.168, 10.x, tsb@) | **0 matches.** PASS |
| PDF text: model names (Qwen3.7-Max, DeepSeek-V4-Pro) | 11 + 3 occurrences — **intentionally restored** (public models do not reveal author identity per ICLR double-blind policy). PASS |
| LaTeX source | 0 identifying strings. PASS |
| Bibliography | **9** REAL verified citations (arXiv primary source, 2026-08-11; incl. v5 additions `harnessaudit` arXiv:2605.14271 and `safetycap` arXiv:2607.28685); no author-identifying info. PASS |
| Figures | TikZ/tabular, inline; no metadata. PASS |
| Acknowledgements | none (anonymous). PASS |
| Ethics statement | Study B = preregistered but unexecuted; no author identity. PASS |
| v5 additions (Appendix B seed `20260811`; HarnessAudit "210 tasks / 8 domains") | Not author-identifying (an internal RNG seed; external-paper statistics). PASS |
