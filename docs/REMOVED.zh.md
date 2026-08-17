**[English](REMOVED.md) | 中文**

# 本分支删除了什么，以及如何取回

`iclr2027-artifact` 从 `master` 的 **`cc797ffe`**（标签 `iclr2027-submission-v3`）切出，收缩为单篇论文的可复现产物。**共删除 21 574 个文件。** 没有任何东西丢失：每个被删文件在 `master` 上完好无损，任意一个都可以用下面的命令取回：

```bash
git checkout master -- <path>          # 或：git show master:<path>
```

规则由仓库主人给出，并被逐字执行：**论文正文或附录涉及的保留，其余不保留。** 其前提是：论文本身就是过滤器 —— 它的内容是经过审视后留下来的，因此支撑它的试错记录不该出现在投稿分支上。

## 最大的一块：P1–P9 基准

`master` 同时也是 **EDA-AgentBench** —— 一个横跨 11 个 track、共 2892 个任务的基准（RTL 调试、testbench 生成、时序报告问答、SPICE 仿真与 deck 调试、DC 综合与约束调试、SpyGlass lint、PrimeTime STA、PnR 报告问答、PT 例外调试）。`submission/main.tex` 从未提及它，只研究三个语义交接家族。

这不是对基准的评价，而是一个范围事实，并且在删除任何东西之前就已机械确认：**`reports/` 下任何位置引用到的每一个 `tasks/` 路径 —— 那是 1337 个文件的冻结保管证据 —— 都指向 p14、p15 或 p16，对 P1–P9 的引用数为零。** 论文的证据链与基准互不相交。

如果你是为基准而来，请用 `master`。

## 清单

| 分组 | 文件数 | 删除理由 |
|---|---:|---|
| `tasks/p1_rtl_debug` | 8129 | P1 已发布 track —— 不在论文中 |
| `tasks/p3_timing_report_qa` | 5040 | P3 已发布 track |
| `tasks/p4_spice_sim` | 2244 | P4 已发布 track |
| `datagen/` | 1413 | P5 spice-deck 工厂；唯一消费者是已删除的 track |
| `tasks/p2_tb_sva_gen` | 910 | P2 已发布 track |
| `tasks/p5_spice_deck_debug` | 900 | P5 已发布 track |
| `tasks/p6_dc_constraint_debug` | 549 | P6 已发布 track |
| `tasks/p7_primetime_sta_debug` | 530 | P7 已发布 track |
| `tasks/p8_pnr_report_qa` | 505 | P8 已发布 track |
| `tasks/p7_spyglass_lint_debug` | 450 | P7 已发布 track |
| `tasks/p6_dc_synthesis_qa` | 255 | P6 已发布 track |
| `tasks/p9_pt_exception_debug` | 212 | P9 已发布 track（作为难度来源已退役 —— 前沿模型饱和） |
| `tasks/p10_synthetic_project` | 96 | 探针家族；已饱和，被 p14 线取代 |
| `docs/phases/` | 44 | 研究编年史：饱和综述、被取代的手稿草稿、模拟评审、成本与下一步规划 |
| `scripts/` | 44 | 各 track 生成器、smoke 脚本、baseline 套件、提示变体工具、被 `phase7c_*` 取代的 `phase6_*` |
| `experiments/` | 36 | 已退役探针：LEC 归因、MCMM、时序等价、可靠性 phase-0 |
| `tasks/p11_flow_handoff` | 34 | 探针家族；已饱和 |
| `eda_agentbench/` | 33 | 16 个各 track 评测器、`pnr/`、`synthesis/`、`timing/`、`prompt/`、`tools/wrappers/`、`task/datagen_bundle.py` |
| `docs/`（顶层） | 32 | 8 份各 track 文档、5 份基准文档、4 轮内部评审、`benchmark_spec` |
| `tests/` | 31 | 各 track 及各已删模块的测试 |
| `reports/`（顶层） | 24 | 基准测量产物、提示多样性报告、可靠性层报告、被 phase-7c 取代的 phase-6 冻结清单 |
| `tasks/p12_multifact_handoff` | 23 | 探针家族；已饱和 |
| `reports/archive/` | 22 | 记录结果为"饱和／仅为正面／已被取代"的探针报告 |
| `generators/` | 18 | 16 个 track 生成器及 P9 库资产 |

## 对规则的有意例外

有四类东西按规则本应删除，但各因一条理由保留：

1. **`tasks/p13_trajectory_handoff/traj_handoff_0001/`**（31 个文件）与 `eda_agentbench/evaluator/trajectory_handoff.py`。`generators/p14_workflow_handoff_gen.py:38` 把该目录当作资产底料读取（"REUSE the committed, b04-validated p13 substrate"），删掉它会让研究 I 的家族无法再生成。它是**资产底料，不是被研究的家族** —— 没有任何论文论断依赖它。把底料搬走的方案被否决：那意味着修改一个已生产出冻结、被哈希钉住任务的生成器，而科学上一无所得。它的契约测试也一并保留，因此保留下来的东西没有一处失去测试覆盖。
2. **`eda_agentbench/llm/` 与 `reliability.py`。** `scripts/llm_agent_driver.py` 属于冻结的成员代码且导入两者；冻结代码不得为了去掉依赖而被修改。
3. **`scripts/generate_model_submissions.py`、`run_model_baseline.py`、`scan_discrimination.py`。** 同样的理由，只是往外一层：`llm_agent_driver.py`、`phase4y_debug_grade.py` 和 `run_agentic_baseline.py` 导入它们。该提交的第一次尝试把三个都删了，测试套件在一个被钉住的驱动内部收集阶段就失败。
4. **四份构建规格文档**从 `docs/phases/` 迁至 `docs/` 而非删除，因为它们是论文所主张之物的构建记录，而非编年史：`synthetic_workflow_generator_spec.md`、`synthetic_phase5a_design.md`、`synthetic_phase5a_family_specs.md`、`synthetic_phase5a_generator_grader_plans.md`。

另有两条路径即便更整洁也**不能**移动：`docs/synthetic_p14_phase4w_clarity_bundle_ablation_design.md` 被一份冻结清单按路径引用；`docs/phase7/phase7_synthesis.md` 的 sha256 记录在 `submission/FREEZE_HASHES.md` 中。

## 被改动而非消失的部分

| 文件 | 改动 |
|---|---|
| `eda_agentbench/cli.py`、`agentic/runner.py` | 两处各有约 55 行 `if/elif` 评测器分派链，并会静默回落到 RTL 调试评测器；现在都委托给 `evaluator/resolve.py`，动态解析且遇未知规格即抛错 |
| `eda_agentbench/schema.py` | track、`task_id`、tool 枚举收缩到存留家族 |
| `eda_agentbench/task/validator.py`、`llm/openai_provider.py` | 修好两处提到已删模块的注释 |
| `scripts/check` | 可选的 Tier-2 判别力扫描（面向整个基准的工具）替换为冻结成员核验器 |
| `scripts/validate_dataset.py` | docstring 示例从已删 track 改指 p15 |
| `scripts/phase4z_figures_tables.py` | 输出从 `docs/phases/` 移到 `reports/`；重跑输出逐字节一致，因此这是搬迁而非重新生成 |
| `tests/test_agentic_runner.py` | 夹具改指 `tests/support/qa_stub_evaluator.py`，因为三个存留家族都需要商业工具，没有一个能在无工具下驱动 runner |
| `tests/test_workflow_handoff_gen.py`、`test_trajectory_handoff.py` | 分派一致性守卫改为断言"委托给共享解析器" —— 同一个不变量，换成对新结构的表达 |
| `reports/README.md` | 重写为面向评审者的证据索引；新增 `README.zh.md` |

本分支新增：`scripts/frozen_membership_verify.py`、`scripts/slim_link_check.py`、`docs/frozen_membership_baseline.json`、`docs/artifact_map.md`、本文件，以及它们的中文版。

## 已知局限：本分支未做匿名化

`reports/evidence/` 下约 212 个文件，以及大约 30 份保留的报告，含有用户名、远端工具主机名或绝对家目录路径。它们是被哈希钉住的保管记录：改写它们会破坏论文所主张的那条保管链，而 `scripts/frozen_membership_verify.py` 会报出漂移。

因此本分支是干净的*内部*产物，不是双盲补充材料。匿名化的补充材料需要另做一次脱敏**导出** —— 由替换流程产出的派生压缩包，并公布替换对照表 —— 而不是 git 编辑。该导出不属于本分支。

## 核验瘦身没有造成损伤

```bash
scripts/check                                          # 测试 + 结构 + 1065 条保管钉
python3 scripts/slim_link_check.py                     # 无悬空仓库路径引用
python3 scripts/phase7c_study1_ledger.py --check       # 58 + 12 = 70 个 episode
python3 scripts/phase7c_claim_statistics.py --check    # 12.5 / [-12.5, 41.7] / -16.7
cd submission && make distclean && make                # 18 页，sha256 不变
```

以上每一项在第一次删除之前于 `master` 上就是绿的，现在依然是绿的。承重的是保管门禁：它重算运行前清单记录的全部 1065 条 `path → sha256` 钉，并要求计数与 `docs/frozen_membership_baseline.json` 完全一致 —— 包括那 2 处既有不匹配与 9 个被 gitignore 的构建产物，它们被原样带过来，而不是被悄悄清理掉。
