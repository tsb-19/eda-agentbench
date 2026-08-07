# Anonymity Audit (double-blind / ICLR 2027)

**Scope:** all submission-package artifacts — compiled PDF, LaTeX source, style
file, bibliography, figures, metadata. ICLR 2027 is double-blind; author
identity in main or supplementary material can cause desk rejection.

## Result: PASS

No author-identifying content was found in the PDF text, the PDF metadata, or
any source file. Models are referred to as **Model A / Model B** throughout.

## Checks performed

| Surface | What was checked | Result |
|---|---|---|
| PDF metadata (`pdfinfo`) | Title, Author, Subject, Keywords, Creator, Producer | Author/Title/Subject/Keywords **empty**; Creator=`LaTeX with hyperref`, Producer=`pdfTeX` (generic). PASS. |
| PDF text (`pdftotext`) | grep for `qwen\|deepseek\|kimi\|minimax\|glm-\|tongsb\|/data1\|/home/\|b04\|eda-agentbench\|/[A-Z]{3}/soft` | **0 matches.** PASS. |
| LaTeX source (`main.tex`) | same pattern set + emails + acknowledgement/funding/corresponding-author language | **0 matches.** PASS. |
| Style file (`iclr2027_conference.sty`) | identifying strings, paths | **0 matches.** PASS. |
| Bibliography (`references.bib`) | author names, emails, affiliations | placeholder author metadata (`{... authors}`), no real names; flagged VERIFICATION-REQUIRED. PASS (finalize before camera-ready). |
| Figures | TikZ/tabular, generated inline | no embedded metadata, paths, or watermarks. PASS. |
| Acknowledgements / funding | none present (anonymous submission). | PASS. |
| Commit / user / machine names | not present in any submission artifact | PASS. |
| Supplementary references | "anonymized supplementary material" wording; no repo URL, no commit hashes in main PDF | PASS (exact hashes deferred to non-identifying supplementary). |

## Anonymization conventions used

- Models: "Model A" (responsive within-family) / "Model B" (cross-model).
- Compute host: "a remote commercial-tool compute server"; tool access: "a transparent remote execution shim".
- Code/artifact: "provided as anonymized supplementary material".
- Internal phase labels (Phase-5C/5D) are retained as methodology labels — they do not identify authors.

## One leak found and fixed during the audit

The SPICE-chronology paragraph initially named the real model ("Qwen, 24 episodes"); corrected to "Model A". Re-audit after the fix: PDF text and source both clean (0 matches).

## Recommendation before camera-ready

Replace the five VERIFICATION-REQUIRED bibliography entries with verified
canonical citations, and confirm the official `iclr2027_conference.sty` does not
embed identifying data when it is dropped in.
