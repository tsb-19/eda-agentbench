# Submission / Freeze-State Attestation (Phase-6C)

This document records the repository state verbatim and resolves the
manuscript/figures/claim-matrix/freeze-manifest to explicit HEADs. It exists to
remove any ambiguity about which commits contribute to the ICLR 2027 submission.

## Verbatim repository state (recorded at start of Phase-6C)

```
$ git status --porcelain=v1
?? docs/synthetic_phase6_manuscript_v2.md
?? docs/synthetic_phase6_manuscript_v2.pdf
?? docs/synthetic_phase6_mock_reviews_v2.md
$ git branch --show-current
master
$ git rev-parse HEAD
013947b84779c7be529a094bc0257b0e7138f5e0
$ git rev-parse origin/master
013947b84779c7be529a094bc0257b0e7138f5e0
$ git rev-list --left-right --count origin/master...HEAD
0       0
```

Interpretation: at Phase-6C start, `master` and `origin/master` were identical
(`013947b`); there were **zero** local commits ahead of origin; the only tree
changes were three untracked Phase-6B deliverable files. There was no genuine
repository inconsistency — "clean tree" in the prior summary meant *no tracked
modifications*, and it did not contradict the three untracked files. Nothing has
been pushed.

## Two explicit HEADs

- **Experiment freeze HEAD (immutable):** `a89e084`
  ("report(phase5d): TypedContract extension complete 36/36"). **No experiment,
  paid model call, or task/model asset beyond `a89e084` contributes to this
  submission.** All numbers in the paper are reproduced from committed ledgers
  at or before this HEAD.
- **Submission HEAD:** the final commit of the Phase-6C series on `master`
  (repository-hardening only: LaTeX conversion, statistical/detectability
  wording, trajectory-stability analysis, SPICE chronology, softened protocol
  language, anonymous package, reviews). It contains **no new experimental
  result** and is ahead of `a89e084` by documentation/submission commits only.

## Untouched assets (confirmed not consumed)

- held-out-family-2 (workflow tasks 0024-0027): not run, not altered.
- Cross-family extensions beyond the frozen Qwen core (Phase-5C) and the
  separately-frozen TypedContract secondary (Phase-5D): not executed.
- No new model calls of any kind during Phase-6C.

## How to verify

```
git rev-parse HEAD            # submission HEAD (Phase-6C tip)
git rev-parse a89e084         # experiment freeze HEAD
git log --oneline a89e084..HEAD   # Phase-6C commits (docs/submission only)
```

# Phase-7 update (manuscript v3; all experiments permanently closed)

- **Experiment freeze HEAD (immutable):** `a89e084` — unchanged; no new experiments/consumed assets in Phase-7.
- **Phase-7 manuscript-freeze HEAD (the submission package):** `06434c0` — manuscript v3 source/PDF + appendix + anonymous package (`submission/`).
- **Phase-7 tip:** the final-review-packet commit (internal review; not part of the submitted package).
- Study A prospective n=12 authoritative; historical STA bug audit = pilot unaffected (no erratum); Study B = preregistered but unexecuted; Study C = Terminal-Bench 2.0->2.1 static audit complete (direct 1/partial 21/Other 4). ICLR 2027 deadlines verified: abstract 2026-09-19, paper 2026-09-26 (11:59 UTC). Anonymous (0 leaks). Not pushed.
