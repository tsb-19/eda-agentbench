**[English](current_status.md) | 中文**

# 基准测试当前状态

**阶段**：8A — P8 PnR 报告问答

## 任务清单

| Track | 数量 | 工具 | 来源 |
|-------|-------|---------|--------|
| P1 RTL 调试 | 1001 | VCS | 1 个手工制作 + 1000 个生成 |
| P2 测试平台/SVA 生成 | 101 | VCS | 1 个冒烟 + 100 个生成 |
| P3 时序报告 QA | 1008 | pt（合成） | 1 个冒烟 + 999 个合成 + 8 个 PT 原型 |
| P4 SPICE 仿真 | 302 | HSPICE, Spectre | 2 个冒烟 + 300 个生成（3 种电路类型） |
| P5 SPICE 网表调试 | 100 | HSPICE | 由 datagen 模块生成 |
| P6 DC 综合 QA | 51 | dc（合成） | 1 个冒烟 + 50 个生成（10 种问题类型） |
| P6 DC 约束调试 | 13 | dc | 1 个冒烟 + 12 个生成（6 种缺陷类别） |
| P7 SpyGlass Lint 调试 | 16 | spyglass | 1 个冒烟 + 15 个生成（3 种缺陷类别） |
| P7 PrimeTime STA 调试 | 17 | pt | 1 个冒烟 + 16 个生成（4 种缺陷类别） |
| P8 PnR 报告问答 | 101 | icc2/innovus（合成） | 1 个冒烟 + 100 个生成（9 种问题类型） |
| **合计** | **2710** | | |

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

100 个导入任务（执行验证的调试对比包），7 种错误类别：

| 类别 | 数量 |
|----------|-------|
| missing_model | 15 |
| duplicate_element | 15 |
| missing_subckt | 14 |
| wrong_pin_count | 14 |
| missing_include | 14 |
| unsupported_dialect | 14 |
| invalid_directive | 14 |

评分：execution_pass（0.9）+ explanation（0.1）。接受任何功能正确的修复（基于执行，无精确 diff）。

## P6 DC 综合 QA（原型）

51 个任务（1 个冒烟 + 50 个生成）。基于解析器的合成 DC 综合报告 QA：
- Agent 回答关于综合报告字段（面积、单元数、时序等）的问题
- 10 种问题类型，轮询分布（每种 5 个）
- 50 个模块名，30 个时钟名
- 评分：answer_match（1.0）
- 不需要真实 DC 工具（合成报告）

## P6 DC 约束调试（原型）

13 个任务（1 个冒烟 + 12 个生成，6 种可靠缺陷类别）。基于执行的 SDC 约束修复：
- Agent 修复损坏的 SDC 约束文件，使 Design Compiler 能够接受
- 评分：constraint_pass（0.6）+ execution_pass（0.3）+ explanation（0.1）
- 接受等价的非完全相同修复（基于执行，无精确 diff）

## P7 SpyGlass Lint 调试（原型）

16 个任务（1 个冒烟 + 15 个生成，3 种可靠 Lint 缺陷类别）。基于执行，使用真实 SpyGlass（sg_shell）：
- Agent 修复 RTL Lint 违规，直至 Lint 检查零违规通过
- 评分：lint_pass（0.9）+ explanation（0.1）

## P7 PrimeTime STA 调试（原型）

17 个任务（1 个冒烟 + 16 个生成，4 种可靠 STA 缺陷类别）。基于执行，使用真实 PrimeTime（pt_shell）：
- Agent 修复 PrimeTime 的时序约束错误
- 评分：timing_check（0.6）+ execution_pass（0.3）+ explanation（0.1）

## P8 PnR 报告问答（原型）

101 个任务（1 个冒烟 + 100 个生成）。基于解析器的合成 ICC2/Innovus PnR 报告 QA：
- Agent 回答关于布局布线报告字段的问题
- 9 种问题类型
- 评分：answer_match（0.9）+ explanation（0.1）
- 不需要真实 ICC2/Innovus 工具（合成报告）

## 测试套件

- pytest：全部通过
- 各 track 的冒烟脚本：RTL（VCS）、P2、P3、HSPICE、Spectre、P5 批量、P6 DC、P7 SpyGlass、P7 PrimeTime、P8 PnR
- 数据集评估冒烟（所有 track）
- Agent 运行器测试

## 数据集评估结果

| 模式 | 任务 | 平均分 | Buggy 较低 |
|------|-------|-----------|-------------|
| Solution | 2710/2710 | 1.00 | N/A |
| Buggy | 2710/2710 | < 1.00 | 2710/2710 |

所有任务已验证：solution 得分完美，buggy 得分严格更低。

## 各 Track 使用的工具

| 工具 | 供应商 | 使用场景 |
|------|--------|--------|
| VCS | Synopsys | P1、P2 |
| HSPICE | Synopsys | P4、P5 |
| Spectre | Cadence | P4 |
| Design Compiler | Synopsys | P6 DC 约束调试 |
| PrimeTime | Synopsys | P7 PrimeTime STA 调试 |
| SpyGlass | Synopsys | P7 SpyGlass Lint 调试 |

P3、P6 DC 综合 QA 和 P8 使用合成报告（基于解析器），不需要真实工具。

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

完整摘要参见 `reports/benchmark_summary.md`。其他产物包括 `task_inventory.json`、`task_inventory.csv`、track/工具/评分分布、按 track 细分和排行榜模板。（数据集变更后请重新生成。）

## 已知限制

1. Agent 运行器 MVP 可用（`run-agent`、`run-agent-dataset`）。单 shell 命令 agent 接口；无交互式循环或逐次工具调用记录。
2. 无 LLM API 集成（提交模式下解释评分默认为 1.0）。
3. P3 在 metadata 中使用 `tool: ["pt"]`，但跳过工具检测（合成报告，无真实 PrimeTime）。
4. P6 DC 综合 QA 是原型（51 个任务）；尚未扩展。
5. P6 DC 约束调试是原型（13 个任务）；尚未扩展到 50+。
6. P7 SpyGlass Lint 调试是原型（16 个任务）；尚未扩展到 50+。
7. P7 PrimeTime STA 调试是原型（17 个任务）；尚未扩展。
8. P8 PnR 报告问答是报告 QA 原型（101 个任务）。尚无物理布局布线执行 track（无 ICC2/Innovus PnR 运行、StarRC 或 Sentaurus）。
9. 无 `generate` CLI 命令（生成需要直接运行 Python 脚本）。
10. Spectre 测量使用 `-format nutascii` + Python 波形解析。

## 阶段历史

- **阶段 0 (P0)**：统一框架、CLI、schema、评估器 — 已完成
- **阶段 1 (P1)**：RTL 调试 + 生成 — 已完成
- **阶段 2A–E**：HSPICE/Spectre 冒烟、SPICE 评估器、数据集/报告 CLI、扩展 — 已完成
- **阶段 4A–F**：P2、P3、文档/数据卡/发布、集成审计、P2 命名、采样评估 — 已完成
- **阶段 5A/B/E/F**：P3→1000、P2→101、PT 原型、P5→100 — 已完成
- **阶段 6A/B/C/D**：P4→302、P6 DC 综合 QA、P6 DC 约束调试、基线运行器/排行榜 — 已完成
- **阶段 7A/B/C**：P7 SpyGlass、P7 PrimeTime、Agent 运行器 MVP — 已完成
- **阶段 8A**：P8 PnR 报告问答原型（101 个任务）— 已完成（当前）

后续工作参见 [roadmap.md](roadmap.md)。
