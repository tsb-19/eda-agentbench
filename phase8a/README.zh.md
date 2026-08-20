**[English](README.md) | 中文**

# `phase8a/` —— 为何本研究的产物置于 `reports/` 之外

Phase-8A 是在 ICLR 投稿冻结并打标签（`iclr2027-submission-v5`）之后开展的一项新研究。其设计与分析计划见
[`docs/phase8a_prereg.zh.md`](../docs/phase8a_prereg.zh.md)。

## 状态：已关闭 —— 2026-08-20

**实验部分已经结束。本分支上不再授权任何付费模型调用 —— 任何臂、实例、条件、模型或 scaffold 都不再有。**

| | |
|---|---|
| arm 1（`qwen3.7-max`，k=6） | 已完成 —— 216 个 episode，¥122.8175 |
| arm 2（`deepseek-v4-pro`） | **未执行** —— 被预注册的 §2.2 成本门控拒绝 |
| 程序总支出 | ¥200 上限中的 ¥145.4747 |
| 剩余 ¥54.53 | **不**用于任何额外的格子、实例、条件或模型（§2.3） |

Arm 2 是既有预注册计划中最后一个尚未填写的格子 —— 不是看到结果之后才想出来的新实验。它现在被报告为
**预注册计划中唯一一个预算内无法填上的格子**。计划由此闭合：每一个格子要么被填上，要么被明确记录为
无法填上。

结论（双语）见 [`docs/phase8a_findings.zh.md`](../docs/phase8a_findings.zh.md)。
一句话的结果是：**在这个预注册的 12 实例、k=6 面板上没有建立一致的 BundleS 优势，并且观察到双向的
实例级异质性** —— 这**不是** "BundleS 无效" 的结论。引用此处任何数字之前，请先读那份结论文档。

```
phase8a/
  evidence/    冻结的调度、运行前完整性清单、preflight 记录、
               运行状态、逐 episode 托管记录
  reports/     分析输出
```

## 规则 1 —— Phase-8A 产出的任何东西都不得写入 `reports/`

`scripts/frozen_membership_verify.py` 将 `SCAN_ROOT` 设为 `REPO / "reports"`，并递归遍历其下**每一个**
`*.json`，以三种形态采集 `path -> sha256` 对。写在那里的任何托管记录都会成为冻结 pin 集的一部分。

这并非假设。`scripts/phase8a_preflight.py` 的一个早期草稿把它的运行前正统完整性清单写进了
`reports/evidence/`。结果是：

```
pins:     1065 -> 1979
mismatch:    2 -> 1
```

该清单新增了 914 个 pin，并且由于它记录了 `generators/p15_sta_handoff_gen.py` 的*当前*哈希，它悄然**消解**了
冻结基线本应报出的两个 mismatch 之一。一个 Phase-8A 文件掩盖了冻结集的一项真实属性。

此时的诱惑是给验证器加一条豁免，或者把哈希记成采集器识别不了的第四种形态。这两者都是 CLAUDE.md 从另一个方向
警告过的同一种反模式——*"一个被调到什么都不打印的验证器，会掩盖下一次真正的变异。"* 所以验证器保持不动，改动的
是本研究的位置。`scripts/phase8a_preflight.py` 的第 11 道闸门对这条规则做断言，而非仅仅信任它。

## 规则 2 —— 绝不以仓库目录作为工作目录调用 `pt_shell`

本机上的 `pt_shell` 是一个转发到 `b04` 的 forwarder
（`/data1/tongsb/eda-remote-shim/bin/forwarder`——路径中的 `V-2023.12` 只是安装目录名，二进制实际是
`S-2021.06-SP5`）。**该 forwarder 会从远端副本同步当前工作目录**，且该同步是增量式的：它会恢复 `b04` 仍持有、
而本地已删除的文件，**并且原样保留其 mtime**。

那三个来自早期草稿的 `reports/evidence/phase8a_*` 残留文件正是这样反复出现的。在本地删除是成功的；而下一次从
仓库根目录发起的 `pt_shell` 调用又把它们恢复了，时间戳仍停留在删除之前。天真的解读是"我的删除失败了"或"我的脚本
又把它们创建了一遍"——两者都错，而且两者都会导致去修改本来正确的代码。

实测行为：

| 动作 | 效果 |
|---|---|
| 以仓库根目录为 cwd 调用 forwarder | 仅存在于远端的文件被**恢复**到本地 |
| 以仓库外的临时目录为 cwd 调用 forwarder | 仓库不受影响 |
| `sta_fairness.check(...)`（任务作用域） | 仓库不受影响 |
| 仅存在于本地的文件 | 从不被删除 |
| 对已跟踪或未跟踪文件的本地修改 | 从不被回退 |

所以这一风险是有界的，但它真实存在：一条远程工具路径可以写入正统树。这与
[`docs/incident_golden_corruption.md`](../docs/incident_golden_corruption.zh.md) 属于同一类——那次长达一天的
"远程工具中断"实际上是测试框架在往正统树里写；监控器是对的，而归因是错的。这一次同样是监控器对了。

因此 `scripts/phase8a_preflight.py:_pt_version` 把它的 Tcl 放进 `tempfile.TemporaryDirectory`，并传入
`cwd=tmp`。任何复现本工作的人，对任何被转发的 EDA 工具都应假定同样的纪律。

## 复现

无任何模型调用。以下每条命令都是从已提交账本出发的只读重新导出。

```bash
python3 scripts/phase8a_schedule.py --model Qwen3.7-Max-TR --reps 6 --arm 1 --check
python3 scripts/phase8a_preflight.py        # 零付费调用；一次不计费的 /v1/models 列表查询
python3 scripts/phase8a_report.py --arm 1 --check
python3 scripts/phase8a_report.py --arm 2 --check    # 不完整臂；聚合量被扣留（§5E.5）
python3 scripts/phase8a_arm2_gate.py --check         # ARM2_NOT_RUN
python3 scripts/phase8a_cost_reconcile.py --arm 2 --block 0 --check
```
