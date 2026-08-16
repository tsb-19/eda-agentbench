**[English](artifact_map.md) | 中文**

# 产物地图 —— 论文每个论断到生成它的文件

本文档的存在，是为了让从论文过来的读者不必猜测就能定位任一论断的证据。章节与表号均指 `submission/main.tex`（手稿 v12，已冻结的 ICLR 2027 投稿；用 `cd submission && make` 构建）。

论文中没有任何数字是手工抄录的。两个派生表脚本读取冻结的逐 episode 记录并生成 LaTeX，由 `main.tex` 直接 `\input`，因此表格不可能与记录脱节：

```bash
python3 scripts/phase7c_study1_ledger.py --check       # -> submission/tables/study1_ledger.tex
python3 scripts/phase7c_claim_statistics.py --check    # -> submission/tables/claim_stats.tex, sta_pilot.tex
```

`--check` 会重新计算并与已提交的输出比对，一旦漂移即以非零码退出。

## 三个任务家族

论文的研究对象是**语义交接**（semantic handoff）：从角色误导性的证据中，把一个元组绑定到规范的类型化角色上；错误的绑定仍会产生绿色的工具签核（*tool-green*），因此只有类型化的溯源/权威 oracle 才会拒绝它。

| 论文名称 | 目录 | 实例数 | 工具 | 评分器（类型化 oracle） |
|---|---|---|---|---|
| workflow 家族（§3，研究 I） | `tasks/p14_workflow_handoff/` | 27 | PrimeTime | `<instance>/hidden/grade_workflow.py` |
| 家族 A —— STA（研究 II，S2-F） | `tasks/p15_sta_handoff/` | 15 × 3 条件 + dev | PrimeTime | `generators/p15_sta_handoff/grade_sta_handoff.py` |
| 家族 B —— SPICE（研究 II，S2-F） | `tasks/p16_spice_handoff/` | 3 × 3 条件 + dev | HSPICE | `generators/p16_spice_handoff/grade_spice_handoff.py` |

生成器：`generators/p14_workflow_handoff_gen.py`、`p15_sta_handoff_gen.py`、`p16_spice_handoff_gen.py`。评测器（harness 侧）：`eda_agentbench/evaluator/{workflow,sta,spice}_handoff.py`。

附录 F 所主张的五条结构性独立准则（独立的模板、词汇、真值、评分器、诱饵）由 `scripts/phase5a_independence_check.py` 机械核验，输出 `reports/synthetic_phase5_independence_check.json`。家族设计见 `docs/synthetic_phase5a_family_specs.md`、`docs/synthetic_workflow_generator_spec.md`。

## 正文

| 论文位置 | 论断 | 证据所在 |
|---|---|---|
| §1，图 1 | 五个支撑 S0 / S1 / S2-M / S2-F / S3 | 框架性论述；它点到的单元格通过下面各行落地 |
| §3.1，表 1 | 论断资格标准 | 仅论述 —— 这是声明的标准，不是测量 |
| §3，表 6（附录 A） | 工作实例：4 份随附证据源，两两自洽，且全部 PrimeTime 绿 | `tasks/p14_workflow_handoff/workflow_handoff_0009/files/report_A_role_swap.rpt`、`report_B_role_stale.rpt`、`report_C_role_pvt.rpt`、`evidence_D_role_mismatch.json` |
| §3 | 294 个候选赋值中恰有一个满足 C1–C5 | 唯一性穷举在 `generators/p14_workflow_handoff_gen.py`；隐藏真值在 `workflow_handoff_0009/hidden/handoff_truth.json` |
| §3 | oracle 如何裁决；两种绝不合并的失败子类型 | `workflow_handoff_0009/hidden/grade_workflow.py` |
| §3 | Base / BundleS / TypedContract 三个条件 | 各实例 `files/` 的可见集合；组件定义见 `docs/synthetic_p14_phase4w_clarity_bundle_ablation_design.md` |
| §4 | S0 上 Base 1/3 → BundleS 3/3；S1 上方向一致 | `reports/synthetic_p14_phase4w_run1.*`（S0）、`_heldout.*`（S1）、`_run2.*`（重复窗口） |
| §4 | 台账划分：70 个 episode → 41 正确、24 错轴、5 角色条件取值 | `reports/synthetic_p14_study1_ledger.json` |
| §4 | 未隔离出稳定的最小组件（仅 C1、仅 C2、仅 C4、C24 桥均未过阈） | `reports/synthetic_p14_phase4y_stage1.*`、`_phase4y2_stage2.*`、`_phase4y3_stage3.*`、`_phase4y3_c24_bridge.*` |
| §4 | 三个条件×模型组合在不同运行窗口中自相矛盾 | 表 7 中的重复行；不去重的理由见 `reports/README.zh.md` |
| §5，表 2 第 3 行 | S2-M：DeepSeek 3/4 = 3/4，未确立 | `reports/synthetic_p14_study1_ledger.json`（受控对各行） |
| §5，表 2 第 4 行 | S2-F STA：12 个实例上 Base .208 / BundleS .333 / TypedContract .458 | `reports/synthetic_phase7a_sta72_report.json` |
| §5 | +12.5 pp，敏感带 −12.5 至 41.7；符号检验 p=1.0；置换检验 p=0.31 | `scripts/phase7c_claim_statistics.py` → `reports/synthetic_p14_claim_statistics.json` |
| §5 | 三实例试点方向相反（−16.7 pp） | `reports/synthetic_phase5d_collection_report.json` |
| §5，表 2 第 5 行 | S2-F SPICE：Base = BundleS = TypedContract = 1.00 天花板 | `reports/synthetic_phase5c_collection_report.json` |
| §6，表 3 | 七个审计事件 | 每行对应下表一行 |
| §6 | 模型保管：episode 跨度、快照留存率、逐 episode 传输记录 | `scripts/phase7c_claim_statistics.py`（`resolved_snapshot_retained`、diag-episode 计数）作用于 `reports/evidence/` |
| §6 | Terminal-Bench 2.0→2.1：1 直接 / 21 部分 / 4 在外；采样层 0 | `scripts/phase7c_tb21_audit.py`、`scripts/phase7a_terminalbench_audit.py`、`reports/synthetic_phase7c_terminalbench_audit.md`、`reports/evidence/phase7c_terminalbench/`（冻结量表 + PR-53 快照） |

### 表 3 逐行

每行是一个威胁、抓住它的控制措施，以及同时展示两者的产物。

| 威胁（层） | 控制 | 产物 |
|---|---|---|
| 以工具成功为代理（能力层） | 类型化溯源/权威 oracle，绝不看工具退出码 | `grade_workflow.py`、`grade_sta_handoff.py`、`grade_spice_handoff.py` |
| 非流式传输截断（执行层） | SSE 流式 + 终态传输仲裁器 | `eda_agentbench/llm/openai_provider.py`、`scripts/episode_arbiter.py`、`tests/test_llm_streaming.py`、`tests/test_llm_driver_{timeout,deadline}.py`；事件全过程见 `reports/synthetic_p14_qwen_0009_fairness_anchor.*`（未解决）→ `_stream_anchor.*`（已解决） |
| 位置混淆（采样层） | 精确的位置平衡分块 | `scripts/phase4w_randomize.py`、`scripts/phase5b_schedules.py`、`scripts/phase7a_sta72_schedule.py` |
| 降级后恢复（执行层） | 终态有效与恢复态分离 | `scripts/episode_arbiter.py`、`tests/test_transport_telemetry.py` |
| PrimeTime 污染测量（执行层） | 带前后书签的工具健康哨兵 | `scripts/pt_health_sentinel.py`、`scripts/hspice_health_sentinel.py`、`tests/test_pt_health_sentinel.py` |
| SPICE 动作面假阳性（产物层） | 不可变核心 + 取证审计 | `scripts/phase5c_spice_forensic_audit.py`、`reports/synthetic_phase5c_spice_forensic_audit.json`、`tests/test_phase5_spice_repair.py`、`tests/test_phase5_hidden_isolation.py` |
| 规范源被改写（产物层） | 精确 commit 的隔离 worktree + 规范哈希守卫 | `scripts/canonical_integrity.py`（`FAILED_INTEGRITY` 停机）、`scripts/chain_executor.py`、`scripts/run_chain_guarded.py`、`tests/test_canonical_integrity.py`，以及 `tests/test_fullpath_check.py` 中的触发线 `test_canonical_golden_fingerprint_intact` |

§6 的"监控器的可信度不超过其参照标准的保管强度"就是最后一行的完整讲述：[`incident_golden_corruption.md`](incident_golden_corruption.md)。监控器的逻辑是对的，不匹配也是真的；错的是归因 —— 参照产物是被测试脚手架自身的一个组件改写的，而不是远端工具服务器。

## 附录

| 附录 | 内容 | 位置 |
|---|---|---|
| A | 工作实例的证据源 | `tasks/p14_workflow_handoff/workflow_handoff_0009/files/` |
| B | 研究 I 逐实例台账；逐单元精确区间；被搁置的合并数值 | `scripts/phase7c_study1_ledger.py` → `reports/synthetic_p14_study1_ledger.json` → `submission/tables/study1_ledger.tex` |
| C | 前瞻 STA 逐实例表；试点表；冻结的统计流程；事后敏感带 | `reports/synthetic_phase7a_sta72_report.json`、`reports/synthetic_phase5d_collection_report.json`、`submission/tables/sta_pilot.tex` |
| D | 完整 26 项 Terminal-Bench 编码 | `reports/synthetic_phase7c_terminalbench_audit.md`、`reports/evidence/phase7c_terminalbench/` |
| E | 冻结点、探索性对确认性、项目账目（58/24/36/72 episode；¥745.29） | `reports/synthetic_p14_phase4z_freeze_manifest.json`、`docs/phase7/phase7a_preregistration.md`，以及 `reports/evidence/` 下的 `prerun_freeze_manifest.json` / `membership_code_manifest.json` |
| F | 基础设施与保管；前瞻运行前被预检抓到的评分路径缺陷 | `docs/phase7/phase7a_preflight.md`、`docs/phase7/phase7a_sta_bug_audit.md`、`scripts/fullpath_check.py`、`scripts/spice_fullpath_check.py`、`scripts/measurement_control.py`、`scripts/fairness_retry.py` |
| G | 相对已有工作的定位 | `submission/references.bib` |
| 伦理声明 | 研究 B（盲法人类构念效度）已预注册但未执行 | `docs/phase7/phase7b_annotation_freeze.md`、`scripts/phase7a_annotation_packets.py` |
| 可复现性声明 | 冻结清单、排程、保管哈希、逐 episode 证据 | `reports/evidence/`，由 `scripts/frozen_membership_verify.py` 核验 |

## 论文*没有*主张什么，以及这在仓库中如何体现

- **S3（同时换模型与换家族）从未测量。** 这里刻意不存在任何报告；`reports/` 中它的缺席本身就是该论断。
- **没有人类构念验证。** `docs/phase7/phase7b_annotation_freeze.md` 是预注册；不存在标注结果，因为找不到合格的独立标注者，且没有用 LLM 顶替。
- **模型身份只是提供方别名，不是解析后的快照。** `phase7c_claim_statistics.py` 报告 `resolved_snapshot_retained: false`。论文把这写成自己欠下的局限（第五条 Layer-4 要求），而非已行使的控制。
- **两个生成器在冻结之后发生了漂移。** `scripts/frozen_membership_verify.py` 报告恰好 2 处不匹配、9 个缺失的被钉文件；均为既有状态，解释见 `docs/frozen_membership_baseline.json`。论文报告的数字来自被钉住的版本。

## 不用商业工具也能复现的部分

所有派生结果 —— 每个表格、区间、敏感带和 *p* 值 —— 都可以在不用 EDA 工具、不联网、不调用模型的前提下从冻结记录重算：

```bash
scripts/check                                          # 测试 + 结构 + 保管钉
python3 scripts/phase7c_study1_ledger.py --check
python3 scripts/phase7c_claim_statistics.py --check
cd submission && make distclean && make                # 15 页，逐字节可复现
```

重跑*episode* 是另一回事，本仓库做不到：那需要 PrimeTime 与 HSPICE 以及付费 API，而实验程序已在冻结的实验 HEAD 上永久关闭（见 [`provenance.zh.md`](provenance.zh.md)）。
