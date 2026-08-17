**[English](provenance.md) | 中文**

# 溯源 —— 哪个 commit 产出了什么，以及什么已被冻结

一次测量只有在你能说清"究竟是仓库的哪个状态产出了它"时才是可复现的。本文档把论文的论断落到明确的 commit 上，并说明什么已经不允许再改。它取代了基准时期的状态文档，并吸收了 Phase-6C 的冻结证明。

## 两个明确的 HEAD

| | Commit | 含义 |
|---|---|---|
| **实验冻结 HEAD** | `a89e084` | *"report(phase5d): TypedContract extension complete 36/36"*。**此 commit 之后的任何实验、付费模型调用、任务/模型资产都不对论文有贡献。** 所有报告的数字都是从该 commit 及其之前已提交的台账重新派生的。 |
| **投稿 HEAD（v12）** | `cc797ffe`（标签 `iclr2027-submission-v3`） | 手稿 v12。相对 `a89e084` 仅多出文档与投稿工作 —— 没有新的实验结果。**作为不可变的历史快照保留；v13 不改写它。** |
| **投稿 HEAD（v13）** | `c7b3828a`，以标签 `iclr2027-submission-v4` 发布 | 手稿 v13，已冻结。把 Phase-7D 的事后结果提到 claim-scope 框架之前，新增四条引用，并把 harness 适用范围写成一条局限。**没有付费模型调用、没有新 episode、没有任务语义改动、没有派生实验数字发生移动** —— 三个生成表全部与 v12 逐字节相同。 |

本分支 `iclr2027-artifact` 从 `cc797ffe` 切出，完全不含实验改动：只有删除、文档，以及两个核验脚本。见 [`REMOVED.zh.md`](REMOVED.zh.md)。

### 手稿谱系

| 标签 | Commit | 手稿 |
|---|---|---|
| `iclr2027-submission-v1` | `3d3e77b7` | v5 |
| `iclr2027-submission-v2` | `5858d843` | v7 —— 收敛了研究 I 的 episode 账目（58 项目主体 对 70 条描述性台账） |
| `iclr2027-submission-v3` | `cc797ffe` | v12。证据支撑格、对称的论断资格、与估计量对齐的不确定性 |
| `iclr2027-submission-v4` | 打在记录 `c7b3828a` 的那个 commit 上 | **v13 —— 当前版。** Phase-7D 事后审计成为首要结果：在 169 条已验证配对的冻结轨迹上工具成功信号恒为接受，并接受了全部 82 条语义错绑，因此类型化溯源/权威 oracle 承担了全部测量。仅涉及解读与定位。 |

### v12 的冻结为何被重新打开

冻结的意义在于能够精确回到某个版本，而不是此后不得再有任何版本。有两件事使 v13 成为更站得住的选择。第一，Phase-7D 审计把论文自身的评分基座变成了一个测得的结果——类型化 oracle 一直是评分依据，但它对测量的贡献从未被量化。第二，`arXiv:2605.10448` 在 v12 冻结之前就已公开而 v12 未引用它，因此提交 v12 就意味着交出一个已知定位不完整的稿件。v12 的源码与 PDF 哈希继续被记录，其 PDF 仍可从它自己的 commit 逐字节重建；v13 是一次新的冻结，而不是对 v12 的修订。

**Phase-7D 在每一处出现时都被标注为事后、冻结之后的分析**，手稿与 [`artifact_map.zh.md`](artifact_map.zh.md) 皆然。它没有被当作预注册分析呈现，因为它不是。

## 实验已永久关闭

所有付费模型调用在 `a89e084` 处结束。本仓库中没有任何东西能够、也不应该重开它们：从一次 checkout 到一个新 episode 不存在通路，冻结的任务语义不得改动，手稿的数字已固定。试图"刷新"某个结果，会在没有当初授权那次测量的预注册的情况下改变论文所报告的内容。

**项目账目**（附录 E 与可复现性声明）：58 + 24 + 36 + 72 个付费主体 episode；已提交台账成本 ¥745.29。描述性的研究 I 台账报告 **70** 个 workflow episode —— 即那 58 个加上更早的 12 个受控对 episode，后者早于该账目、也在其成本台账之外。两个计数刻意不同，论文也如实说明；`scripts/phase7c_study1_ledger.py` 会把两者都与冻结的项目清单相互断言，不一致就中止。

## 什么被冻结，以及由什么强制

| 对象 | 冻结方式 | 强制手段 |
|---|---|---|
| 成员代码与任务文件 —— 1020 个任务文件、36 个脚本、6 个生成器文件、3 个包模块；没有任何测试或文档带哈希 | `reports/evidence/` 下运行前清单中的 **1065 条 `path → sha256` 钉** | `scripts/frozen_membership_verify.py`，由 `scripts/check` 调用 |
| `docs/phase7/phase7_synthesis.md` | sha256 记录在 `submission/FREEZE_HASHES.md`（`9dbecd9f…`） | 该文件；此文档不得移动或改动 |
| `docs/synthetic_p14_phase4w_clarity_bundle_ablation_design.md` | 在 `reports/evidence/p14_phase4w_fairness/MANIFEST.json` 中作为预先声明的解释表**按路径**被引用 | 该清单已冻结，故此路径必须保持有效 |
| 三个任务家族 | 逐 episode 保管字节比对；每个 episode 前后的规范哈希核验 | `scripts/canonical_integrity.py`（`FAILED_INTEGRITY` 停机）、`scripts/chain_executor.py` |
| `tasks/p14_workflow_handoff/workflow_handoff_0009/solution/flow_config.json` | 触发线测试 | `tests/test_fullpath_check.py` 中的 `test_canonical_golden_fingerprint_intact` |
| `submission/main.pdf` | Makefile 中钉住的 `SOURCE_DATE_EPOCH` | 重建逐字节一致；sha256 在 `FREEZE_HASHES.md` |

### 保管门禁原样带过来的三项发现

`frozen_membership_verify.py` 报告的计数非零，这是正确的，不是需要"打扫干净"的缺陷。`docs/frozen_membership_baseline.json` 记录了 `cc797ffe` 时的状态：

- **9 个缺失** —— 九个 p16 实例下的 `circuit_built.sp`。HSPICE 构建产物，已被 gitignore；清单在运行时钉住了它们，仓库从未跟踪过。
- **2 处不匹配** —— `generators/p15_sta_handoff_gen.py` 与 `p16_spice_handoff_gen.py` 在 phase-5B/5C 冻结之后被编辑过。**论文报告的数字来自被钉住的版本。** 该漂移是既有状态，被如实陈述而非抹去。
- **1 处多哈希** —— `scripts/phase5c_run.py` 在各阶段间合法地存在多个版本，因此为它钉了多个哈希，"与其中之一不同"并不构成漂移。

门禁断言的是*复现这一基线*，而不是*什么都不报*。一个被调到打印零的核验器，会掩盖下一次真实的改动。

## 探索性对确认性

论文附录 E 已陈述此点；这里给简版，因为它决定了此处任何结果可以怎样被解读：

- **探索性** —— tool-green 错轴失败的发现；传输修复；workflow 受控对；clarity bundle 的构建。**BundleS 是在这一阶段被*挑选*出来的，因此它的开发实例单元（S0）在构造上就是探索性的。** 同样属于探索性的：跨模型臂，以及整个组件分解（C1；Schema 对 Contract；仅 C2、仅 C4、C24 及 C24 桥）。
- **冻结点 1** —— BundleS 固定为 C1+C2+C4+C7 且不含 C6，留出实例也被冻结，**都在**留出评测运行之前。因此 S1 是唯一被描述为"复现了某事"的单元。
- **冻结点 2** —— 对前瞻 STA 研究，实例面板、其规模（*n*=12）、条件、随机化排程与分析方法，全部在*该阶段任何付费调用之前*提交。样本量未做适应性调整；没有任何分析是在看到结果之后才选定的。
- **确认性** —— 前瞻 STA 面板是本研究唯一预注册的迁移确认性检验，而它没有确立效应。

预注册：[`phase7/phase7a_preregistration.md`](phase7/phase7a_preregistration.md)。阶段矩阵与冻结点：`reports/synthetic_p14_phase4z_freeze_manifest.json`。

## 有一项预注册研究从未执行

盲法人类构念效度研究（研究 B）预注册于 [`phase7/phase7b_annotation_freeze.md`](phase7/phase7b_annotation_freeze.md)，标注包由 `scripts/phase7a_annotation_packets.py` 生成。它**未**执行：找不到合格的独立标注者，且**没有用 LLM 标注者顶替**。因此论文主张的是一个形式化构念，而非与专家人类判断的一致性。

## 有一个 episode 因效度原因被替换

`reports/evidence/phase7a_state.json` 记录 `replaced: 1`。被丢弃的产物保存在 `reports/evidence/phase7a_discarded/`，附有记录其原始路径与运行时间戳的说明 —— 它从未进入 git，若在删除原始运行目录树时不先抢救它，就会毁掉论文所披露的那唯一一次"仅因效度"替换的唯一记录。

## 核验本分支

```bash
scripts/check                                          # 测试 + 任务结构 + 1065 条保管钉
python3 scripts/slim_link_check.py                     # 无悬空仓库路径引用
python3 scripts/phase7c_study1_ledger.py --check       # 58 + 12 = 70
python3 scripts/phase7c_claim_statistics.py --check     # 12.5 / [-12.5, 41.7] / -16.7
cd submission && make distclean && make                # 18 页，sha256 不变
```

`make clean` 刻意保留 `main.pdf`；凡是要拿构建日志作为测量依据的场合，先用 `distclean`。曾有一次 v9 的页数测量是从过期 PDF 上取的，因为 `make` 实际是空操作 —— 这也是门禁要去数 pdflatex 启动横幅、而不是相信"日志存在"的原因。

仓库根目录的 `VERIFICATION.md` 记录了本分支每一道门禁的输出。
