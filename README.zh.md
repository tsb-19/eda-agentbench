**[English](README.md) | 中文**

# EDA-AgentBench

一个用于评估 LLM 和编程智能体在使用商用 Synopsys 和 Cadence 工具的真实 EDA 工作流上表现的基准测试。

## 测试内容

EDA-AgentBench 测试智能体是否能够：

- 借助仿真反馈调试 RTL 设计（VCS）
- 修复 SPICE 网表以满足时序规格要求（HSPICE、Spectre）
- （未来）生成 RTL、诊断 EDA 日志、运行时序收敛、Lint 检查和物理设计

所有任务仅使用**商用 EDA 工具**，不需要开源 EDA 工具。

## 当前覆盖范围（Phase 8A — P8 PnR 报告问答）

| 路道 | 任务数 | 工具 | 描述 |
|------|--------|------|------|
| P1 RTL 调试 | 1001 | VCS | 修复有缺陷的 SystemVerilog 设计 |
| P2 测试平台/SVA 生成 | 101 | VCS | 编写能捕获 RTL 变异体的测试平台 |
| P3 时序报告问答 | 1008 | pt（合成） | 回答关于时序报告的问题 |
| P4 SPICE 仿真 | 302 | HSPICE, Spectre | 修复 RC/RLC 滤波器的上升/下降时间 |
| P5 SPICE 网表调试 | 100 | HSPICE | 修复损坏的 SPICE 仿真网表 |
| P6 DC 综合问答 | 51 | dc（合成） | 回答关于 DC 综合报告的问题 |
| P6 DC 约束调试 | 13 | dc | 修复损坏的 SDC 约束文件 |
| P7 SpyGlass Lint 调试 | 16 | spyglass | 修复由 SpyGlass 检测到的 RTL Lint 违规 |
| P7 PrimeTime STA 调试 | 17 | pt | 修复 PrimeTime 的时序约束错误 |
| P8 PnR 报告问答 | 101 | icc2/innovus（合成） | 回答关于 PnR 报告的问题 |
| **合计** | **2710** | | |

- 1001 个 P1 任务：1 个手工制作的冒烟测试 + 1000 个生成（10 种缺陷类型 x 各 100 个）
- 101 个 P2 任务：1 个冒烟测试 + 100 个生成（10 个设计模板，20 个变异体）
- 1008 个 P3 任务：1 个冒烟测试 + 999 个合成 + 8 个 PT 原型（30 个时钟，15 个路径组，10 种问题类型）
- 302 个 P4 任务：2 个冒烟测试 + 300 个生成（3 种电路类型，各 50 个 HSPICE + 50 个 Spectre）
- 100 个 P5 任务：从外部调试对比验证包导入（7 个错误类别）
- 51 个 P6 DC QA 任务：1 个冒烟测试 + 50 个生成（10 种问题类型）
- 13 个 P6 DC 约束任务：1 个冒烟测试 + 12 个生成（6 个缺陷类别）
- 16 个 P7 SpyGlass 任务：1 个冒烟测试 + 15 个生成（3 个 Lint 缺陷类别）
- 17 个 P7 PrimeTime 任务：1 个冒烟测试 + 16 个生成（4 个 STA 缺陷类别）
- 101 个 P8 PnR 报告问答任务：1 个冒烟测试 + 100 个生成（9 种问题类型）

## 工具依赖

| 工具 | 厂商 | 使用场景 |
|------|------|----------|
| VCS | Synopsys | P1 RTL 调试，P2 测试平台/SVA 生成 |
| HSPICE | Synopsys | P4 SPICE 仿真，P5 SPICE 网表调试 |
| Spectre | Cadence | P4 SPICE 仿真 |
| PrimeTime | Synopsys | P7 PrimeTime STA 调试（P3 使用合成报告，不需要真实工具） |
| Design Compiler | Synopsys | P6 DC 约束调试（P6 DC 综合问答使用合成报告） |
| SpyGlass | Synopsys | P7 SpyGlass Lint 调试 |
| ICC2 / Innovus | Synopsys / Cadence | P8 PnR 报告问答（合成报告，不需要真实工具） |

预期安装路径：

- Synopsys: `/EDA/soft2/synopsys/`
- Cadence: `/EDA/soft2/cadence/`

基准测试在运行时会探测文件系统中的工具位置。任务定义中不包含硬编码路径。

## 安装

```bash
pip install -e ".[test]"
```

## 快速开始

### 1. 检测工具

```bash
eda-bench detect-tools
```

预期输出：显示 VCS、HSPICE、Spectre 可用性的表格。

### 2. 运行冒烟测试

```bash
# RTL 调试冒烟测试（VCS）
bash scripts/run_smoke.sh

# SPICE 冒烟测试（HSPICE）
bash scripts/run_spice_smoke.sh

# Spectre 冒烟测试
bash scripts/run_spectre_smoke.sh

# 数据集冒烟测试（所有路道）
bash scripts/evaluate_dataset_smoke.sh
```

### 3. 验证任务

```bash
eda-bench validate-task tasks/p1_rtl_debug/task_000001
```

## 评估任务

### 智能体模式

在沙盒化的工作空间中运行外部智能体命令来执行任务：

```bash
# 使用脚本智能体运行单个任务
eda-bench run-agent tasks/p3_timing_report_qa/smoke \
    --agent-cmd "cp \$EDA_TASK_PATH/solution/answer.txt \$EDA_WORKSPACE/"

# 使用空操作智能体进行采样数据集评估
eda-bench run-agent-dataset tasks --sample-per-track 1 --seed 42 --agent-cmd "true"
```

智能体通过环境变量接收 `EDA_WORKSPACE`、`EDA_TASK_PATH`、`EDA_TASK_ID` 和 `EDA_TIMEOUT`。详情请参阅 [docs/agentic_runner.md](docs/agentic_runner.md)。

### 单个任务

```bash
# 使用正确解答（应得分 1.00）
eda-bench evaluate-task tasks/p1_rtl_debug/task_000001 \
    --submission tasks/p1_rtl_debug/task_000001/solution

# 使用有缺陷的基线（应得分 < 1.00）
eda-bench evaluate-task tasks/p1_rtl_debug/task_000001 \
    --submission tasks/p1_rtl_debug/task_000001/files
```

### 完整数据集

```bash
# 解答模式：每个任务使用其自身的 solution/ 目录作为提交
eda-bench evaluate-dataset tasks --submission-mode solution

# 缺陷模式：每个任务使用其自身的 files/（有缺陷的）目录作为提交
eda-bench evaluate-dataset tasks --submission-mode buggy

# 按路道过滤
eda-bench evaluate-dataset tasks --submission-mode solution --track p1_rtl_debug
```

### 快速采样评估

用于快速集成检查（约 2 分钟完成，而非约 50 分钟）：

```bash
# 每个路道采样 1 个任务（覆盖所有 10 个路道）
eda-bench evaluate-dataset tasks --sample-per-track 1 --seed 42 --submission-mode solution
eda-bench evaluate-dataset tasks --sample-per-track 1 --seed 42 --submission-mode buggy

# 最多评估 10 个任务
eda-bench evaluate-dataset tasks --limit 10 --seed 42 --submission-mode solution

# 完整集成冒烟测试（解答 + 缺陷采样）
bash scripts/evaluate_dataset_fast.sh
```

**注意：** 采样评估不能替代完整评估。在开发过程中用于快速迭代；在最终验证前请运行完整评估。

### 报告

```bash
# 生成所有报告格式（终端 + JSON + Markdown）
eda-bench report runs/dataset_XXXXXXXX --format all
```

## 预期结果

| 模式 | 任务数 | 平均得分 | 备注 |
|------|--------|----------|------|
| 解答 | 2710/2710 | 1.00 | 正确解答始终获得满分 |
| 缺陷 | 2710/2710 | < 1.00 | 有缺陷的基线始终得分 < 1.00 |

## 任务结构

标准布局（P1、P2、P4）：
```
task_xxxxxx/
  prompt.md           # 可读的任务描述
  metadata.json       # 机器可读的任务规格
  files/              # 智能体可见
    design.sv         # 可编辑（RTL）或 circuit.sp（SPICE）
    tb_public.sv      # 公共测试平台（只读）
    run_public.sh     # 公共测试脚本（只读）
  hidden/             # 仅用于评分
    tb_hidden.sv      # 隐藏测试平台
    run_hidden.sh     # 隐藏测试脚本
  solution/           # 正确解答
    design.sv
```

外部包布局（P5）：
```
spice_deck_debug_NNNN/
  prompt.md
  metadata.json
  grader_contract.json
  visible/            # 有缺陷的网表（可编辑）
  hidden/             # 黄金标准修复后网表
  oracle/             # 可读的参考解答
  validation/         # 验证记录
```

## 评分

每个任务生成一个 `score.json`，包含加权组件：

**RTL 调试（P1）：**
- compile：0.2
- public_test：0.3
- hidden_test：0.4
- explanation：0.1

**测试平台/SVA 生成（P2）：**
- compile：0.2
- golden_pass：0.4
- mutant_1：0.2
- mutant_2：0.2

**时序报告问答（P3）：**
- answer_match：1.0

**SPICE 仿真（P4）：**
- tool_run：0.3
- output_generated：0.2
- public_metric：0.2
- hidden_metric：0.2
- explanation：0.1

**SPICE 网表调试（P5）：**
- execution_pass：0.9
- explanation：0.1

**DC 综合问答（P6）：**
- answer_match：1.0

**DC 约束调试（P6）：**
- constraint_pass：0.6
- execution_pass：0.3
- explanation：0.1

**SpyGlass Lint 调试（P7）：**
- lint_pass：0.9
- explanation：0.1

**PrimeTime STA 调试（P7）：**
- timing_check：0.6
- execution_pass：0.3
- explanation：0.1

**PnR 报告问答（P8）：**
- answer_match：0.9
- explanation：0.1

通过阈值：0.5。详情请参阅 [docs/scoring.md](docs/scoring.md)。

## 防作弊

评估器会在执行前对受保护文件（测试平台、运行脚本）进行 SHA-256 哈希快照，并在执行后验证。对受保护文件的修改将导致评估失败。

## 日志清理

所有工具输出日志在存储前都会进行清理：用户名、主机名、绝对路径和许可证服务器名称会被替换为稳定的占位符。

## 运行目录

`runs/` 目录不会提交到 git。所有评估产物（score.json、日志、工作空间）都写入到该本地目录。

## 文档

- [智能体运行器](docs/agentic_runner.md) — 智能体评估模式
- [基准路道](docs/benchmark_tracks.md) — 路道详细描述和评分规则
- [数据集卡片](docs/datacard.md) — 数据集组成和验证结果
- [当前状态](docs/current_status.md) — 当前基准测试状态（Phase 8A）和已知限制
- [v0 状态（已冻结）](docs/current_v0_status.md) — 冻结的 v0 里程碑快照（1113 个任务）
- [可复现性](docs/reproducibility.md) — 确定性生成和评估
- [公开发布策略](docs/public_release_policy.md) — 发布检查清单和排除项
- [商用工具策略](docs/commercial_tool_policy.md) — 支持的工具和许可证
- [基准规格](docs/benchmark_spec.md) — 整体设计和评估模型
- [任务模式](docs/task_schema.md) — metadata.json 字段参考
- [评分规则](docs/scoring.md) — 任务评分方式
- [添加任务](docs/adding_tasks.md) — 如何创建新任务
- [路线图](docs/roadmap.md) — 未来阶段
- [数据工厂 (eda-bench-prototypes)](https://github.com/tsb-19/eda-bench-prototypes) — 生成并验证 P5 SPICE 网表调试赛道的兄弟仓库

## 许可证

Apache-2.0
