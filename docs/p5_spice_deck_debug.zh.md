**[English](p5_spice_deck_debug.md) | 中文**

# P5：SPICE 网表调试

## P5 测量内容

P5 评估智能体诊断和修复 SPICE 仿真网表中语法/结构错误的能力。与 P4（测试基于指标的电路优化）不同，P5 专注于**调试无法运行的破损网表**。

每个任务提供一个被 HSPICE 拒绝的有缺陷 `.sp` 文件。智能体必须识别错误并生成一个 HSPICE 能成功执行的修正网表。

## P5 与 P4 SPICE 仿真的区别

| 方面 | P4 SPICE 仿真 | P5 SPICE 网表调试 |
|------|---------------|-------------------|
| 目标 | 优化电路指标（上升时间等） | 修复语法/结构错误 |
| 缺陷类型 | 错误的元件值 | 缺失模型、错误引脚、重复等 |
| 评分 | 基于指标（容差范围） | 基于执行（退出码 + 无致命错误） |
| 需要标准答案 | 是（目标值） | 否（接受任何有效的修复） |
| 精确差异 | 不适用 | 不要求 |

## 外部包来源

P5 任务从兄弟仓库导入：

```
../eda-bench-prototypes/tasks_eval_private/
```

此包在外部生成和验证。主基准通过以下命令以只读方式导入：

```
python3 scripts/import_p5_tasks.py
```

导入过程将外部元数据转换为主 schema，同时保留 `grader_contract.json`、`visible/`、`hidden/`、`oracle/` 和 `validation/` 目录。

## 任务结构

每个导入的 P5 任务具有以下布局：

```
spice_deck_debug_NNNN/
  metadata.json           # 主 schema 格式
  prompt.md               # 任务描述
  grader_contract.json    # 基于执行的评分规则
  visible/
    *_bug.sp              # 有缺陷的网表（智能体可编辑）
  hidden/
    *_fixed.sp            # 黄金修正网表（用于解答模式）
  oracle/
    answer.md             # 人类可读的预期修复
  validation/
    validation_record.json
    normalized_errors.json
    raw_log.sha256
```

## 基于执行的评分

P5 使用**基于执行的**评分，而非精确差异匹配：

1. 在提交的网表上运行 HSPICE
2. 检查退出码 == 0
3. 检查 `grader_contract.json` 中无致命错误模式
4. 两个条件都满足则通过

任何 HSPICE 能执行的语法有效修复都会被接受，即使它与标准答案不同。

## 评分权重

```json
{
  "execution_pass": 0.9,
  "explanation": 0.1
}
```

## 错误类别

100 个导入的任务涵盖以下错误类别：

| 类别 | 数量 | 描述 |
|------|------|------|
| missing_model | 15 | 引用了未定义的 MOSFET/二极管模型 |
| duplicate_element | 15 | 两个元件共享同一名称 |
| missing_subckt | 14 | 引用了未定义的子电路 |
| wrong_pin_count | 14 | 子电路实例引脚数量错误 |
| missing_include | 14 | .include 引用了不存在的文件 |
| unsupported_dialect | 14 | HSPICE 不支持的模型级别 |
| invalid_directive | 14 | 格式错误的 .include（无文件名） |

## 运行 P5

### 验证任务

```bash
eda-bench validate-task tasks/p5_spice_deck_debug/imported/spice_deck_debug_0001
```

### 评估单个任务

```bash
eda-bench evaluate-task tasks/p5_spice_deck_debug/imported/spice_deck_debug_0001 \
  --submission <submission_dir>
```

### 批量评估

```bash
bash scripts/evaluate_p5_spice_deck_debug.sh
```

预期：100/100 解答通过，100/100 有缺陷版本失败。

### 数据集评估

```bash
eda-bench evaluate-dataset tasks --track p5_spice_deck_debug --submission-mode solution
eda-bench evaluate-dataset tasks --track p5_spice_deck_debug --submission-mode buggy
```

## 为什么不要求精确差异

SPICE 网表可以通过多种有效方式修复。例如，缺失的模型可以添加在：

- 引用它的元件之前
- 元件之后（HSPICE 解析前向引用）
- 使用不同的空白或注释

所有产生退出码 0 且无致命错误的有效修复都获得相同的分数。这测试的是智能体产生**功能正确**输出的能力，而非记忆特定答案的能力。

## 公开包与私有包

`../eda-bench-prototypes/tasks_eval_private/` 处的外部包是**私有评估包**。它包含：

- 有缺陷的网表（对智能体可见）
- 修正的网表（隐藏，用于解答模式评估）
- 标准答案（用于人工审查）
- 验证记录（调试对比验证）

公开发布包（包含任务子集）可能会单独发布。导入脚本可以处理任一包。
