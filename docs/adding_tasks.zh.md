**[English](adding_tasks.md) | 中文**

# 添加任务

本指南说明如何为 EDA-AgentBench 创建新任务。

## 通用工作流程

1. 创建任务目录结构
2. 编写包含所有必填字段的 `metadata.json`
3. 编写描述任务的 `prompt.md`
4. 创建可见/隐藏/解答文件
5. 验证：解答文件得分为 1.00，缺陷文件得分 < 1.00
6. 运行 `eda-bench validate-task` 检查 schema

## 目录结构

```
task_xxxxxx/
  prompt.md
  metadata.json
  files/           # 对 agent 可见
    ...            # 可编辑的设计文件 + 只读测试文件
  hidden/          # 仅用于评分，agent 看不到
    ...
  solution/        # 正确答案
    ...
```

## P1 RTL 调试任务

### 文件结构

```
task_000042/
  prompt.md
  metadata.json
  files/
    design.sv           # 带缺陷的设计（可编辑）
    tb_public.sv        # 公开测试平台（只读）
    run_public.sh       # 使用公开测试平台运行 VCS（只读）
  hidden/
    tb_hidden.sv        # 隐藏测试平台
    run_hidden.sh       # 使用隐藏测试平台运行 VCS
  solution/
    design.sv           # 正确设计
```

### metadata.json

```json
{
  "task_id": "task_000042",
  "track": "p1_rtl_debug",
  "tool": ["vcs"],
  "difficulty": "easy",
  "data_type": "mutation_synthetic",
  "resource_preset": "fast",
  "timeout_sec": 120,
  "max_tool_calls": 10,
  "max_patch_attempts": 3,
  "max_output_tokens": 16000,
  "files": {
    "visible": ["design.sv", "tb_public.sv", "run_public.sh"],
    "editable": ["design.sv"],
    "hidden": ["tb_hidden.sv", "run_hidden.sh"],
    "forbidden": ["tb_public.sv", "run_public.sh", "tb_hidden.sv", "run_hidden.sh"]
  },
  "run_command": "bash run_public.sh",
  "scoring": {
    "weights": {
      "compile": 0.2,
      "public_test": 0.3,
      "hidden_test": 0.4,
      "explanation": 0.1
    }
  },
  "sanitizer": {"enabled": true},
  "version": "1.0.0"
}
```

### 编写缺陷

从正确的 `design.sv` 出发，注入一个缺陷。支持的缺陷类型：

- `sensitivity_list`：不完整的 `always @(*)` 敏感列表
- `blocking_nonblocking`：`=` 与 `<=` 的错误使用
- `reset_polarity`：高有效与低有效的极性不匹配
- `width_truncation`：端口宽度不匹配导致数据丢失
- `comparison_boundary`：比较操作中的差一错误
- `wrong_mux_select`：不正确的多路复用器 case/select 信号
- `priority_order`：错误的 if-else 优先级
- `fsm_transition_error`：不正确的状态转移
- `counter_off_by_one`：计数器边界错误
- `enable_condition`：缺失或错误的使能条件

### 编写测试平台

- `tb_public.sv`：2-3 个对 agent 可见的测试用例
- `tb_hidden.sv`：1-2 个 agent 永远看不到的测试用例
- 两者都应打印评估器可解析的 PASS/FAIL 计数

### 编写运行脚本

`run_public.sh`：
```bash
#!/bin/bash
set -e
WORK_DIR="$(pwd)"
vcs -full64 -sverilog \
    "$WORK_DIR/design.sv" \
    "$WORK_DIR/tb_public.sv" \
    -o "$WORK_DIR/simv_public" 2>&1
cd "$WORK_DIR" && ./simv_public
```

`run_hidden.sh`：使用 `tb_hidden.sv` 和 `simv_hidden`，其余模式相同。

## P4 SPICE 仿真任务

### 文件结构（HSPICE）

```
hspice_custom_000001/
  prompt.md
  metadata.json
  files/
    circuit.sp          # 带缺陷的网表（可编辑）
    run_public.sh       # 运行 HSPICE，提取测量值
  hidden/
    run_hidden.sh       # 运行隐藏测量
  solution/
    circuit.sp          # 正确网表
```

### 文件结构（Spectre）

```
spectre_custom_000001/
  prompt.md
  metadata.json
  files/
    circuit.scs         # 带缺陷的网表（可编辑）
    run_public.sh       # 运行 Spectre，解析波形
  hidden/
    run_hidden.sh       # 运行隐藏测量
  solution/
    circuit.scs         # 正确网表
```

### metadata.json

```json
{
  "task_id": "task_000100",
  "track": "p4_spice_sim",
  "tool": ["hspice"],
  "difficulty": "easy",
  "data_type": "template_synthetic",
  "resource_preset": "fast",
  "timeout_sec": 120,
  "max_tool_calls": 10,
  "max_patch_attempts": 3,
  "max_output_tokens": 16000,
  "files": {
    "visible": ["circuit.sp", "run_public.sh"],
    "editable": ["circuit.sp"],
    "hidden": ["run_hidden.sh"],
    "forbidden": ["run_public.sh", "run_hidden.sh"]
  },
  "run_command": "bash run_public.sh",
  "scoring": {
    "weights": {
      "tool_run": 0.3,
      "output_generated": 0.2,
      "public_metric": 0.2,
      "hidden_metric": 0.2,
      "explanation": 0.1
    },
    "evaluator": "spice_sim.SPICESimEvaluator",
    "metrics": {
      "public": {"measure": "tdrise", "min": 8e-9, "max": 15e-9},
      "hidden": {"measure": "tdfall", "min": 8e-9, "max": 15e-9}
    }
  },
  "sanitizer": {"enabled": true},
  "version": "1.0.0"
}
```

### 编写 SPICE 运行脚本

HSPICE 运行脚本应当：

1. 运行 `hspice -i circuit.sp -o <prefix>`
2. 评估器解析 `.lis` 文件中的 `.measure` 结果

Spectre 运行脚本应当：

1. 运行 `spectre circuit.scs +escchars +log spectre.out -format nutascii`
2. 使用 Python 解析 `.raw` 波形文件
3. 将结果写入 `metrics.json`

参见 `tasks/p4_spice_sim/` 中已有任务的参考实现。

## 使用生成器

批量生成请使用生成器脚本：

```bash
# 生成 100 个 P1 任务
python scripts/generate_p1_tasks.py --count 100 --seed 42

# 生成 10 个 P4 任务（5 个 HSPICE + 5 个 Spectre）
python scripts/generate_p4_spice_tasks.py --count 10 --seed 42
```

生成器确保：

- 基于种子的确定性输出
- 缺陷类型/配置的均衡分布
- 通过 schema 验证的有效 metadata
- 正确解答文件得分为 1.00

## 验证清单

提交新任务前请确认：

1. `eda-bench validate-task <task_dir>` 通过
2. `eda-bench evaluate-task <task_dir> --submission <task_dir>/solution` 得分为 1.00
3. `eda-bench evaluate-task <task_dir> --submission <task_dir>/files` 得分 < 1.00
4. 评估后所有禁止文件保持不变（防作弊通过）
5. 任务 ID 唯一（与已有任务无冲突）
6. 任务目录中无工具生成的中间文件（`.o`、`.log`、`simv` 等）
