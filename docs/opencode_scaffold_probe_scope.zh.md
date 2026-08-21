**[English](opencode_scaffold_probe_scope.md) | 中文**

# OpenCode scaffold probe —— 接入范围与零调用对齐审计

**状态：什么都还没跑。** 没有调用任何模型，不存在任何 episode，没有触碰任何冻结结果，也没有挑选任何实例。
本文是决定"是否开跑"之前的**范围审计**，并且刻意**不是**预注册。

**那份预注册现在已单独存在：
[`opencode_probe_analysis_plan.zh.md`](opencode_probe_analysis_plan.zh.md)**，在任何 OpenCode episode 的任何
outcome 字段被读取之前提交，做法同
[`phase8a_arm2_analysis_plan.zh.md`](phase8a_arm2_analysis_plan.zh.md)。它固定问题、outcome 定义、措辞标准与
扩充规则；本文固定接入面以及决定能否执行的九项结构检查。两者相接之处（设计表、事先固定的问题）以方案为准。

**目前获得授权的是接入，加上一次不计分、丢弃的付费 dry run。** 那 48 条的正式臂**未**获授权，只有在下述九项
检查全部通过之后才获得授权。见 `CLAUDE.md` 硬约束 1 —— 它划出这块范围，而不重新打开 `a89e084` 程序。

下文关于 OpenCode 的一切，都是从**已安装的二进制**（`~/.opencode/bin/opencode`，`opencode 1.18.19`）、
它发布的 config schema（`https://opencode.ai/config.json`）以及它自带的配置参考（`opencode debug skill`）
中确立的。关于受控 runner 的一切都读自冻结代码。凡是不跑一个 episode 就无法确立的事实，都标注为
**必须在 dry run 中核验**，而不是假定。

## 为什么做这个 probe，以及它真正能回答什么

手稿（v20）研究的是一个**task-information intervention**，且智能体脚手架保持固定。论文里每一条 episode
都跑在我们自己的同一个 runner 上，所以论文 §7 自己就承认："169 条中 82 条"这个 tool-green 占据率是那个
runner 的性质。因此，一个独立 scaffold 正是论文目前缺的、最承重的那块外部效度。

**但这个问题的严格形式做不到，而且这句话必须先说。** 论文把 task information 定义为*提示、可见文件、
披露包、公开工具反馈与动作面*。OpenCode 必然会替换掉动作面和提示框架。所以一个 OpenCode 臂并不是"只变
scaffold" —— 按论文自己的分类，它同时变动了 scaffold **和** task information 的两个组成部分。

能在这个反驳之下站住的是**交互项**，而它本来就是更有意思的那个量：

| | Base | BundleS |
|---|---|---|
| 受控 runner | 已测（arm 2） | 已测（arm 2） |
| OpenCode | probe | probe |

**scaffold 主效应**（行间差）存在混淆，绝不可作为 scaffold effect 报告。**OpenCode 内部的 treatment
effect**（下面那一行的列间差）是干净的、自足的，它就是被估计量。它与上面一行是否同号，属于**描述性的
跨批次比较**，适用论文已经对自己的跨批次一致性施加的那一整套纪律 —— 而且比大多数情况支撑更好，因为模型、
实例、条件和 *k* 都可以保持完全相同（见[probe 设计](#最小正式-probe-设计)）。

第二个问题根本不需要任何比较，而且是更便宜的收获：**在独立 scaffold 下，tool-green 的语义错绑是否仍然
出现？** 这是"oracle 判决 对 工具信号"的逐 episode 性质，因此靠计数即可回答：只要有一条 OpenCode episode
把角色绑错、而 `run_public.sh` 仍然返回绿色，就确立了该失败模式并非我们自研 runner 独有。**允许写多强，
随计数而定，而孤例只会被如实写成孤例** —— 报告量是有效 episode 上的 `n_semantic_wrong` 与
`n_tool_green_wrong`，任何计数下都不作显著性主张，计数为零也以同等篇幅报告。这个界固定在
[分析方案](opencode_probe_analysis_plan.zh.md#第-1-层--首要外部效度问题存在性与频率)里，而不是在看到数字
之后才定。

## 让这件事变便宜的那个发现：接缝本来就存在

`run_single_agentic(task_path, agent_cmd, meta, timeout, ...)` 接受的 `agent_cmd` 是一个 **shell 字符串**
（`eda_agentbench/agentic/runner.py:179`），以 `cwd=<agent workspace>` 运行它，此后的一切都由它自己完成：
evaluator workspace、hidden 叠加、`run_public.sh` / `run_hidden.sh`、类型化 oracle，以及三项 anti-cheat
检查。冻结的 episode runner 本来就是手工拼出那个字符串的（`scripts/phase8a_episode_runner.py:187`）。

所以一个 OpenCode 臂就是**换一个 `agent_cmd`，别的什么都不动**。runner、两阶段 workspace、各评分器、任务
文件和任务语义全都不改。这就是对"评分器有没有变"这个问题最强的回答 —— 它不只是没变，它甚至不在这次替换
所触及的范围里。

## 对齐目标，以及冻结的精确数值

读自 `scripts/phase8a_run.py`、`scripts/phase8a_episode_runner.py`、`scripts/llm_agent_driver.py`
与 `phase8a/models_arm2.json`：

| 量 | 冻结值 |
|---|---|
| 动作预算 | `--max-actions 60` |
| episode 挂钟 | `EDA_TIMEOUT` 1800 s；driver 在 1770 s 自行停止 |
| 单条命令超时 | `min(180, 剩余)` s |
| 观察截断 | 4000 字节（driver 默认值；从未被覆盖） |
| 采样温度 | 0.7 |
| 每次请求 `max_tokens` | 32000 |
| socket 不活动超时 | 120 s |
| 硬请求截止 | 300 s（隔离 worker 被杀） |
| 重试权威 | 6 次重试，每次尝试新 worker，仅限基础设施故障 |
| 传输 | SSE 流式**开** |
| 置信度征询 | 开（`--elicit-confidence`） |
| 动作语法 | `RUN:` / `WRITE:` / `FINISH`，**每轮恰好一个**，取第一个标记 |
| 写入范围 | 仅 editable 的 basename；其他一律拒绝 |
| 读取范围 | 正则拒绝：`EDA_TASK_PATH`、`/hidden`、`/solution`、`/oracle`、`run_hidden`、`../` |
| 上下文管理 | **无** —— 历史单调增长，episode 在动作上限处结束 |

## 逐面映射

判定：**完全可对齐** = 能做到相同并可核验；**有界对齐** = 能带到一个被记录下来、站得住的等价物；
**不可对齐** = 不可约的 scaffold 差异，只能如实披露，不得糊过去。

### 1. Workspace 与文件暴露面 —— 完全可对齐，有一个前提

受控 runner 交给智能体的是 `<instance>/files/` 摊平后的 `/tmp/eda_agent_*` 副本，别无其他。OpenCode 接受
`--dir`，因此可以指向同一个 workspace，可见字节集合于是在构造上就相同。

前提是：OpenCode 的**配置发现会从 cwd 向上走**（项目级 `opencode.json` / `opencode.jsonc` /
`.opencode/opencode.json`，一直走到 worktree 根），并且另外读取 `~/.config/opencode/`。这台机器上两者目前
都是干净的 —— 没有 `~/.config/opencode/opencode.json`，`/`、`/tmp` 和 `$HOME` 下都没有 `AGENTS.md` ——
但"目前干净"不是一项控制。wrapper 必须去**断言**它为空，而不是指望它为空，办法是
`OPENCODE_DISABLE_PROJECT_CONFIG=1` 加一个显式的 `OPENCODE_CONFIG=<被钉住的文件>`。

这个 workspace 不是 git 仓库。在那种情况下 OpenCode 把什么当作 "worktree 根"，**必须在 dry run 中核验**。

### 2. 任务文本 —— 文本可对齐，框架不可对齐

`prompt.md`、`spec.md`、`glossary.md` 与 `public_check_summary.json` 都在 `files/` 里，因此经由 workspace
逐字节抵达。任务文本还可以原样作为 `run` 的 message 传入。

无法对齐的是 OpenCode 包在它外面的一切：它自己给该 agent 的 system prompt、仍然启用的那些工具的 JSON
schema，以及它的环境前言。agent 的 `prompt` 字段替换的是该 agent 的基础 prompt，而**不是**工具 schema，
也不是环境块。这就是"相同 task information"这项要求中不可约的那一半，它与
[§ 为什么做这个 probe](#为什么做这个-probe以及它真正能回答什么) 说的是同一件事：提示框架本身就是 task
information，所以不可能在 scaffold 变化的同时把它保持固定。

有四个注入源必须显式关掉，因为每一个都会添加在冻结运行中根本不存在对应物的、智能体可见的内容：

| 注入源 | 控制手段 |
|---|---|
| 项目级/全局指令文件 | `instructions: []`，加上前述的为空断言 |
| skills，包括自动加载的 `~/.claude/skills` 与 `~/.agents/skills` | `OPENCODE_DISABLE_EXTERNAL_SKILLS=1`、`OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1`、`permission.skill: deny` |
| plugins，包括从 `.opencode/plugin/` 的自动发现 | `--pure` / `OPENCODE_PURE=1`、`OPENCODE_DISABLE_DEFAULT_PLUGINS=1`、`plugin: []` |
| MCP 服务器 | `mcp: {}` |

解析后的配置里还带着 `"username": "tongsb"`。这既是智能体可见内容，**也是**一条去匿名化通道 —— 而本分支
并未匿名化；应把 `username` 设成一个中性字面值。

### 3. 动作面 —— 不可对齐

这是最大、也是最需要如实说明的缺口。冻结语法是三个动词、每轮一个动作、取第一个标记。OpenCode 的 `build`
agent 解析出的工具是 `bash, read, write, edit, glob, grep, task, webfetch, todowrite, skill, question,
invalid`，**每个 assistant 轮次可以发出多次工具调用**，而且以 patch 而非整文件覆写的方式编辑。

它可以被收窄很多。permission 的键恰好是 `read, edit, glob, grep, list, bash, task, external_directory,
todowrite, question, webfetch, websearch, lsp, doom_loop, skill`，每个取 `allow` / `ask` / `deny`，而在
逐 pattern 的对象内部**最后一条匹配规则生效**，所以宽规则要写在前面。一个最小面是：允许 `bash`、`read`
与 `write`/`edit`，其余全部 deny，并且 `lsp: false`、`subagent_depth` 取下限、`task: deny`。

它仍然做不到每轮一个动作，也没有任何配置能把 patch 编辑变成整文件 `WRITE`。**要把这一点记录成 probe 刻意
引入的那个 scaffold 差异** —— 它是干预本身，不是缺陷。不能发生的是：把行间差当成动作面已被固定来报告。

### 4. 观察预算 —— 有界到完全可对齐，但有一个坑

`tool_output` 的默认值是 `max_lines` 2000、`max_bytes` **51200** —— 是冻结的 4000 字节截断的 12.8 倍。
设 `tool_output.max_bytes: 4000` 即可对上这个数。

坑在于：溢出时 OpenCode 会**把全文写进一个截断目录、只返回一段预览**，而默认的 `build` agent 恰恰把
`external_directory` 对 `~/.local/share/opencode/tool-output/*` 显式设为 *allow*。于是一段被截断的观察
可以靠读文件找回来，而冻结 driver 的硬切片让这不可能。两项设置都需要：`tool_output.max_bytes: 4000`
**并且**对该路径 deny `external_directory`（`/tmp/opencode/*` 同理，它也被同一份默认值放行）。

### 5. 停止条件与预算 —— 有界对齐，有一处单位不匹配

| 冻结控制 | OpenCode 等价物 | 说明 |
|---|---|---|
| `--max-actions 60` | agent 的 `steps` | **不是同一个单位** —— `steps` 数的是 agentic 迭代，而一次迭代可以携带多次工具调用。记录为 scaffold 差异；不得声称动作预算相等。 |
| 硬请求截止 300 s | provider `options.timeout`（毫秒） | 直接对应 |
| socket 不活动 120 s | provider `options.chunkTimeout`（毫秒） | 直接对应，仅流式 |
| —— | provider `options.headerTimeout` | 冻结侧无对应物；仍需钉住 |
| episode 挂钟 1800 s | wrapper 用 `timeout(1)` 包住 `opencode run` | runner 自己的 `subprocess` 超时依然生效 |
| 单条命令 180 s | **未见配置项** | 必须在 dry run 中核验；否则在 wrapper 里强制 |
| 重试 6 次，仅基础设施 | **未见配置项** | 必须在 dry run 中核验 |
| 温度 0.7 | agent `temperature` | 直接对应 |
| `max_tokens` 32000 | provider `models.<id>` 选项 | 直接对应 |
| **无 compaction** | `compaction.auto` 默认 **true** | 设 `false`；此后长 episode 会撑爆上下文而不是优雅停止 —— 这个替代行为必须被记录，不能藏起来 |

### 6. 额外的模型调用 —— 有界对齐，漏掉就会破坏成本记账

OpenCode 在 `build`、`plan`、`general`、`explore` 之外还带着隐藏的内部 agent `title`、`summary` 与
`compaction`。它们会发出**额外的模型请求**，而 `small_model` 还可能指向完全不同的模型。放任不管的话，它们
会（a）在被测量的臂之外花钱，（b）在一个名义上单模型的格子里塞进第二个模型，（c）注入任何冻结 episode
都没见过的摘要式上下文。

控制：把 `small_model` 钉成同一个 model id，显式传 `--title` 使标题不被生成，`compaction.auto: false`、
`task: deny`，并禁用未用到的 primary agent。然后对照 `opencode stats` 核验该 episode 的请求数与"每次迭代
一次"的预期相符。

### 7. Grader 交接 —— 完全可对齐，但有两处字节级危险

在构造上就未改变（见[接缝](#让这件事变便宜的那个发现接缝本来就存在)）。但 OpenCode 有两个默认值会破坏
提交的产物：

- **`formatter`** —— OpenCode 会格式化它编辑过的文件。被重新格式化的 `flow_config.json` 或 `.sdc` 与
  智能体写下的字节串已经不同，而 grader 读的是字节。设 `formatter: false`。
- **`snapshot`** —— 文件系统快照跟踪会把状态写进工作树。runner 会对整个 workspace 做前后 sha256 快照
  比对，并把新增文件喂给 `detect_hidden_shadows` / `detect_forbidden_modifications`。多出来的产物轻则是
  噪声，重则构成一次假的 anti-cheat 违规。设 `snapshot: false`，并在 dry run 中确认 episode 之后的
  workspace 差异只含 editable 文件。

### 8. Oracle 隔离 —— 靠配置做不到；硬前提

冻结 driver 用三种方式保护 oracle：它从不透露 `EDA_TASK_PATH`；它**把 `EDA_TASK_PATH` 与 `EDA_TASK_ID`
从每个 `RUN` 子进程的环境中抹掉**（`llm_agent_driver.py:693`）；并且用正则拒绝提到 `hidden`、`solution`、
`oracle`、`run_hidden` 或 `../` 的命令。

而 runner 会把那些变量导入 agent 命令的环境（`runner.py:424`），规范 `hidden/` 目录是 775 —— 全局可读 ——
并且 **OpenCode 的 `external_directory` 是一道文件工具边界，预期并不约束 `bash`**（必须在 dry run 中
核验 —— 而且无论结论如何，这都是安全的那一侧假设）。所以 `bash: allow` 加上一个没被抹掉的环境，
就是一条直通 `cat $EDA_TASK_PATH/hidden/handoff_truth.json` 的路 —— 那不只是让 probe 有偏，而是让它作废。

需要两层，且两层都不是可选项：

1. **wrapper 抹环境** —— OpenCode 的 `agent_cmd` 必须在 exec 之前删除 `EDA_TASK_PATH` 与 `EDA_TASK_ID`，
   与 driver 的做法完全一致。
2. **文件系统隔离** —— 本机有 `bwrap`。让 OpenCode 在任务树未被挂载的情况下运行，使 oracle 不只是没被
   命名，而是根本不存在。denylist 是比空挂载更弱的控制，而这正是更强的那一种恰好很便宜的场合。

在这两层之上还应加一条 dry-run 断言：一条**明确指示**智能体去读 oracle 的提示，必须找不到它。

### 9. 发布与匿名 —— 完全可对齐

`share: "disabled"`（以及已废弃的 `autoshare: false`）。本分支并未匿名化，约 212 个冻结保管文件仍带着
用户名或主机名；一个 OpenCode session 绝不可被上传。`--pure` 同时能让外部 plugin 看不到 episode 内容。

## Dry run 规格

两条 episode，**都不计分、都丢弃**，跑在 `p15_dev_0000` 上 —— 这是该家族唯一的 dev 实例，也是唯一一个
落在所有被研究面板之外的 p15 目录。十二实例面板是 `p15_eval_0004`–`p15_eval_0015`；`p15_eval_0001`–`0003`
是被单独报告的三实例试点，同样不得触碰。`p15_dev_0000` 没有条件变体，所以这两条 dry-run episode 是同一个
实例的两次重复 —— 这样就够了，因为下面九项检查全是结构性的：**没有一项去看条件对比，也没有任何实例是按
outcome 挑出来的。**

| # | 检查 | 通过判据 |
|---|---|---|
| 1 | 文件暴露面 | workspace 列表与 `<instance>/files/` 相同；`hidden`/`solution` 路径均不可解析 |
| 2 | 注入源静默 | `opencode debug config` 显示 `instructions`、`plugin`、`mcp`、`skills` 为空；`username` 中性 |
| 3 | 工具权限 | 每个被 deny 的工具在尝试时都被拒绝，且拒绝出现在 JSON 事件流中 |
| 4 | 无人工闸门 | episode 无人值守地跑完；解析后的权限集中不残留任何 `ask` |
| 5 | oracle 隔离 | 一条明确索取 oracle 的提示无法触及它 |
| 6 | 观察上限 | **负控制，不是检视** —— 故意产生超过 4000 字节的工具输出，然后确认智能体**无法通过任何路径**取回溢出部分：返回消息中已被截断，且截断文件经 `read`、`glob`、`grep` 与 `bash` 均不可读 |
| 7 | 停止行为 | `steps` 上限与挂钟都能干净终止；单条命令超时可被观察到 |
| 8 | 产物保真 | episode 后的 workspace 差异只含 editable 文件；无 formatter 重写、无 snapshot 状态 |
| 9 | 请求记账 | `--format json` 事件流与 `opencode stats` 的请求数一致；无 `small_model` 调用 |

**第 6 项必须做成负控制，因为这种失败是无声的。** 如果 OpenCode 表面只给模型 4000 字节，却把完整输出写进
一个允许模型读取的目录，那么这个 4000 字节上限**根本不存在** —— 它只差一次额外的工具调用，而 probe 声称已经
对齐的整个观察预算都是虚构的。设好 `tool_output.max_bytes` 再把它读回来，什么都证明不了；只有制造一次溢出
并且取不回来，才证明得了。

**成本校准是 dry run 的一部分，而论文自己的历史已经说明该怎么做。** `ARM2_NOT_RUN` 门控之所以拒绝了一个
其实负担得起的臂，是因为它的速率估计量校准在 `p15_eval_0004` 上 —— 十二个实例中最贵的那个（¥1.1094/ep，
面板均值 ¥0.6266，最低 ¥0.3298，实例级离散 3.4 倍）。因此这里测出的任何速率都必须来自一个覆盖该离散度的
样本，并且必须把它自己的离散度带进决策，而不是压缩成一个均值。

## 最小正式 probe 设计

**先说预算：这不能从冻结程序里出。** 那个程序在 ¥200 上限中花了 ¥183.9329，剩 ¥16.07。一个 scaffold
probe 需要属于自己的上限、自己的账本和自己的门控。

这个设计精确地镜像 arm 2 —— 同一个模型、同样十二个冻结实例、同样的条件、同样的 *k*。准确的说法是这样，
而这个措辞很重要：**它把模型、任务实例、处理条件、重复深度、评分器与 EDA 环境全部匹配到既有的
DeepSeek（*k*=2）面板上，同时替换执行 scaffold 以及该 scaffold 所隐含的界面框架。** 它**并没有**使 scaffold
成为唯一变动因子 —— 按论文自己的分类，OpenCode 同时改变了提示框架与动作面，所以这是设计所能达到的最大限度
匹配，而不是一个单因素因果实验：

| | 取值 |
|---|---|
| 模型 | `deepseek-v4-pro`（同 arm 2） |
| 实例 | `p15_eval_0004`–`0015` 全部 12 个，**不按此前是否 informative 做任何挑选** |
| 条件 | Base、BundleS |
| *k* | 2（同 arm 2） |
| **episode 数** | **48** |

加上 TypedContract 可把镜像补全为 72 条。成本的下界是 arm 2 实测的 ¥0.6266/episode → 48 条 ¥30.1，但
OpenCode 更重的单次请求框架与多工具轮次使 2–4 倍的系数是可信的；**这要由 dry run 去测，本文任何数字都
不得当作预测使用。**

此前摆在桌上的备选是 12 × 2 × k=3 = 72。它买到的是单元内解析度，代价是失去精确镜像：在 k=3 下，OpenCode
臂与 arm 2 在 scaffold **和**深度上同时不同，于是重新引入了 v18 与 v19 花了两个版本才清理掉的双因子混淆。
**建议取 k=2 以保持镜像。** 无论取哪个都要注明：k=2 不承载任何幅度主张 —— arm 1 正是在这个家族上测出
36 个单元中有 7 个在六次完全相同的重复之间彼此不一致。

**扩充到 k=6 是一条规则、而不是事后判断，并且它固定在
[分析方案](opencode_probe_analysis_plan.zh.md#扩充到-k6--规则在任何-outcome-之前固定)里，在任何 outcome
之前。** 阶段 1 保持 k=2，因为这个 probe 的首要目的是外来 scaffold 上的存在性加上 within-OpenCode 行为，
而不是精确估计 Δ。当且仅当轨迹 100% 完整、至少 5 个实例有信息量（既非地板/地板也非天花板/天花板）、且成本
能装进 probe 自己的上限时才扩充 —— 而届时**无论哪个条件得分更高都照样进行**。这要防的正是那种
outcome-adaptive 行为：*"看到 +20 pp 所以继续跑确认；看到 0 所以停止。"*

刻意排除：第二个模型、更多 Bundle 消融、以及 SPICE。在第一个 scaffold 观测存在之前，每一项都只是多加一个
因子。

## 事先固定的问题

现在、在任何 outcome 存在之前写下来，使两者都不可能事后挑选：

1. **在独立 scaffold 下，tool-green 的语义错绑是否出现？** 描述性的存在性与频率，报告为有效 episode 上的
   `n_semantic_wrong` 与 `n_tool_green_wrong`。一个被绿色 `run_public.sh` 接受的错绑，确立了该失败模式并非
   我们自研 runner 独有；孤例被写成孤例，而且**任何计数下都不作显著性主张**。两个方向都被授权 ——
   0/*n* 也是一个结果，并以同等篇幅报告 —— 且无需任何对比。
2. **在 OpenCode 内部，Base → BundleS 的对比是否有可观察的效应？** 这是被估计量。按与 arm 2 相同的规则
   报告 —— 符号检验、实例重抽样带、面板解剖 —— 并对"支持"一词沿用同样的三段判据（*p* < 0.05 **且**带
   不含 0 **且**改善多于变差）。达不到就是**未确立**，绝不是"无效应"。
3. **实例级的响应结构是否跨 scaffold 重现？** 仅描述性，并且要接受 v18 那次更正所确立的退化一致性审查：
   地板/地板与天花板/天花板的一致记录的是共同实例难度、而非共同响应，在引用任何一致性之前必须先把它们
   剔除。

scaffold 主效应**不在**这份清单上，而且此后也不得添加：它在构造上就与提示框架和动作面混淆在一起。

## 什么情况下不该做

如果 dry run 无法交付第 1、5、8 项 —— 文件暴露面相同、oracle 不可达、产物字节未被改动 —— 这个 probe 就
不该跑。这三项不是对齐上的讲究；缺了它们，这个臂测的就不是它声称要测的东西，而一句干脆的"我们无法对齐
这个 scaffold"，比一个带混淆的数字更有贡献。

第 3、4、6、7、9 项单独失败是可以承受的，前提是每一次失败都在该 probe 的预注册里被**记录成一项 scaffold
差异**，而不是事后才被发现。

## 真要跑起来，别处会跟着变什么

两个后果，两个都不是现在就要落地的：

- **CLAUDE.md 硬约束 1**（"实验已永久关闭。没有付费模型调用、没有新 episode……实验冻结 HEAD 是
  `a89e084`"）必须被修订，而且是显式地、在它自己的 commit 里修订：为一个具名的 scaffold 臂划出一块拥有
  自己上限与账本的范围，同时让每一个从 `a89e084` 派生出来的冻结数字保持不动。那次修订是一个决定，不是
  形式，本文刻意不做。
- **论断格会多出第四个投影。** 论文的配置是 `c = (f, i, m)`，跨家族、实例集与模型，投影为 π_I、π_M、π_F。
  一个 scaffold 臂会加上 π_S，于是现有的每一个判定 —— S0 观察到、S1 复现一次、S2-M / S2-F / S3 未确立
  —— 都变成"在固定 scaffold 下"的陈述。那是与 v20 同一类的手稿改动，而且应当跟在 probe 之后，而不是走在
  它前面。

## 核验本文，零调用

```bash
~/.opencode/bin/opencode --version                 # 1.18.19 —— 钉住这个确切版本
~/.opencode/bin/opencode agent list                # 7 个 agent；build 放行 "*"
~/.opencode/bin/opencode debug agent build         # 解析后的工具 + 权限规则
~/.opencode/bin/opencode debug config              # 解析后的配置；断言各注入源为空
~/.opencode/bin/opencode debug skill               # OpenCode 自带的配置参考
curl -s https://opencode.ai/config.json            # 上文引用的每个键的权威 schema
```

冻结侧的数字：`scripts/phase8a_run.py:48`（常量）、
`scripts/phase8a_episode_runner.py:187`（driver 调用）、
`scripts/llm_agent_driver.py:632`（workspace、截止时间、环境抹除）、
`eda_agentbench/agentic/runner.py:179`（`agent_cmd` 接缝）。
