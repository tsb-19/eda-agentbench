# Anonymity Audit — manuscript v10 (official ICLR 2027 style; double-blind)

**Result: PASS.** Re-scanned on the v10 PDF (configuration-support scope lattice + statistical
wording + one concurrent citation, over v9 = `7c2f9c4f`; v8 = `83379da4`; v7 = `5858d843`, tagged
`iclr2027-submission-v2`; v5 = `3d3e77b`, tagged `iclr2027-submission-v1`).

## Checks
| Surface | Result |
|---|---|
| PDF metadata (pdfinfo) | Title/Author/Subject/Keywords empty; Creator/Producer generic. PASS |
| PDF text: infra leaks (tongsb, /data1, /home, b04, eda-agentbench, harbor-framework, laude-institute, 192.168, 10.x, tsb@) | **0 matches.** PASS |
| PDF text: repository/forge identifiers (github, gitlab, tsb-19) | **0 matches.** PASS — the paper does not link the (public) working repository, so the double-blind supplement is not tied to an identifiable account |
| PDF text: model names (Qwen3.7-Max, DeepSeek-V4-Pro) | **intentionally retained** (public models do not reveal author identity per ICLR double-blind policy). PASS |
| LaTeX source | 0 identifying strings. PASS |
| **All generated `.tex` under `tables/`** | scanned directly as well as through the PDF: **0 matches.** PASS |
| Bibliography | **12** REAL verified citations (arXiv primary source; entries 1–9 verified 2026-08-11 and byte-identical since v5, the 2 v9 additions verified 2026-08-13, the 1 v10 addition verified 2026-08-13); no author-identifying info. PASS |
| Figures | tabular, inline; no metadata. PASS |
| Acknowledgements | none (anonymous). PASS |
| Ethics statement | Study B = preregistered but unexecuted; no author identity. PASS |

## v10 additions specifically audited
| Addition | Anonymity assessment |
|---|---|
| Configuration notation (`c=(f,i,m)`, `C ⊆ 𝒞`, projections `π_I`, `π_M`, `π_F`) | Abstract set-theoretic notation over already-disclosed public model names and internal family labels. No external referent. PASS |
| "Instances are family-specific" / sparse-support prose | Methodological prose about the design space. Names no instance path, generator seed, host or repository. PASS |
| Reworded scope-region enumeration (four of five regions, five supports) | Framework prose. PASS |
| Sharpened band wording (with-replacement resampling; central 95%; empirical reweighting) | Statistical prose over already-published numbers. PASS |
| Trajectory-level Monte-Carlo limitation paragraph (Appendix C) | States a limit of the analysis; discloses only the already-published two-repetitions-per-cell design. PASS |
| "Sole basis for the confirmatory verdict" rewording | Methodological prose only. PASS |
| Pilot `−16.7pp` surfaced into §5 via `\StatPilotDelta` | Already-published number, previously appearing in Appendix C; relocating it discloses nothing new. PASS |
| One concurrent citation (arXiv:2606.23127) | Third-party public preprint, cited neutrally alongside 11 existing works; no self-citation, no venue or affiliation hint, no phrasing implying authorship. Positioned as prior/related work whose existence *narrows* our novelty claim — which is the opposite of a self-promotional tell. PASS |
| Positioning table relocated to Appendix G (+1 row for AFTER) | Content unchanged from the v9 audit apart from the added row, which names only a public preprint and a framework property. Re-scanned in its new position. PASS |
| `\tabcolsep` set to 4pt in three tables | Typesetting only; no textual content. PASS |

## Carried over from v6–v9 (re-audited on the v10 PDF)
| Item | Anonymity assessment |
|---|---|
| Worked instance + evidence table (Appendix A) | Generic design/module names (`acc_stage`, `netlist_v2.v`, `clk_main`), axis values and a PVT descriptor. **No paths, hosts, users, licence servers or tool-install prefixes.** The tool is named generically ("PrimeTime"). PASS |
| Typed-oracle description (§3) | Predicate semantics, not file paths or internal script names. PASS |
| Study I ledger (Appendix B, `\input` from a generated table) | Frozen synthetic task identifiers (`0009`–`0023`) and stage labels only. PASS |
| 12-instance STA table + three-instance pilot table (Appendix C) | Frozen synthetic instance identifiers (`0001`–`0015`) and rates only. PASS |
| Reference-standard custody principle (§6) | Attributes the write to "a component of our own test harness" without naming the file, host or repository. **Does not repeat the superseded "unidentified external process" attribution** (0 occurrences of "unidentified"/"external process" in the PDF). PASS |
| Model-custody paragraph (§6) — 0/70 snapshot, 66/70 alias+date, 4 no record | States what was **not** recorded. Names no endpoint, gateway, key, account, region, host or provider-internal identifier. **Confirms rather than weakens anonymity** — no request/response identifiers are disclosed because none were retained. PASS |
| Generated `tables/claim_stats.tex` | Numbers, percentages, ISO dates and counts only. **Run dates (2026-07-12 … 2026-08-03) remain deliberately disclosed** as measurement provenance; they identify a calendar window, not a person, host, institution or account, and carry no timezone or working-hours signal. PASS |
| Exploratory/confirmatory chronology with freeze points (Appendix E) | Describes ordering and what was committed when; names no commit hash, repository, host or date beyond the phase structure. PASS |
| Falsifiability section (§7) | Methodological prose only. PASS |
| Reproducibility statement | Program totals and cost figures only; no endpoint, key, gateway or account information. PASS |
