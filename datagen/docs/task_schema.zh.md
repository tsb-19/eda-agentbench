**[English](task_schema.md) | 中文**

# 任务模式

每个基准任务存放在 `tasks_candidates/`、`tasks_validated/` 或 `tasks_public/` 下的独立目录中。

## 目录结构

```
<task_id>/
  metadata.json        # 任务元数据（见下方模式）
  prompt.md            # 给智能体的自然语言提示
  visible/             # 评测期间智能体可见的文件
  hidden/              # 对智能体隐藏的文件（评分器使用）
  oracle/              # 参考解答和评分数据
```

## 任务 ID 格式

任务 ID 遵循模式：`<domain>_NNNN`

- `domain` 与元数据中的 `domain` 字段匹配
- `NNNN` 为 4 位零填充数字（0001-0100）
- 示例：`spice_deck_debug_0001`、`spice_deck_debug_0100`

## 元数据模式

完整的 JSON Schema 位于 `schemas/task_schema.json`。关键字段：

| 字段                   | 类型     | 描述 |
|----------------------|----------|------|
| `task_id`            | string   | 唯一标识符：`<domain>_NNNN` |
| `domain`             | enum     | `spice_deck_debug`（本工厂唯一的活跃领域） |
| `task_family`        | string   | 领域内的子类别 |
| `difficulty`         | enum     | `easy`、`medium`、`hard` |
| `tags`               | string[] | 可搜索标签 |
| `prompt_file`        | string   | `prompt.md` 的相对路径 |
| `visible_files`      | string[] | 智能体可读的文件 |
| `hidden_files`       | string[] | 仅评分器使用的文件 |
| `expected_outputs`   | string[] | 智能体应生成的文件 |
| `grader`             | object   | 评分策略和标准 |
| `timeout_sec`        | int      | 任务完成的最大秒数 |
| `license_notes`      | string   | 任务内容的许可证 |
| `generation_source`  | enum     | `synthetic`、`derived`、`manual` |
| `oracle_description` | string   | 期望解答的描述 |
| `validation_status`  | enum     | 当前验证状态 |
| `optional_tool_backends` | string[] | 可验证的商业工具 |
| `public_release_safe`| bool     | 是否可公开发布 |

## 验证记录模式

当任务经商业工具验证后，会生成符合 `schemas/validation_record_schema.json` 的验证记录。记录仅包含规范化数据 — 原始商业日志永远不会存储在任务包中。
