**[English](p7_spyglass_lint_debug.md) | 中文**

# P7 SpyGlass Lint 调试

## 目标

评估智能体修复 Synopsys SpyGlass 检测到的 RTL lint 违规的能力。

## 测量内容

- 理解导致 lint 违规的常见 RTL 编码错误
- 阅读 SpyGlass lint 输出并识别根本原因的能力
- 修复 RTL 代码以消除 lint 违规同时保持功能的能力

## 任务结构

```
sg_lint_NNNN/
  metadata.json
  prompt.md
  files/
    design.v          # 有缺陷的 RTL（可编辑）
    spyglass.prj      # SpyGlass 项目文件（不可编辑）
    run_public.sh     # 公开测试运行器（不可编辑）
    run_public.tcl    # SpyGlass TCL 脚本（不可编辑）
  hidden/
    run_hidden.sh     # 隐藏测试运行器（不可编辑）
    run_hidden.tcl    # 隐藏 SpyGlass TCL 脚本（不可编辑）
  solution/
    design.v          # 正确的 RTL（零违规）
```

## 缺陷类别

仅包含在 SpyGlass Lint（`lint/lint_rtl` 目标，默认策略）下经验证能产生可靠违规的类别。

| 类别 | 难度 | 描述 | SpyGlass 检测 |
|------|------|------|---------------|
| `latch_inference` | 简单 | 组合 always 块中不完整的 if-else 导致推断锁存器 | 错误 + 警告 |
| `multi_driven` | 中等 | 同一信号在两个 always 块中被赋值 | 错误 + 警告 |
| `blocking_in_seq` | 中等 | 时序 always 块中使用阻塞赋值（=） | 错误 |

### 被拒绝的类别

这些类别经过测试但 SpyGlass 默认 lint **不会**标记：

- `width_mismatch`：SpyGlass 接受且无警告
- `unused_signal`：SpyGlass 接受且无警告
- `undriven_signal`：SpyGlass 接受且无警告
- `missing_default`：SpyGlass 接受且无警告
- `implicit_net`：SpyGlass 接受且无警告

## 评分

```json
{
  "lint_pass": 0.9,
  "explanation": 0.1
}
```

- **lint_pass**：如果 SpyGlass 报告零违规（致命 + 错误 + 警告）则为 1.0，否则为 0.0
- **explanation**：在提交模式下为 1.0（不需要解释）

## 运行脚本行为

1. 检查 `sg_shell` 是否可用（如果不可用则优雅跳过）
2. 运行 `sg_shell -tcl run_public.tcl`，该脚本：
   - 读取 RTL 设计
   - 设置顶层模块
   - 运行 `lint/lint_rtl` 目标
3. 从 SpyGlass 输出中解析"目标违规摘要"
4. 如果零违规则发出 `LINT_PASS`，否则发出 `LINT_FAIL`

## 验证结果

- **SpyGlass 检测**：S-2021.09-SP1 可在 `/EDA/soft2/synopsys/spyglass/` 获取
- **解答模式**：1.00（所有任务通过 lint）
- **有缺陷模式**：0.10（所有任务因违规而 lint 失败）
- **pytest**：35/35 通过
- **冒烟测试**：通过（solution=1.00，buggy=0.10）

## SpyGlass 命令说明

- `sg_shell -tcl <file>` 运行 TCL 启动脚本
- `-project` 和 `-tcl` 互斥
- `current_goal` 之前需要 `set_option top <module>`
- `report_goal` 不是有效命令；结果在目标摘要中
- 违规计数在"目标违规摘要"部分：
  ```
  Reported Messages: 0 Fatals, 1 Errors, 1 Warnings, 3 Infos
  ```
