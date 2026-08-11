**[English](status.md) | 中文**

# 基准测试状态

**状态（2026-08）：** 数据集冻结于 **2985 个任务 / 18 个 track 目录**；ICLR 2027 稿件已定稿（`submission/`，v5），停在等待人工上传 OpenReview。**所有实验性模型调用已永久关闭**；实验冻结 HEAD 为 `a89e084`（不可变）。

本文档取代原先的 `current_status.md` 与 `roadmap.md`。已冻结的 v0 里程碑快照见 [phases/current_v0_status.zh.md](phases/current_v0_status.zh.md)。

## 任务清单

已发布基准为 **2892 个任务 / 11 条 track（P1–P9）**。P10–P16 为探针门控的研究族（未发布）。

| Track | 数量 | 工具 | 来源 |
|-------|-------|---------|--------|
| P1 RTL Debug | 1001 | VCS | 1 手写 + 1000 生成 |
| P2 Testbench/SVA Gen | 101 | VCS | 1 冒烟 + 100 生成（10 模板） |
| P3 Timing Report QA | 1008 | pt（合成） | 1 冒烟 + 999 合成 + 8 PT 原型 |
| P4 SPICE Sim | 349 | HSPICE, Spectre | 2 冒烟 + 297 生成（3 种电路） + 30 阻尼 + 20 OTA 定尺寸 |
| P5 SPICE Deck Debug | 100 | HSPICE | 由 datagen 模块生成 |
| P6 DC Synthesis QA | 51 | dc（合成） | 1 冒烟 + 50 生成（10 种题型） |
| P6 DC Constraint Debug | 61 | dc | 1 冒烟 + 60 生成（6 类 bug × 10 RTL 模板） |
| P7 SpyGlass Lint Debug | 50 | spyglass | 1 冒烟 + 49 生成（3 类 lint × 设计库） |
| P7 PrimeTime STA Debug | 53 | pt | 1 冒烟 + 52 生成（4 类 bug × 13 模板） |
| P8 PnR Report QA | 101 | icc2/innovus（合成） | 1 冒烟 + 100 生成（9 种题型） |
| P9 PT Exception Debug | 17 | pt | 时序例外（false_path/multicycle）调试——前沿模型已饱和，作为难度来源退役 |
| **已发布小计** | **2892** | | **11 条 track（P1–P9）** |
| P10–P13 合成（研究） | 10 | pt | 多产物项目/交接探针（p10 6、p11 2、p12 1、p13 1） |
| P14 Workflow Handoff（研究） | 27 | pt | 语义交接对照组 + clarity-bundle 消融 |
| P15 STA Handoff（研究） | 46 | pt | Family A 跨族交接（来源/权威 DAG） |
| P16 SPICE Handoff（研究） | 10 | HSPICE | Family B 跨族交接（请求—权威 join） |
| **合计** | **2985** | | **18 个 track 目录** |

## P1 Bug 类型分布

10 类 bug，每类 100 个：sensitivity_list、blocking_nonblocking、reset_polarity、width_truncation、comparison_boundary、wrong_mux_select、priority_order、fsm_transition_error、counter_off_by_one、enable_condition。

## P2 Testbench/SVA 生成

101 个任务（1 冒烟 + 100 生成）。10 个设计模板、20 个变异体。基于变异的评分：
- 智能体为黄金 RTL 设计编写 testbench
- testbench 必须在黄金设计上通过，并捕获 2 个变异体
- 评分：compile (0.2) + golden_pass (0.4) + mutant_1 (0.2) + mutant_2 (0.2)
- 模板：mux2、counter、fsm、handshake、priority_encoder、pulse_detector、arbiter、edge_detector、valid_ready_fsm、fifo_status

## P3 Timing Report QA

1008 个任务（1 冒烟 + 999 合成 + 8 PT 原型）。合成的规范化报告：
- 10 种题型轮转分布（每种 99–100）
- 30 个时钟名、15 个 path group、约 30% 多时钟报告
- path 数 3–50，WNS 范围 -5.0 至 -0.01，TNS 范围 -75 至 -0.3
- 评分：answer_match (1.0)；合成任务无需真实 PrimeTime
- 8 个 PT 原型任务：手写或真实 PrimeTime 支撑的报告（ID 900000–900007）

## P4 配置分布

297 个生成任务覆盖 3 种电路（每种约 100：HSPICE + Spectre），外加 2 个冒烟任务和两条硬残差**定尺寸**轨道（30 阻尼设计 + 20 OTA 定尺寸）。

- **RC 上升/下降延迟** —— 27 种 R_sol（220–47kΩ）、16 种 C（1pF–470pF）；R_bug 为 R_sol 的 5–20 倍；指标 tdrise（公开）/ tdfall（隐藏）
- **RLC 响应** —— 14 种 R_sol（100–3300Ω）、14 种 L（1µH–470µH）、10 种 C（1pF–1nF）；R_bug 为 4–10 倍；过阻尼的 buggy 比欠阻尼的 solution 响应更慢
- **定尺寸轨道** —— 使用各自的真实 Spectre 标定门 + 智能体公平性门，而非 250 抽样门。两条定尺寸轨道均被证明**对前沿模型过易**（工具可用后顶级模型达到 1.00），这正是后续工作转向诊断/结构类任务的原因。

P4 的稳定时间接受窗口基于真实仿真标定；早期"全部黄金 = 1.00"的笼统结论先于该标定，掩盖了 5 个损坏的稳定时间任务（已修复/剔除）。

## P5 错误类别分布

100 个导入任务（执行验证的调试对照包），7 类错误：missing_model (15)、duplicate_element (15)、missing_subckt (14)、wrong_pin_count (14)、missing_include (14)、unsupported_dialect (14)、invalid_directive (14)。

评分：execution_pass (0.9) + explanation (0.1)。接受任何功能正确的修复（基于执行，不做精确 diff）。

## P6 DC Synthesis QA

51 个任务（1 冒烟 + 50 生成）。基于解析器的合成 DC 综合报告问答；10 种题型（各 5 个）；50 个模块名、30 个时钟名。评分：answer_match (1.0)。无需真实 DC 工具。

## P6 DC Constraint Debug

61 个任务（1 冒烟 + 60 生成，6 类 bug × 10 RTL 模板）。针对 Design Compiler 的执行式 SDC 约束修复。评分：constraint_pass (0.6) + execution_pass (0.3) + explanation (0.1)。接受等价的非完全相同修复。

## P7 SpyGlass Lint Debug

50 个任务（1 冒烟 + 49 生成，3 类 lint × 设计库）。使用真实 SpyGlass（sg_shell）执行；智能体将 RTL lint 违规修至零。评分：lint_pass (0.9) + explanation (0.1)。

## P7 PrimeTime STA Debug

53 个任务（1 冒烟 + 52 生成，4 类 bug × 13 模板）。使用真实 PrimeTime（pt_shell）执行。评分：timing_check (0.6) + execution_pass (0.3) + explanation (0.1)。

## P8 PnR Report QA

101 个任务（1 冒烟 + 100 生成）。基于解析器的合成 ICC2/Innovus PnR 报告问答；9 种题型。评分：answer_match (0.9) + explanation (0.1)。无需真实 ICC2/Innovus。

## P9 PT Exception Debug

17 个任务。真实 PrimeTime 上的时序例外（false_path / multicycle）调试。**已作为难度来源退役**：前沿模型对"明示意图"和"从 RTL 推断的意图"都能解出，印证了小规模单故障定位已饱和。

## P10–P16 研究族（未发布）

用于语义交接研究线的探针门控合成多产物族。*语义交接*要求从具误导性角色的证据中，将一个元组绑定到规范化的类型化角色；错误绑定仍会产生绿色的工具签核，因此只有类型化的来源/权威 oracle 才能拒绝它。结果摘要见 `CLAUDE.md`，设计编年见 `docs/phases/`。

## 测试套件

- `scripts/check` —— 本地门禁：免工具 pytest（`-m "not requires_tools"`）+ 结构化数据集校验（2985/2985）。这是提交前的门禁。
- EDA 工具测试标记为 `requires_tools`，需要 b04 shim；本地门禁将其排除。
- 真实工具的**黄金**门（`scripts/validate_dataset.py --changed` + b04 shim）是独立的手动步骤，无法在本地门禁中完成。
- 各 track 的冒烟脚本：RTL (VCS)、P2、P3、HSPICE、Spectre、P5 批量、P6 DC、P7 SpyGlass、P7 PrimeTime、P8 PnR；另有数据集评测冒烟与智能体运行器测试。

云 CI 已被有意否决（2026-06-18）：GitHub runner 既跑不了商业工具也连不上 b04，只能跑免工具子集，会给出虚假的信心。

## 数据集验证

- **Solution 模式（黄金通过）：** 本地 QA/解析类 track 在全量数据集上 = 1.00；商业工具类 track 通过真实 Synopsys/Cadence 路径在 250 任务分层跨轨样本上验证 = 1.00（seed 7）。全量真实工具复验已由 `scripts/validate_dataset.py` 自动化并做哈希缓存。
- **Buggy 模式：** 全部 < 1.00，并强制每任务 `golden − buggy` 客观分差 ≥ 0.15（未修复的输入不得得分与修复相当）。
- **公平性门：** 在采信模型分数之前，先让已知正确解走同一条路径评分；必须约为 1.0，否则说明评分器/环境在扭曲测量。

## 各 Track 使用的工具

| 工具 | 厂商 | 使用者 |
|------|------|--------|
| VCS | Synopsys | P1, P2 |
| HSPICE | Synopsys | P4, P5, P16 |
| Spectre | Cadence | P4 |
| Design Compiler | Synopsys | P6 DC Constraint Debug |
| PrimeTime | Synopsys | P7 PrimeTime STA Debug, P9, P10–P15 |
| SpyGlass | Synopsys | P7 SpyGlass Lint Debug |

P3、P6 DC Synthesis QA、P8 使用合成报告（基于解析器），无需真实工具。商业工具**未在本地安装** —— 通过透明 shim 在 b04 上运行（见 `CLAUDE.md`）。

## CLI 命令

`eda-bench detect-tools` · `validate-task` · `evaluate-task` · `evaluate-dataset` · `report` · `run-agent` · `run-agent-dataset` —— 均可用。

## 报告产物

```bash
python scripts/export_benchmark_summary.py
```

重新生成 `reports/benchmark_summary.md` 以及 `task_inventory.{json,csv}`、track/工具/评分分布、各 track 明细和排行榜模板。数据集变更后需重新生成。

## 已知限制

1. 智能体运行器采用两阶段工作区模型 + 单 shell 命令接口；已有 LLM 驱动（`scripts/llm_agent_driver.py`，多模型网关），但没有交互式的逐工具调用记录界面。
2. P3 在 metadata 中声明 `tool: ["pt"]` 但跳过工具检测（合成报告）。
3. P6 DC Synthesis QA 仍是原型（51 个任务），尚未扩容。
4. P8 仅为报告问答 —— 没有物理布局布线执行轨道（无 ICC2/Innovus PnR 运行、StarRC、Sentaurus）。
5. 没有 `generate` CLI 命令；生成需直接运行 Python 脚本。
6. Spectre 测量使用 `-format nutascii` + Python 波形解析。
7. 两条 P4 定尺寸轨道对前沿模型已饱和（顶级模型 1.00），不再有区分度。
8. P9 单故障定位同样饱和，已作为难度来源退役。

## 阶段历史

- **Phase 0 (P0)** —— 统一框架、CLI、schema、评分器
- **Phase 1 (P1)** —— RTL Debug 与生成（1001）
- **Phase 2A–E** —— HSPICE/Spectre 冒烟、SPICE 评分器、数据集/报告 CLI、扩容
- **Phase 4A–F** —— P2、P3、文档/数据卡/发布策略、集成审计、P2 命名清理、抽样评测
- **Phase 5A/B/E/F** —— P3→1008、P2→101、PT 原型（8）、P5→100
- **Phase 6A–D** —— P4→302、P6 DC Synthesis QA、P6 DC Constraint Debug、基线运行器 + 排行榜
- **Phase 7A–C（建设）** —— P7 SpyGlass、P7 PrimeTime、智能体运行器 MVP
- **Phase 8A/B** —— P8 PnR Report QA 原型；真实工具调试轨道扩容（P6 DC Constraint→61、SpyGlass→50、PrimeTime→53）
- **难度强化** —— P4 定尺寸轨道（阻尼 30、OTA 20）、P9 PT Exception Debug；两者均被发现已饱和
- **研究线（P10–P16）** —— 语义交接族、可靠性/校准层、跨族外部效度，最终形成 ICLR 2027 稿件（`submission/`）

> **命名警告：** 上面的建设阶段复用了 "Phase 7A/7B/7C" 标签，而 "Phase-7A/7B/7C" **同时**被用于研究/稿件阶段。两者无关。

## 后续阶段

当前没有进行中的工作。实验计划已关闭，稿件等待人工上传 OpenReview。以下为候选的未来工作，均未启动：

- **P5 Spectre 方言** —— Spectre 方言的 SPICE deck 修复（P5 目前仅 HSPICE）
- **专家级物理设计轨道** —— ICC2/Innovus 布局布线执行（超出 P8 报告问答）、StarRC 寄生参数提取、Sentaurus TCAD
- **智能体与评分基础设施** —— 带逐工具调用记录的交互式智能体循环；LLM 评判的解释评分；排行榜 / API 提交基础设施
- **基准难度** —— 依据饱和度结论，新的难度应来自诊断/结构类与覆盖/查全类任务，而非单故障定位
