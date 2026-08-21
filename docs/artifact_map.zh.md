**[English](artifact_map.md) | 中文**

# 产物地图 —— 论文每个论断到生成它的文件

本文档的存在，是为了让从论文过来的读者不必猜测就能定位任一论断的证据。章节与表号均指 `submission/main.tex`（手稿 **v16**，当前的 ICLR 2027 投稿；用 `cd submission && make` 构建）。
v14 是一个冻结的历史点，可凭 `submission/FREEZE_HASHES.md` 中记录的 commit 与哈希逐字节恢复；下文若某一行引用的是
v14 的节号，会明确写出。

论文中没有任何数字是手工抄录的。三个派生表脚本读取冻结的逐 episode 记录并生成 LaTeX，由 `main.tex` 直接 `\input`，因此表格不可能与记录脱节：

```bash
python3 scripts/phase7c_study1_ledger.py --check       # -> submission/tables/study1_ledger.tex
python3 scripts/phase7c_claim_statistics.py --check    # -> submission/tables/claim_stats.tex, sta_pilot.tex
python3 scripts/phase8a_claim_statistics.py --check     # -> phase8a_stats.tex, sta12_k6.tex, sta_concordance.tex
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

运行层独立性附录所主张的五条结构性独立准则（独立的模板、词汇、真值、评分器、诱饵）由 `scripts/phase5a_independence_check.py` 机械核验，输出 `reports/synthetic_phase5_independence_check.json`。家族设计见 `docs/synthetic_phase5a_family_specs.md`、`docs/synthetic_workflow_generator_spec.md`。

## 正文

| 论文位置 | 论断 | 证据所在 |
|---|---|---|
| §1，图 1 | 五个支撑 S0 / S1 / S2-M / S2-F / S3 | 框架性论述；它点到的单元格通过下面各行落地 |
| §3.1，表 9（附录 E） | 论断资格标准 | 仅论述 —— 这是声明的标准，不是测量 |
| §3，表 6（附录 A） | 工作实例：4 份随附证据源，两两自洽，且全部 PrimeTime 绿 | `tasks/p14_workflow_handoff/workflow_handoff_0009/files/report_A_role_swap.rpt`、`report_B_role_stale.rpt`、`report_C_role_pvt.rpt`、`evidence_D_role_mismatch.json` |
| §3 | 294 个候选赋值中恰有一个满足 K1–K5 | 唯一性穷举在 `generators/p14_workflow_handoff_gen.py`；隐藏真值在 `workflow_handoff_0009/hidden/handoff_truth.json`。**命名：**论文用 **K1–K5** 指这五条*任务约束*；冻结的任务文件把同样五条编号为 C1–C5，与*清晰度组件* C1–C7 相撞 —— 约束 K5（签核对）正是组件 C6 所断言的内容。实验刺激保留其原有编号，因为改写它们会改变测量 |
| §3 | oracle 如何裁决；两种绝不合并的失败子类型 | `workflow_handoff_0009/hidden/grade_workflow.py` |
| §3 | Base / BundleS / TypedContract 三个条件 | 各实例 `files/` 的可见集合；组件定义见 `docs/synthetic_p14_phase4w_clarity_bundle_ablation_design.md` |
| §4 | S0 上 Base 1/3 → BundleS 3/3；S1 上方向一致 | `reports/synthetic_p14_phase4w_run1.*`（S0）、`_heldout.*`（S1）、`_run2.*`（重复窗口） |
| §4 | 台账划分：70 个 episode → 41 正确、24 错轴、5 角色条件取值 | `reports/synthetic_p14_study1_ledger.json` |
| §4 | 未隔离出稳定的最小组件（仅 C1、仅 C2、仅 C4、C24 桥均未过阈） | `reports/synthetic_p14_phase4y_stage1.*`、`_phase4y2_stage2.*`、`_phase4y3_stage3.*`、`_phase4y3_c24_bridge.*` |
| §4 | 三个条件×模型组合在不同运行窗口中自相矛盾 | 表 7 中的重复行；不去重的理由见 `reports/README.zh.md` |
| §5，表 2 第 3 行 | S2-M：DeepSeek 3/4 = 3/4，未确立 | `reports/synthetic_p14_study1_ledger.json`（受控对各行） |
| §5，表 2 第 4 行 | **S2-F STA 主要证据（k=6）：** 12 个实例上 Base .278 / BundleS .250 / TypedContract .361 | `phase8a_sta_report.json`（在 `phase8a/reports/` 中） —— 详见下方 Phase-8A 一节 |
| §5，表 2 第 5 行 | S2-F STA 更早的 k=2 批次：同样 12 个实例上 Base .208 / BundleS .333 / TypedContract .458。**绝不与上一行汇合** | `reports/synthetic_phase7a_sta72_report.json` |
| §5、附录 C | k=2 批次：+12.5 pp，敏感带 −12.5 至 41.7；符号检验 p=1.0；置换检验 p=0.31 | `scripts/phase7c_claim_statistics.py` → `reports/synthetic_p14_claim_statistics.json` |
| §5、附录 C | k=6 批次：−2.8 pp，带 −31.9 至 +26.4；符号检验 p=1.0；置换检验 p=0.72 | `scripts/phase8a_claim_statistics.py` → `phase8a_claim_statistics.json`（在 `phase8a/reports/` 中） |
| §5 | 三实例试点方向相反（−16.7 pp） | `reports/synthetic_phase5d_collection_report.json` |
| §5，表 2 第 5 行 | S2-F SPICE：Base = BundleS = TypedContract = 1.00 天花板 | `reports/synthetic_phase5c_collection_report.json` |
| §3、附录 G | 在 169 条已验证配对的轨迹上工具成功信号是**常量**（接受），并接受了全部 82 条语义错绑，因此全部测得判别力都由类型化 oracle 承担；SPICE-5D 为负对照（18/18 正确，oracle 与工具一致） | `scripts/phase7d_semantic_proxy_gap.py --check` → `reports/synthetic_phase7d_semantic_proxy_gap.json`；回归测试 `tests/test_phase7d_semantic_proxy_gap.py` |
| §4、附录 F | 仅凭 BundleS 自身的披露无法唯一确定 golden assignment：294 个候选中仍存 9–147 个（区间对应两种读法），在 S0 与预先冻结的留出实例上都从不为 1；而带答案的组件 C6 会把 (scenario, corner) 投影压缩到 1。**只**排除了直接公布答案 | `scripts/phase7e_answer_identifiability.py --check` → `reports/synthetic_phase7e_answer_identifiability.json`；回归测试 `tests/test_phase7e_answer_identifiability.py` |
| §5、附录 C | 面板解剖结构（事后），在两个批次中重现：6 个地板受限、1 个天花板受限、5 个具判别力；去掉两个主导实例后 k=2 为 −5.0 pp、k=6 为 −20.0 pp | `phase7c_claim_statistics.py --check` → `sta_finite_panel.panel_anatomy`；`phase8a_claim_statistics.py --check` → `k6_panel.panel_anatomy` |
| §6 | 58 条 workflow episode 中有 9 条被排除，因为记录的工具判决并未证明其对应最终提交产物；tuple 相等只能抓到其中 2 条 | 同一 JSON —— `per_episode[].pairing_verified` 与 `exclusion_reason` |
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
| C | 前瞻 STA 逐实例表；试点表；冻结的统计流程；事后敏感带；**面板结构** | `reports/synthetic_phase7a_sta72_report.json`、`reports/synthetic_phase5d_collection_report.json`、`submission/tables/sta_pilot.tex`，以及 `reports/synthetic_p14_claim_statistics.json` 中的 `sta_finite_panel.panel_anatomy` |
| D | 什么会改变每一条结论 —— 七条可反驳条件，每个判决一条 | 论述；S0–S1 那一条现在报告附录 F 的结果，而不再是承诺去做 |
| E | 论断资格标准的完整分层定义 | 仅论述 —— 这是声明的标准，不是测量 |
| F | 各 treatment 条件的**仅凭披露的答案可唯一确定性** | `scripts/phase7e_answer_identifiability.py --check` → `reports/synthetic_phase7e_answer_identifiability.json`；回归测试 `tests/test_phase7e_answer_identifiability.py` |
| G | 语义/工具判别力：排除账目与配对敏感性 | `scripts/phase7d_semantic_proxy_gap.py --check` → `reports/synthetic_phase7d_semantic_proxy_gap.json` |
| H | 完整 26 项 Terminal-Bench 编码 | `reports/synthetic_phase7c_terminalbench_audit.md`、`reports/evidence/phase7c_terminalbench/` |
| I | 运行层独立性（五条结构性准则）、冻结点、探索性对确认性、项目账目（58/24/36/72 episode；¥745.29） | `scripts/phase5a_independence_check.py`、`reports/synthetic_p14_phase4z_freeze_manifest.json`、`docs/phase7/phase7a_preregistration.md`，以及 `reports/evidence/` 下的 `prerun_freeze_manifest.json` / `membership_code_manifest.json` |
| J | 基础设施与保管；前瞻运行前被预检抓到的评分路径缺陷 | `docs/phase7/phase7a_preflight.md`、`docs/phase7/phase7a_sta_bug_audit.md`、`scripts/fullpath_check.py`、`scripts/spice_fullpath_check.py`、`scripts/measurement_control.py`、`scripts/fairness_retry.py` |
| K | 相对已有工作的定位 | `submission/references.bib` |
| 伦理声明 | 研究 B（盲法人类构念效度）已预注册但未执行 | `docs/phase7/phase7b_annotation_freeze.md`、`scripts/phase7a_annotation_packets.py` |
| 可复现性声明 | 冻结清单、排程、保管哈希、逐 episode 证据 | `reports/evidence/`，由 `scripts/frozen_membership_verify.py` 核验 |

## 如何解读 Phase-7D 结果（v13 的 §3 与 §6 引用）

Phase-7D 是一项**事后、冻结之后**的派生分析：在实验程序关闭之后才确定，未经预注册，完全从实验冻结点及其之前已提交的记录重新推导——没有模型调用、没有 EDA 工具运行、没有新 episode。手稿在每处出现时都如此标注，任何对它的转述也必须如此。

有两件事必须随这个数字一起传递，且两者都写在 JSON 内部，而不是只留在正文里：

- **适用范围。** 这些家族本就被*构造*成"错绑仍然工具通过"。因此 1.0 的误接受率表明构造按规格生效，并量化了它对测量的代价；它**不是**对智能体基准中误接受普遍程度的估计。各分层分别报告、从不合并——它们跨越阶段、条件、模型与运行窗口，并不构成同一个抽样框。真正非平凡的部分是行为性的而非定义性的：真实智能体确实 82 次进入了"工具通过但语义错误"的区域。
- **Δ 不是第二个发现。** 因为工具信号恒定，`Δ = S_tool − S_semantic ≡ 1 − S_semantic`。Δ 仅供附录使用。

202 条纳入考虑的轨迹中有 33 条被**排除而非填补**：12 条受控对 episode 只以单元计数形式存在，12 条 SPICE-5C episode 没有冻结的工具字段，9 条 workflow episode 未通过判决—产物配对。最后这道门是实质性的——只有当工具判决与语义判决描述同一份最终提交时，两者才可以比较。STA/SPICE 由构造满足这一点（隐藏 runner 在评分时从提交的绑定现场产生工具判决），而 workflow 的智能体在 episode 中途运行证据链，之后仍可修改 `flow_config.json`。`stage2_summary.json` 记录了 `input_hashes["flow_config.json"]`，因此配对可由哈希判定：58 条中有 9 条失败，而 tuple 相等只能抓到其中 2 条——另外 7 条 `(scenario, corner, netlist)` 一致却消费了不同的文件。冻结 grader 早已独立标记了这些（`stage_chain == 0.0`）。

## 如何解读 Phase-7E 结果（v14 的 §4 与附录 F 引用）

Phase-7E 与 Phase-7D 属于同一类分析：**事后、冻结之后**，在实验程序关闭之后才确定，未经预注册，完全从实验冻结点及其之前
已提交的文件重新推导 —— 没有模型调用、没有 EDA 工具运行、没有新 episode。

它只回答一个问题：*只读某个条件所披露的内容、绝不读取任务证据，golden assignment 是否已被唯一确定？*

- **它关闭了什么。** 直接公布答案。BundleS 留下 294 个候选中的 9–147 个，从不为 1，因此 S0/S1 的结果不能用"treatment
  其实已经把答案写出来了"来解释。探针本身被证明有能力检测披露：组件 **C6** 恰好只在消融设计声明携带它的两个实例
  （`0010`、`0014`）中被检出，其余十二个都没有，并且在两种读法下都把 (scenario, corner) 投影压缩到 1。一旦该正控制不再
  触发，`main()` 就以非零码退出 —— 因此不可能用一个已经失灵的探针去报告这个否定结论。
- **它*没有*关闭什么。** 更微妙的信息泄漏、先验收窄、提示诱发的启发式线索、偶然的词汇相关、模型特异的利用方式。
  **不要**把它说成"没有泄漏" —— 正确的名称是*直接公布答案*或*答案可唯一确定性*。
- **这不是等信息量的对照。** BundleS 本来就被*设计*用来降低语义歧义；在最有利于泄漏假设的读法下，它把类型化网格从
  49 个候选收窄到 9 个。这是一个实质性的信息优势，但仍未到公布答案的程度 —— 这句话的两半必须一起出现。
- **给出界，而不是机制。** 探针给出的是某个条件信息优势的界。它不识别行为机制，候选数之比也不得被改述为机制 ——
  在严格读法下 BundleS 相对 Base 根本没有收窄候选集合。
- **报区间，不报单点。** 9 是最有利于泄漏假设的下界，147 是严格读法的上界。只报 9 会高估 treatment 的收窄程度，
  只报 147 则会低估。

读取纪律是可执行的，而不是口头承诺：探针只读 `prompt.md`、`spec.md`、`glossary.md` 与
`public_check_summary.json`；各份 report、`evidence_D`、`prev_signoff`、`flow_config.json`、handoff 清单、网表以及
`hidden/` 下的一切都会抛出 `ForbiddenRead`。有九个测试断言这些拒绝确实会触发。候选域被断言在全部十四个条件间逐字节
相同，而 golden 元组通过一个独立的访问器载入，且只在所有存活集合都已确定之后才被调用。

## 论文*没有*主张什么，以及这在仓库中如何体现

- **S3（同时换模型与换家族）从未测量，其后又被判定为「未执行」。** 这是两个不同的理由，不可混为一谈。在原实验程序中，它没有在已经看到 S2-F 结果之后被补上，因为「看到不利结果再扩展证据」正是论文自身标准要防止的、随结果自适应的做法；成本不是那个程序的约束（其 72 个 episode 的 STA 面板只花了 ¥43.56，总额 ¥745.29）。随后 Phase-8A 正式预注册了一个 S3 实验臂，并在任何结果存在之前就把成本门控固定成公式，而门控拒绝了它（`ARM2_NOT_RUN`）。上限之下的余额被刻意不用于跑一个更浅的版本。**两个理由都不产生效应方向** —— S3 是未测试，而不是负结果；这里刻意不存在任何报告。**那一格上确实存在 72 条 episode**，而这个区分很重要：它们是在门控判定被提交**之后**、在隔离状态下生成的，不是那个预注册实验臂，而且**它们的条件对比从未被计算过**。详见下方 Phase-8A 一节。
- **更微妙的信息泄漏并未被排除。** Phase-7E 只关闭了*直接公布答案*（BundleS 留下 294 中的 9–147 个，从不为 1）。先验收窄、提示诱发的启发式线索、偶然的词汇相关与模型特异的利用方式仍然开放；Base/BundleS 的对照刻意**不是**等信息量比较。
- **没有向生产级 harness 的迁移结论。** 论文里的 "harness" 指**任务层的信息结构**（§2）—— 提示、可见文件、
  披露包、公开工具反馈、动作面 —— 而不是智能体脚手架。所有 episode 都经由 `scripts/llm_agent_driver.py`
  与 `eda_agentbench/agentic/` 运行，没有测试任何生产级编码智能体。§7 明确写下了这一点，因此"169 条中 82 条"
  这个占据率只适用于该运行器。**不**依赖脚手架的是判别力结论本身：工具成功字段无法区分角色绑定的正确与错误，
  这是任务与其 oracle 的性质 —— 这也正是它被表述为基准/评分器层面发现的原因。
- **没有人类构念验证。** `docs/phase7/phase7b_annotation_freeze.md` 是预注册；不存在标注结果，因为找不到合格的独立标注者，且没有用 LLM 顶替。
- **模型身份只是提供方别名，不是解析后的快照。** `phase7c_claim_statistics.py` 报告 `resolved_snapshot_retained: false`。论文把这写成自己欠下的局限（第五条 Layer-4 要求），而非已行使的控制。
- **两个生成器在冻结之后发生了漂移。** `scripts/frozen_membership_verify.py` 报告恰好 2 处不匹配、9 个缺失的被钉文件；均为既有状态，解释见 `docs/frozen_membership_baseline.json`。论文报告的数字来自被钉住的版本。

## Phase-8A —— 高重复的 S2-F 面板（v15 中的 S2-F 主要证据）

Phase-8A 用**完全相同的冻结 12 实例 STA 设计、k=6** 重跑了一次，因为每格只跑两次无法确定该格自身的取值。
**自手稿 v15 起它就是 S2-F 的主要证据**，而先前 k=2 的面板保留为促使把 k 提高的更早的前瞻研究。它在 v14 冻结
之后执行，因此 **v14 并未引用它**；v14 仍可凭其记录的 commit 与哈希逐字节恢复（见 `submission/FREEZE_HASHES.md`）。

两个批次**绝不汇合**：没有任何量跨批次求和、求均值或求差，两者的 episode 数不相加，也不存在 k=8 的面板。
理由是它们是**两个独立的实验批次**，后者是单独预注册的高重复后续研究 —— **而不是**因为它们的 serving endpoint
不同。Phase-8A 通过一个不同的 serving endpoint 访问同一个模型别名（原端点已停止提供这些模型）；我们控制的 API
参数被固定并记录，底层 serving 实现不是我们能证实的东西，因此服务提供方的更换是**如实披露、且不作为实验因子处理**的。

| 主张（论文位置） | 证据所在 |
|---|---|
| **高重复面板结果**（§5 表 2 第 4 行；摘要）。216 个 episode，12 实例 × 3 条件 × k=6，¥122.8175。没有建立一致的 BundleS 优势；描述性均值 Base .278 / BundleS .250 / TypedContract .361；−2.8 pp，实例重抽样带 −31.9 至 +26.4。预注册符号检验 5 个非零差中 k⁺=2，双侧 *p*=1.0；置换 *p*=0.72（描述性） | `scripts/phase8a_report.py --arm 1 --check` → `phase8a/reports/` 中的 `phase8a_sta_report.json`；手稿数字经 `scripts/phase8a_claim_statistics.py --check` |
| **实例级异质性，且是双向的**（§5；附录 C 表 5）。12 个实例中只有 5 个能表达差异（6 个在两个主条件上同处地板，1 个同处天花板）。这 5 个上的差值为 −1.0、−0.8333、−0.1667、+0.6667、+1.0 —— 有两个实例在**相反方向**上各自达到可能的最大幅度 | 同一 JSON 的 `k6_panel.per_instance` 与 `panel_anatomy`；叙述见 [`phase8a_findings.zh.md`](phase8a_findings.zh.md) |
| **在这个粒度上重复不是可选项**（§5；§6 讨论）。36 个（实例, 条件）单元中有 7 个，其 6 次完全相同的重复彼此不一致；`p15_eval_0013` 的 Base 是 6 次中的 3 次。用单条轨迹去估计这样一个单元，估的是该单元并不具有的取值 | 同一 JSON 的 `within_cell_replication_stability`；逐次布尔值见 `phase8a_sta_report.json` |
| **把 k 提高反而让组成带变宽而非变窄**（§5；附录 C）。k=6 为 −31.9 至 +26.4，k=2 为 −12.5 至 +41.7：把各单元解析清楚之后，实例级差值变大了，而重抽样扰动的正是这些差值。重复深度与面板组成是两条互相独立的限制 | 两个统计脚本的 `--check`；两条带由同一个函数 `instance_resampling_band` 计算 |
| **联合 model × family 面板 —— S3 已测量，迁移未确立**（§1 图 1；§5 表 2；附录 C）。Arm 2（`deepseek-v4-pro`），72 个 episode，同样 12 个冻结实例 × 3 条件 × k=2，¥58.11。描述性均值 Base .250 / BundleS .375 / TypedContract .4167；+12.5 pp，实例重抽样带 −16.7 至 +41.7。符号检验 7 个非零差中 k⁺=5，双侧 *p*=0.453；置换 *p*=0.336（描述性）。解剖为 4 地板 / 1 天花板 / 7 有信息量。点估计有利于 BundleS，而判别力得不出结论：**未确立** —— 它既不是"无效应"，也不是负结果 | `scripts/phase8a_report.py --arm 2 --check` → `phase8a/reports/` 中的 `phase8a_sta_report_arm2.json`；`phase8a_claim_statistics.json` 的 `arm2_joint_panel`；逐实例表 `submission/tables/sta12_arm2.tex` |
| **Arm 2 的执行不是预注册的，而论文从不这样写**（§5；附录 D）。它的 episode 是在预注册成本门控返回 `ARM2_NOT_RUN` **之后**才跑的，因此不是预注册所规划的那个臂。支配分析的是一份在读取任何 arm-2 outcome 字段之前提交的方案；报告记录该方案的 sha256，而方案缺失时 `phase8a_report.py` 根本拒绝生成 arm-2 报告 | [`phase8a_arm2_analysis_plan.zh.md`](phase8a_arm2_analysis_plan.zh.md) → `phase8a/evidence/arm2_analysis_plan.json`；`phase8a_sta_report_arm2.json` 的 `provenance`；先后次序由 `tests/test_phase8a.py` 对照 git 历史核验 |
| **没有为那次分析弱化任何规则**（§5；附录 D）。`phase8a_report.py` **当且仅当**某个计划实例缺失时才扣留条件聚合量 —— block 就是实例，所以 block 的子集会让预算或服务提供方挑样本。Arm 2 跑完 12 个中的 12 个，因此未经修改的规则本身就允许输出：这项控制是前提被满足，而不是被放松 | `scripts/phase8a_report.py:369` 的扣留分支；`test_the_withholding_rule_still_fires_when_an_instance_is_missing` 通过声明第十三个计划实例把它重新证伪 |
| **k=2 不承载任何幅度主张**（§5；附录 C）。Arm 1 在同一家族上测出 36 个单元中有 7 个在六次完全相同的重复之间不一致，因此 arm 2 的单元取值是已知带噪的，其聚合量**不**与 arm 1 的 k=6 聚合量并列摆放、仿佛解析程度相同 | `arm2_joint_panel` 的 `repetition_depth_limit`；`test_the_k2_magnitude_limit_travels_with_the_arm2_numbers` |
| **跨模型一致性：事后、存在混淆，且大部分是退化的**（§5；附录 C）。12 个实例中有 10 个在两臂获得相同分类，但对所讨论的问题而言**其中 5 处一致是退化的** —— 在两个被比较条件下都处于地板或天花板，任一臂都没有可表达的差异，因此这种一致记录的是共同的实例难度、而不是共同的响应。只有两处都有信息量的那 5 个实例才**可能**在方向上出现分歧，其中 4 个符号一致。两臂在模型**和** k 上同时不同；这个子集是在读取 outcome 之后才确定的；而在每个实例符号独立的零假设下，达到 4/5 或更好的概率是 0.1875（描述性敏感度数字，只在附录出现，不是检验）。**允许的措辞**：*与反复出现的任务特异性结构相符*。**不允许的措辞**：实例结构与模型无关、异质性是实例而非后端的属性、或聚合效应发生了迁移 | `phase8a_claim_statistics.json` 的 `cross_model_structural_concordance`，其中自带 `confounded: true`、`class_agreements_that_are_degenerate`、`sign_exchangeability_tail_p` 以及对应的 `..._is_not_a_hypothesis_test` 免责字段 |
| **预注册成本门控曾在 arm 2 运行前拒绝了它**（研究过程记录；刻意**不进**手稿）。在成本探针与 block 00 共 12 个 episode 上汇总得 r′=¥0.8051/episode；最便宜的合格方案预计 ¥57.97，而 ¥200 上限下仅剩 ¥44.53 → `ARM2_NOT_RUN`。由于门控的两个输入此后都变了，`--check` 现在**核验**已记录的决定（对照它自己声明的输入），而不再重算；三种篡改被断言为失败 | `scripts/phase8a_arm2_gate.py --check` → `phase8a/evidence/arm2_gate_decision.json`；`test_the_gate_verification_can_actually_fail` |
| **门控拒绝了一个其实负担得起的实验臂**（研究过程记录；**不进**手稿）。对它所定价的那 66 条 episode 预计 ¥53.14，可用 ¥44.53；实际花费 ¥38.46 —— 够，还余 ¥6.07。规则施行无误；错的是速率估计量被校准在 `p15_eval_0004` 上，它是十二个实例中最贵的（¥1.109/ep，面板均值 ¥0.627，最便宜 ¥0.330）。这**不是**分析该臂的理由 —— 事前方案才是 | `scripts/phase8a_arm2_cost_calibration.py --check` → `phase8a/evidence/arm2_cost_calibration.json` |
| 程序总支出，一个数字（附录 I；可复现性声明）：¥200 上限中的 ¥183.9329，未花掉 ¥16.07。arm 2 被排除在分析之外时曾按两个数字分列；既然每一分钱都站在某个被报告的数字背后，现在就是一个数字 | `phase8a_claim_statistics.json` 的 `money`，由 runner 自己的 `_program_spend()` 重算；`scripts/phase8a_cost_reconcile.py --arm 2 --block 0 --check` |
| 预注册及其六条编号修正案 —— 每条都在相应的进入分析的 episode 之前固定（附录 I，冻结点 3） | [`phase8a_prereg.zh.md`](phase8a_prereg.zh.md) |
| 金钱（附录 I；可复现性声明）：逐 episode 保管记录、归档的废弃轮次、被替换尝试账本、低报成本的更正 | `phase8a/evidence/`；`scripts/phase8a_cost_reconcile.py --arm 2 --block 0 --check` |

### 事后观察：实例级结构在两个批次之间重现

Phase-7A 附录 C 的解剖结构（6 个地板受限、1 个天花板受限、5 个有信息量）在 k=6 上以**完全相同的计数**重现，
而且**12 个实例中有 10 个获得完全一致的分类** —— 六个地板受限的实例是同样那六个。在两处都有信息量的实例
中，**符号**在全部 4 个上都一致：`p15_eval_0004` 与 `p15_eval_0007` 在两处都为负，`p15_eval_0011` 与
`p15_eval_0012` 在两处都为正。只有 `p15_eval_0010`（+0.5 → 0.0）与 `p15_eval_0013`（0.0 → −0.1667）
改变了类别，且都是在地板/天花板边界上的小幅移动。

两个批次由**同一个函数**分类，并且 `phase8a_claim_statistics.py` 会先把这个函数跑在 Phase-7A 自己的实例上、
断言其计数等于 Phase-7A 冻结的 `panel_anatomy` 块，然后才形成这个比较。没有这道断言，"解剖结构重现了"就可能
只是两套措辞略有差别的规则造成的假象。

这是**事后的、非预注册的**观察，与 Phase-7A 自己的 `panel_anatomy` 块标注一致（`post_hoc: true`）。
它也**不是**汇合：没有任何数字跨这两项研究相加。按论文自身的资格标准，它也**不是**复制 —— 两个批次重跑的是
*同一批*冻结实例，这属于对稳定性的重复测量，而不是任何投影的扩大。它支持的是一个狭窄而有用的表述 ——
实例级异质性是**实例**的性质，而不是 k=2 下的抽样噪声，因为它在一次独立执行中把重复深度增至三倍之后依然存在。
它**不**授权用其中一个后端去推断另一个后端的任何结论，也不意味着总体方向得到了复制 —— 并没有；而"结构稳定、
总体不稳定"这个对比本身才是那个观察。

交叉核对：`scripts/phase7c_claim_statistics.py --check` → `reports/synthetic_p14_claim_statistics.json`
中的 `sta_finite_panel.panel_anatomy`，对照 `phase8a/reports/` 中 `phase8a_claim_statistics.json` 的
`cross_batch_structural_concordance`。

### 属于方法附录而非正文的部分

Phase-8A 期间发现并修复了三个 harness/账本缺陷。它们证明的是复现治理，而不是科学结果。v15 把它们作为通用的
**账目要求**写在附录 J，正文中一处也没有；事件层面的细节留在
[`phase8a_findings.zh.md`](phase8a_findings.zh.md) 的"测量效度发现"一节：从未执行的 slot 被误算为
measurement-invalid；一个靠缩小观察范围而变绿的成本校验器；以及一个被存放在"后续正当操作有权覆盖"路径上的
原始工件。

唯一进入正文的过程性发现是参照标准保管原则，它之所以在正文，是因为它在 v13 就已经被提升为一条 Layer-4 要求 ——
以要求的形式陈述，事件叙述放在附录 J。

## 不用商业工具也能复现的部分

所有派生结果 —— 每个表格、区间、敏感带和 *p* 值 —— 都可以在不用 EDA 工具、不联网、不调用模型的前提下从冻结记录重算：

```bash
scripts/check                                          # 测试 + 结构 + 保管钉
python3 scripts/phase7c_study1_ledger.py --check
python3 scripts/phase7c_claim_statistics.py --check
python3 scripts/phase7d_semantic_proxy_gap.py --check   # 纳入 169 条 / 82 条工具通过型错绑
python3 scripts/phase7e_answer_identifiability.py --check  # 候选域 294；BundleS 9–147，从不为 1
python3 scripts/phase8a_claim_statistics.py --check        # arm1 k=6：−2.8 pp；arm2 k=2：+12.5 pp
python3 scripts/phase8a_arm2_gate.py --check               # 核验已记录的 ARM2_NOT_RUN 决定
python3 scripts/phase8a_arm2_cost_calibration.py --check   # 预计 ¥53.14 对实际 ¥38.46
cd submission && make distclean && make                # 正文 9 页，逐字节可复现
python3 scripts/submission_page_limit_check.py         # 正文结束于第 9 页（ICLR 上限 9）
```

重跑*episode* 是另一回事，本仓库做不到：那需要 PrimeTime 与 HSPICE 以及付费 API，而实验程序已在冻结的实验 HEAD 上永久关闭（见 [`provenance.zh.md`](provenance.zh.md)）。
