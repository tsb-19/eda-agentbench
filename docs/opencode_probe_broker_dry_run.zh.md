**[English](opencode_probe_broker_dry_run.md) | 中文**

# broker 配置下唯一一次付费 dry run

**状态：仪器说明与预注册门槛，日期 2026-08-22。在运行之前写好并提交。** 本文不授权正式 48 episode
arm，本文中的任何内容都不得当作结果来读。

治理文档不变：[`opencode_probe_analysis_plan.md`](opencode_probe_analysis_plan.zh.md)（预注册）、
[`opencode_scaffold_probe_scope.md`](opencode_scaffold_probe_scope.zh.md)（集成范围，九项结构检查）与
[`opencode_probe_remote_broker_design.md`](opencode_probe_remote_broker_design.zh.md)（本次运行所要
检验的 capability）。`a89e084` programme 不被触碰。

## 1. 这次运行被授权回答什么

一个 episode，实例 `p15_dev_0000`，**不计分且丢弃**，在最终 bwrap sandbox 加受限 SSH broker 配置下。
五个问题，别无其他：

1. 真实 OpenCode + DeepSeek 请求能否在这一配置下完成一个 episode；
2. Agent 是否真正拿到真实 PrimeTime 反馈并据此继续推理；
3. request ledger 是否始终只有被 pin 的那个模型——没有 title、summary 或 compaction 模型；
4. **完全未修改的** grader 与类型化 oracle 能否给提交的 artifact 打分；
5. 这一个 episode 花了多少钱、用了多长时间。

第 5 项是一次 **single-run operational observation**。它是一个实例的一次重复，没有离散度，把它乘 48
正是让预注册成本门槛返回 `ARM2_NOT_RUN` 的那个错误：一个在 `p15_eval_0004` 上标定的速率（¥1.1094/ep，
而面板均值 ¥0.6266、最小值 ¥0.3298，实例间跨度 3.4×）否掉了一个其实负担得起的 arm。因此驱动脚本不
计算任何外推，若出现外推则
`test_the_driver_refuses_to_project_the_arm_from_one_episode` 失败。

## 2. 不得被用来读出什么

- **没有 Base/BundleS 对比。** `p15_dev_0000` 不带条件变体，这正是范围审计选它的原因之一：连误用都无从
  发生。
- **没有 scaffold main effect。** OpenCode 同时替换了 action surface 与 prompt frame，而论文自己的第 2
  节把两者都算作 task information。
- **分数不得作任何 treatment 解释。** 即使 grader 给出语义正确性数值，该分数只作为「评分流水线端到端跑
  通」的证据。
- **不授权正式 arm。** 通过只清掉结构性条件；arm 仍未授权，须等第 6 节的独立成本标定。

该 episode 不进入任何 ledger、任何 claim statistic、任何正式 custody root。

## 3. 两条工具通道，以及为何不能混淆

| | Agent | Grader |
|---|---|---|
| 经由何处到达 PrimeTime | sandbox 内的 broker capability | 主机上的私有 forwarder |
| 持有 | 一把 episode key，两个操作 | 操作者的普通环境 |
| 是否看到 `EDA_TOOL_ROOT`、`B04_HOST` | 否——两者都被 scrub | 是——detector 需要它们 |
| `EDA_PT_CMD` | 被覆写为 broker launcher | forwarder shim |

评分路径就是被冻结的那一条，不发生改变。这意味着驱动脚本必须在自己的环境里**设置** forwarder 变量——
否则工具 detector 什么也找不到，`run_hidden.sh` 会在没有任何工具真正运行的情况下打分，而第 4 项就会
报告一个从未启动过任何东西的绿色 grader。于是驱动脚本有意制造了 sandbox scrub 所要封堵的那个条件。

这暴露出一个既有缺口。preflight control 12 是用 preflight 自身的环境来构造 sandbox 环境的，而其中
`EDA_TOOL_ROOT` 与 `B04_HOST` 并未设置——所以它确认了两者「不存在」，却从未检验过负责「移除」它们的
代码。`test_the_scrub_removes_the_forwarder_pointers_when_they_are_actually_set` 现在检验存在的情形，
包括更锋利的那一半：`EDA_PT_CMD` 不是被 scrub 而是被**重定向**，若它带着 forwarder shim 路径存活下来，
sandbox 内的 `run_public.sh` 就会派发到 forwarder，episode 会在看上去正确的同时测了错误的工具通道。

无 broker 的配置在此有意保持原样而不加严：没有 broker 时 `EDA_PT_CMD` 会作为一个未挂载的绝对路径存活，
`command -v` 失败，`run_public.sh` 打印 `SKIP`。这就是上一次 dry run 被记录下来的行为，是一条不附带
任何 capability 的去匿名化痕迹；[dry run 报告](opencode_probe_dry_run_report.zh.md)已把它记为在任何
导出之前需要中和的残留。

## 4. 成本上限是实时的，并且会如实说明自己

¥20，硬上限，是 runaway 保护而非 arm 预算。它不是装饰：在 `compaction.auto: false` 之下历史单调增长，
所以缓存输入随轮次数的平方增长——10 轮时 80 896 tokens，26 轮时 485 888——把这条曲线外推到配置中的 60
轮上限就会超过 ¥20。

**在哪里执行。** `opencode run --format json` 每行输出一个 JSON 对象，而每个 `step_finish` 都带着那次
请求的 token 计数，所以事件流**就是** ledger，并且是一次请求一次地到达。governor 在那里累加，越限即杀
掉整个进程组。

**计价单位。** 网关报告 `cost: 0`，所以金额由 token 按 `phase8a/models_arm2.json` 中 pin 定的速率折算
（输入 12.0、输出 24.0 ¥/1M）——从该文件读取而非在此重述，使 probe 的 ledger 与被冻结 arm 的 ledger 不
会静默漂移。这是把一个冻结文件当作**价格参照**；它不池化、不求和、不做差任何冻结结果。

缓存流量按**输入**计价，而这正是「参考量级」与「可用数字」之间的差别：dry run 第 2 个 episode 重读了
485 888 个缓存 token，而新鲜输入只有 36 311 个，所以忽略缓存会把 ¥6.41 变成 ¥0.58——低估 11×，得到一个
松了 11× 却仍显得有原则的上限。`test_the_cost_arithmetic_reproduces_the_published_dry_run_figures`
从两个已提交的事件流重新计算两个已发布 episode，并要求与报告表格中的数字精确一致。

**上限用哪个数字。** 计算两个数字，差别仅在于推理 token 是否按输出计价，因为网关并不说明。上限按**上界**
执行——对 runaway 保护是安全方向，对预测开销是错误方向。

**它是否实时，是被测量而非被断言的。** governor 记录它所见每一条 token 记录的到达偏移，只有当这些记录
在整个运行过程中分散到达时才报告 `live`。若 OpenCode 哪天缓冲了 stdout，`live` 就会是 false，上限退化
为事后审计，wall clock 才是唯一实时边界——这必须被报告，而不是被吸收。两种情形都在花钱之前用发出事件流
形状的假 opencode 定下来了：`test_the_governor_kills_a_streaming_child_and_says_it_was_live` 与
`test_the_governor_admits_when_it_was_not_live`。

**fail-closed，与 `transport_output_limit` 同一意义。** 越限即杀进程组——`SIGTERM`、宽限、`SIGKILL`，
针对组而非单个进程，因为这条链是 bwrap → opencode → bash → `run_public.sh` → broker client → 一个持有
远端 PrimeTime license 的 ssh。随后 wrapper 以 121 退出并带 `MEASUREMENT_INVALID cost_cap_exceeded`
标记，使被杀掉的 episode 不可能被读成「模型提前结束」。第二条边界即 wall clock 跑在自己的线程里，完全
不依赖 OpenCode，所以一个在请求中途停止响应的模型仍然是有界的。

**不会为了跑完而提高上限。** 一个逼近 ¥20 的 episode 本身就是结论：这个集成不适合直接扩到 48 条。

## 5. 运行前就固定的门槛

每个条件都被机械评估并记录在 `opencode_probe/evidence/broker_dry_run/record.json`：

| 条件 | 如何建立 |
|---|---|
| 启动时被跟踪工作树干净 | `git status --porcelain -uno` 为空；记录 HEAD |
| grader 与 oracle 未被修改 | Family A 评分链四个被 pin 文件的 sha256 |
| grader 拥有真实工具 | detector 为评分路径解析出 PrimeTime |
| episode 完成 | runner 未抛异常返回 |
| 真实 PrimeTime 工具环路 | 服务端调用计数 ≥ 1 **且** 工具输出中出现 PrimeTime 标记 **且** 首次工具调用之后 ≥ 1 步 **且** 没有 `SKIP` 行 |
| 无 broker 传输失败 | 任何工具输出中都没有 `eda-broker: MEASUREMENT_INVALID` 标记 |
| artifact 保真 | 改动文件 ⊆ editable；workspace manifest 存在 |
| grader 给 artifact 打了分 | 存在 `ScoreResult` |
| request ledger 只有目标模型 | OpenCode session storage 中任何位置出现的每一个 model id |
| ledger 确实读到了东西 | `json_files_scanned` > 0 |
| 植入的诱饵从未出现 | sentinel 不出现于 transcript、artifacts 与 session storage |
| canonical task tree 完好 | 前后指纹一致；`git status -- tasks/` 为空 |
| 成本在上限内 | governor 未触发 |
| 停止规则有名且干净 | 由事件流推出 `model_finished` 或 `steps_cap` |
| broker 留下干净状态 | 无 managed 条目、无 episode 目录、无 quarantine |
| 诱饵已移除 | 在远端核验 |
| 无操作者介入 | 记录在案 |

其中三项值得说明理由。

**工具环路检查需要服务端计数器。** transcript 里出现 PrimeTime 输出并不证明 PrimeTime 运行过——那段文字
可以来自 Agent 能写的任何地方。计数器由 b04 上的 forced command 写入，位于 capability 的另一侧，没有真实
远端调用就无法递增。

**它还需要首次工具调用之后仍有工作。** 最后一步里的工具调用是一次工具调用，不是环路，而 arm 依赖的是
Agent 读到真实反馈之后再行动。

**并且它必须在 `SKIP` 上失败。** `SKIP: pt_shell not found` 是 `run_public.sh` 在没有可达工具时打印的
内容，也正是上一次 dry run 的结果。一个满是这种输出的 episode 不能被读成「选择了不迭代」的 episode。

标记只有在真会出现时才有用，所以 `PT_MARKERS` 取自 `p15_dev_0000/run_public.sh` 的一次真实 forwarder
运行而非猜测，其中两个绑定到已提交产物：横幅绑定到 preflight 捕获的 broker 输出，`PUBLIC_DONE` 绑定到
任务自身的 canonical `run_public.tcl`。

**诱饵控制是被动的，并如此标注。** 在 b04 上植入一个唯一命名的 oracle 仿制品并在运行前核验其存在；运行
之后在事件流、被评分的 artifacts 与 OpenCode 自身状态中搜索该 sentinel。这建立的东西比 check 5 更窄：
一个被明确指示去搜寻 oracle 的 Agent 属于 `negctl` episode，而跑它就是第二个付费 episode。本配置下机械
的、非被动的结果是 preflight 的 control 5、6、10、11 与 12。

**失败不得被修成通过。** 集成 bug 可以修，但修好后的配置需要一次**新的**被丢弃的 dry run；这一次不能被
重新解读。

## 6. 通过之后授权了什么

就其本身而言什么也没有。48 episode arm 仍未授权，须等一次独立的 **仅 Base 成本标定**，覆盖 3–4 个刻意
跨越已测 3.4× 跨度的实例——依据历史成本与任务规模选择，**绝不依据任何 OpenCode 结果**——并且这些运行本身
同样被丢弃。只有那时才有一个带离散度的速率可以驱动预算上限。

## 7. 文件

```
scripts/opencode_probe_broker_dry_run.py             驱动脚本；无 --confirm-paid-run 即拒绝
scripts/opencode_probe_agent.py                      CostGovernor、run_governed、session_ledger
tests/test_opencode_cost_governor.py                 governor 与本次运行的读取器
opencode_probe/evidence/broker_dry_run/record.json   记录
opencode_probe/evidence/broker_dry_run/eventstream.json  原始事件流与 ledger
```

运行方式：

```bash
python3 scripts/opencode_probe_broker_dry_run.py --cost-cap-cny 20 --confirm-paid-run
```
