**[English](benchmark_spec.md) | 中文**

# 基准测试规范

## 概述

EDA-AgentBench 用于评估 LLM/Agent 使用商业工具执行真实 EDA 工程任务的能力。该基准测试衡量 agent 是否能正确修改设计以通过基于仿真的测试。

## 评估模式

### 提交/工作区模式（v0）

当前模式评估针对任务预先生成的提交：

1. Agent 接收任务文件（prompt、可见文件）
2. Agent 生成修改后的文件（提交目录）
3. 评估器将提交复制到工作区，运行测试，计算分数

评估期间不发生工具调用。Agent 的输出是一组静态文件。

### Agent 模式（未来）

在 agent 模式下，agent 在沙箱化工作区内运行，具有：

- 可见文件的读取权限
- 可编辑文件的写入权限
- 运行所提供命令的能力
- 迭代直到超时或工具调用限制

评估器捕获最终工作区状态并以相同方式进行评分。

## 文件可见性模型

每个任务定义四类文件：

| 类别 | Agent 可读？ | Agent 可编辑？ | 用于评分？ |
|----------|----------------|-----------------|-------------------|
| visible | 是 | 否（除非也可编辑） | 是 |
| editable | 是 | 是 | 是 |
| hidden | 否 | 否 | 是 |
| forbidden | 否 | 否 | 检查是否被篡改 |

约束条件：

- `editable` 必须是 `visible` 的子集
- `hidden` 不得与 `visible` 重叠
- `forbidden` 必须是 `visible + hidden` 的子集

## 评估流程

```
1. 加载任务元数据并验证 schema
2. 检测所需的 EDA 工具（尽力检测）
3. 对所有禁止文件生成 SHA-256 哈希快照
4. 构建工作区：
   - 复制 files/ -> work_dir/
   - 复制提交中的可编辑文件 -> work_dir/（覆盖）
5. 运行公开测试：在 work_dir 中执行 bash run_public.sh
6. 运行隐藏测试：在 work_dir 中执行 bash run_hidden.sh
7. 验证防作弊：禁止文件的哈希值未变
8. 清理所有日志
9. 按照 metadata.scoring.weights 计算分数
10. 将 score.json 写入 runs/<task_id>/<timestamp>/
11. 清理 work_dir
```

## 公开测试与隐藏测试

- **公开测试**：通过 `run_public.sh` 和 `tb_public.sv` 对 agent 可见。Agent 可以针对这些测试进行迭代。
- **隐藏测试**：仅在评分时通过 `run_hidden.sh` 和 `tb_hidden.sv` 使用。Agent 永远看不到这些测试。

这可以防止针对特定测试用例的投机取巧。正确的解答必须具有通用性。

## 防作弊

在运行任何测试之前，评估器会计算 `metadata.files.forbidden` 中列出的所有文件的 SHA-256 哈希值。执行后重新计算并比较。如果任何哈希值不同，评估将因防作弊违规而失败。

禁止文件通常包括：

- `tb_public.sv` / `run_public.sh`（公开测试基础设施）
- `tb_hidden.sv` / `run_hidden.sh`（隐藏测试基础设施）

## 日志清理

所有 EDA 工具输出在存储前都会被清理。清理器替换：

- 用户名 -> `<USER>`
- 主机名 -> `<HOST>`
- 绝对路径 -> `<PROJECT_ROOT>`、`<EDA_ROOT>`
- 许可证服务器 -> `<LICENSE_SERVER>`

这使得评估日志可以公开共享而不会泄漏环境详情。

## 数据集评估

`eda-bench evaluate-dataset` 会发现根目录下的所有任务并对每个任务进行评估。两种提交模式：

- **solution**：每个任务的 `solution/` 目录作为提交（预期：所有任务得分为 1.00）
- **buggy**：每个任务的 `files/` 可编辑文件作为提交（预期：所有任务得分 < 1.00）

数据集级别的聚合会计算按 track、按工具、按难度的统计数据和分数分布。

## 报告生成

`eda-bench report` 读取评估结果并生成：

- **终端**：带通过/失败计数和分数分布的彩色表格
- **JSON**：机器可读的 `summary.json`，包含完整聚合数据
- **Markdown**：人类可读的 `report.md`，包含表格和统计数据
