**English | [中文](ABORTED.zh.md)**

# Aborted pass — arm 2, block 00 (`8A_sta:p15_eval_0004:DeepSeek-V4-Pro-TR`), attempt 1

Archived under the rule fixed in [`docs/phase8a_prereg.md` §5B.3](../../../../docs/phase8a_prereg.md),
and recorded in [§5E](../../../../docs/phase8a_prereg.md).
**Nothing here enters the analysis. Its cost does enter the ledger.**

## What happened

| | |
|---|---|
| started | 2026-08-19T03:31:01Z |
| ended | 2026-08-19T04:00:08Z, `executor_exit_code: 2` |
| slots completed | 2 of 6 |
| episodes collected | 3 — BundleS 1, TypedContract 1, Base 1 (invalid) |
| cause | provider returned HTTP `503 {"code":"SERVICE_BUSY","message":"API Key 鉴权服务暂时不可用，请稍后重试"}` on three consecutive attempts at `Base/pos2`; each attempt exhausted all 6 chat retries (`recovered_failed_attempts: 6`); `episode_arbiter` reached STOP at the 2-replacement cap, as designed |
| classification | `measurement_valid: false`, `classification_source: request_telemetry` — an infrastructure fault, never a capability failure |
| cost paid | **¥1.9492** = ¥1.4024 in surviving episodes + ¥0.5468 for a replaced attempt |

## This is not the block-02 fault, and the proof is an unbilled endpoint

Arm 1 block 02 died on `402 INSUFFICIENT_BALANCE` — the account had run out of money. That outage
left `GET /v1/models` returning `200` with the full model list, because listing models is not billed.

Here `GET /v1/models` **also returns `503 SERVICE_BUSY` with the same authentication-service
message**. An outage that blocks an unbilled endpoint cannot be a balance condition. The provider's
own label is that its API-key authentication service is down, and the unbilled canary corroborates
it rather than merely repeating it — which is the point, because a provider's error string is its
account of itself, not evidence.

Nor is it this backend's ordinary throttling. The measured 503 rate that motivated the raised retry
budget (35% back-to-back, 8.3% at 15 s spacing) is a *per-request* failure rate that 6 retries with
3/6/12/24/45 s backoff reaches past. Here all 6 retries failed, three attempts running, for 29
minutes — the endpoint was not throttling, it was unavailable.

## What the guard caught, and why it matters more than the outage

`p15_eval_0004_base_r1` was written to custody with **`total_cost: 0.0` and `total_score: 0.5`**, and
`error: null`. No model was called — and the episode still carries a score, because
`run_single_agentic` grades whatever is in the workspace and an untouched p15 workspace scores 0.5.

Unguarded, this arm would have recorded a provider auth outage as a **0.5 for DeepSeek on
instance 0004 under Base**. With replacements clustering during an outage, a bad hour becomes a
column of plausible mid-range scores that look collected. `_telemetry_faults` in
`scripts/phase8a_run.py` refuses to continue past an episode with no evidence of a model call, which
is what stopped this pass at block 00 rather than at block 12.

## Why the whole pass was discarded rather than resumed

`p15_eval_0004_bundles_r1` (¥0.8669, score 1.0) and `p15_eval_0004_typedcontract_r1` (¥0.5355,
score 0.5) completed **validly**. `chain_executor.py` restarts a block at position 0 and
`phase8a_episode_runner.py` overwrites a trial's custody directory, so re-running the block in place
would have overwritten them anyway.

Keeping them and resuming at position 2 would waste nothing — but it puts the keep/discard boundary
between episodes whose scores were already known, which is the shape of retrying away a valid score.
Discarding the pass whole is all-or-nothing and so cannot depend on any episode's score. Note that
the discarded pair happens to contain this arm's only score of 1.0 so far; that is exactly why the
rule may not be decided now.

## Contents

```
p15_eval_0004_bundles_r1/         valid episode, discarded from the analysis     ¥0.8669
p15_eval_0004_typedcontract_r1/   valid episode, discarded from the analysis     ¥0.5355
p15_eval_0004_base_r1/            terminal-invalid: ¥0 cost, no model call       ¥0
run_state.json                    copy of the aborted chain_executor run state
chain_log_arm2_block00.log        sanitized copy of the chain log
```

`run_state.json` is a **copy**. The one the report reads is
`phase8a/evidence/run_state_arm2_block00_attempt1.json`, kept at that path because
`phase8a_report._states()` globs `run_state_arm2*.json` non-recursively — the three `503` attempts
must stay countable as measurement-invalid, or the record would understate this backend's
infrastructure noise.

`chain_log_arm2_block00.log` is copied in because `runs/` is gitignored and this log is the **only**
surviving record of what each attempt cost. Attempt 1 of `Base/pos2` cost ¥0.5468 and was then
overwritten by two ¥0 attempts, so the custody tree reports ¥0 for a slot that was billed — see
`phase8a/evidence/replaced_attempt_ledger.json`, whose two entries were reconstructed from this file.

This directory sits **outside** `phase8a/evidence/episodes_arm2/` deliberately: that tree's
`*/episode.json` glob is the grading and spend glob, and an archive nested inside it would make the
same trial appear twice, once from this pass and once from the re-run.
