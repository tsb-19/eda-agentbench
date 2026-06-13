**[English](p6_dc_synthesis_qa.md) | 中文**

# P6 DC 综合报告问答

## 概述

P6 是一个面向 Design Compiler 综合报告的报告问答赛道。给定一份净化后的综合报告，任务是回答关于综合指标的精确问题。

**不需要执行 EDA 工具。** 答案通过基于解析器的合成报告提取进行验证。

## 任务目录结构

与 P3 时序报告问答相同：

```
p6_dc_syn_NNNNNN/
  prompt.md
  metadata.json
  files/
    synthesis_report.rpt   # 只读综合报告
    answer.txt             # 可编辑，空占位符
  hidden/                  # 空
  solution/
    answer.txt             # 预期答案
```

## 问题类型（10 种）

| 类型 | 答案 | 示例 |
|------|------|------|
| `total_area` | 数值（容差=0.01） | 21250.75 |
| `combinational_area` | 数值（容差=0.01） | 12500.50 |
| `sequential_area` | 数值（容差=0.01） | 8750.25 |
| `cell_count` | 数值（精确） | 3500 |
| `register_count` | 数值（精确） | 1200 |
| `top_module` | 字符串 | alu_top |
| `worst_slack` | 数值（容差=0.01） | -0.1500 |
| `compile_status` | 字符串 | 0 errors, 3 warnings |
| `clock_period` | 数值（容差=0.01） | 10.0000 |
| `warning_count` | 数值（精确） | 3 |

## 评分

单一组件：`answer_match`（权重 1.0）

- 数值答案：相对容差（默认 1%）
- 字符串答案：不区分大小写，标准化空白

## 生成器

`generators/p6_dc_synthesis_qa_gen.py`

- 确定性种子（默认 42）
- 50 个模块名称，30 个时钟名称
- 10 种问题类型轮询
- 每 50 个任务批次中每种问题类型 5 个

## 解析器

`eda_agentbench/synthesis/dc_report_parser.py`

提取：顶层模块、面积分解、单元/寄存器计数、时序、编译状态、警告/错误计数。

## 评估器

`eda_agentbench/evaluator/dc_synthesis_qa.py`

复用与 P3 TimingReportQAEvaluator 相同的答案匹配逻辑。

## 当前规模

- 冒烟测试：1 个任务（`p6_dc_syn_000000`）
- 生成任务：50 个
- 总计：51 个任务

## DC 检测

DC（`dc_shell`）会被检测但评估不需要。冒烟测试会报告 DC 是否可用。
