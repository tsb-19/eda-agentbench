**[English](p7_primetime_sta_debug.md) | 中文**

# P7 PrimeTime STA 调试

**目标**：修复有缺陷的 SDC 约束文件，使 PrimeTime STA 时序检查通过。

**测量内容**：智能体使用 PrimeTime 时序分析反馈诊断 SDC 约束缺陷并生成正确约束修复的能力。

**赛道 ID**：`p7_primetime_sta_debug`

**工具**：PrimeTime（pt_shell）

**评估方式**：基于执行 — TCL 运行脚本通过 PrimeTime 验证约束并发出标记。

## 任务结构

```
pt_sta_debug_NNNN/
  metadata.json
  prompt.md
  files/
    design.v            # RTL 设计（可见，只读）
    constraints.sdc      # 有缺陷的 SDC（可见，可编辑）
    run_public.sh        # 公开运行脚本（可见，只读）
    run_public.tcl       # PrimeTime TCL 脚本（可见，只读）
  hidden/
    design_netlist.v     # 用于 PT 的结构网表（隐藏）
    run_hidden.sh        # 隐藏运行脚本
    run_hidden.tcl       # 隐藏 PrimeTime TCL 脚本
  solution/
    constraints.sdc      # 正确的 SDC
```

## 缺陷类别（4 种可靠类别）

| 缺陷类型 | 描述 | 难度 | 检测方法 |
|----------|------|------|----------|
| missing_clock | 缺失 `create_clock` 定义 | 简单 | `all_clocks` 为空 → `no_clocks_created` |
| wrong_port_name | 端口引用中的拼写错误 | 简单 | 源日志 `Can't find` → `port_or_clock_not_found` |
| syntax_error | SDC 中缺失括号 | 简单 | 源日志 `Error:` → `pt_error_in_source` |
| invalid_get_ports | 不存在的端口模式 | 中等 | 源日志 `Can't find` → `port_or_clock_not_found` |

### 推迟的类别

这些类别曾被考虑但被推迟，因为 PrimeTime 静默接受它们或检测具有不确定性：

- `wrong_period` — PT 接受任何周期值；没有结构性检查能检测
- `missing_input_delay` — PT 接受缺失的延迟
- `missing_output_delay` — PT 接受缺失的延迟
- `false_path_too_broad` — 需要真实的时序数据
- `multicycle_path_error` — 需要真实的时序数据
- `wrong_uncertainty` — PT 接受，仅略微调整数值

## 设计模板

4 个 RTL 模板及对应的结构网表：

| 模板 | 端口 | 描述 |
|------|------|------|
| counter | clk, rst_n, en, count[7:0] | 8 位计数器 |
| fsm_ctrl | clk, rst_n, start, busy, done | FSM 控制器 |
| adder_pipe | clk, rst_n, a[15:0], b[15:0], sum[16:0] | 流水线加法器 |
| mux_reg | clk, rst_n, sel[1:0], d0-d3[7:0], q[7:0] | 多路复用器 + 寄存器 |

## 评分

| 组件 | 权重 | 描述 |
|------|------|------|
| timing_check | 0.6 | TCL 验证标记（TIMING_CHECK_OK / TIMING_CHECK_FAIL） |
| execution_pass | 0.3 | pt_shell 执行成功完成 |
| explanation | 0.1 | 在提交模式下始终为 1.0 |

## TCL 验证脚本

TCL 脚本在导入 SDC 后执行以下检查：

1. 扫描源日志中的 `Error:`、`Can't find`、`unknown command`
2. 验证至少创建了一个时钟（`all_clocks`）
3. 验证预期的时钟名称存在于 `all_clocks` 集合中
4. 验证所有设计端口解析成功（`get_ports`）
5. 验证 `report_timing` 成功（有效的时序图）
6. 发出 `TIMING_CHECK_OK` 或 `TIMING_CHECK_FAIL: <reasons>`

## PrimeTime 集成

- 使用 PrimeTime 能通过 `read_verilog` + `link_design` 读取的结构 Verilog 网表（DFFX1 原语）
- 网表是隐藏文件 — 智能体只能看到 RTL 和 SDC
- Bash 脚本检查 `pt_shell` 是否可用，如果未找到则优雅跳过

## 冒烟测试

```bash
bash scripts/run_primetime_sta_debug_smoke.sh
```

预期结果：
- 解答模式：得分 = 1.0（PrimeTime 可用时）
- 有缺陷模式：得分 < 1.0（仅解释组件通过）
- 如果 PrimeTime 不可用则优雅跳过

## 生成器

```bash
python3 scripts/generate_p7_primetime_sta_debug_tasks.py --count 16 --seed 42
```

使用基于种子的周期变化（2.0、3.0、5.0、10.0 ns）进行确定性生成。
4 种缺陷类型和 4 个 RTL 模板轮询（16 种唯一组合）。

任务 ID 方案：
- 冒烟测试：`pt_sta_debug_0000`（使用 `--id-start 0` 生成）
- 生成任务：`pt_sta_debug_0001` 到 `pt_sta_debug_0016`（默认 `--id-start 1`）
