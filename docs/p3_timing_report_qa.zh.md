**[English](p3_timing_report_qa.md) | 中文**

# P3 时序报告问答

## 概述

P3 时序报告问答赛道评估智能体能否阅读 STA 格式的时序报告并回答精确的量化问题。

## 任务概念

给定：
- 一份标准化的 PrimeTime/OpenSTA 格式时序报告
- 一个自然语言问题

模型应能回答以下事实：
- WNS（最差负裕量）
- TNS（总负裕量）
- 违规路径数量
- 最差起点 / 终点
- 路径组 / 时钟名称
- 所需时间 / 到达时间
- 指定命名路径的裕量

## 问题类型

| 类型 | 描述 | 答案类型 | 难度 |
|------|------|----------|------|
| `wns` | 最差负裕量 | 数值 | 简单 |
| `tns` | 总负裕量 | 数值 | 简单 |
| `violating_paths` | 负裕量路径计数 | 数值 | 简单 |
| `worst_endpoint` | 最差路径的终点 | 字符串 | 中等 |
| `worst_startpoint` | 最差路径的起点 | 字符串 | 中等 |
| `path_group` | 最差路径的路径组 | 字符串 | 中等 |
| `clock_name` | 最差路径的时钟 | 字符串 | 中等 |
| `required_time` | 最差路径的所需时间 | 数值 | 困难 |
| `arrival_time` | 最差路径的到达时间 | 数值 | 困难 |
| `slack_of_named_path` | 指定命名路径的裕量 | 数值 | 困难 |

## 评分

- 数值答案：基于容差的匹配（默认 1% 相对容差）
- 字符串答案：精确标准化匹配（不区分大小写，去除空白）
- 正确得 1.00 分，否则得 0.00 分

## 任务结构

```
tasks/p3_timing_report_qa/
  smoke/                          # 手工制作的冒烟任务
    files/timing_report.rpt       # 时序报告（可见）
    solution/answer.txt           # 正确答案
    prompt.md                     # 问题提示
    metadata.json                 # 任务元数据
  generated/                      # 生成的任务
    p3_timing_000001/ ... p3_timing_000999
```

注意：生成的任务 ID 从 000001 开始，以避免与冒烟任务（p3_timing_000000）冲突。

## 生成

```bash
python3 scripts/generate_p3_tasks.py --count 999 --seed 42
```

选项：
- `--count`：生成任务数量（默认：100）
- `--seed`：随机种子（默认：42）
- `--output-dir`：输出目录（默认：`tasks/p3_timing_report_qa/generated`）

## 冒烟测试

```bash
bash scripts/run_p3_smoke.sh
```

## PrimeTime 原型（阶段 5E）

一小组基于真实或手工制作的 PrimeTime 报告的原型任务。
存储在 `tasks/p3_timing_report_qa/pt_prototype/` 下（8 个任务，ID 900000-900007）。

这些任务使用与合成 P3 任务相同的 schema、评估器和解析器。
区别在于报告包含真实的 PrimeTime 信息行，
并在存储前通过 `LogSanitizer` 进行了净化。

### 生成

```bash
# 手工制作（不需要 PrimeTime）
python3 scripts/generate_pt_report_prototypes.py --mode handcrafted --seed 42

# 真实 PrimeTime（需要 pt_shell）
python3 scripts/generate_pt_report_prototypes.py --mode real --seed 42
```

### 冒烟测试

```bash
bash scripts/run_pt_report_smoke.sh
```

冒烟脚本会检查 PrimeTime 是否可用，如果不可用则优雅跳过。

### 涵盖的问题类型

| 索引 | 场景 | 问题类型 |
|------|------|----------|
| 900000 | 简单的寄存器到寄存器建立路径 | wns |
| 900001 | 多路径，3 条违规 | tns |
| 900002 | 组合逻辑输入到寄存器路径 | worst_endpoint |
| 900003 | 时钟域交叉 | worst_startpoint |
| 900004 | 保持时间违规路径 | violating_paths |
| 900005 | 寄存器到输出路径组 | path_group |
| 900006 | 多时钟设计 | clock_name |
| 900007 | 深度组合逻辑路径 | arrival_time |

## 范围

- 合成任务不需要调用 PrimeTime（仅使用合成的标准化报告）
- 1 个冒烟任务 + 999 个生成任务（共 1000 个合成任务）
- 8 个 PrimeTime 原型任务（900000-900007，手工制作或真实 PT 支持）
- P3 任务总计 1008 个
- 10 种问题类型，轮询分配（每种 99-100 个）
- 30 个唯一时钟，15 个路径组，约 30% 多时钟报告
- 路径计数 3-50，WNS 范围 -5.0 到 -0.01，TNS 范围 -75 到 -0.3
- 信号名称具有层次深度和可选位索引
- 使用种子确定性生成
- 完整解答评估：1000/1000 = 1.00
