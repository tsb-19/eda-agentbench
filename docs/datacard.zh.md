**[English](datacard.md) | 中文**

# EDA-AgentBench 数据集卡片

## 摘要

EDA-AgentBench 是一个用于评估 LLM 和编码 agent 在使用商业 Synopsys 和 Cadence 工具的真实 EDA（电子设计自动化）工作流程中表现的基准测试。它衡量 agent 是否能正确修改 RTL 设计、SPICE 网表和仿真网表以通过基于工具的验证。

## 数据集组成

| Track | 数量 | 工具 | 数据类型 | 评分方式 |
|-------|-------|---------|-----------|----------------|
| P1 RTL 调试 | 1001 | VCS | mutation_synthetic | 编译 + 公开测试 + 隐藏测试 + 解释 |
| P2 测试平台/SVA 生成 | 101 | VCS | mutation_synthetic | 编译 + golden_pass + mutant_1 + mutant_2 |
| P3 时序报告 QA | 1008 | pt（合成） | template_synthetic | 答案匹配 |
| P4 SPICE 仿真 | 102 | HSPICE, Spectre | template_synthetic | 工具运行 + 输出 + 公开指标 + 隐藏指标 + 解释 |
| P5 SPICE 网表调试 | 100 | HSPICE | flow_synthetic | 基于执行（退出码 + 无致命错误）+ 解释 |
| P6 DC 综合 QA | 51 | dc（合成） | template_synthetic | 答案匹配 |
| P6 DC 约束调试 | 13 | dc | template_synthetic | 基于执行（约束 + 执行） |
| P7 SpyGlass Lint 调试 | 16 | spyglass | template_synthetic | 基于执行（lint 违规） |
| **合计** | **2592** | | | |

### P1 RTL 调试（1001 个任务）

- 1 个手工制作的冒烟任务
- 1000 个生成任务：10 种缺陷类型 x 每种 100 个任务
- 数据类型：`mutation_synthetic`（在正确设计中注入缺陷）

| 缺陷类型 | 数量 | 描述 |
|----------|-------|-------------|
| sensitivity_list | 100 | 不完整的 `always @(*)` 敏感列表 |
| blocking_nonblocking | 100 | `=` 与 `<=` 的错误使用 |
| reset_polarity | 100 | 高有效与低有效的极性不匹配 |
| width_truncation | 100 | 端口宽度不匹配导致数据丢失 |
| comparison_boundary | 100 | 比较操作中的差一错误 |
| wrong_mux_select | 100 | 不正确的多路复用器 case/select 信号 |
| priority_order | 100 | 错误的 if-else 优先级 |
| fsm_transition_error | 100 | 不正确的状态转移 |
| counter_off_by_one | 100 | 计数器边界错误 |
| enable_condition | 100 | 缺失或错误的使能条件 |

### P2 测试平台/SVA 生成（101 个任务）

- 1 个冒烟任务 + 100 个生成任务
- 10 个设计模板：mux2、counter、fsm、handshake、priority_encoder、pulse_detector、arbiter、edge_detector、valid_ready_fsm、fifo_status
- 10 个模板共 20 个变异体变种（极性反转、stuck-at、错误转移、阈值错误等）
- 数据类型：`mutation_synthetic`（正确设计 + 每个任务 2 个变异体）
- Agent 编写在正确设计上通过并捕获两个变异体的测试平台
- 评分：compile（0.2）+ golden_pass（0.4）+ mutant_1（0.2）+ mutant_2（0.2）

### P3 时序报告 QA（1008 个任务）

- 1 个冒烟任务 + 999 个生成任务 + 8 个 PT 原型任务
- 数据类型：`template_synthetic`（合成的标准化时序报告）
- Agent 回答关于时序报告字段（WNS、TNS、slack 等）的问题
- 10 种问题类型，轮询分布（每种 99–100 个）
- 30 个唯一时钟，15 个路径组，~30% 多时钟报告
- 不需要真实 PrimeTime 工具（使用合成报告）
- 评分：answer_match（1.0）

### P4 SPICE 仿真（102 个任务）

- 2 个冒烟任务（1 个 HSPICE，1 个 Spectre）
- 100 个生成任务：50 个 HSPICE + 50 个 Spectre
- 数据类型：`template_synthetic`（带参数化元件值的 RC 滤波器电路）

每个任务修复一个 RC 滤波器电路以满足上升/下降时间规格。缺陷版本的电阻值过高 5-10 倍，导致边沿缓慢。解答版本将其替换为正确的电阻。

### P5 SPICE 网表调试（100 个任务）

- 100 个从外部调试对比验证包导入的任务
- 数据类型：`flow_synthetic`（在有效网表中注入结构/语法错误，用真实 HSPICE 验证）

| 错误类别 | 数量 | 描述 |
|----------------|-------|-------------|
| missing_model | 15 | 引用未定义的 MOSFET/二极管模型 |
| duplicate_element | 15 | 两个元件共享相同名称 |
| missing_subckt | 14 | 引用未定义的子电路 |
| wrong_pin_count | 14 | 子电路实例引脚数错误 |
| missing_include | 14 | .include 引用不存在的文件 |
| unsupported_dialect | 14 | 模型级别不被 HSPICE 支持 |
| invalid_directive | 14 | 格式错误的 .include（无文件名） |

### P6 DC 综合 QA（51 个任务，原型）

- 1 个冒烟任务 + 50 个生成任务
- 数据类型：`template_synthetic`（合成的 DC 综合报告）
- Agent 回答关于综合报告字段（面积、单元数、时序等）的问题
- 10 种问题类型，轮询分布（每种 5 个）
- 50 个模块名，30 个时钟名
- 不需要真实 DC 工具（使用合成报告）
- 评分：answer_match（1.0）

## 评估模式

每个任务支持两种提交模式用于验证：

- **Solution 模式**：任务的 `solution/` 目录作为提交。预期：所有任务得分为 1.00。
- **Buggy 模式**：任务的可见/可编辑文件（有缺陷的原始文件）作为提交。预期：所有任务得分 < 1.00。

这些模式验证任务校准良好：正确答案总是通过，缺陷基线总是失败。

## 当前验证结果

| 模式 | 任务 | 平均分 | Buggy 较低 |
|------|-------|-----------|-------------|
| Solution | 2363/2363 | 1.00 | N/A |
| Buggy | 2363/2363 | < 1.00 | 2363/2363 |

## 测试套件

- 265 个 pytest 测试（全部通过，2 个跳过）
- 每个 track 的冒烟脚本（VCS、P2、P3、HSPICE、Spectre、P5、P6）
- 数据集评估冒烟（所有 track）

## 文件可见性

| 类别 | Agent 可读？ | Agent 可编辑？ | 用于评分？ |
|----------|----------------|-----------------|-------------------|
| visible | 是 | 否（除非也可编辑） | 是 |
| editable | 是 | 是 | 是 |
| hidden | 否 | 否 | 是 |
| forbidden | 否 | 否 | 检查是否被篡改 |

## 生成的产物

确定性数据集产物位于 `reports/` 下：

- `task_inventory.json` / `task_inventory.csv` — 包含元数据的完整任务清单
- `benchmark_summary.md` — 人类可读的摘要（v0.3-phase6b-2363）
- 按 track 分布：`p1_bug_distribution.csv`、`p2_template_mutant_distribution.csv`、`p3_question_type_distribution.csv`、`p5_error_category_distribution.csv`、`p6_question_type_distribution.csv`
- `leaderboard_template.csv` — 用于记录模型评估结果的空模板

生成命令：`python scripts/export_benchmark_summary.py`

## 已知限制

1. 尚无 Agent 运行器（仅支持提交/工作区模式）。
2. P1 和 P4 使用精确解答匹配；P5 接受任何功能正确的修复。
3. P4 仅覆盖 RC 滤波器拓扑（无运放或数字 SPICE）。
4. P5 有 100 个任务（执行验证，7 种错误类别）。
5. 提交模式下无 LLM API 集成用于解释评分。

## 预期用途

本基准测试适用于：

- 评估 LLM/agent 执行 EDA 工程任务的能力
- 在基于工具的代码修复和优化方面比较模型
- 硬件设计 agent 工作流程的研究

本基准测试不适用于：

- 知识问答式的 EDA 问题
- 无需运行 EDA 工具即可解决的任务
- 训练数据（任务是合成的，非真实设计）

## 伦理考量

- 所有任务使用合成设计；不包含真实知识产权。
- 商业 EDA 工具输出在存储前经过清理。
- 日志去除用户名、主机名、绝对路径和许可证服务器名称。
- 任务文件中不存储 API 密钥或凭证。
