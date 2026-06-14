**[English](scoring.md) | 中文**

# 评分规则

## 分数结构

每次评估生成一个 `score.json`：

```json
{
  "schema_version": "1.0.0",
  "task_id": "task_000001",
  "track": "p1_rtl_debug",
  "mode": "submission",
  "total_score": 0.78,
  "max_possible": 1.0,
  "objective_score": 0.69,
  "explanation_score": 0.09,
  "passed": true,
  "passing_threshold": 0.5,
  "components": [...],
  "anti_cheat": {...},
  "resource_usage": {...}
}
```

## 分数组件

### total_score

所有加权组件分数之和。范围：[0.0, 1.0]。

### objective_score

所有非解释组件分数之和。这是主要指标。

### explanation_score

来自 `explanation` 组件的分数。仅在使用 LLM 评估的智能体模式下有意义。在提交模式下默认为 1.0。

### 通过阈值

`passed = total_score >= 0.5`

这是一个二元标志。它并不定义"正确"与"缺陷"——见下文。

## P1 RTL 调试评分

组件：

| 组件 | 权重 | 衡量内容 |
|------|------|----------|
| compile | 0.2 | 设计使用 VCS 编译无错误 |
| public_test | 0.3 | 公开测试平台通过所有用例 |
| hidden_test | 0.4 | 隐藏测试平台通过所有用例 |
| explanation | 0.1 | 智能体对修复的解释（LLM 评判，默认 1.0） |

**评估逻辑：**

- `compile`：检查 VCS 退出码和日志中的错误
- `public_test`：解析公开测试日志中的通过/失败计数
- `hidden_test`：解析隐藏测试日志中的通过/失败计数
- `explanation`：保留用于 LLM 评估；在提交模式下返回 1.0

## P4 SPICE 仿真评分

组件：

| 组件 | 权重 | 衡量内容 |
|------|------|----------|
| tool_run | 0.3 | EDA 工具（HSPICE/Spectre）运行无致命错误 |
| output_generated | 0.2 | 仿真产生了输出（波形/测量值） |
| public_metric | 0.2 | 公开测量值在规格范围内 |
| hidden_metric | 0.2 | 隐藏测量值在规格范围内 |
| explanation | 0.1 | 智能体的解释（默认 1.0） |

**评估逻辑：**

- `tool_run`：要求有明确的完成标志且无错误（HSPICE：`job concluded`；Spectre：`spectre completes with 0 errors`）。工具缺失/崩溃/超时一律判 0。
- `output_generated`：检查输出中的测量值（HSPICE：`.lis`；Spectre：`metrics.json`）
- `public_metric`：检查公开测量值（如 `tdrise`）是否在 `[min, max]` 范围内
- `hidden_metric`：检查隐藏测量值（如 `tdfall`）是否在 `[min, max]` 范围内

**指标提取：**

- HSPICE：解析 `.lis` 文件中的 `.measure` 结果，支持工程后缀（如 `1.234n`）
- Spectre：读取运行脚本写入的 `metrics.json`，该脚本解析 `-format nutascii` 波形输出

## 缺陷基线语义

**缺陷基线的正确判据是 `total_score < 1.0`。**

不要与通过阈值（0.5）混淆。有缺陷的设计如果部分可用，分数仍可能高于 0.5。关键属性是：

- 解答必须得分**恰好为 1.00**
- 缺陷基线必须得分**严格低于 1.00**

数据集评估跟踪 `buggy_lower_than_solution_count`：缺陷模式得分低于解答模式的任务数量。对于设计良好的基准，这应等于总任务数。

## 提交模式下的解释分数

在提交/工作空间模式（v0）中，智能体在评估期间不生成解释。`explanation` 组件默认 `raw_score = 1.0`，将其全部权重贡献给总分。

这意味着：

- 提交模式下的完美解答应得 1.00
- 解释组件不会惩罚提交模式的评估
- 在未来的智能体模式中，解释评分将由 LLM 评判

## 自定义权重

任务可以通过 `metadata.scoring.weights` 覆盖默认权重。唯一的约束是权重之和必须为 1.0。未在权重中列出的组件不会被评估。
