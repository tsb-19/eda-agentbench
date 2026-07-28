# Phase-4Y Stage-3 fairness — b04 golden-corruption blocker (evidence note)

**Status: Stage-3 construction SOUND; real-PT fairness BLOCKED by b04 golden-corruption under gate load.**

## Variant soundness (proven)
C2-only (0022) = 0009 + a single PVT-definition line in spec.md. The grader does NOT read spec.md
(verified: grade_workflow.py / run_hidden.sh / run_public.sh contain no spec.md read). Therefore 0022's
golden grading path is byte-identical to 0009's. **Clean-isolation confirmation (EnvShim env, no load):**
0022 golden stage1 → `signoff=OK` MET (slack 0.13), 13 s, identical to 0009 golden. **0022 is a sound
variant; golden grades 1.0 when b04 PT runs correctly.**

## The blocker
Under the full fairness gate (0009 → 0022 → 0023, ~60 PT ops), b04 PT intermittently produces
**corrupted output for the 0022 golden** (a false signoff=RED / stale-evidence result on a known-MET
config). Observed across two fresh full-gate runs:
- Run 1: 0022 golden = 0.2 (signoff GREEN, evgen 0). 0009=1.0, 0023=1.0 in the same run.
- Run 2: 0022 golden = 0.1 (signoff RED, evgen 0). 0009=1.0, 0023=1.0 in the same run.

The varying wrong scores (0.2 then 0.1) for a proven-MET golden = b04 PT corruption under load, not a
variant defect. 0009 and 0023 (which bracket 0022 in the run) grade golden=1.0 each time.

## Rule interaction
Under the corrected validity-only retry rule, a gradeable result with an unfavorable score is a HARD
gate failure and is not retried. The gate therefore hard-fails on the b04-corrupted 0022 golden and
(correctly) does not retry it. A golden signoff=RED for a known-MET config is, by nature, corrupted PT
output (PT cannot legitimately produce RED for slack=0.13) — arguably the rule's "truncated / corrupted
output" infra-failure case — but this is a rule-interpretation decision that is the user's to make
(given the prior explicit correction away from golden-retry-until-1.0).

## Decision needed
Is a b04-corrupted golden score on a proven-sound variant retryable (as corrupted-PT-output infra
failure), or a hard failure under the strict validity-only reading? The variant is sound either way;
this gates only whether the fairness collection can complete under intermittent b04 load.
