**[English](task_schema.md) | 中文**

# 任务 Schema 参考

每个任务是一个包含 `metadata.json`、`prompt.md` 和支持文件的目录。本文档描述 `metadata.json` 的字段。

## 必需字段

### task_id

- 类型：`string`
- 模式：`^task_[0-9]{6}$`
- 示例：`"task_000001"`

任务的唯一标识符。六位数字，零填充。

### track

- 类型：`string`
- 允许值：`p1_rtl_debug`、`p2_rtl_gen`、`p2_tb_sva_gen`、`p3_timing_report_qa`、`p4_spice_sim`、`p5_spice_deck_debug`、`p6_lint`、`p7_physical`

该任务所属的基准轨道。

### tool

- 类型：`array of strings`
- 最少项数：1
- 允许值：`vcs`、`xcelium`、`hspice`、`spectre`、`dc`、`pt`、`spyglass`、`icc2`、`innovus`、`starrc`、`sentaurus`、`verdi`

评估该任务所需的 EDA 工具。

### difficulty

- 类型：`string`
- 允许值：`easy`、`medium`、`hard`、`expert`

任务难度级别。

### data_type

- 类型：`string`
- 允许值：`template_synthetic`、`mutation_synthetic`、`flow_synthetic`

任务的生成方式：

- `template_synthetic`：从受控模板生成
- `mutation_synthetic`：向正确设计注入缺陷
- `flow_synthetic`：通过运行真实 EDA 工具生成

### resource_preset

- 类型：`string`
- 允许值：`fast`、`standard`、`expert`

智能体评估的资源限制：

| 预设 | 墙钟时间 | 工具调用 | 补丁 | 输出 token |
|------|----------|----------|------|------------|
| fast | 60 秒 | 10 | 3 | 16000 |
| standard | 300 秒 | 30 | 8 | 32000 |
| expert | 900 秒 | 80 | 15 | 64000 |

### timeout_sec

- 类型：`integer`
- 范围：1--3600

最大评估时间（秒）。

### max_tool_calls

- 类型：`integer`
- 范围：1--200

最大工具调用次数（智能体模式）。

### max_patch_attempts

- 类型：`integer`
- 范围：1--50

最大文件编辑尝试次数（智能体模式）。

### max_output_tokens

- 类型：`integer`
- 范围：1000--200000

智能体可生成的最大 token 数。

### run_command

- 类型：`string`

执行公开测试的 shell 命令。示例：`"bash run_public.sh"`。

### files

- 类型：`object`
- 必需子字段：`visible`、`editable`、`hidden`、`forbidden`

文件可见性和可编辑性声明：

```json
{
  "visible": ["design.sv", "tb_public.sv", "run_public.sh"],
  "editable": ["design.sv"],
  "hidden": ["tb_hidden.sv", "run_hidden.sh"],
  "forbidden": ["tb_public.sv", "run_public.sh", "tb_hidden.sv", "run_hidden.sh"]
}
```

约束：

- `editable` 必须是 `visible` 的子集
- `hidden` 不得与 `visible` 重叠
- `forbidden` 必须是 `visible + hidden` 的子集

### scoring

- 类型：`object`
- 必需子字段：`weights`

```json
{
  "weights": {
    "compile": 0.2,
    "public_test": 0.3,
    "hidden_test": 0.4,
    "explanation": 0.1
  },
  "evaluator": "rtl_debug.VCSRTLEvaluator",
  "explanation_weight": 0.1,
  "metrics": {
    "public": {"measure": "tdrise", "min": 8e-9, "max": 15e-9},
    "hidden": {"measure": "tdfall", "min": 8e-9, "max": 15e-9}
  }
}
```

- `weights`：将组件名称映射到浮点权重。总和必须为 1.0（容差 0.01）。
- `evaluator`：评估器的 Python 类路径。默认为 `"rtl_debug.VCSRTLEvaluator"`。
- `explanation_weight`：浮点数 0--0.2，用于 LLM 评判的解释评分。
- `metrics`：（仅 P4/时序）定义预期测量范围。

## 可选字段

### sanitizer

```json
{"enabled": true}
```

是否为此任务启用日志清洗。

### generator

```json
{
  "script": "p1_rtl_debug_gen.py",
  "seed": 42,
  "config_index": 0,
  "bug_type": "sensitivity_list"
}
```

生成器来源：哪个脚本、种子和参数生成了该任务。支持确定性重新生成。

### version

- 类型：`string`
- 示例：`"1.0.0"`

任务格式版本。

## 验证规则

`eda-bench validate-task` 检查：

1. 所有必需字段存在
2. `task_id` 匹配模式
3. 评分权重总和为 1.0
4. `editable` 是 `visible` 的子集
5. `hidden` 与 `visible` 不相交
6. `forbidden` 是 `visible + hidden` 的子集
7. 所有声明的文件存在于磁盘上
8. 解答目录存在
