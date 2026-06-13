**[English](reproducibility.md) | 中文**

# 可复现性

## 概述

EDA-AgentBench 中的每个任务都设计为可复现的。本文档描述了确保确定性任务生成、一致评估和可验证结果的机制。

## 确定性任务生成

### 生成器

P1 和 P4 任务由生成器脚本生成：

- `scripts/generate_p1_tasks.py`——生成 P1 RTL 调试任务
- `scripts/generate_p4_spice_tasks.py`——生成 P4 SPICE 仿真任务

两个生成器都接受 `--seed` 参数以实现确定性输出：

```bash
python scripts/generate_p1_tasks.py --count 100 --seed 42
python scripts/generate_p4_spice_tasks.py --count 10 --seed 42
```

给定相同的种子，生成器产生相同的任务。每个任务的 `metadata.json` 记录了生成器脚本、种子和使用的参数：

```json
{
  "generator": {
    "script": "p1_rtl_debug_gen.py",
    "seed": 42,
    "config_index": 0,
    "bug_type": "sensitivity_list"
  }
}
```

### P5 导入

P5 任务通过 `scripts/import_p5_tasks.py` 从外部包导入。导入是从兄弟仓库 `../eda-bench-prototypes/tasks_eval_private/` 的只读副本。主仓库不修改外部包。

## 评估模式

每个任务支持两种提交模式用于验证和校准：

### 解答模式

使用任务的 `solution/` 目录作为智能体的提交。这验证了正确答案始终产生满分：

```
eda-bench evaluate-dataset tasks --submission-mode solution
```

**预期**：所有任务得分恰好为 1.00。

### 缺陷模式

使用任务的可见/可编辑文件（存在缺陷的原始文件）作为提交。这验证了基线缺陷始终产生低于满分的分数：

```
eda-bench evaluate-dataset tasks --submission-mode buggy
```

**预期**：所有任务得分严格低于 1.00。

### 校准属性

对于校准良好的基准：

- 每个任务的 `solution_score == 1.0`
- 每个任务的 `buggy_score < 1.0`
- 每个任务的 `buggy_score < solution_score`

数据集评估脚本跟踪 `buggy_lower_than_solution_count` 以验证此属性在所有任务中成立。

## 冒烟测试

冒烟测试验证每条轨道的端到端评估流水线：

| 脚本 | 测试内容 |
|------|----------|
| `scripts/run_smoke.sh` | P1 RTL 调试：编译、公开测试、隐藏测试 |
| `scripts/run_spice_smoke.sh` | P4 HSPICE：工具运行、指标提取 |
| `scripts/run_spectre_smoke.sh` | P4 Spectre：工具运行、指标提取 |
| `scripts/run_pt_report_smoke.sh` | P3 PT 原型：手工制作任务生成、验证、评分（如果 PT 不可用则跳过） |
| `scripts/evaluate_dataset_smoke.sh` | 所有轨道：在小子集上运行解答和缺陷模式 |

运行所有冒烟测试：

```bash
bash scripts/run_smoke.sh
bash scripts/run_spice_smoke.sh
bash scripts/run_spectre_smoke.sh
bash scripts/evaluate_dataset_smoke.sh
```

## 数据集评估脚本

| 脚本 | 用途 |
|------|------|
| `scripts/evaluate_dataset_smoke.sh` | 所有轨道的快速冒烟测试（小子集） |
| `scripts/evaluate_dataset_fast.sh` | 快速采样评估（所有轨道，约 2 分钟） |
| `scripts/evaluate_p1_generated.sh` | 完整的 P1 生成任务评估 |
| `scripts/evaluate_p5_spice_deck_debug.sh` | 完整的 P5 评估 |
| `scripts/evaluate_large_dataset.sh` | 完整数据集评估（所有轨道） |

## 采样评估

对于快速集成检查，CLI 支持采样评估：

```bash
# 每条轨道采样 N 个任务（使用种子确定性选择）
eda-bench evaluate-dataset tasks --sample-per-track 1 --seed 42 --submission-mode solution

# 评估最多 N 个任务
eda-bench evaluate-dataset tasks --limit 10 --seed 42 --submission-mode solution
```

采样评估是确定性的：相同的种子和任务树始终产生相同的选择。摘要 JSON 包含 `sampled: true`、`seed`、`total_candidates` 和 `selected_task_ids` 以保证透明性。

**警告：** 采样评估不能替代完整评估。开发期间用于快速迭代；最终验证前请运行完整评估。

## 防作弊验证

评估器在执行前对所有禁止文件进行 SHA-256 哈希快照，并在执行后重新计算。如果任何哈希值不同，评估将失败。这确保：

- 智能体不能修改测试平台以强制通过
- 智能体不能修改评分脚本
- 智能体不能修改隐藏测试基础设施

## 日志清洗

所有 EDA 工具输出在存储前都会被清洗。清洗器替换：

- 用户名 → `<USER>`
- 主机名 → `<HOST>`
- 绝对路径 → `<PROJECT_ROOT>`、`<EDA_ROOT>`
- 许可服务器 → `<LICENSE_SERVER>`
- 机器名 → `<HOST>`

这确保评估日志可以共享而不会泄露环境详情。

## 环境检测

基准在运行时探测文件系统以查找 EDA 工具。任务定义中不存储硬编码路径。`eda-bench detect-tools` 命令报告哪些工具可用：

```bash
eda-bench detect-tools
```

预期路径（探测而非硬编码）：
- Synopsys：`/EDA/soft2/synopsys/`
- Cadence：`/EDA/soft2/cadence/`

## 复现特定评估

要复现评估结果：

1. 安装基准：`pip install -e ".[test]"`
2. 检测工具：`eda-bench detect-tools`
3. 运行冒烟测试以验证工具可用性
4. 评估特定任务：
   ```bash
   eda-bench evaluate-task tasks/<track>/<task_id> \
     --submission tasks/<track>/<task_id>/solution
   ```
5. 将 `score.json` 输出与预期结果进行比较

## 版本管理

每个任务的 `metadata.json` 包含 `version` 字段（当前为 `"1.0.0"`）。基准包版本在 `pyproject.toml` 中（当前为 `0.1.0`）。

## 基准清单导出

可以从任务元数据生成确定性的清单和摘要：

```bash
python scripts/export_benchmark_summary.py
```

这会在 `reports/` 下生成所有报告产物（任务清单、轨道/工具/评分分布、每条轨道的明细、排行榜模板和 markdown 摘要）。输出完全确定——在同一任务树上运行两次会产生相同的文件。

## 基线套件

基线运行器自动化运行解答和缺陷基线并生成排行榜产物：

```bash
# 采样基线（快速，约 2 分钟）
python scripts/run_baseline_suite.py --sample-per-track 1 --seed 123

# 完整基线（需要所有 EDA 工具）
python scripts/run_baseline_suite.py

# 单条轨道，单个模式
python scripts/run_baseline_suite.py --track p3_timing_report_qa --modes solution --sample-per-track 5
```

### CLI 标志

| 标志 | 默认值 | 描述 |
|------|--------|------|
| `--modes` | `solution,buggy` | 要运行的逗号分隔模式 |
| `--track` | 全部 | 过滤到单条轨道 |
| `--sample-per-track` | 完整 | 每条轨道采样 N 个任务 |
| `--seed` | 42 | 确定性采样种子 |
| `--timeout` | 任务默认值 | 覆盖每个任务的超时时间 |
| `--tasks-root` | `tasks/` | 覆盖任务目录 |

### 输出产物

| 文件 | 描述 |
|------|------|
| `reports/baseline_results_solution.csv` | 解答模式的每个任务得分 |
| `reports/baseline_results_buggy.csv` | 缺陷模式的每个任务得分 |
| `reports/leaderboard_baseline_filled.csv` | 包含基例行的排行榜模板 |
| `reports/baseline_summary.md` | 包含表格的人类可读摘要 |

### 基线解读

| 模式 | 预期平均分 | 预期通过率 | 用途 |
|------|-----------|-----------|------|
| 解答 | 1.00 | 1.00 | 上限：验证评估流水线 |
| 缺陷 | < 1.00 | < 1.00 | 下限：验证区分能力 |

任何真实 LLM 提交的分数应在缺陷基线和解答基线之间。
不会调用外部模型 API——所有评估都是本地且确定性的。

## 智能体运行的可复现性

智能体运行（`run-agent`、`run-agent-dataset`）在智能体命令确定且任务树未更改时是可复现的。输出包括：

- `workspace_manifest.json`：智能体运行前后智能体可见文件的 SHA-256
- `modified_files.json`：文件变更的精确列表
- `transcript.jsonl`：完整的智能体输出（标准输出、标准错误、事件）
- `metadata.json`：智能体命令、超时、任务元数据

### 安全模型

智能体运行器使用两阶段工作空间模型：

1. **智能体工作空间**：仅包含可见+可编辑文件。没有隐藏/预言/评分文件。
2. **评估器工作空间**：在智能体退出后创建，合并智能体编辑 + 来自任务根目录的隐藏文件。

隐藏/预言文件永远不会被智能体进程读取。`workspace_manifest.json` 仅包含智能体可见文件。

要复现智能体结果：

```bash
eda-bench run-agent tasks/<track>/<task_id> --agent-cmd "YOUR_COMMAND"
```

分数取决于智能体的编辑和任务的评估器。对于问答任务（P3、P6 问答），不需要 EDA 工具，因此结果在不同机器间完全确定。对于基于工具的任务（P1、P2、P4、P5、P6 约束），结果取决于 EDA 工具的可用性和版本。
