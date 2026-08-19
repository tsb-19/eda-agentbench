**[English](ABORTED.md) | 中文**

# 已废弃的执行轮次 —— arm 2，block 00（`8A_sta:p15_eval_0004:DeepSeek-V4-Pro-TR`），第 1 次

依据 [`docs/phase8a_prereg.md` §5B.3](../../../../docs/phase8a_prereg.md) 中确定的规则归档，
并记录于 [§5E](../../../../docs/phase8a_prereg.md)。
**此处任何内容都不进入分析。其花费进入账本。**

## 发生了什么

| | |
|---|---|
| 开始 | 2026-08-19T03:31:01Z |
| 结束 | 2026-08-19T04:00:08Z，`executor_exit_code: 2` |
| 完成的 slot | 6 个中的 2 个 |
| 采集到的 episode | 3 个 —— BundleS 1、TypedContract 1、Base 1（无效） |
| 原因 | 供应商在 `Base/pos2` 上连续三次尝试均返回 HTTP `503 {"code":"SERVICE_BUSY","message":"API Key 鉴权服务暂时不可用，请稍后重试"}`；每次尝试都耗尽了全部 6 次 chat 重试（`recovered_failed_attempts: 6`）；`episode_arbiter` 按设计在 2 次替换上限处到达 STOP |
| 分类 | `measurement_valid: false`，`classification_source: request_telemetry` —— 基础设施故障，绝非能力失败 |
| 已付费用 | **¥1.9492** = 存活 episode 的 ¥1.4024 + 被替换尝试的 ¥0.5468 |

## 这不是 block 02 的那个故障，证据是一个不计费的端点

arm 1 的 block 02 死于 `402 INSUFFICIENT_BALANCE` —— 账户余额耗尽。那次故障期间
`GET /v1/models` 仍返回 `200` 并给出完整模型列表，因为列出模型不计费。

而这一次，`GET /v1/models` **同样返回 `503 SERVICE_BUSY`，且是同一条鉴权服务的消息**。
一次连不计费端点都阻断的故障不可能是余额问题。供应商自己的说法是其 API Key 鉴权服务不可用，
而那个不计费的探针是在**印证**它、而不只是复述它 —— 这一点很关键，因为供应商的错误字符串
是它对自己的陈述，不是证据。

这也不是该后端平常的限流。促成提高重试预算的实测 503 率（背靠背 35%、间隔 15 s 时 8.3%）
是**单次请求**的失败率，6 次重试配 3/6/12/24/45 s 退避足以穿过它。这一次是全部 6 次重试都失败、
连续三次尝试、持续 29 分钟 —— 端点不是在限流，而是不可用。

## 守卫抓到了什么，以及为何它比这次故障本身更重要

`p15_eval_0004_base_r1` 被写入 custody 时带着 **`total_cost: 0.0` 与 `total_score: 0.5`**，
且 `error: null`。没有任何模型调用发生 —— 而这个 episode 仍然带着一个分数，因为
`run_single_agentic` 会给工作区中的任何状态打分，而未被触碰的 p15 工作区恰好得 0.5 分。

若无守卫，这条 arm 就会把一次供应商鉴权故障记录成 **DeepSeek 在实例 0004、Base 条件下得 0.5**。
由于替换会在故障期间成簇出现，糟糕的一小时会变成一整列看起来"已采集"的、貌似合理的中位分数。
`scripts/phase8a_run.py` 中的 `_telemetry_faults` 拒绝在出现"无任何模型调用证据"的 episode 之后
继续运行，正是它让这一轮停在 block 00 而不是 block 12。

## 为何整轮废弃而不是断点续跑

`p15_eval_0004_bundles_r1`（¥0.8669，得分 1.0）与 `p15_eval_0004_typedcontract_r1`
（¥0.5355，得分 0.5）**有效完成**。`chain_executor.py` 会把一个 block 从位置 0 重新开始，
而 `phase8a_episode_runner.py` 会覆盖某个 trial 的 custody 目录，所以原地重跑该 block
本来也会覆盖它们。

保留它们并从位置 2 续跑不会浪费任何东西 —— 但那会把"保留/丢弃"的分界线画在两个**分数已知**的
episode 之间，而这正是"把有效分数重试掉"的形状。整轮丢弃是全有或全无的，因此不可能依赖
任何 episode 的分数。请注意：被丢弃的这一对里恰好包含本条 arm 目前唯一的 1.0 分 ——
这正是为什么这条规则不能在此刻才决定。

## 目录内容

```
p15_eval_0004_bundles_r1/         有效 episode，已从分析中丢弃              ¥0.8669
p15_eval_0004_typedcontract_r1/   有效 episode，已从分析中丢弃              ¥0.5355
p15_eval_0004_base_r1/            终局无效：¥0 花费，无模型调用              ¥0
run_state.json                    被废弃的 chain_executor 运行状态副本
chain_log_arm2_block00.log        chain 日志的脱敏副本
```

`run_state.json` 是**副本**。报告实际读取的是
`phase8a/evidence/run_state_arm2_block00_attempt1.json`，保留在该路径是因为
`phase8a_report._states()` 以非递归方式 glob `run_state_arm2*.json` —— 那三次 `503` 尝试
必须保持可计数为 measurement-invalid，否则记录就会低估该后端的基础设施噪声。

`chain_log_arm2_block00.log` 被复制进来，是因为 `runs/` 被 gitignore，而这个日志是每次尝试
花费的**唯一**存留记录。`Base/pos2` 的第 1 次尝试花了 ¥0.5468，随后被两次 ¥0 的尝试覆盖，
于是 custody 树对一个已计费的 slot 报告 ¥0 —— 见
`phase8a/evidence/replaced_attempt_ledger.json`，其两条记录是从本文件重建的。

本目录**位于** `phase8a/evidence/episodes_arm2/` **之外**，这是刻意的：该树的
`*/episode.json` glob 就是评分与花费的 glob，嵌套在其内的归档会让同一个 trial 出现两次 ——
一次来自被废弃的这一轮，一次来自重跑。
