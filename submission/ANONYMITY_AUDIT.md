# Anonymity Audit — manuscript v9 (official ICLR 2027 style; double-blind)

**Result: PASS.** Re-scanned on the v9 PDF (estimand-aligned uncertainty + formalized scope order +
two concurrent citations, over v8 = `83379da4`; v7 = `5858d843`, tagged `iclr2027-submission-v2`;
v5 = `3d3e77b`, tagged `iclr2027-submission-v1`).

## Checks
| Surface | Result |
|---|---|
| PDF metadata (pdfinfo) | Title/Author/Subject/Keywords empty; Creator/Producer generic. PASS |
| PDF text: infra leaks (tongsb, /data1, /home, b04, eda-agentbench, harbor-framework, laude-institute, 192.168, 10.x, tsb@) | **0 matches.** PASS |
| PDF text: repository/forge identifiers (github, gitlab, tsb-19) | **0 matches.** PASS — the paper does not link the (public) working repository, so the double-blind supplement is not tied to an identifiable account |
| PDF text: model names (Qwen3.7-Max, DeepSeek-V4-Pro) | **intentionally retained** (public models do not reveal author identity per ICLR double-blind policy). PASS |
| LaTeX source | 0 identifying strings. PASS |
| **All generated `.tex` under `tables/`** | scanned directly as well as through the PDF: **0 matches.** PASS |
| Bibliography | **11** REAL verified citations (arXiv primary source; entries 1–9 verified 2026-08-11 and byte-identical since v5, the 2 additions verified 2026-08-13); no author-identifying info. PASS |
| Figures | tabular, inline; no metadata. PASS |
| Acknowledgements | none (anonymous). PASS |
| Ethics statement | Study B = preregistered but unexecuted; no author identity. PASS |

## v9 additions specifically audited
| Addition | Anonymity assessment |
|---|---|
| Set-theoretic scope definitions (`{i_dev} ⊂ {i_dev, i_held}`, `{Qwen} ⊂ {Qwen, DeepSeek}`, `{workflow} ⊂ {workflow, STA}`) | Abstract notation over already-disclosed public model names and internal family labels. No external referent. PASS |
| Reworded claim-qualification tiers (replicated / estimated) | Methodological prose only. PASS |
| Instance-resampling sensitivity-band wording (§5, Appendix C) | Statistical prose and already-published numbers. PASS |
| New generated macros `\StatSnapshotEpisodes` (0), `\StatNoDiagEpisodes` (4) | Bare counts. PASS |
| Exact model-custody sentence (0/70 snapshot; 66/70 alias+date; 4 no record) | States what was **not** recorded. Names no endpoint, gateway, key, account, region, host or provider-internal identifier; the models are named only by their already-disclosed public aliases. **Confirms rather than weakens anonymity** — no request/response identifiers are disclosed because none were retained. PASS |
| S2-F coordinate-class note in the main-result caption | Framework notation. PASS |
| Two concurrent citations (arXiv:2607.28802, arXiv:2608.00794) | Third-party public preprints, cited neutrally alongside 9 existing works; no self-citation, no venue or affiliation hint, no phrasing that implies authorship of either. Both are *concurrent* (2026-07-30, 2026-08-01) and are positioned as related work, not as prior work by the authors. PASS |
| 12-instance STA table relocated to Appendix C | Content unchanged from the v8 audit (frozen synthetic instance identifiers `0004`–`0015` and rates only); re-scanned in its new position. PASS |
| Regenerated `tables/claim_stats.tex` | Macro **names** changed; contents remain only numbers, percentages, ISO dates and counts. **Run dates (2026-07-12 … 2026-08-03) remain deliberately disclosed** as measurement provenance; they identify a calendar window, not a person, host, institution or account, and carry no timezone or working-hours signal. PASS |

## Carried over from v6–v8 (re-audited on the v9 PDF)
| Item | Anonymity assessment |
|---|---|
| Worked instance + evidence table (Appendix A) | Generic design/module names (`acc_stage`, `netlist_v2.v`, `clk_main`), axis values and a PVT descriptor. **No paths, hosts, users, licence servers or tool-install prefixes.** The tool is named generically ("PrimeTime"). PASS |
| Typed-oracle description (§3) | Predicate semantics, not file paths or internal script names. PASS |
| Study I ledger (Appendix B, `\input` from a generated table) | Frozen synthetic task identifiers (`0009`–`0023`) and stage labels only. PASS |
| Three-instance pilot table (Appendix C) | Frozen synthetic instance numbers (`0001`–`0003`) and rates only. PASS |
| Reference-standard custody principle (§6) | Attributes the write to "a component of our own test harness" without naming the file, host or repository. **Does not repeat the superseded "unidentified external process" attribution** (0 occurrences of "unidentified"/"external process" in the PDF). PASS |
| Model-custody paragraph (§6) + backend-drift limitation | Names providers only by their already-disclosed public model names. No endpoint, gateway, key, account or region. PASS |
| Exploratory/confirmatory chronology with freeze points (Appendix E) | Describes ordering and what was committed when; names no commit hash, repository, host or date beyond the phase structure. PASS |
| Falsifiability section (§7) | Methodological prose only. PASS |
| Reproducibility statement | Program totals and cost figures only; no endpoint, key, gateway or account information. PASS |
