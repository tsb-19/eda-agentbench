**[English](release_checklist.md) | 中文**

# 发布安全检查清单

## 可发布内容

| 目录/文件 | 可否发布 | 说明 |
|-----------|---------|------|
| `tasks_public/` | **可以** | 公开安全的任务包。已剥离 hidden/oracle。 |
| `schemas/` | **可以** | 任务、验证记录、评分合约的 JSON Schema。 |
| `generators/` | **可以** | 合成任务生成器。 |
| `validators/common/` | **可以** | 共享验证工具。 |
| `docs/` | **可以** | 文档。 |
| `scripts/generate_prototypes.sh` | **可以** | 任务生成脚本。 |
| `scripts/smoke_static.sh` | **可以** | 静态冒烟测试。 |
| `scripts/package_public_task.sh` | **可以** | 公开打包脚本。 |
| `scripts/package_spice_public_batch.sh` | **可以** | 批量公开打包。 |
| `scripts/check_release_safety.sh` | **可以** | 发布安全扫描器。 |
| `tests/` | **可以** | 测试套件。 |
| `pyproject.toml` | **可以** | 项目配置。 |
| `README.md` | **可以** | 项目自述文件。 |

## 禁止发布的内容

| 目录/文件 | 原因 |
|-----------|------|
| `tasks_eval_private/` | 包含 hidden/oracle 解答。仅供评测器使用。 |
| `.local_runs/` | 包含原始商业工具日志。 |
| `tasks_validated/*/hidden/` | 标准解答文件。 |
| `tasks_validated/*/oracle/` | 参考答案。 |
| 任何 `*.log`、`*.lis`、`*.trn`、`*.dsn`、`*.raw` 文件 | 原始仿真器输出。 |
| 任何 `*.st0`、`*.sw0`、`*.ac0`、`*.ic0` 文件 | HSPICE 原始输出。 |

## 发布前需通过安全检查的内容

| 项目 | 所需检查 |
|------|---------|
| `tasks_validated/`（不含 hidden/oracle） | 必须通过 `check_release_safety.sh` |
| `validation_record.json` | 必须仅包含规范化数据，无原始日志 |
| `raw_log.sha256` | 仅 SHA-256 哈希，无日志内容 |
| `normalized_errors.json` | 仅清理后的错误摘要 |

## 安全扫描检查清单

发布前，运行：

```bash
bash scripts/check_release_safety.sh tasks_public
```

扫描器检查以下内容：

1. **hidden/oracle 目录** — 公开包中不得存在
2. **原始仿真器文件** — `.log`、`.lis`、`.trn`、`.dsn`、`.raw`、`.st0`、`.sw0`、`.ac0`、`.ic0`
3. **绝对路径** — `/EDA/`、`/home/`、`/data1/`、`/tmp/`、`/tools/`、`/usr/local/`
4. **许可证变量** — `LM_LICENSE_FILE`、`SNPSLMD_LICENSE_FILE`、`CDS_LIC_FILE`
5. **主机名/用户名** — 可检测的主机/用户引用
6. **私有包泄露** — `tasks_eval_private/` 不得出现在公开发布中

## 发布层级

### 第一层：公开发布（可安全发布）

- `tasks_public/` — 完全清理，无 hidden/oracle
- `schemas/` — JSON Schema
- `generators/` — 合成生成器
- `docs/` — 文档
- `scripts/` — 生成和打包脚本
- `tests/` — 测试套件

### 第二层：私有评测器包（仅与评测器仓库共享）

- `tasks_eval_private/` — 包含评分合约和 hidden/oracle
- 必须通过私有渠道传输，不得放在公开仓库中

### 第三层：永不发布

- `.local_runs/` — 原始商业工具日志
- 任何包含商业工具绝对路径的文件
- 任何包含许可证服务器信息的文件
- 任何包含主机名或用户名的文件

## 应急检查清单

如果文件意外提交了专有数据：

1. 从仓库中移除该文件
2. 如果文件已推送到远程仓库，重写 git 历史
3. 轮换任何已暴露的凭据或许可证信息
4. 运行 `bash scripts/check_release_safety.sh` 验证清理结果
