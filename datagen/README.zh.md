**[English](README.md) | 中文**

# EDA-AgentBench：SPICE 网表调试数据工厂（`datagen/`）

本目录是 EDA-AgentBench 的**仓库内数据生成模块**——一个自包含的工具子树。所有命令都在此目录下运行（`cd datagen`）。

负责范围：`spice_deck_debug` 领域的任务 schema、合成 SPICE 生成器、商业工具（HSPICE）验证适配器、规范化公开安全打包和冒烟测试。

**不负责**agent 运行器/评测 harness（位于父仓库 `eda-agentbench`）。它是 **P5 SPICE 网表调试赛道的唯一来源**；父仓库的 `scripts/import_p5_tasks.py` 导入它导出的评测包（见 `CLAUDE.md` 的“与基准的关系”）。

> **注意：** 早期的 `rtl_debug` 和 `timing_report_qa` 原型领域已退役。RTL 调试与时序报告问答任务直接由父仓库的 `generators/`（赛道 p1/p3）生成。

## 流水线

```
tasks_candidates/  -->  validate  -->  tasks_validated/  -->  package  -->  tasks_public/
     (generated)       (commercial)     (with validation/)     (safety)     (public-safe)
```

### 快速开始

```bash
# 1. 生成 SPICE 网表调试任务（100 个候选）
bash scripts/generate_prototypes.sh

# 2. 运行静态冒烟测试（不需要 EDA 工具）
bash scripts/smoke_static.sh
python -m pytest tests

# 3. 运行商业验证（需要 EDA 工具在 PATH 或环境变量中）
bash scripts/validate_one_candidate.sh tasks_candidates/spice_deck_debug_0001 hspice

# 4. 打包已验证任务用于公开发布
bash scripts/package_public_task.sh tasks_validated/spice_deck_debug_0001
```

## 架构

```
.
├── schemas/                    # JSON Schema 定义
│   ├── task_schema.json
│   └── validation_record_schema.json
├── generators/                 # 合成任务生成器
│   └── spice_deck_debug/generate.py
├── validators/                 # 验证适配器
│   ├── common/                 # 共享工具
│   ├── vcs/                    # Synopsys VCS 适配器
│   ├── hspice/                 # Synopsys HSPICE 适配器
│   ├── spectre/                # Cadence Spectre 适配器
│   └── pt/                     # Synopsys PrimeTime 适配器
├── tasks_candidates/           # 生成的任务候选
├── tasks_validated/            # 通过验证的任务
│   └── <task_id>/
│       ├── validation/
│       │   ├── validation_record.json
│       │   ├── normalized_errors.json
│       │   └── raw_log.sha256
│       └── ...（任务文件）
├── tasks_public/               # 公开安全的任务包
├── .local_runs/                # 原始商业日志（git 忽略）
├── tests/                      # Pytest 测试套件
├── scripts/                    # Shell 脚本
└── docs/                       # 文档
```

## 验证模式

### 静态模式（默认）

验证任务结构、schema 合规性和生成器确定性。不需要 EDA 工具。

```bash
bash scripts/smoke_static.sh
python -m pytest tests
```

### 商业验证模式（可选）

使用商业 EDA 工具验证任务。工具必须在 PATH 中或通过环境变量设置：

| 环境变量 | 工具 | PATH 回退 |
|---|---|---|
| `EDA_VCS_CMD` | Synopsys VCS | `vcs` |
| `EDA_HSPICE_CMD` | Synopsys HSPICE | `hspice` |
| `EDA_SPECTRE_CMD` | Cadence Spectre | `spectre` |
| `EDA_PT_CMD` | Synopsys PrimeTime | `pt_shell` |

当环境变量和 PATH 工具都不可用时，验证会优雅跳过（exit 0）。

```bash
# 单任务验证
bash scripts/validate_one_candidate.sh tasks_candidates/spice_deck_debug_0001 hspice

# 批量验证示例
bash scripts/validate_commercial_example.sh
```

## 打包用于公开发布

默认情况下只有 `tasks_validated/` 下的任务可以被打包：

```bash
bash scripts/package_public_task.sh tasks_validated/spice_deck_debug_0001
```

对未验证任务的覆盖（显式选择加入）：
```bash
bash scripts/package_public_task.sh tasks_candidates/spice_deck_debug_0001 --allow-unvalidated
```

公开包经过验证，确保不包含：
- `.log`、`.lis`、`.trn`、`.dsn`、`.raw` 文件
- 绝对路径（`/home/`、`/EDA/`、`/tools/`、`/data1/`、`/tmp/`）
- 许可证变量引用（`LM_LICENSE_FILE`、`SNPSLMD_LICENSE_FILE` 等）
- 主机名或用户名
- 验证摘要（`validation/normalized_errors.json`、`validation/raw_log.sha256`）

## 商业工具策略

原始商业工具日志仅存储在 `.local_runs/` 下（git 忽略）。公开任务包绝不包含：
- 许可证横幅、主机名、用户名
- 绝对路径、工具版本横幅、时间戳
- 专有 PDK 数据或许可证服务器信息

详见 `docs/public_release_policy.zh.md`。

## 任务领域

| 领域 | 候选 | 已验证 | 公开 | 描述 |
|---|---|---|---|---|
| `spice_deck_debug` | 100 | 100 | 10 | 调试 SPICE 电路仿真 deck |

`rtl_debug` 和 `timing_report_qa` 原型领域已退役；这些赛道改由父仓库的 `generators/`（p1/p3）生成。

详见 `docs/taxonomy.zh.md` 了解完整任务家族分类。

## 许可证

Apache-2.0
