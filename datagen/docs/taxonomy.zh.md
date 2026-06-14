**[English](taxonomy.md) | 中文**

# 任务分类体系

> **范围：** 本模块仅负责 `spice_deck_debug` 领域。早期的 `rtl_debug` 和
> `timing_report_qa` 原型领域已退役 —— RTL 调试与时序报告问答任务直接由父仓库的
> `generators/`（赛道 p1/p3）生成。退役说明见 `CLAUDE.md`。

## 命名规范

任务 ID 遵循模式：`<domain>_NNNN`

其中：
- `domain` 为 `spice_deck_debug`
- `NNNN` 为 4 位零填充数字（0001、0002、..., 0100）

示例：
- `spice_deck_debug_0001`
- `spice_deck_debug_0100`

任务目录中的文件名包含完整的 task_id 前缀：
- `visible/spice_deck_debug_0001_bug.sp`
- `hidden/spice_deck_debug_0001_fixed.sp`

## 领域

### spice_deck_debug
涉及调试 SPICE 电路仿真网表的任务。

**任务族：**
- `syntax_error` — 格式错误的 SPICE 语法（缺少节点、错误值）
- `convergence_issue` — 仿真收敛失败
- `wrong_topology` — 错误的电路拓扑或连接
- `parameter_error` — 错误的元件值或模型参数
- `missing_ground` — 缺少或错误的接地参考

**SPICE 错误类别（验证期间观察到）：**

| 类别 | HSPICE 可捕获 | 示例 |
|------|--------------|------|
| `missing_model` | 是 | `Definition of model/subckt "pmos_typo" is not found` |
| `missing_subckt` | 是 | `Definition of model/subckt "buf" is not found`（X 元件） |
| `wrong_pin_count` | 是 | `Number of nodes mismatch between instance "x1" and subcircuit "inv"` |
| `duplicate_element` | 是 | `attempts to redefine r1` |
| `missing_include` | 是 | `unable to open file "nonexistent.lib"` |
| `unsupported_dialect` | 是 | `Invalid model level 99` |
| `invalid_directive` | 是 | `.include` 无文件名 -> `syntax error` |
| `floating_node` | 仅警告 | HSPICE 发出警告但不中止 |
| `convergence_failure` | 仅警告 | HSPICE 通常收敛或警告，极少中止 |
| `invalid_measure` | 仅警告 | `.measure` 错误为警告，非致命 |
| `unknown` | 视情况而定 | 未分类错误的兜底类别 |

**注意：** `floating_node`、`convergence_failure` 和 `invalid_measure` 会产生 HSPICE 警告但不会导致仿真中止（退出码 != 0）。对于调试对比验证，这些类别使用可被 HSPICE 捕获的替代缺陷，以测试相同的电路拓扑。请参阅任务元数据 `notes` 字段了解映射关系。

## 难度等级

| 等级   | 描述 |
|--------|------|
| `easy`  | 单一明显错误，直接修复 |
| `medium` | 多个交互问题或非明显根因 |
| `hard`  | 需要深入领域知识，存在微妙的交互关系 |
