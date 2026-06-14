**[English](benchmark_tracks.md) | 中文**

# 基准测试 Track 概览

| Track | ID | 数量 | 工具 | 用途 | 评分方式 |
|-------|----|-------|---------|---------|---------|
| P1 RTL 调试 | `p1_rtl_debug` | 1001 | VCS | 基于仿真反馈的代码修复 | 编译 + 公开测试 + 隐藏测试 + 解释 |
| P2 测试平台/SVA 生成 | `p2_tb_sva_gen` | 101 | VCS | 面向 RTL 验证的测试平台/SVA 生成 | 编译 + golden_pass + mutant_1 + mutant_2 |
| P3 时序报告 QA | `p3_timing_report_qa` | 1008 | pt（合成） | 时序报告字段提取与问答 | 答案匹配 |
| P4 SPICE 仿真 | `p4_spice_sim` | 302 | HSPICE, Spectre | 基于指标的 RC/RLC/SPICE 优化 | 工具运行 + 输出 + 公开指标 + 隐藏指标 + 解释 |
| P5 SPICE 网表调试 | `p5_spice_deck_debug` | 100 | HSPICE | 基于执行的网表/网表修复 | 执行通过 + 解释 |
| P6 DC 综合 QA | `p6_dc_synthesis_qa` | 51 | dc（合成） | DC 综合报告问答 | 答案匹配 |
| P6 DC 约束调试 | `p6_dc_constraint_debug` | 13 | dc | SDC 约束修复 | 约束通过 + 执行通过 |
| P7 SpyGlass Lint 调试 | `p7_spyglass_lint_debug` | 16 | spyglass | RTL lint 违规修复 | Lint 通过（基于执行） |
| P7 PrimeTime STA 调试 | `p7_primetime_sta_debug` | 17 | pt | SDC/时序约束修复 | 时序检查 + 执行通过 |
| P8 PnR 报告问答 | `p8_pnr_report_qa` | 101 | icc2/innovus（合成） | PnR 报告字段提取与问答 | 答案匹配 |
| **合计** | | **2710** | | | |

## P1: RTL 调试

**目标**：修复有缺陷的 SystemVerilog 设计，使其在 VCS 仿真下同时通过公开和隐藏测试平台。

**衡量内容**：Agent 利用仿真反馈（编译错误、测试失败）诊断 RTL 缺陷并产出正确修复的能力。

**任务结构**：
- `design.sv` — 有缺陷的 RTL（agent 可编辑）
- `tb_public.sv` — 公开测试平台（2-3 个测试用例，对 agent 可见）
- `tb_hidden.sv` — 隐藏测试平台（1-2 个测试用例，agent 永远看不到）
- `run_public.sh` / `run_hidden.sh` — VCS 编译仿真脚本

**缺陷类型**（10 种类型，每种 100 个任务）：

| 缺陷类型 | 描述 | 难度范围 |
|----------|-------------|------------------|
| sensitivity_list | 不完整的 `always @(*)` 敏感列表 | easy–medium |
| blocking_nonblocking | `=` 与 `<=` 的错误使用 | easy–medium |
| reset_polarity | 高有效与低有效的极性不匹配 | easy |
| width_truncation | 端口宽度不匹配 | medium |
| comparison_boundary | 比较操作中的差一错误 | medium |
| wrong_mux_select | 不正确的多路复用器选择信号 | medium |
| priority_order | 错误的 if-else 优先级 | medium–hard |
| fsm_transition_error | 不正确的状态转移 | hard |
| counter_off_by_one | 计数器边界错误 | medium |
| enable_condition | 缺失或错误的使能条件 | easy–medium |

**评分权重**：
```json
{
  "compile": 0.2,
  "public_test": 0.3,
  "hidden_test": 0.4,
  "explanation": 0.1
}
```

**通过条件**：`total_score >= 0.5`

**验证**：solution 模式得分 1.00；buggy 模式所有 1001 个任务得分 < 1.00。

## P2: 测试平台/SVA 生成

**目标**：编写 SystemVerilog 测试平台，验证正确的 RTL 设计并捕获已知的变异体。

**衡量内容**：Agent 编写有效验证代码——测试平台或 SVA 断言——通过仿真检测设计缺陷的能力。

**任务结构**：
- `design_golden.sv` — 正确的 RTL 设计（可见，只读）
- `tb.sv` — 空的测试平台模板（agent 可编辑）
- `design_mutant1.sv` / `design_mutant2.sv` — 有缺陷的设计（隐藏，用于评分）
- `run_public.sh` — 使用正确设计进行编译和仿真
- `run_hidden.sh` — 使用变异体设计进行编译和仿真

**评分**：基于变异体的评分：
1. 编译：测试平台能通过 VCS 编译（0.2）
2. Golden 通过：测试平台在正确设计上通过（0.4）
3. 变异体 1：测试平台捕获第一个变异体（0.2）
4. 变异体 2：测试平台捕获第二个变异体（0.2）

**评分权重**：
```json
{
  "compile": 0.2,
  "golden_pass": 0.4,
  "mutant_1": 0.2,
  "mutant_2": 0.2
}
```

**注意**：Track ID 在 Phase 4E 中从 `p2_rtl_gen` 重命名为 `p2_tb_sva_gen`。引用 `rtl_gen.RTLGenEvaluator` 的旧 metadata 仍通过兼容性垫片被接受。

**验证**：solution 模式得分 1.00；buggy 模式所有 101 个任务得分 0.20。

## P3: 时序报告 QA

**目标**：根据合成的标准化时序报告，回答关于时序报告字段（WNS、TNS、slack 等）的问题。

**衡量内容**：Agent 解析和提取 EDA 时序报告信息的能力——时序收敛工作流程中的关键技能。

**任务结构**：
- `timing_report.rpt` — 合成的标准化时序报告（可见，只读）
- `answer.txt` — 空的答案文件（agent 可编辑）
- `solution/answer.txt` — 正确答案

**关键设计选择**：使用合成的标准化报告而非真实的 PrimeTime 输出。这使得该 track 无需 PrimeTime 许可证即可运行，同时仍然测试相同的解析技能。

**多样性**：
- 30 个唯一时钟名、15 个路径组、50 个模块名、27 个实例前缀
- ~30% 多时钟报告（每条路径不同时钟）
- 路径数量：3–50，WNS 范围：-5.0 至 -0.01，TNS 范围：-75 至 -0.3
- 具有层次深度和可选位索引的信号名
- 10 种问题类型，轮询分布（每种 99–100 个）

**评分**：
```json
{
  "answer_match": 1.0
}
```

**验证**：solution 模式得分 1.00；buggy 模式所有 1000 个任务得分 0.00。

## P4: SPICE 仿真

**目标**：修复有缺陷的 SPICE 网表，使时序测量值满足规范范围。

**衡量内容**：Agent 利用 HSPICE 或 Spectre 仿真反馈诊断模拟电路问题并优化元件值的能力。

**任务结构**：
- `circuit.sp`（HSPICE）或 `circuit.scs`（Spectre）— 有缺陷的网表（可编辑）
- `run_public.sh` — 运行仿真，提取公开测量值
- `run_hidden.sh` — 运行仿真，提取隐藏测量值
- `solution/` — 具有正确元件值的正确网表

**电路类型**（300 个生成任务，每种 100 个）：

| 电路类型 | 描述 | 公开指标 | 隐藏指标 |
|-------------|-------------|---------------|---------------|
| RC 上升延迟 | RC 低通滤波器，上升时间过慢 | tdrise | tdfall |
| RC 下降延迟 | RC 低通滤波器，下降时间过慢 | tdrise | tdfall |
| RLC 响应 | RLC 带通滤波器，响应过慢 | tdrise | tdfall |

缺陷版本的 R_bug（过高 4-20 倍），解答版本的 R_sol（正确值）。对于 RLC 任务，缺陷的 R 导致过阻尼；正确的 R 产生良好阻尼的响应。

**生成配置**（每种类型 100 个任务，每种 50 个 HSPICE + 50 个 Spectre）：
- RC 任务：27 种 R_sol 选择（220–47kΩ）、16 种 C 选择（1pF–470pF）、随机化的 R_bug 倍数（5-20x）
- RLC 任务：14 种 R_sol 选择（100–3300Ω）、14 种 L 选择（1µH–470µH）、10 种 C 选择（1pF–1nF）、R_bug 倍数（4-10x）
- RLC 使用 tdrise/tdfall（与 RC 任务相同）；缺陷的过阻尼 R 比解答的欠阻尼 R 响应更慢

**评分权重**：
```json
{
  "tool_run": 0.3,
  "output_generated": 0.2,
  "public_metric": 0.2,
  "hidden_metric": 0.2,
  "explanation": 0.1
}
```

**指标提取**：
- HSPICE：解析 `.lis` 文件中的 `.measure` 结果，支持工程后缀；RLC 使用 `rise=last` 获取建立时间
- Spectre：从 Python 波形解析器读取 `metrics.json`（使用 `-format nutascii`）

**验证**：solution 模式得分 1.00；buggy 模式所有 302 个任务得分 < 1.00。

## P5: SPICE 网表调试

**目标**：修复因语法或结构错误被 HSPICE 拒绝的 SPICE 仿真网表。

**衡量内容**：Agent 利用 HSPICE 错误信息作为反馈来诊断和修复网表级错误（缺失模型、错误引脚数、重复元件等）的能力。

**与 P4 的关键区别**：P4 任务语法正确但元件值错误。P5 任务语法/结构已损坏，导致仿真器根本无法运行。

**任务结构**（datagen 包布局）：
- `visible/*_bug.sp` — 有缺陷的网表（可编辑）
- `hidden/*_fixed.sp` — 正确的固定网表（用于 solution 模式）
- `oracle/answer.md` — 人类可读的预期修复
- `grader_contract.json` — 基于执行的评分规则
- `validation/` — 调试对比验证记录

**评分**：基于执行，非精确 diff 匹配：
1. 在提交的网表上运行 HSPICE
2. 检查退出码 == 0
3. 检查 `grader_contract.json` 中的无致命错误模式
4. 两个条件都满足则通过

**评分权重**：
```json
{
  "execution_pass": 0.9,
  "explanation": 0.1
}
```

**错误类别**（共 100 个任务）：

| 类别 | 数量 | 描述 |
|----------|-------|-------------|
| missing_model | 15 | 引用未定义的 MOSFET/二极管模型 |
| duplicate_element | 15 | 两个元件共享相同名称 |
| missing_subckt | 14 | 引用未定义的子电路 |
| wrong_pin_count | 14 | 子电路实例引脚数错误 |
| missing_include | 14 | .include 引用不存在的文件 |
| unsupported_dialect | 14 | 模型级别不被 HSPICE 支持 |
| invalid_directive | 14 | 格式错误的 .include（无文件名） |

**为什么不要求精确 diff**：SPICE 网表可以通过多种有效方式修复。任何 HSPICE 可以执行的语法正确修复都会被接受。

## P6: DC 综合 QA

**目标**：回答关于合成 Design Compiler 综合报告（面积、单元数、时序等）的问题。

**衡量内容**：Agent 解析和提取综合报告信息的能力。

**任务结构**：合成的标准化综合报告（可见）+ 答案文件（可编辑）+ `solution/`。

- 51 个任务（1 个冒烟 + 50 个生成），10 种问题类型（轮询，每种 5 个）
- 50 个模块名，30 个时钟名；不需要真实 DC 工具（合成报告）

**评分权重**：
```json
{
  "answer_match": 1.0
}
```

## P6: DC 约束调试

**目标**：修复损坏的 SDC 约束文件，使 Design Compiler 能够接受。

**衡量内容**：Agent 利用 DC 反馈诊断和修复 SDC 约束错误的能力。

- 13 个任务（1 个冒烟 + 12 个生成），6 种可靠缺陷类别
- 基于执行：接受等价的非完全相同修复（无精确 diff）

**评分权重**：
```json
{
  "constraint_pass": 0.6,
  "execution_pass": 0.3,
  "explanation": 0.1
}
```

## P7: SpyGlass Lint 调试

**目标**：修复 Synopsys SpyGlass 检测到的 RTL lint 违规，使 lint 检查零违规通过。

**衡量内容**：Agent 理解 SpyGlass lint 输出、识别 lint 违规根因并修复 RTL 代码以消除违规的能力。

**任务结构**：
- `design.v` — 有 lint 问题的 RTL（agent 可编辑）
- `spyglass.prj` — SpyGlass 项目文件（可见，不可编辑）
- `run_public.sh` / `run_public.tcl` — SpyGlass lint 运行器（可见，不可编辑）
- `run_hidden.sh` / `run_hidden.tcl` — 隐藏 lint 运行器（隐藏，不可编辑）
- `solution/design.v` — 零违规的正确 RTL

**缺陷类别**（经 SpyGlass S-2021.09-SP1 验证的 3 个可靠类别）：

| 类别 | 难度 | SpyGlass 检测 |
|----------|-----------|-------------------|
| latch_inference | easy | Error + Warning |
| multi_driven | medium | Error + Warning |
| blocking_in_seq | medium | Error |

**被拒绝的类别**（SpyGlass 默认 lint 不会标记这些）：
width_mismatch、unused_signal、undriven_signal、missing_default、implicit_net

**评分**：`lint_pass`（0.9）+ `explanation`（0.1）。Lint 通过 = 如果零 Fatal + Error + Warning 则为 1.0。

**验证**：solution=1.00，buggy=0.10（所有任务在真实 SpyGlass 下产生有效对比）。

## P7: PrimeTime STA 调试

**目标**：修复 SDC/时序约束错误，使 PrimeTime 能够运行干净的 STA。

**衡量内容**：Agent 利用真实 PrimeTime（pt_shell）反馈诊断时序约束问题的能力。

- 17 个任务（1 个冒烟 + 16 个生成），4 种可靠 STA 缺陷类别
- 基于执行，使用真实 PrimeTime

**评分权重**：
```json
{
  "timing_check": 0.6,
  "execution_pass": 0.3,
  "explanation": 0.1
}
```

## P8: PnR 报告问答

**目标**：回答关于合成 ICC2/Innovus 布局布线报告的问题。

**衡量内容**：Agent 解析和提取 PnR 报告信息的能力。

- 101 个任务（1 个冒烟 + 100 个生成），9 种问题类型
- 基于解析器；不需要真实 ICC2/Innovus 工具（合成报告）

**评分权重**：
```json
{
  "answer_match": 0.9,
  "explanation": 0.1
}
```

## 未来 Track（规划中）

| Track | ID | 工具 | 状态 |
|-------|----|---------|--------|
| P5 Spectre 方言 | `p5_spice_deck_debug` | Spectre | Spectre 方言网表修复 |
| P6 DC 约束扩展 | `p6_dc_constraint_debug` | dc | 扩展到 50+ 任务 |
| P7 SpyGlass Lint 扩展 | `p7_spyglass_lint_debug` | SpyGlass | 扩展到 50+ 任务 |
| P7 PrimeTime STA 扩展 | `p7_primetime_sta_debug` | pt | 扩展到 50+ 任务 |
| 专家级物理设计 | `p_physical` | ICC2/Innovus/StarRC/Sentaurus | PnR 执行、寄生参数提取、TCAD |
