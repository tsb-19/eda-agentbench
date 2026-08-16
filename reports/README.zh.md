**[English](README.md) | 中文**

# reports/ —— 证据索引

论文中的每一个数字都由已提交的脚本从本目录派生，从不手工抄录。这里放两类东西：

- **`evidence/`** —— 冻结、只读的保管记录：逐 episode 的脱敏产物（提交的 `flow_config.json`、评分细项、流式传输诊断、agent 日志）、运行前冻结清单、随机化排程，以及把每批付费 episode 运行时生效的确切代码钉死的 `path → sha256` 成员清单。`scripts/frozen_membership_verify.py` 会复核全部 1065 条钉；`scripts/check` 每次运行都会调用它。
- **顶层** —— 各阶段的采集报告，以及论文直接读取的派生产物。这些同样不手工编辑；每个文件都写明了生成它的脚本。

在本分支上，本目录只保留论文研究的三个语义交接（semantic handoff）家族的证据。基准测量产物（baseline 扫描、排行榜、任务清单、各 track 分布）、可靠性层报告、被 phase-7c 取代的 phase-6 冻结清单，以及 `archive/`（结果为饱和的探针）都随其描述的 track 一起移除 —— 清单与从 `master` 取回的方法见 [`../docs/REMOVED.zh.md`](../docs/REMOVED.zh.md)。

## 哪份报告支撑哪个论断

完整的论文↔文件对应见 [`../docs/artifact_map.zh.md`](../docs/artifact_map.zh.md)。简版：

| 论文位置 | 报告 |
|---|---|
| 表 2，S0 / S1 / S2-M 行 | `synthetic_p14_study1_ledger.json`（由 `scripts/phase7c_study1_ledger.py` 生成） |
| 表 2，STA 行（S2-F） | `synthetic_phase7a_sta72_report.json` |
| 表 2，SPICE 行（S2-F 天花板） | `synthetic_phase5c_collection_report.json` |
| 表 7 台账；所有 `\Stat*` 宏 | `synthetic_p14_study1_ledger.json`、`synthetic_p14_claim_statistics.json` |
| 表 9，三实例试点 | `synthetic_phase5d_collection_report.json` |
| §5 Terminal-Bench 2.0→2.1 编码 | `synthetic_phase7c_terminalbench_audit.md`、`evidence/phase7c_terminalbench/` |
| §5 传输截断事件 | `synthetic_p14_qwen_0009_fairness_anchor.*`（未解决）→ `synthetic_p14_qwen_0009_stream_anchor.*`（已解决） |
| §5 SPICE 动作面假阳性 | `synthetic_phase5c_spice_forensic_audit.json` |
| 附录 F 冻结点、项目账目 | `synthetic_p14_phase4z_freeze_manifest.json` |
| 附录 F 家族独立性（5 条准则） | `synthetic_phase5_independence_check.json` |

## 顶层报告

**研究 I —— workflow 家族（p14）。** 消融链，按实际运行顺序排列。同一条件若在两个运行窗口中测过，两份报告都保留；台账刻意不做去重，因为窗口之间的不一致本身就是证据：*k*=4 下的组件结果不足以稳定到可以命名一个机制。

| 报告 | 承载内容 |
|---|---|
| `synthetic_p14_v5_0006_constraint_graph_probe` | 语义角色绑定机制的起点：第一个真实的能力难度信号（DeepSeek 2/3，含一个逐字节确认的"自信但错"episode；Qwen 3/3） |
| `synthetic_p14_v5_0006_deepseek_k5_preserved` | 0006 信号在 *k*=5 下的表现（4/5，一次全局赋值错误） |
| `synthetic_p14_v4_0005_deepseek_calibrated` · `_k5_preserved` · `_preserved_followup` | 0005 链：混合的解出与"自信但错"episode |
| `synthetic_p14_semantic_role_controlled_pair_probe` | 首个受控对：DeepSeek 0009 0/3 对 0010 3/3 |
| `synthetic_p14_qwen_0009_fairness_anchor` | 该锚点**未解决** —— 因非流式传输截断长推理模型而测量无效。论文表 3，执行层 |
| `synthetic_p14_qwen_0009_stream_anchor` | 同一锚点改走 SSE 流式：错轴失败复现（2/3） |
| `synthetic_p14_balanced_controlled_pair` | 平衡 2×2 × *k*=3：完整 bundle（含 C6）把两个模型都推到 3/3 |
| `synthetic_p14_phase4w_run1` · `_run2` · `_heldout` | BundleS 在开发实例、其重复窗口，以及预先冻结的留出实例上的结果（论文 S0 与 S1） |
| `synthetic_p14_phase4x_dev` · `_stage1b` · `_stage1c` | Schema 对 Contract 的分解 |
| `synthetic_p14_phase4y_stage1` · `_phase4y2_stage2` · `_phase4y3_stage3` · `_phase4y3_c24_bridge` | 组件消融：仅 C1、仅 C2、仅 C4、C24 桥 —— 均未隔离出稳定组件 |
| `synthetic_p14_phase4z_freeze_manifest` · `_synthesis` | 附录 F 背后的阶段矩阵、冻结点与项目账目 |
| `synthetic_p14_phase4z_figures_tables.md` | 生成的图表转储（`scripts/phase4z_figures_tables.py`） |
| `synthetic_p14_study1_ledger.json` · `synthetic_p14_claim_statistics.json` | 论文 `\input` 的两个派生产物 |

**研究 II —— 跨家族探针（p15 STA、p16 SPICE）。**

| 报告 | 承载内容 |
|---|---|
| `synthetic_phase5a_design.json` | 预先声明的跨家族设计（仅设计，无付费调用） |
| `synthetic_phase5_independence_check.json` | 五条结构性独立准则的机械核验 |
| `synthetic_phase5b_eval_set_report` · `_gate_report` · `_phase5c_budget` | 评测集构建、运行前门禁、已提交的预算 |
| `synthetic_phase5c_collection_report` | 家族 B（SPICE）：Base = BundleS = TypedContract = 1.00，无判别力的天花板 |
| `synthetic_phase5c_spice_forensic_audit.json` | 曾把 12 个 SPICE episode 误判为零、从而掩盖了该天花板的动作面假阳性 |
| `synthetic_phase5d_collection_report` | 三实例 STA 试点（论文表 9），其描述性方向被前瞻面板反转 |
| `synthetic_phase7a_sta12_construction` | 十二个前瞻 STA 实例的构建 |
| `synthetic_phase7a_sta72_report` | 前瞻面板：72 个 episode，Base .208 / BundleS .333 / TypedContract .458 |

**研究 III —— 测量效度。**

| 报告 | 承载内容 |
|---|---|
| `synthetic_phase7c_terminalbench_audit.md` | 26 项 Terminal-Bench 2.0→2.1 修复在冻结的四层量表下的编码：1 直接、21 部分、4 在外；采样层为 0 |

## 重新生成派生产物

```bash
python3 scripts/phase7c_study1_ledger.py --check       # 台账：58 项目主体 + 12 受控对 = 70
python3 scripts/phase7c_claim_statistics.py --check    # 区间、敏感带、p 值、试点表
python3 scripts/phase4z_figures_tables.py              # 图表转储
```

`--check` 从 `evidence/` 重新计算并与已提交的 JSON 比对，一旦漂移即以非零码退出；去掉 `--check` 则改写文件。两个脚本都会把各阶段的 episode 数与冻结的项目清单相互断言，不一致就中止 —— 早先一次对同一批记录的聚合用 (condition, model) 作字典键，静默丢掉了同一条件的重复测量；仅靠写下纳入规则并不能阻止这种失效。
