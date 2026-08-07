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
