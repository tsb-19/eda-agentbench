**English | [中文](ABORTED.zh.md)**

# Aborted pass — arm 1, block 01 (`8A_sta:p15_eval_0005:Qwen3.7-Max-TR`), attempt 1

Archived under the rule fixed in [`docs/phase8a_prereg.md` §5B.3](../../../../docs/phase8a_prereg.md).
**Nothing here enters the analysis. Its cost does enter the ledger.**

## What happened

| | |
|---|---|
| started | 2026-08-17T15:33:08Z … 18:07:50Z was block 00; this pass 18:07:50Z |
| ended | 2026-08-17T18:22:51Z, `executor_exit_code: 2` |
| slots completed | 1 of 18 |
| cause | provider returned HTTP `502` (`ProviderHTTPError`, `category=retryable_http`) on three consecutive attempts at `Base/pos1`; `episode_arbiter` reached STOP at the 2-replacement cap, as designed |
| classification | `measurement_valid: false`, `classification_source: request_telemetry` — an infrastructure fault, never a capability failure |
| cost paid | **¥0.5597** |

The endpoint was reachable again on 2026-08-18 (`/v1/models` 200; 5/5 chat probes at 3–6 s), so the
`502` window was transient. Block 01 was re-executed **whole**.

## Why the whole pass was discarded rather than resumed

`p15_eval_0005_typedcontract_r1` here completed **validly** (¥0.5597, gradeable artifact, telemetry
custody). `chain_executor.py` restarts a block at position 0 and `phase8a_episode_runner.py`
overwrites a trial's custody directory, so re-running the block in place would have overwritten it.

Keeping it and resuming at position 1 would waste nothing — but it puts the keep/discard boundary
between two episodes whose scores were already known, which is the shape of retrying away a valid
score. Discarding the pass whole is all-or-nothing and so cannot depend on any episode's score.

## Contents

```
p15_eval_0005_typedcontract_r1/   valid episode, discarded from the analysis    ¥0.5597
p15_eval_0005_base_r1/            terminal-invalid: ¥0 cost, no model call      ¥0
run_state.json                    copy of the aborted chain_executor run state
```

`run_state.json` is a **copy**. The one the report reads is
`phase8a/evidence/run_state_arm1_block01_attempt1.json`, kept at that path because
`phase8a_report._states()` globs `run_state_arm*.json` non-recursively — the three `502` attempts must
stay countable as measurement-invalid, or the record would understate this backend's infrastructure
noise.

This directory sits **outside** `phase8a/evidence/episodes/` deliberately: that tree's
`*/episode.json` glob is the grading and spend glob, and an archive nested inside it would make the
same trial appear twice, once from this pass and once from the re-run. `_aborted_spend()` in both
`scripts/phase8a_run.py` and `scripts/phase8a_report.py` reaches in here for cost alone.
