**[English](current_v0_status.md) | 中文**

# EDA-AgentBench v0 状态

> **⚠️ 已冻结的历史快照。** 本文档记录 v0 里程碑（1113 个任务，提交 `960677c`），
> 仅作参考保留。实时基准测试状态（Phase 8A，2828 个任务）见
> [current_status.md](current_status.md)。

**检查点提交：** `960677c`

## 任务清单

| Track | 数量 | 工具 | 来源 |
|-------|-------|---------|--------|
| P1 RTL 调试 | 1001 | VCS | 1 个手工制作 + 1000 个生成 |
| P4 SPICE 仿真 | 102 | HSPICE, Spectre | 2 个冒烟 + 100 个生成 |
| P5 SPICE 网表调试 | 10 | HSPICE | 由 datagen 模块生成 |
| **合计** | **1113** | | |

### P1 缺陷类型分布

10 种缺陷类型，每种 10 个任务：

| 缺陷类型 | 数量 |
|----------|-------|
| sensitivity_list | 10 |
| blocking_nonblocking | 10 |
| reset_polarity | 10 |
| width_truncation | 10 |
| comparison_boundary | 10 |
| wrong_mux_select | 10 |
| priority_order | 10 |
| fsm_transition_error | 10 |
| counter_off_by_one | 10 |
| enable_condition | 10 |

### P4 配置分布

5 组 RC 参数集，每组生成 1 个 HSPICE + 1 个 Spectre 任务：

| 配置 | R_bug | R_sol | C |
|--------|-------|-------|------|
| 0 | 10k | 1.2k | 10p |
| 1 | 22k | 2.2k | 4.7p |
| 2 | 4.7k | 560 | 22p |
| 3 | 15k | 1.5k | 6.8p |
| 4 | 33k | 3.3k | 3.3p |

## 测试套件

- **63** 个 pytest 测试
- **5** 个 RTL 冒烟测试（`scripts/run_smoke.sh`）
- **7** 个 HSPICE 冒烟测试（`scripts/run_spice_smoke.sh`）
- **12** 个 Spectre 冒烟测试（`scripts/run_spectre_smoke.sh`）
- **15** 个数据集冒烟测试（`scripts/evaluate_dataset_smoke.sh`）

## 数据集评估结果

| 模式 | 任务 | 平均分 | Buggy 较低 |
|------|-------|-----------|-------------|
| Solution | 113/113 | 1.00 | N/A |
| Buggy | 113/113 | 0.51 | 113/113 |

所有任务已验证：solution 得分完美，buggy 得分严格更低。

## 检测到的工具

| 工具 | 供应商 | 状态 |
|------|--------|--------|
| VCS | Synopsys | 可用 |
| HSPICE | Synopsys | 可用 |
| Spectre | Cadence | 可用 |

## CLI 命令

| 命令 | 状态 |
|---------|--------|
| `eda-bench detect-tools` | 正常 |
| `eda-bench validate-task` | 正常 |
| `eda-bench evaluate-task` | 正常 |
| `eda-bench evaluate-dataset` | 正常 |
| `eda-bench report` | 正常 |

## 已知限制

1. **无 Agent 运行器**：仅支持提交/工作区模式。Agent 在评估期间不能运行工具。
2. **无 LLM API 集成**：提交模式下解释评分默认为 1.0。
3. **无 P2 RTL 生成 track**：任务仅限调试，不包含生成。
4. **无 P5 时序 track**（注：P5 是 SPICE 网表调试，非时序）。
5. **无 P6 lint track**：无 SpyGlass 任务。
6. **无 P7 物理 track**：无 ICC2/Innovus/StarRC/Sentaurus 任务。
7. **P4 仅含 RC 滤波器**：单一电路拓扑，无运放或数字 SPICE 任务。
8. **P5 仅含执行任务**：10 个来自 datagen 包的任务，尚无生成的任务。
9. **无 `generate` CLI 命令**：生成需要直接运行 Python 脚本。
10. **Python 3.9**：使用 `from __future__ import annotations` 进行前向引用。
11. **Spectre 测量**：使用 `-format nutascii` + Python 波形解析（Spectre 21.1 不支持 `.measure`）。
