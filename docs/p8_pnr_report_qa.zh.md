**[English](p8_pnr_report_qa.md) | 中文**

# P8 PnR 报告问答

## 概述

P8 PnR 报告问答是一个面向物理实现报告的报告问答赛道。给定合成的 ICC2 格式或 Innovus 格式 PnR 报告，智能体回答精确的物理设计问题。

**这是报告问答，而非执行调试。** 报告是合成/净化的。pytest 不需要 ICC2/Innovus 许可证。

## 任务结构

每个任务包含：
- `report.txt`：合成的 PnR 报告（可见，禁止修改）
- `prompt.md`：要回答的问题（可见，禁止修改）
- `answer.txt`：智能体填写 JSON 答案（可见，可编辑）
- `solution/answer.txt`：标准答案（对智能体隐藏）

## 问题类型

| 类别 | 字段 |
|------|------|
| 时序 | setup_wns, setup_tns, setup_violations, hold_wns, hold_tns, hold_violations, worst_endpoint, worst_startpoint, timing_met |
| 利用率 | core_utilization, placement_density, instance_count, sequential_count |
| 面积 | cell_area, macro_area, total_cell_area, buffer_count |
| 拥塞 | max_horizontal_overflow, max_vertical_overflow, total_overflow, congested_bins, worst_congestion_layer, congestion_pass |
| 布线 | total_wirelength, drc_total, shorts, opens, antenna_violations, route_completed |
| 功耗 | internal_power, switching_power, leakage_power, total_power |
| 流程状态 | stage, tool_family, design_name |

## 评分

- **answer_match**（0.9）：字符串/整数精确匹配，浮点数 2% 容差，布尔值精确匹配
- **explanation**（0.1）：在提交模式下默认为 1.0

## 工具族

- **ICC2 格式**：使用 `:` 分隔符，ICC2 头部的报告
- **Innovus 格式**：使用 `=` 分隔符，Innovus 头部的报告

## 数据集规模

- 冒烟测试：1 个任务
- 生成任务：100 个
- 总计：101 个任务
- ICC2：约 45 个任务，Innovus：约 56 个任务

## 验证

```bash
# 运行 P8 测试
pytest tests/test_p8_pnr_report_qa.py -v

# 运行冒烟测试
bash scripts/run_pnr_report_qa_smoke.sh

# 评估所有 P8 任务
eda-bench evaluate-dataset tasks --track p8_pnr_report_qa --submission-mode solution
eda-bench evaluate-dataset tasks --track p8_pnr_report_qa --submission-mode buggy
```

## 已知限制

- 报告是合成的，不是来自真实的 ICC2/Innovus 运行
- 仅涵盖基本的 PnR 指标
- 没有布局可视化或 GDSII 解析
- 解析器能处理 `:` 和 `=` 分隔符，但可能无法覆盖所有报告变体
