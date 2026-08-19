**English | [中文](ABORTED.zh.md)**

# Aborted pass — arm 2, block 00 (`8A_sta:p15_eval_0004:DeepSeek-V4-Pro-TR`), attempt 2

Archived by `scripts/phase8a_archive_pass.py` at 2026-08-19T08:07:47Z under the rule fixed in
[`docs/phase8a_prereg.md` §5B.3](../../../../docs/phase8a_prereg.md).
**Nothing here enters the analysis. Its cost does enter the ledger.**

| | |
|---|---|
| started | 2026-08-19T04:36:39Z |
| ended | 2026-08-19T06:32:45Z, `executor_exit_code: 0` |
| slots completed | 6 of 6 |
| episodes collected | 6 |
| cause | `harness race, not a provider fault: run_single_agentic returned before llm_agent_driver had written its agent log, so p15_eval_0004_base_r2 was graded while the agent was still editing the workspace and recorded at cost 0.0 with no telemetry (the pinned arbiter, seeing no fault, ACCEPTed it), and p15_eval_0004_base_r1 attempt 1 was charged the ARCHIVED pass's cost and classified on the ARCHIVED pa` |
| classification | `measurement_valid: false` — an infrastructure fault, never a capability failure |
| cost paid | **¥5.5222** = ¥5.5222 in collected episodes + ¥0 for replaced attempts |

The whole pass is discarded rather than resumed. Some episodes here may have completed **validly**;
keeping those and resuming mid-block would put the keep/discard boundary between episodes whose
scores were already known, which is the shape of retrying away a valid score. All-or-nothing cannot
depend on any episode's score. `chain_executor.py` restarts a block at position 0 and
`phase8a_episode_runner.py` overwrites a trial's custody directory, so an in-place re-run would
overwrite them anyway.

The reasoning is set out at greater length, for the first such pass, in
[`../arm2_block00_attempt1/ABORTED.md`](../arm2_block00_attempt1/ABORTED.md).

## Contents

```
p15_eval_0004_bundles_r1/          ¥0.4673
p15_eval_0004_typedcontract_r1/    ¥0.538
p15_eval_0004_base_r1/             ¥2.9422
p15_eval_0004_bundles_r2/          ¥0.4374
p15_eval_0004_typedcontract_r2/    ¥1.1373
p15_eval_0004_base_r2/             ¥0.0
run_state.json                     copy of the aborted chain_executor run state
chain_log_arm2_block00.log   sanitized chain log — the only per-attempt cost record
```

The live run state was renamed to `run_state_arm2_block00_attempt2.json` so that
`phase8a_report._states()` still counts this pass's measurement-invalid attempts, and so the re-run
writes a fresh state rather than resuming this one.

This directory sits **outside** `phase8a/evidence/episodes_arm2/` deliberately: that tree's
`*/episode.json` glob is the grading and spend glob, and an archive nested inside it would make the
same trial appear twice, once from this pass and once from the re-run.
