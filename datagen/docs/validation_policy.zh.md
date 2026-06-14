**[English](validation_policy.md) | 中文**

# 验证政策

## 流水线

```
tasks_candidates/  -->  validate  -->  tasks_validated/  -->  package  -->  tasks_public/
     （已生成）        （商业工具）      （含 validation/）      （安全检查）    （公开安全）
```

已验证的任务包含一个 `validation/` 子目录，其中包含：
- `validation_record.json` — 完整的规范化记录
- `normalized_errors.json` — 提取的错误摘要
- `raw_log.sha256` — 原始日志的 SHA-256 哈希

原始 `.log` 文件仅保留在 `.local_runs/` 下（已加入 .gitignore）。

## 双模式验证

### 静态模式（默认）

静态模式验证任务结构和元数据，不调用任何 EDA 工具。它是默认模式，始终可用。

**执行的检查：**
- `metadata.json` 根据 `schemas/task_schema.json` 进行验证
- 所有引用的文件存在于任务目录中
- `prompt.md` 非空
- 目录布局符合预期结构
- Oracle 文件存在且非空
- 生成器输出是确定性的（重新运行会产生相同的任务）

静态模式从不调用：`vcs`、`xrun`、`hspice`、`spectre`、`pt_shell`、`dc_shell`、`innovus`、`icc2`、`iverilog`、`verilator`、`yosys`、`ngspice`、`opensta`、`openroad`。

### 商业验证模式（可选）

商业模式运行实际的 EDA 工具来验证任务是否有效且可解。该模式需要显式启用。

**激活方式：**
- 设置相关的 `EDA_*_CMD` 环境变量
- 显式运行验证脚本（例如 `bash scripts/validate_commercial_example.sh`）

**支持的商业工具：**
| 后端   | 环境变量           | 工具 |
|--------|------------------|------|
| VCS    | `EDA_VCS_CMD`    | Synopsys VCS |
| HSPICE | `EDA_HSPICE_CMD` | Synopsys HSPICE |
| Spectre| `EDA_SPECTRE_CMD`| Cadence Spectre |
| PT     | `EDA_PT_CMD`     | Synopsys PrimeTime |

**环境变量缺失时的行为：**
- 脚本输出明确的跳过信息
- 退出码为 0（非失败）
- 静态冒烟测试不受影响

## 验证记录

每次商业验证都会生成符合 `schemas/validation_record_schema.json` 的规范化记录。记录包含：
- 任务 ID、后端、工具名称、规范化版本
- 状态和退出码
- 规范化的错误摘要
- 解析后的指标
- 原始日志的 SHA-256 哈希
- 原始日志是否保留在 `.local_runs/` 中
- UTC 时间戳和备注

原始日志仅存储在 `.local_runs/` 下（已加入 .gitignore），永远不会包含在公开任务包中。
