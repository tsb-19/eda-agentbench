# Anonymity Audit — manuscript v8 (official ICLR 2027 style; double-blind)

**Result: PASS.** Re-scanned on the v8 PDF (claim-scope lattice + symmetric claim calibration +
offline statistics, over v7 = `5858d843`, tagged `iclr2027-submission-v2`; v5 = `3d3e77b`, tagged
`iclr2027-submission-v1`).

## Checks
| Surface | Result |
|---|---|
| PDF metadata (pdfinfo) | Title/Author/Subject/Keywords empty; Creator/Producer generic. PASS |
| PDF text: infra leaks (tongsb, /data1, /home, b04, eda-agentbench, harbor-framework, laude-institute, 192.168, 10.x, tsb@) | **0 matches.** PASS |
| PDF text: repository/forge identifiers (github, gitlab, tsb-19) | **0 matches.** PASS — the paper does not link the (public) working repository, so the double-blind supplement is not tied to an identifiable account |
| PDF text: model names (Qwen3.7-Max, DeepSeek-V4-Pro) | **intentionally retained** (public models do not reveal author identity per ICLR double-blind policy). PASS |
| LaTeX source | 0 identifying strings. PASS |
| **All generated `.tex` under `tables/`** | scanned directly as well as through the PDF: **0 matches.** PASS |
| Bibliography | **9** REAL verified citations (arXiv primary source, 2026-08-11); unchanged from v5–v7 (hash-identical); no author-identifying info. PASS |
| Figures | tabular, inline; no metadata. PASS (the v6/v7 TikZ taxonomy figure was removed in v8) |
| Acknowledgements | none (anonymous). PASS |
| Ethics statement | Study B = preregistered but unexecuted; no author identity. PASS |

## v8 additions specifically audited
| Addition | Anonymity assessment |
|---|---|
| Scope-lattice relabelling (S0/S1/S2-M/S2-F/S3) throughout | Abstract notation only; no external referent. PASS |
| Claim-qualification standard (§3.1) and Table 2 (evidence → licensed wording) | Methodological prose and generic evidence shapes; no data, hosts or paths. PASS |
| Generated stat macros (`tables/claim_stats.tex`) | Contains only numbers, percentages, ISO dates and counts. **Run dates (2026-07-12 … 2026-08-03) are deliberately disclosed** as measurement provenance; they identify a calendar window, not a person, host, institution or account, and carry no timezone or working-hours signal. PASS |
| Generated pilot table (`tables/sta_pilot.tex`) | Frozen synthetic instance numbers (`0001`–`0003`) and rates only. PASS |
| Model-custody paragraph (§6) + backend-drift limitation | States that a provider-resolved snapshot was **not** retained, and names providers only by their already-disclosed public model names. No endpoint, gateway, key, account or region. PASS |
| Exploratory/confirmatory chronology with freeze points (Appendix E) | Describes ordering and what was committed when; names no commit hash, repository, host or date beyond the phase structure. PASS |
| Table 6 Capability row | Generic threat/control wording. PASS |
| Ledger and worked-instance tables relocated to the appendix | Content unchanged from the v7 audit (frozen synthetic task identifiers and stage labels only); re-scanned in their new position. PASS |

## Carried over from v6/v7 (re-audited on the v8 PDF)
| Item | Anonymity assessment |
|---|---|
| Worked instance + evidence table (now Appendix A) | Generic design/module names (`acc_stage`, `netlist_v2.v`, `clk_main`), axis values and a PVT descriptor. **No paths, hosts, users, licence servers or tool-install prefixes.** The tool is named generically ("PrimeTime"). PASS |
| Typed-oracle description (§3) | Predicate semantics, not file paths or internal script names. PASS |
| Study I ledger (now Appendix A, `\input` from a generated table) | Frozen synthetic task identifiers (`0009`–`0023`) and stage labels only. PASS |
| Reference-standard custody principle (§6) | Attributes the write to "a component of our own test harness" without naming the file, host or repository. **Does not repeat the superseded "unidentified external process" attribution** (0 occurrences of "unidentified"/"external process" in the PDF). PASS |
| Falsifiability section (§7) | Methodological prose only. PASS |
| Reproducibility statement | Program totals and cost figures only; no endpoint, key, gateway or account information. PASS |
