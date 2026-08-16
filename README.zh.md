**[English](README.md) | 中文**

# 审计 LLM Agent Harness 的泛化论断 —— 可复现产物

本分支是单篇论文的产物：***Auditing Generalization Claims for LLM Agent Harnesses: Semantic Binding and Measurement Validity***（ICLR 2027 投稿，手稿 v12，已冻结）。论文在 [`submission/`](submission/)，用 `cd submission && make` 构建。

> 想找 **EDA-AgentBench** —— 那个 2892 任务的商业 EDA 基准？它在 `master` 上。本分支只保留论文涉及的内容 —— 见 [`docs/REMOVED.zh.md`](docs/REMOVED.zh.md)。

## 论文主张什么

当一次 harness 干预改变了 agent 的行为，你可以主张什么？"多general"不是一个轴而是三个 —— 跨任务**实例**、跨模型**后端**、跨任务**家族** —— 而且拓宽其中一个与拓宽另一个是*不可比*的移动，不是阶梯上更高的一级。因此论文把一个论断的*证据*按其被测量到的 (家族, 实例, 模型) 配置集合来索引，并以包含关系排序。

用到自己的结果上（在一个以工具为地基的**语义交接**任务上）：

| 支撑 | 测到了什么 | 判定 |
|---|---|---|
| **S0** 局部（Qwen3.7-Max，workflow 家族，开发实例） | Base 1/3 → BundleS 3/3，BundleS 下零错轴失败 | **已观察到** |
| **S1** + 留出实例（拓宽实例范围） | 在预先冻结的实例上方向一致 | **复现一次** |
| **S2-M** + DeepSeek-V4-Pro（拓宽模型范围） | 3/4 = 3/4 | **未确立** —— 也不等于不存在 |
| **S2-F** + STA 家族，12 个前瞻实例 | +12.5 pp，敏感带 −12.5 至 41.7；三实例试点方向*相反*（−16.7 pp） | **在固定面板上估计；敏感带跨零** |
| **S2-F** + SPICE 家族 | 1.00 = 1.00 = 1.00 | **天花板；无信息量** |
| **S3** 同时换模型*与*换家族 | 什么都没有 | **未测量** —— 报为未检验，而非失败 |

错误的绑定仍会产生绿色的工具签核（*tool-green*），因此只有类型化的溯源/权威 oracle 才会拒绝它。这正是论文中的失败能够在"以工具退出码计分"的基准里存活的原因。

第二项正交的贡献是四层 **Harness 效应审计协议** —— 能力、采样、执行、产物完整性。每一层都抓到了一个会改变科学结论的具体威胁；其中两个（传输截断、动作面假阳性）在*任何*对未校正日志的分析中都会产出"自信但错"的数字。

## 从这里开始

| 如果你想…… | 读 |
|---|---|
| 找某个具体论断／表格／图的证据 | **[`docs/artifact_map.zh.md`](docs/artifact_map.zh.md)** —— 论文每个对象到生成它的文件 |
| 理解证据基础 | [`reports/README.zh.md`](reports/README.zh.md) |
| 复现数字 | [`docs/reproducibility.zh.md`](docs/reproducibility.zh.md) |
| 了解任务家族是什么 | [`docs/datacard.zh.md`](docs/datacard.zh.md) |
| 了解正确性如何判定 | [`docs/scoring.zh.md`](docs/scoring.zh.md) |
| 了解哪个 commit 产出了什么 | [`docs/provenance.zh.md`](docs/provenance.zh.md) |
| 了解本分支删了什么、为什么 | [`docs/REMOVED.zh.md`](docs/REMOVED.zh.md) |
| 想看一页速览 | [`docs/overview.zh.html`](docs/overview.zh.html) |

## 目录结构

```
submission/        冻结的手稿：main.tex、main.pdf（15 页）、生成的表格、冻结哈希
tasks/             三个语义交接家族
  p14_workflow_handoff/   27 个实例 —— 研究 I（PVT 轴，PrimeTime）
  p15_sta_handoff/        家族 A —— 研究 II S2-F（溯源 DAG，PrimeTime）
  p16_spice_handoff/      家族 B —— 研究 II S2-F（请求-权威联接，HSPICE）
  p13_trajectory_handoff/ 并非被研究的家族 —— 是 p14 生成器读取的资产底料
generators/        三个家族的生成器及其类型化评分器
eda_agentbench/    harness：任务加载器、agentic runner、两阶段工作区、反作弊
scripts/           审计基础设施，以及各阶段的冻结／公平性／分析脚本
reports/           证据基础；reports/evidence/ 是冻结的保管记录
docs/              文档，中英双语
```

## 不用任何 EDA 工具复现论文

所有派生数字 —— 每个表格、区间、敏感带和 *p* 值 —— 都可以在不用商业工具、不联网、不调用模型的前提下从冻结的逐 episode 记录重算：

```bash
pip install -e ".[test]"

scripts/check                                          # 测试 + 任务结构 + 1065 条保管钉
python3 scripts/phase7c_study1_ledger.py    --check    # 研究 I 台账：58 + 12 = 70 个 episode
python3 scripts/phase7c_claim_statistics.py --check    # 12.5 / [-12.5, 41.7] / -16.7
python3 scripts/slim_link_check.py                     # 无悬空仓库路径引用

cd submission && make distclean && make                # 15 页；逐字节可复现的 PDF
```

`--check` 从 `reports/evidence/` 重算并与已提交的输出比对，一旦漂移即以非零码退出。论文中没有一张表是手工抄录的：`main.tex` 直接 `\input` 这些脚本的产出。

## 运行任务家族

给一个交接实例评分需要真实工具 —— p14/p15 用 PrimeTime，p16 用 HSPICE —— 因为错误的绑定只有在工具*绿灯签核之后*才可被检出。工具可达时：

```bash
eda-bench detect-tools
eda-bench evaluate-task tasks/p14_workflow_handoff/workflow_handoff_0009 \
    --submission tasks/p14_workflow_handoff/workflow_handoff_0009/solution
eda-bench run-agent tasks/p14_workflow_handoff/workflow_handoff_0009 --agent-cmd "<你的 agent>"
```

agentic 路径采用两阶段工作区模型：agent 只看到可见+可编辑文件，永远看不到 `hidden/`；评分在第二个工作区中进行，那里叠加了隐藏真值。见 [`docs/agentic_runner.zh.md`](docs/agentic_runner.zh.md)。

## 刻意不在此处的东西

- **付费 episode 无法重跑。** 实验程序已在冻结的实验 HEAD 上永久关闭；所有报告的数字都是从该 HEAD 及其之前已提交的台账重新派生的。见 [`docs/provenance.zh.md`](docs/provenance.zh.md)。
- **没有 S3 证据。** 同时换模型*与*换家族从未测量。它的缺席就是论断本身，而不是遗漏。
- **没有人类构念验证。** 盲法人类研究已预注册但从未执行 —— 也没有用 LLM 顶替缺席的标注者。
- **本分支未做匿名化。** 约 212 个冻结的保管文件含有用户名、主机名或绝对路径，改写它们会破坏论文所主张的保管链。双盲补充材料需要另做一次脱敏导出，而不是 git 编辑。见 [`docs/REMOVED.zh.md`](docs/REMOVED.zh.md)。
- **两个生成器在冻结之后漂移了。** `frozen_membership_verify.py` 报告恰好 2 处不匹配、9 个缺失的被钉文件，均为既有状态，解释见 `docs/frozen_membership_baseline.json`。它们被原样带过来而不是被悄悄清理，因为一张"干净的表"会掩盖真实的漂移。

## 商业工具

三个家族面向商业 Synopsys 工具；没有开源 EDA 工具可以替代。探测默认在 `/EDA/soft2/synopsys/` 与 `/EDA/soft2/cadence/` 下进行；若安装前缀不同，可设 `EDA_TOOL_ROOT` 替换开头的 `/EDA`。任务定义中不写死任何路径。见 [`docs/commercial_tool_policy.zh.md`](docs/commercial_tool_policy.zh.md)。

## 许可

Apache-2.0
