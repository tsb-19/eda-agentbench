**[English](ABORTED.md) | 中文**

# 被中止的执行 —— 臂 1，区组 01（`8A_sta:p15_eval_0005:Qwen3.7-Max-TR`），第 1 次

依据 [`docs/phase8a_prereg.md` §5B.3](../../../../docs/phase8a_prereg.zh.md) 中定下的规则归档。
**此处内容一律不进入分析。它的成本进入账本。**

## 发生了什么

| | |
|---|---|
| 开始 | 2026-08-17T15:33:08Z … 18:07:50Z 属于区组 00；本次执行始于 18:07:50Z |
| 结束 | 2026-08-17T18:22:51Z，`executor_exit_code: 2` |
| 完成槽位 | 18 个中的 1 个 |
| 原因 | 提供方在 `Base/pos1` 上连续三次返回 HTTP `502`（`ProviderHTTPError`，`category=retryable_http`）；`episode_arbiter` 按设计在 2 次替补上限处到达 STOP |
| 分类 | `measurement_valid: false`，`classification_source: request_telemetry` —— 基础设施故障，绝非能力失败 |
| 已付成本 | **¥0.5597** |

该端点在 2026-08-18 恢复可达（`/v1/models` 返回 200；5/5 次对话探针，3–6 秒），故那次 `502` 只是暂时窗口。
区组 01 已**整体**重跑。

## 为何整体作废而不是续跑

此处的 `p15_eval_0005_typedcontract_r1` 是**有效**完成的（¥0.5597，有可判分产物，有遥测保管）。
`chain_executor.py` 会从位置 0 重启一个区组，而 `phase8a_episode_runner.py` 会覆写某个 trial 的保管目录，
所以就地重跑该区组会把它覆写掉。

保留它并从位置 1 续跑不会浪费任何东西——但那会让"保留/作废"的边界落在两个分数已知的 episode 之间，
而这正是"把有效分数重试掉"的形状。整体作废这次执行是全有或全无的，因此不可能依赖任何 episode 的分数。

## 内容

```
p15_eval_0005_typedcontract_r1/   有效 episode，从分析中作废          ¥0.5597
p15_eval_0005_base_r1/            终态无效：¥0 成本，无模型调用        ¥0
run_state.json                    被中止的 chain_executor 运行状态副本
```

`run_state.json` 是**副本**。报告实际读取的是
`phase8a/evidence/run_state_arm1_block01_attempt1.json`；之所以留在那个路径，是因为
`phase8a_report._states()` 以非递归方式 glob `run_state_arm*.json` —— 那三次 `502` 尝试必须仍可被计为测量无效，
否则记录会低估这个后端的基础设施噪声。

本目录刻意位于 `phase8a/evidence/episodes/` **之外**：后者的 `*/episode.json` 正是判分与支出所用的 glob，
若归档嵌在它里面，同一个 trial 会出现两次——一次来自本次执行，一次来自重跑。
`scripts/phase8a_run.py` 与 `scripts/phase8a_report.py` 中的 `_aborted_spend()` 只为取成本而伸进这里。
