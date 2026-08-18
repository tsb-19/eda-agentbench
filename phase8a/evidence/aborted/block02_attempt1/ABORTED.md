**English | [中文](ABORTED.zh.md)**

# Aborted pass — arm 1, block 02 (`8A_sta:p15_eval_0006:Qwen3.7-Max-TR`), attempt 1

Archived under the rule fixed in [`docs/phase8a_prereg.md` §5B.3](../../../../docs/phase8a_prereg.md),
and recorded in [§5C](../../../../docs/phase8a_prereg.md).
**Nothing here enters the analysis. Its cost does enter the ledger.**

## What happened

| | |
|---|---|
| started | 2026-08-18T05:17:56Z |
| ended | 2026-08-18T06:18:54Z, `executor_exit_code: 2` |
| slots completed | 12 of 18 |
| episodes collected | 13 — Base 5, BundleS 4, TypedContract 4 |
| cause | provider returned HTTP `402 {"code":"INSUFFICIENT_BALANCE","message":"余额不足"}` on three consecutive attempts at `Base/pos12`; `episode_arbiter` reached STOP at the 2-replacement cap, as designed |
| classification | `measurement_valid: false`, `classification_source: request_telemetry` — an infrastructure fault, never a capability failure |
| cost paid | **¥7.2848** |

The `402` is classified `non_retryable_http`, so the driver correctly spent **no** retry on it — each
of the three attempts failed in ~1.25 s. This is not the same fault as block 01's `502` window: that
was transient congestion, this was the account running out of money.

The exhaustion was **account-level, not per-model**. A sweep of all 17 model IDs the backend serves
returned `402` for 15, `503 SERVICE_BUSY` for 2, and `200` for none, while `GET /v1/models` still
returned `200` with the full list — the credential was valid and the balance was zero. No cheaper
model on the same backend was a fallback. The balance was restored later the same day
(`qwen3.7-max` and `deepseek-v4-pro` both `200`), and block 02 was re-executed **whole**.

Note what did *not* stop this run: the preregistered **¥200 cap still showed ¥164.07 available**. See
prereg §5C.1 — the cap was never the operative stop rule.

## Why the whole pass was discarded rather than resumed

Twelve of these slots completed **validly**, with gradeable artifacts and telemetry custody.
`chain_executor.py` restarts a block at position 0 and `phase8a_episode_runner.py` overwrites a
trial's custody directory, so re-running the block in place would have overwritten all twelve.

Resuming at position 12 instead would waste nothing — but it puts the keep/discard boundary between
episodes whose scores were already known (Base 0.480 at k=5, BundleS 0.500 at k=4, TypedContract
0.500 at k=4). That is the shape of retrying away a valid score. Discarding the pass whole is
all-or-nothing and so cannot depend on any episode's score.

This is the second time the rule has fired. It was applied, not rewritten.

## One episode here has no model call behind it

`p15_eval_0006_base_r5` is the third `402` attempt. It carries `total_cost: 0.0` and a **gradeable
workspace scoring 0.5** — a score with no evidence of a model call. It is archived rather than
deleted because the record of a fault is evidence. Two independent guards already handle it:
`phase8a_report.py:101` excludes zero-cost episodes from grading, and `phase8a_run.py` halted the
chain on it rather than walking further into a dead backend.

## Contents

```
p15_eval_0006_base_r1 .. base_r4              valid episodes, discarded from the analysis
p15_eval_0006_base_r5                         the third 402 attempt: ¥0 cost, no model call
p15_eval_0006_bundles_r1 .. bundles_r4        valid episodes, discarded from the analysis
p15_eval_0006_typedcontract_r1 .. _r4         valid episodes, discarded from the analysis
run_state.json                                copy of the aborted chain_executor run state
```

`run_state.json` is a **copy**. The one the report reads is
`phase8a/evidence/run_state_arm1_block02_attempt1.json`, kept at that path because
`phase8a_report._states()` globs `run_state_arm*.json` non-recursively — the three `402` attempts must
stay countable as measurement-invalid, or the record would understate this backend's infrastructure
noise.

This directory sits **outside** `phase8a/evidence/episodes/` deliberately: that tree's
`*/episode.json` glob is the grading and spend glob, and an archive nested inside it would make the
same trial appear twice, once from this pass and once from the re-run. `_aborted_spend()` in both
`scripts/phase8a_run.py` and `scripts/phase8a_report.py` reaches in here for cost alone, and it sums
**every** archived pass — block 01's ¥0.5597 plus this pass's ¥7.2848 — so the ledger total is
unchanged by the move at ¥35.9287.
