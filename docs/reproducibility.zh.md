**[English](reproducibility.md) | 中文**

# 可复现性

这里有两样东西可以被复现，而区分你指的是哪一样很重要：

1. **论文的数字** —— 每个表格、精确区间、敏感带与 *p* 值。现在就可复现，不需要商业工具、不联网、不调用模型。先做这个。
2. **产出那些记录的付费 episode** —— 无法从本仓库复现。实验程序已在冻结的实验 HEAD 上永久关闭，重跑需要 PrimeTime、HSPICE 与付费 API。见 [`provenance.zh.md`](provenance.zh.md)。

*可以*复现的是从保存下来的逐 episode 记录到排版表格的整条链路。`submission/main.tex` 中没有一个数字是手工抄的：`main.tex` 直接 `\input` 下列脚本的产出。

## 复现论文（无需工具）

```bash
pip install -e ".[test]"

# 1. 仓库自身一致
scripts/check
#    [1] pytest 无工具子集        [2] 任务结构 84/84
#    [3] 冻结成员：全部 1065 条 path->sha256 钉重新哈希并与基线比对

# 2. 派生表格从冻结记录重算
python3 scripts/phase7c_study1_ledger.py    --check   # 研究 I 台账：21 个单元，58 + 12 = 70 个 episode
python3 scripts/phase7c_claim_statistics.py --check   # 12.5 / [-12.5, 41.7] / -16.7；Fisher .4/.4/1.0

# 3. 没有文档指向已不存在的东西
python3 scripts/slim_link_check.py

# 4. 手稿逐字节可构建
cd submission && make distclean && make               # 18 页，283 476 字节
```

`--check` 从 `reports/evidence/` 重算并与已提交的 JSON 比对，一旦漂移即以非零码退出；去掉 `--check` 则改写输出。

`make clean` 刻意保留 `main.pdf`，因此 `clean` 之后直接 `make` 是空操作。凡是要拿构建日志作为测量依据的场合，先用 `distclean` —— 曾有一次 v9 的页数测量正是因此取自过期 PDF。PDF 之所以逐字节可复现，是因为 Makefile 中钉住了 `SOURCE_DATE_EPOCH`；其 sha256 在 `submission/FREEZE_HASHES.md`。

### 哪个脚本写哪张表

| 脚本 | 读取 | 写出 |
|---|---|---|
| `scripts/phase7c_study1_ledger.py` | `reports/evidence/p14_phase4*_episodes/<trial>/{flow_config.submitted.json,result.json,agentlog.sanitized.json}`、冻结的项目清单 | `reports/synthetic_p14_study1_ledger.json` → `submission/tables/study1_ledger.tex` |
| `scripts/phase7c_claim_statistics.py` | 上述台账、`synthetic_phase7a_sta72_report.json`、`synthetic_phase5d_collection_report.json`、`reports/evidence/` | `reports/synthetic_p14_claim_statistics.json` → `submission/tables/{claim_stats,sta_pilot}.tex` |
| `scripts/phase4z_figures_tables.py` | 受控对矩阵与保存的 episode 台账 | `reports/synthetic_p14_phase4z_figures_tables.md` |

两个 `phase7c_*` 脚本都会把各阶段的 episode 数与冻结的项目清单相互断言，不一致就中止。这道检查之所以存在：早先一次对同一批记录的聚合用 `(condition, model)` 作字典键，静默丢掉了同一条件的重复测量 —— 把 70 个 episode 压成了 54 个。写下纳入规则并不能阻止这件事；代码里的断言可以。

## 确定性的任务生成

每个家族都由带种子的生成器产出，且每个任务的 `metadata.json` 都记录了产出它的生成器、种子与参数。

| 家族 | 生成器 | 说明 |
|---|---|---|
| p14 workflow | `generators/p14_workflow_handoff_gen.py`（驱动：`scripts/generate_workflow_handoff_tasks.py`） | 从 `tasks/p13_trajectory_handoff/traj_handoff_0001/` 读取资产底料 |
| p15 STA（家族 A） | `generators/p15_sta_handoff_gen.py`（12 实例面板：`scripts/phase7a_generate_sta12.py`） | 底料在 `generators/p15_sta_handoff/substrate/` |
| p16 SPICE（家族 B） | `generators/p16_spice_handoff_gen.py` | 评分器与可信度规格在 `generators/p16_spice_handoff/` |

准入是有门禁的，而不只是有种子。一个实例被接受之前：

- **唯一性** —— 在声明的取值域上穷举，必须恰好得到一个满足该实例约束的赋值（工作实例是 294 → 1）。"正确"由约束系统固定，而非由评分器判断。
- **硬可行性** —— 烘焙过程必须产出一个错误绑定的产物，它能被工具接受、能执行、能给出貌似合理的签核，却在语义上是错的，并且*确实*被类型化 oracle 拒绝。若错误绑定平凡地工具报红或无法解析，该实例即不合格并重新生成。

有两个生成器在其运行前冻结之后被编辑过；`frozen_membership_verify.py` 会报出那 2 处不匹配，而论文的数字来自被钉住的版本。这一点在 [`provenance.zh.md`](provenance.zh.md) 中如实陈述，而非抹去。

## 给一个家族实例评分（需要真实工具）

语义正确性由类型化的溯源/权威 oracle 判定，绝不看工具退出码 —— 因此评分既需要工具真的跑起来，*又*需要 oracle 去拒绝一次绿色的运行。p14/p15 用 PrimeTime，p16 用 HSPICE。

```bash
eda-bench detect-tools

# golden 必须得 1.00
eda-bench evaluate-task tasks/p14_workflow_handoff/workflow_handoff_0009 \
    --submission tasks/p14_workflow_handoff/workflow_handoff_0009/solution

# 随附的（错绑定的）可见文件必须 < 1.00，同时工具保持绿灯
eda-bench evaluate-task tasks/p14_workflow_handoff/workflow_handoff_0009 \
    --submission tasks/p14_workflow_handoff/workflow_handoff_0009/files
```

golden 对 buggy 这一对就是公平性门禁：先让已知正确的解走同一条路径。如果它没得到 ~1.00，说明评分器或环境正在扭曲测量，那条路径上得到的任何模型分数都不可信。

`scripts/validate_dataset.py` 把该门禁在整个家族上自动化，并带内容哈希缓存，因此 `--changed` 只重评动过的任务，同时仍报告其余任务的缓存判定：

```bash
python3 scripts/validate_dataset.py --structural --tasks-root tasks          # 无需工具
python3 scripts/validate_dataset.py --tasks-root tasks/p15_sta_handoff \
    --glob 'p15_eval_*' --concurrency 4                                       # 真实 PrimeTime
```

## 可复现的是*测量*，不只是分数

论文的第二个轴是：一个数字可能因为与模型完全无关的原因而错。让一个 episode 的测量可信的那些控制措施，属于可复现路径的一部分，且每项都有测试：

| 控制 | 脚本 | 测试 |
|---|---|---|
| 精确 commit 的隔离 worktree；每个 episode 前后核验规范哈希 | `canonical_integrity.py`、`chain_executor.py`、`run_chain_guarded.py` | `test_canonical_integrity.py`、`test_chain_executor.py`，以及 `test_fullpath_check.py` 中的触发线 |
| 终态有效与恢复态的 episode 仲裁 | `episode_arbiter.py` | `test_episode_arbiter.py`、`test_transport_telemetry.py` |
| SSE 流式（非流式传输会在生成中途截断长推理模型） | `eda_agentbench/llm/openai_provider.py`、`llm_agent_driver.py` | `test_llm_streaming.py`、`test_llm_driver_{timeout,deadline}.py` |
| 带前后书签的工具健康哨兵 | `pt_health_sentinel.py`、`hspice_health_sentinel.py` | `test_pt_health_sentinel.py` |
| 仅基础设施故障才重试（有效的错误分数是硬失败，绝不重试） | `fairness_retry.py`、`measurement_control.py` | `test_fairness_retry.py`、`test_measurement_control.py` |
| 位置平衡的分块随机化，在任何付费调用之前冻结 | `phase4w_randomize.py`、`phase5b_schedules.py`、`phase7a_sta72_schedule.py` | 排程本身即已提交的产物 |

基础设施超时、网关错误或 worker 失败属于**测量无效**，绝不计为能力失败。反过来同样成立而且更要紧：一个*有效的*错误分数是真实结果，不许被重试掉。

## 环境

- Python ≥ 3.10；安装后的包无第三方依赖。`pip install -e ".[test]"` 会额外装 pytest。
- 家族评分器需要商业 Synopsys 工具；没有替代品。探测在 `/EDA/soft2/synopsys/` 与 `/EDA/soft2/cadence/` 下进行；可用 `EDA_TOOL_ROOT` 替换开头的 `/EDA`。见 [`commercial_tool_policy.zh.md`](commercial_tool_policy.zh.md)。
- 只有跑*新的* episode 才需要模型访问，而冻结禁止这样做。驱动控制项见 [`agentic_runner.zh.md`](agentic_runner.zh.md)。
- `runs/` 与 `workspaces/` 是本地输出，永不提交。
