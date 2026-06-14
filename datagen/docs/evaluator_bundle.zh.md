**[English](evaluator_bundle.md) | 中文**

# 评测器数据包

## 公开包与私有评测包

| 方面 | `tasks_public/` | `tasks_eval_private/` |
|------|-----------------|----------------------|
| 受众 | 研究人员、公开基准 | 仅限评测器仓库 |
| `hidden/` | 已剥离 | 包含 |
| `oracle/` | 已剥离 | 包含 |
| `grader_contract.json` | 不包含 | 包含 |
| `validation/` | 规范化记录 | 规范化记录 |
| 原始 `.log` 文件 | 永不包含 | 永不包含 |
| Git 跟踪 | 是 | 否（`.gitignore`） |

## 为什么公开包中不包含 Oracle

Oracle 文件（`hidden/*.sp`、`oracle/answer.md`）包含参考解答。如果公开发布，智能体可以直接复制答案而非解决问题。公开包仅提供带有缺陷的提示和验证元数据。

## 评分合约

`grader_contract.json` 文件告诉主评测器仓库如何对智能体的尝试进行评分。

### 关键字段

| 字段 | 用途 |
|------|------|
| `editable_files` | 智能体可修改的文件（位于 `visible/` 下） |
| `hidden_files` | 用于评分的文件（位于 `hidden/` 下） |
| `oracle_files` | 参考解答文件 |
| `backend` | 运行智能体输出的商业工具 |
| `backend_env_var` | 工具命令的环境变量 |
| `command_template` | 使用 `{file}` 占位符的执行命令 |
| `success_criteria` | 通过评分的标准 |
| `failure_patterns` | 表示失败的错误模式 |

### SPICE 调试任务的成功标准

SPICE 网表调试任务使用**基于执行的评分**，而非精确文本匹配：

```json
{
  "exit_code": 0,
  "no_fatal_errors": true,
  "execution_based": true,
  "notes": "Agent output must run with HSPICE (exit 0) and produce no fatal errors."
}
```

这意味着：
1. 智能体生成一个修复后的 `.sp` 文件
2. 评测器使用 HSPICE 运行该文件
3. 如果 HSPICE 以退出码 0 退出且无致命错误，则智能体通过
4. 修复方案**不需要**与 `oracle/fixed.sp` 完全相同

### 为什么使用基于执行的评分

电路设计问题通常有多种有效解决方案。例如，缺少的模型可以通过以下方式修复：
- 内联添加 `.model` 语句
- 包含模型库
- 使用已存在的其他模型名称

精确文本匹配会拒绝合理的替代方案。基于执行的评分验证修复在功能上是否正确。

## 使用数据包

主评测器仓库应：

1. 克隆或创建 `tasks_eval_private/` 的符号链接
2. 对每个任务，读取 `grader_contract.json`
3. 将 `editable_files` 复制到工作目录
4. 让智能体修改可编辑文件
5. 使用智能体的输出运行 `command_template`
6. 根据运行结果检查 `success_criteria`
7. 与验证记录中的 `failure_patterns` 进行对比

### 示例流程

```python
import json
import subprocess

contract = json.load(open("tasks_eval_private/spice_deck_debug_0001/grader_contract.json"))

# Agent modifies visible/spice_deck_debug_0001_bug.sp
agent_file = contract["editable_files"][0]

# Run HSPICE on agent's output
cmd = contract["command_template"].format(
    hspice_cmd=os.environ["EDA_HSPICE_CMD"],
    file=agent_file,
)
result = subprocess.run(cmd.split(), timeout=contract["timeout_sec"])

# Check success
passed = (
    result.returncode == contract["success_criteria"]["exit_code"]
    and no_fatal_errors(result.stdout)
)
```

## 目录结构

```
tasks_eval_private/
  manifest.jsonl                    # 机器可读索引
  spice_deck_debug_0001/
    metadata.json
    prompt.md
    grader_contract.json            # 评分指令
    visible/
      spice_deck_debug_0001_bug.sp  # 有缺陷的网表（智能体可见）
    hidden/
      spice_deck_debug_0001_fixed.sp  # 标准修复（评分器使用）
    oracle/
      answer.md                     # 参考解答
    validation/
      validation_record.json        # 规范化验证数据
      normalized_errors.json
      raw_log.sha256
  ...
```
