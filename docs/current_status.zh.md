**[English](current_status.md) | 中文**

# 基准测试当前状态

**阶段**：7 — P7 SpyGlass + PrimeTime + Agent 运行器

## 任务清单

| Track | 数量 | 工具 | 来源 |
|-------|-------|---------|--------|
| P1 RTL 调试 | 1001 | VCS | 1 个手工制作 + 1000 个生成 |
| P2 测试平台/SVA 生成 | 101 | VCS | 1 个冒烟 + 100 个生成 |
| P3 时序报告 QA | 1008 | pt（合成） | 1 个冒烟 + 999 个合成 + 8 个 PT 原型 |
| P4 SPICE 仿真 | 302 | HSPICE, Spectre | 2 个冒烟 + 300 个生成（3 种电路类型） |
| P5 SPICE 网表调试 | 100 | HSPICE | 从外部包导入 |
| P6 DC 综合 QA | 51 | dc（合成） | 1 个冒烟 + 50 个生成（10 种问题类型） |
| P6 DC 约束调试 | 13 | dc | 1 个冒烟 + 12 个生成（6 种缺陷类别） |
| P7 SpyGlass Lint 调试 | 16 | spyglass | 1 个冒烟 + 15 个生成（3 种缺陷类别） |
| P7 PrimeTime STA 调试 | 17 | pt | 1 个冒烟 + 16 个生成（4 种缺陷类别） |
| **合计** | **2609** | | |

## P1 缺陷类型分布

10 种缺陷类型，每种 100 个任务：

| 缺陷类型 | 数量 |
|----------|-------|
| sensitivity_list | 100 |
| blocking_nonblocking | 100 |
| reset_polarity | 100 |
| width_truncation | 100 |
| comparison_boundary | 100 |
| wrong_mux_select | 100 |
| priority_order | 100 |
| fsm_transition_error | 100 |
| counter_off_by_one | 100 |
| enable_condition | 100 |

## P2 测试平台/SVA 生成

101 个任务（1 个冒烟 + 100 个生成）。10 个设计模板，20 个变异体变种。基于变异体的评分：
- Agent 为正确的 RTL 设计编写测试平台
- 测试平台必须在正确设计上通过并捕获 2 个变异体
- 评分：compile（0.2）+ golden_pass（0.4）+ mutant_1（0.2）+ mutant_2（0.2）
- 模板：mux2、counter、fsm、handshake、priority_encoder、pulse_detector、arbiter、edge_detector、valid_ready_fsm、fifo_status

## P3 时序报告 QA

1008 个任务（1 个冒烟 + 999 个合成 + 8 个 PT 原型）。合成的标准化报告：
- Agent 回答关于时序报告字段（WNS、TNS、slack 等）的问题
- 10 种问题类型，轮询分布（每种 99–100 个）
- 30 个唯一时钟，15 个路径组，~30% 多时钟报告
- 路径数量 3–50，WNS 范围 -5.0 至 -0.01，TNS 范围 -75 至 -0.3
- 评分：answer_match（1.0）
- 合成任务不需要真实 PrimeTime 工具（使用合成报告）
- 8 个 PT 原型任务：手工制作或真实 PrimeTime 支持的报告（ID 900000–900007）
- 完整解答评估：1008/1008 = 1.00

## P4 配置分布

300 个生成任务，3 种电路类型（每种 100 个：50 个 HSPICE + 50 个 Spectre）：

### RC 上升延迟（100 个任务）
- 27 种 R_sol 选择（220–47kΩ），16 种 C 选择（1pF–470pF）
- R_bug 倍数：5–20x R_sol
- 指标：tdrise（公开）、tdfall（隐藏）

### RC 下降延迟（100 个任务）
- 与 RC 上升延迟相同的参数空间
- 指标：tdrise（公开）、tdfall（隐藏）

### RLC 响应（100 个任务）
- 14 种 R_sol 选择（100–3300Ω），14 种 L 选择（1µH–470µH），10 种 C 选择（1pF–1nF）
- R_bug 倍数：4–10x R_sol
- 指标：tdrise（公开）、tdfall（隐藏）
- 缺陷的过阻尼 R 比解答的欠阻尼 R 响应更慢

另有 2 个冒烟任务（1 个 HSPICE，1 个 Spectre）。

## P5 错误类别分布

## P6 DC 综合 QA（原型）

51 个任务（1 个冒烟 + 50 个生成）。基于解析器的合成 DC 综合报告 QA：
- Agent 回答关于综合报告字段（面积、单元数、时序等）的问题
- 10 种问题类型，轮询分布（每种 5 个）
- 50 个模块名，30 个时钟名
- 评分：answer_match（1.0）
- 不需要真实 DC 工具（合成报告）
- 完整解答评估：51/51 = 1.00
- 系统上检测到 DC：是

| 类别 | 数量 |
|----------|-------|
| missing_model | 15 |
| duplicate_element | 15 |
| missing_subckt | 14 |
| wrong_pin_count | 14 |
| missing_include | 14 |
| unsupported_dialect | 14 |
| invalid_directive | 14 |

## 测试套件

| 类别 | 数量 | 状态 |
|----------|-------|--------|
| pytest 测试 | 360+ | 全部通过 |
| RTL 冒烟测试 | 5 | 通过 |
| P2 冒烟测试 | 4 | 通过 |
| P3 冒烟测试 | 7 | 通过 |
| HSPICE 冒烟测试 | 7 | 通过 |
| Spectre 冒烟测试 | 12 | 通过 |
| P5 批量评估 | 100/100 + 100/100 | 通过 |
| P7 SpyGlass 冒烟 | 1 | 通过 |
| P7 PrimeTime 冒烟 | 1 | 通过 |
| Agent 运行器测试 | 38 | 通过 |

## 数据集评估结果

| 模式 | 任务 | 平均分 | Buggy 较低 |
|------|-------|-----------|-------------|
| Solution | 2609/2609 | 1.00 | N/A |
| Buggy | 2609/2609 | < 1.00 | 2609/2609 |

所有任务已验证：solution 得分完美，buggy 得分严格更低。

## 检测到的工具

| 工具 | 供应商 | 状态 |
|------|--------|--------|
| VCS | Synopsys | 可用 |
| HSPICE | Synopsys | 可用 |
| Spectre | Cadence | 可用 |
| PrimeTime | Synopsys | 可用 |
| SpyGlass | Synopsys | 可用 |
| DC | Synopsys | 可用 |

## CLI 命令

| 命令 | 状态 |
|---------|--------|
| `eda-bench detect-tools` | 正常 |
| `eda-bench validate-task` | 正常 |
| `eda-bench evaluate-task` | 正常 |
| `eda-bench evaluate-dataset` | 正常 |
| `eda-bench report` | 正常 |
| `eda-bench run-agent` | 正常 |
| `eda-bench run-agent-dataset` | 正常 |

## 报告产物

确定性基准测试摘要和清单产物由以下命令生成：

```bash
python scripts/export_benchmark_summary.py
```

完整摘要参见 `reports/benchmark_summary.md`（v0.3-phase5f-2312）。其他产物包括 `task_inventory.json`、`task_inventory.csv`、track/工具/评分分布、按 track 细分和排行榜模板。

## 已知限制

1. Agent 运行器 MVP 可用（`run-agent`、`run-agent-dataset`）。单 shell 命令 agent 接口；无交互式循环或逐次工具调用记录。
2. 无 LLM API 集成（提交模式下解释评分默认为 1.0）。
3. P2 命名在 Phase 4E 中已清理：`p2_tb_sva_gen` track、`tb_sva_gen.TBSVAGenEvaluator`。
4. P3 在 metadata 中使用 `tool: ["pt"]`，但跳过工具检测（合成报告，无真实 PrimeTime）。
5. P6 DC 综合 QA 是原型（51 个任务）；尚未扩展。
6. P7 SpyGlass Lint 调试是原型（16 个任务）；尚未扩展。
7. P7 PrimeTime STA 调试是原型（17 个任务）；尚未扩展。
8. 无 P8 物理 track（无 ICC2/Innovus/StarRC/Sentaurus 任务）。
9. P4 有 3 种电路类型：RC 上升延迟、RC 下降延迟、RLC 建立（共 302 个任务）。
10. P5 有 100 个任务（执行验证，7 种错误类别）。
11. 无 `generate` CLI 命令（生成需要直接运行 Python 脚本）。
12. Spectre 测量使用 `-format nutascii` + Python 波形解析。

## 后续阶段

- **Phase 4A**：P2 测试平台/SVA 生成 — 已完成
- **Phase 4B**：P3 时序报告 QA — 已完成
- **Phase 4C**：文档/数据卡/发布政策 — 已完成
- **Phase 4D**：集成审计 — 已完成
- **Phase 4E**：P2 命名清理 — 已完成
- **Phase 4F**：采样评估模式 — 已完成
- **Phase 5A**：P3 扩展到 1000 — 已完成
- **Phase 5B**：P2 扩展到 101 — 已完成
- **Phase 5E**：PT 原型（8 个任务）— 已完成
- **Phase 5F**：P5 扩展到 100 — 已完成
- **Phase 6A**：P4 扩展到 302（RC 上升/下降 + RLC 建立）— 已完成
- **Phase 6B**：P6 DC 综合 QA 原型（51 个任务）— 已完成
- **Phase 6D**：基线运行器和排行榜 — 已完成
- **Phase 7A**：P7 SpyGlass Lint 调试原型（16 个任务）— 已完成
- **Phase 7B**：P7 PrimeTime STA 调试原型（17 个任务）— 已完成
- **Phase 7C**：Agent 运行器 MVP — 已完成
