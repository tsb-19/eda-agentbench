**[English](p6_dc_constraint_debug.md) | 中文**

# P6 DC 约束调试赛道

## 概述

P6 DC 约束调试赛道评估智能体修复有缺陷的 SDC
（Synopsys 设计约束）或 DC TCL 脚本的能力，使 Design Compiler 综合
成功完成。

## 任务格式

每个任务提供：

- 一个小型 RTL 设计（`design.v`）
- 一个有缺陷的约束文件（`constraints.sdc`）— **可编辑**
- DC TCL 脚本（`run_public.tcl`、`run_hidden.tcl`）— 只读
- Shell 运行脚本（`run_public.sh`、`run_hidden.sh`）— 只读

智能体只需修复 `constraints.sdc`，使 DC 综合通过。

## 保留的缺陷类别

仅包含在 DC 下能产生**可检测故障**的类别。

| 缺陷 | 难度 | 检测方法 |
|------|------|----------|
| missing_clock | 简单 | `all_clocks` 返回 0 个时钟 |
| wrong_port_name | 简单 | DC 输出 "Can't find port" 警告 |
| invalid_get_ports | 中等 | DC 输出 "Can't find ports matching" 警告 |
| wrong_top_module | 困难 | DC 对带前缀的端口输出 "Can't find port" |
| syntax_error | 简单 | DC 非零退出（TCL 解析错误） |
| unsupported_command | 中等 | DC 输出 "unknown command" 错误 |

## 已移除/推迟的类别

以下类别因 DC 静默接受而被移除：

| 缺陷 | 原因 |
|------|------|
| wrong_period | DC 接受任何周期值而不报错 |
| missing_input_delay | DC 接受缺失的延迟而不报错 |
| missing_output_delay | DC 接受缺失的延迟而不报错 |
| tight_constraint | DC 接受过紧的约束而不报错 |

这些可能会作为报告问答/诊断任务（非基于执行）重新考虑。

## 检测机制

TCL 脚本使用 `redirect -file` 捕获 SDC 源输出，然后检查：

1. 源输出中的 `Error:`、`Can't find` 或 `unknown command` 模式
2. `all_clocks` 返回至少一个时钟
3. 所有设计端口通过 `get_ports` 解析
4. `compile_ultra` 成功

标记：
- `CONSTRAINTS_OK` — 所有检查通过
- `CONSTRAINTS_FAIL: reason1,reason2` — 一个或多个检查失败

评估器使用 `^CONSTRAINTS_OK`（锚定）以避免匹配回显的 TCL 代码。

## RTL 模板

10 个小型可综合模板（使用 `lsi_10k.db` 经 `compile_ultra`）：

- `counter` — 带使能的 8 位计数器
- `updown_counter` — 加/减计数器
- `accumulator` — 累加寄存器
- `shift_reg` — 移位寄存器
- `adder_pipe` — 流水线加法器
- `alu_reg` — 寄存 ALU
- `comparator_reg` — 寄存比较器
- `decoder_reg` — 寄存译码器
- `mux_reg` — 多路复用器 + 寄存器
- `fsm_ctrl` — 3 状态 FSM 控制器

## 评分

| 组件 | 权重 | 描述 |
|------|------|------|
| constraint_pass | 0.6 | 存在 CONSTRAINTS_OK 标记 |
| execution_pass | 0.3 | DC 运行且约束通过 |
| explanation | 0.1 | 在提交模式下始终为 1.0 |

## 工具要求

- Design Compiler（`dc_shell`）— 单元测试可选，执行时必需
- Synopsys 默认安装中的标准单元库（`lsi_10k.db`）

## 已知限制

- DC 对许多约束问题较为宽容；仅 6 个类别能产生可检测的故障
- 规模：61 个任务（1 个冒烟 + 60 个生成，6 种缺陷类别 × 10 个 RTL 模板）
- 不支持 Spectre 方言
- 尚未集成智能体运行器
