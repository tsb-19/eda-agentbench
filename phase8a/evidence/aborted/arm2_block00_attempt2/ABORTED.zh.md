**[English](ABORTED.md) | 中文**

# 已废弃的执行轮次 —— arm 2，block 00（`8A_sta:p15_eval_0004:DeepSeek-V4-Pro-TR`），第 2 次

由 `scripts/phase8a_archive_pass.py` 于 2026-08-19T08:07:47Z 依
[`docs/phase8a_prereg.md` §5B.3](../../../../docs/phase8a_prereg.md) 中确定的规则归档。
**此处任何内容都不进入分析。其花费进入账本。**

| | |
|---|---|
| 开始 | 2026-08-19T04:36:39Z |
| 结束 | 2026-08-19T06:32:45Z，`executor_exit_code: 0` |
| 完成的 slot | 6 个中的 6 个 |
| 采集到的 episode | 6 |
| 原因 | `harness race, not a provider fault: run_single_agentic returned before llm_agent_driver had written its agent log, so p15_eval_0004_base_r2 was graded while the agent was still editing the workspace and recorded at cost 0.0 with no telemetry (the pinned arbiter, seeing no fault, ACCEPTed it), and p15_eval_0004_base_r1 attempt 1 was charged the ARCHIVED pass's cost and classified on the ARCHIVED pa` |
| 分类 | `measurement_valid: false` —— 基础设施故障，绝非能力失败 |
| 已付费用 | **¥5.5222** = 已采集 episode 的 ¥5.5222 + 被替换尝试的 ¥0 |

整轮废弃而不是断点续跑。此处某些 episode 可能是**有效完成**的；保留它们并从中途续跑，
会把"保留/丢弃"的分界线画在**分数已知**的 episode 之间，而这正是"把有效分数重试掉"的形状。
全有或全无才不可能依赖任何 episode 的分数。此外 `chain_executor.py` 会把一个 block 从位置 0
重新开始，而 `phase8a_episode_runner.py` 会覆盖某个 trial 的 custody 目录，所以原地重跑
本来也会覆盖它们。

更详尽的论证见第一个这样的轮次：
[`../arm2_block00_attempt1/ABORTED.zh.md`](../arm2_block00_attempt1/ABORTED.zh.md)。

## 目录内容

```
p15_eval_0004_bundles_r1/          ¥0.4673
p15_eval_0004_typedcontract_r1/    ¥0.538
p15_eval_0004_base_r1/             ¥2.9422
p15_eval_0004_bundles_r2/          ¥0.4374
p15_eval_0004_typedcontract_r2/    ¥1.1373
p15_eval_0004_base_r2/             ¥0.0
run_state.json                     被废弃的 chain_executor 运行状态副本
chain_log_arm2_block00.log   脱敏的 chain 日志 —— 唯一的逐次花费记录
```

活动运行状态已重命名为 `run_state_arm2_block00_attempt2.json`，
以便 `phase8a_report._states()` 仍能计入本轮的 measurement-invalid 尝试，
并使重跑写入一份新的状态而不是续用这一份。

本目录**位于** `phase8a/evidence/episodes_arm2/` **之外**，这是刻意的：该树的 `*/episode.json`
glob 就是评分与花费的 glob，嵌套在其内的归档会让同一个 trial 出现两次 ——
一次来自被废弃的这一轮，一次来自重跑。
