**[English](ABORTED.md) | 中文**

# 被中止的执行 —— 臂 1，区组 02（`8A_sta:p15_eval_0006:Qwen3.7-Max-TR`），第 1 次

依据 [`docs/phase8a_prereg.zh.md` §5B.3](../../../../docs/phase8a_prereg.zh.md) 中定下的规则归档，
并记录于 [§5C](../../../../docs/phase8a_prereg.zh.md)。
**此处内容一律不进入分析。它的成本进入账本。**

## 发生了什么

| | |
|---|---|
| 开始 | 2026-08-18T05:17:56Z |
| 结束 | 2026-08-18T06:18:54Z，`executor_exit_code: 2` |
| 完成槽位 | 18 个中的 12 个 |
| 收得 episode | 13 个 —— Base 5、BundleS 4、TypedContract 4 |
| 原因 | 提供方在 `Base/pos12` 上连续三次返回 HTTP `402 {"code":"INSUFFICIENT_BALANCE","message":"余额不足"}`；`episode_arbiter` 按设计在 2 次替补上限处到达 STOP |
| 分类 | `measurement_valid: false`，`classification_source: request_telemetry` —— 基础设施故障，绝非能力失败 |
| 已付成本 | **¥7.2848** |

该 `402` 被分类为 `non_retryable_http`，故驱动正确地**没有**在它身上耗费任何重试——三次尝试各在约 1.25 秒内
失败。这与区组 01 的 `502` 窗口不是同一类故障：那是暂时性拥塞，这是账户把钱用光了。

这次耗尽是**账户级的，不是按模型的**。对该后端所服务的全部 17 个 model ID 做一轮探测：15 个返回 `402`，
2 个返回 `503 SERVICE_BUSY`，`200` 一个也没有；而 `GET /v1/models` 仍返回 `200` 并给出完整列表——凭据有效，
余额为零。同一后端上没有任何更便宜的模型可作退路。当天稍后余额已恢复（`qwen3.7-max` 与 `deepseek-v4-pro`
均返回 `200`），区组 02 已**整体**重跑。

请注意什么**没有**让这次运行停下：预注册的 **¥200 上限当时仍显示尚有 ¥164.07 可用**。见预注册 §5C.1 ——
该上限从未成为真正生效的停止规则。

## 为何整体作废而不是续跑

这里有 12 个槽位是**有效**完成的，有可判分产物，有遥测保管。`chain_executor.py` 会从位置 0 重启一个区组，
而 `phase8a_episode_runner.py` 会覆写某个 trial 的保管目录，所以就地重跑该区组会把这 12 个全部覆写掉。

改为从位置 12 续跑不会浪费任何东西——但那会让"保留/作废"的边界落在一批分数已知的 episode 之间
（Base 0.480，k=5；BundleS 0.500，k=4；TypedContract 0.500，k=4）。而这正是"把有效分数重试掉"的形状。
整体作废这次执行是全有或全无的，因此不可能依赖任何 episode 的分数。

这是该规则第二次生效。它是被**应用**的，而不是被重写。

## 此处有一个 episode 背后没有模型调用

`p15_eval_0006_base_r5` 就是第三次 `402` 尝试。它带着 `total_cost: 0.0` 和一个**可判分、得分 0.5 的工作区**
—— 一个没有任何模型调用证据的分数。它被归档而非删除，因为故障的记录本身就是证据。已有两道彼此独立的守卫
处理它：`phase8a_report.py:101` 把零成本 episode 排除在判分之外，而 `phase8a_run.py` 在它上面让整条链停下，
而不是继续走进一个已死的后端。

## 内容

```
p15_eval_0006_base_r1 .. base_r4              有效 episode，从分析中作废
p15_eval_0006_base_r5                         第三次 402 尝试：¥0 成本，无模型调用
p15_eval_0006_bundles_r1 .. bundles_r4        有效 episode，从分析中作废
p15_eval_0006_typedcontract_r1 .. _r4         有效 episode，从分析中作废
run_state.json                                被中止的 chain_executor 运行状态副本
```

`run_state.json` 是**副本**。报告实际读取的是
`phase8a/evidence/run_state_arm1_block02_attempt1.json`；之所以留在那个路径，是因为
`phase8a_report._states()` 以非递归方式 glob `run_state_arm*.json` —— 那三次 `402` 尝试必须仍可被计为测量无效，
否则记录会低估这个后端的基础设施噪声。

本目录刻意位于 `phase8a/evidence/episodes/` **之外**：后者的 `*/episode.json` 正是判分与支出所用的 glob，
若归档嵌在它里面，同一个 trial 会出现两次——一次来自本次执行，一次来自重跑。
`scripts/phase8a_run.py` 与 `scripts/phase8a_report.py` 中的 `_aborted_spend()` 只为取成本而伸进这里，
且它会累加**每一次**被归档的执行——区组 01 的 ¥0.5597 加上本次的 ¥7.2848——所以账本总额未因这次搬移而改变，
仍为 ¥35.9287。
