# Anonymity Audit — manuscript v7 (official ICLR 2027 style; double-blind)

**Result: PASS.** Re-scanned on the v7 PDF (principled ledger recomputation + 3 wording fixes over
v6 = 0e82e59; v5 = 3d3e77b, tagged `iclr2027-submission-v1`).

## Checks
| Surface | Result |
|---|---|
| PDF metadata (pdfinfo) | Title/Author/Subject/Keywords empty; Creator/Producer generic. PASS |
| PDF text: infra leaks (tongsb, /data1, /home, b04, eda-agentbench, harbor-framework, laude-institute, 192.168, 10.x, tsb@) | **0 matches.** PASS |
| PDF text: repository/forge identifiers (github, gitlab, tsb-19) | **0 matches.** PASS — the paper does not link the (public) working repository, so the double-blind supplement is not tied to an identifiable account |
| PDF text: model names (Qwen3.7-Max, DeepSeek-V4-Pro) | **intentionally retained** (public models do not reveal author identity per ICLR double-blind policy). PASS |
| LaTeX source | 0 identifying strings. PASS |
| Bibliography | **9** REAL verified citations (arXiv primary source, 2026-08-11); unchanged from v5 and v6 (hash-identical); no author-identifying info. PASS |
| Figures | TikZ/tabular, inline; no metadata. PASS |
| Acknowledgements | none (anonymous). PASS |
| Ethics statement | Study B = preregistered but unexecuted; no author identity. PASS |

## v7 additions specifically re-audited
| Addition | Anonymity assessment |
|---|---|
| Recomputed Study I ledger (Table 3, `\input` from `tables/study1_ledger.tex`) | The 5 added rows introduce only frozen synthetic task identifiers (`0013`–`0023`) and stage labels (`C6 ablation`, `cross-model 1C`, `decomp. 3`). No paths, hosts, users, run directories, dates or repository names. The generated `.tex` was scanned directly as well as through the PDF. PASS |
| Ledger caption (inclusion rule) | Names the frozen manifest by role, not by repository path; states counts only. Re-scanned after the accounting patch, which added phase-family words ("ablation phases", "controlled pair") and counts only. PASS |
| Episode-accounting sentences (Table 3 caption, Appendix A, Appendix D, reproducibility statement) | Counts and phase-family names only; no host, path, ledger file name, account or date. PASS |
| Three wording fixes (§4 over-claim, §6 limitation, §5/§7 softenings) | Methodological prose only; the custody paragraph continues to attribute the write to "a component of our own test harness" without naming file, host or repository. PASS |

## v6 additions (still present, re-audited on the v7 PDF)
| Addition | Anonymity assessment |
|---|---|
| Worked instance + evidence table (§3) | Content is drawn from a frozen synthetic task: generic design/module names (`acc_stage`, `netlist_v2.v`, `clk_main`), axis values (`slow`/`func`/`typ`) and a PVT descriptor. **No paths, hosts, users, licence servers or tool-install prefixes.** The tool is named generically ("PrimeTime"), as already throughout v5. PASS |
| Typed-oracle description (§3) | Describes predicate semantics, not file paths or internal script names. PASS |
| Study I per-condition ledger (promoted to main text; now Table 3, recomputed in v7) | Condition labels (`BundleS`, `C24`, instance numbers) are internal experiment identifiers with no external referent. PASS |
| Reference-standard custody principle (§5) | States the failure mode in general terms; attributes the write to "a component of our own test harness" without naming the file, the host, or the repository. **Does not repeat the superseded "unidentified external process" attribution** (0 occurrences of "unidentified"/"external process" in the PDF). PASS |
| Falsifiability section (§7) | Methodological prose only. PASS |
| Relocated Reproducibility statement | Program totals and cost figures only; no endpoint, key, gateway or account information. PASS |
