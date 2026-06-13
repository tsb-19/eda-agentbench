**[English](agentic_runner.md) | 中文**

# Agent 运行器

## 概述

Agent 运行器用于评估可在沙箱化工作区中与任务文件交互的 agent。与标准评估模式中模型生成静态提交不同，agent 模式允许外部 agent 命令在评分前读取和编辑文件。

## 安全模型：两阶段工作区

Agent 运行器使用严格的两阶段工作区模型来防止信息泄漏：

### 阶段 1：Agent 工作区（仅包含可见+可编辑文件）

- 仅包含 `files/` 中的文件（P5 任务为 `visible/`）
- Agent 进程在此运行
- 隐藏测试平台、oracle 文件、评分脚本和解答文件**永远不会复制到此处**
- Agent 无法读取、列出或发现隐藏/oracle 文件

### 阶段 2：评估器工作区（agent 输出 + 隐藏文件）

- 在 agent 进程退出**后**创建
- 以任务根目录中的可见文件为基础
- 覆盖 agent 的编辑内容（仅限可编辑文件）
- 从任务根目录添加隐藏/oracle 文件
- EDA 工具执行和评分在此进行
- Agent 进程已终止，无法访问此工作区

### Agent 可访问的资源

| 资源 | Agent 可读？ | Agent 可写？ |
|----------|----------------|-----------------|
| 可见文件（`files/`） | 是 | 否（除非也可编辑） |
| 可编辑文件 | 是 | 是 |
| 隐藏文件（`hidden/`） | **否** | **否** |
| Oracle 文件（`oracle/`） | **否** | **否** |
| 解答文件（`solution/`） | **否** | **否** |
| `$EDA_TASK_PATH` | 是（只读） | 否 |

Agent 接收指向原始任务目录的 `$EDA_TASK_PATH`。Agent 可以从该路径读取 solution/（因为它在文件系统上），但这是设计如此——由 agent 封装层决定暴露哪些内容。关键保证是隐藏/oracle 文件不在 agent 的工作区中。

## 非 Agent 模式与 Agent 模式对比

| 方面 | 非 Agent 模式 | Agent 模式 |
|--------|-------------|---------|
| Agent 产出 | 静态文件 | 通过 shell 命令编辑 |
| 工作区 | 从提交目录创建 | 仅 agent（无隐藏文件） |
| 隐藏文件 | 复制用于评估 | 仅在 agent 退出后添加 |
| 工具执行 | Agent 不能运行工具 | Agent 可以运行工具（在 agent 工作区中） |
| 评估方式 | `_evaluate_single()` | `run_single_agentic()` |
| score.json 中的模式 | `submission` | `agentic` |

## CLI 用法

### 单个任务

```bash
eda-bench run-agent TASK_PATH --agent-cmd "YOUR_AGENT_COMMAND"
```

选项：
- `--agent-cmd`（必填）：作为 agent 执行的 shell 命令
- `--timeout N`：覆盖超时时间（秒）
- `--run-id ID`：自定义运行标识符
- `--output-dir DIR`：覆盖输出目录

### 采样数据集

```bash
eda-bench run-agent-dataset tasks --agent-cmd "YOUR_AGENT_COMMAND" \
    --sample-per-track 1 --seed 42
```

选项：
- `--agent-cmd`（必填）：要执行的 shell 命令
- `--track TRACK`：过滤到单个 track
- `--sample-per-track N`：每个 track 采样 N 个任务
- `--limit N`：全局任务限制
- `--seed N`：采样种子（默认：42）
- `--timeout N`：覆盖超时时间

## Agent 接口

Agent 命令接收以下环境变量：

| 变量 | 描述 |
|----------|-------------|
| `EDA_WORKSPACE` | Agent 工作区路径（仅包含可见+可编辑文件） |
| `EDA_TASK_PATH` | 原始任务目录路径（包含 solution/、hidden/） |
| `EDA_TASK_ID` | 任务 ID 字符串 |
| `EDA_TIMEOUT` | 超时时间（秒） |

命令以 `shell=True` 和 `cwd=EDA_WORKSPACE` 运行。

### 示例

**空操作 agent**（什么都不做）：
```bash
eda-bench run-agent tasks/p3_timing_report_qa/smoke --agent-cmd "true"
```

**复制答案 agent**（从任务路径复制正确答案）：
```bash
eda-bench run-agent tasks/p3_timing_report_qa/smoke \
    --agent-cmd "cp \$EDA_TASK_PATH/solution/answer.txt \$EDA_WORKSPACE/"
```

**自定义 agent 脚本**：
```bash
eda-bench run-agent tasks/p3_timing_report_qa/smoke \
    --agent-cmd "python3 my_agent.py --workspace \$EDA_WORKSPACE --task \$EDA_TASK_PATH"
```

## 输出结构

每次 agent 运行生成：

```
runs/<run_id>/<task_id>/<timestamp>/
    transcript.jsonl        # JSONL 事件：start、stdout、stderr、file_changes、score、end
    stdout.log              # 原始 agent 标准输出
    stderr.log              # 原始 agent 标准错误
    score.json              # ScoreResult（与非 agent 格式相同）
    workspace_manifest.json # agent 可见文件在运行前后的 SHA-256
    modified_files.json     # 文件变更和防作弊违规
    metadata.json           # 运行元数据（task_id、agent_cmd、mode 等）
```

`workspace_manifest.json` 仅包含 agent 可见文件。隐藏/oracle 文件永远不会包含在内。

对于数据集运行，会在 `runs/<run_id>/` 下写入 `summary.json`。

## 防作弊

- **可编辑文件强制执行**：仅 `metadata.files.editable` 中的文件可以被修改
- **禁止文件检查**：对禁止的可见文件进行 SHA-256 快照/验证
- **隐藏文件隔离**：隐藏文件永远不会进入 agent 工作区
- **分数归零**：防作弊违规将强制将分数置为 0
- **超时终止**：超时后 agent 命令将被终止

## 测试 Agent

`eda_agentbench/agentic/test_agents.py` 中内置的测试 agent 工厂：

| 工厂 | 行为 | 预期分数 |
|---------|----------|----------------|
| `make_noop_agent()` | 什么都不做 | ~0（无答案） |
| `make_copy_solution_agent(task_path)` | 通过 $EDA_TASK_PATH 复制 solution/ | 1.0（文件编辑任务） |
| `make_copy_answer_agent(task_path)` | 复制 solution/answer.txt | 1.0（QA 任务） |
| `make_buggy_answer_agent()` | 写入错误答案 | 0 |

## MVP 限制

- Agent 是单个 shell 命令，不是交互式循环
- 无逐次工具调用的记录（仅捕获 stdout/stderr）
- 无 max_tool_calls 强制执行（仅超时控制）
- 无工作区隔离之外的文件系统沙箱（agent 可通过 $EDA_TASK_PATH 访问其他路径）
- 无流式输出捕获
