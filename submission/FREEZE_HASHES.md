# Phase-7C Final Submission Freeze (v5 — final-review patch)

**Submission HEAD:** the commit that adds this file (v5 patch over v4 = bd18973).
**Experiment freeze HEAD:** a89e084 (immutable; no new experiments — v5 is manuscript-only).

## v5 review-patch summary (manuscript-only; no experiments reopened)
- **Bug fixed (review did not name it):** Table 3 (`tab:sta12`) aggregate row `0005–0009` hid instance **0007**, which is a decline (Base `Yn(.5)` → BundleS `nn(0)`, S−B = −0.5). Expanded to all 12 individual rows so the table now matches the prose (3 improve / 2 decline / 7 tie), the exact sign-test (n=5 non-zero, p=1.0), and the permutation sensitivity (Σ=1.5, p=0.31). Ground truth: `reports/synthetic_phase7a_sta72_report.json`.
- **Claim wording:** abstract/§5/figure "clean null" → "not established" / "no established effect" (statistical non-establishment ≠ proven zero effect).
- **Measurement language:** `false ceiling` → "spuriously zeroed; semantic-binding ceiling obscured" (Table 4 + §6); §6 heading "Why the controls are causal" → "materially affected interpretation"; Table 4 caption softened; Table 1 "causal threat log" → "threat log".
- **Label clash removed:** validity-layer labels `L1/L2/L3/L4` → `Cap./Samp./Exec./Art.` (Figure 1, Table 4, Appendix C) so they no longer collide with claim Levels 0–3.
- **AI-use statement** expanded to the ICLR 2027 AI-policy scope (discloses design/critique + result-interpretation assistance; affirms author responsibility; no LLM-as-oracle).
- **Appendix B** now writes out the frozen sign-test + permutation procedure (unit, tie handling, H0, seed, MC replicates).
- **Citations:** added 2 arXiv-verified entries — `harnessaudit` (Auditing Agent Harness Safety, Liu et al. 2026, arXiv:2605.14271) and `safetycap` (Safety, or Just Capability?, Wang et al. 2026, arXiv:2607.28685). Both verified against arXiv primary source on 2026-08-11.
- **Title:** "...Semantic Binding, External Validity, and Evaluation Reliability" → "...Semantic Binding and Measurement Validity" (matches the framework term; removes the reliability≠validity imprecision and a bad line-break).
- **Table 2:** column `$n$` → `\#inst.`; caption distinguishes correct-of-$k$-reps (workflow/SPICE) from mean-rate-over-instances (STA).
- **Cosmetic:** `\hypersetup{hidelinks}` to remove colored hyperlink borders.

## SHA-256 hashes (frozen artifacts, v5)
| Artifact | SHA-256 |
|---|---|
| Source (main.tex) | 80cc2b822d57adf9f87aa420d0033b6d8b24da511db1839249b605978bc10e48 |
| Final PDF (main.pdf, 8 pp) | 373ab09b95fa4bb775a8dd90abdf897bd075218fc1a203330248cf3b449a8df4 |
| Bibliography (references.bib, 9 entries) | 867562f4be4a6c576bdfd3752e8e7e20ad50885a58214f3cd2dda330b99c9670 |
| Style (iclr2027_conference.sty) | 797deef41724e93761426ac0cbcca46279a91cc650dd1f0ce76a4f08d2098ea6 |
| Bibstyle (iclr2027_conference.bst) | 2d67552db7ed38ccfccb5957b52f95656e25c249724761d3cf5f7922ad1844c5 |
| Claim-evidence matrix (docs/phase7/phase7_synthesis.md) | 9dbecd9fedc65ac19bc5ab1c14589013942f746cf18c2b3900c9627b317f961b |

Source-archive and supplement-archive tarball hashes are recomputed at final OpenReview packaging (v4 tarballs superseded by this patch).

## ICLR 2027 compliance audit
- Main text <=9 pages: **PASS** (5 pp main text, p1–p5; official iclr2027 style).
- References outside page limit: **PASS** (references begin p6, after main text).
- Appendix after references: **PASS** (Appendix A begins p7, after references).
- Double-blind anonymity: **PASS** (0 infra/path/user/credential leaks in PDF text; public model names Qwen3.7-Max/DeepSeek-V4-Pro retained — they do not reveal author identity).
- PDF metadata anonymous: **PASS** (Title/Author/Subject/Keywords empty).
- AI-use statement: **PASS** (present, outside page limit; expanded to ICLR 2027 policy scope in v5).
- Ethics statement: **PASS** (accurately records Study B as preregistered-but-unexecuted).
- Reproducibility statement: **PASS** (present; frozen manifests in supplement; Appendix B now documents the STA test procedure).
- No private endpoint/path/user/credential metadata: **PASS**.
- Citations: **PASS** (9 entries, all verified against arXiv primary source; 0 placeholders).
- Build: **PASS** (pdflatex+bibtex; 0 undefined refs/citations; bibtex 0 warnings).
- OpenReview profiles: **HUMAN STEP** — authors must register before abstract deadline (Sept 18, 2026 AOE).

## Deadlines (official ICLR 2027 site)
- Abstract: September 18, 2026 AOE.
- Full paper: September 25, 2026 AOE.
