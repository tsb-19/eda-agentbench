**[English](scoring.md) | 中文**

# 评分 —— 正确性如何判定

唯一要紧的规则：**语义正确性绝不从工具是否成功推断出来。** 不看退出码，不看隐藏的数值答案，也不看产物总分。它只由一件事判定：提交的元组是否与独立的溯源/权威 oracle 所证实的绑定一致。

这不是风格偏好。在工作实例中，随附的*每一份*证据源在 PrimeTime 下都签核为绿 —— 包括那份两个角色字段被互换的。一个读工具退出码的评分器会把错误绑定判为通过，而论文的整个失败类别都将不可见。

## 主证据门禁

每个家族的评分器都有一个主门禁 —— workflow 家族里是 `EVIDENCE_OK` —— 而类型化判定谓词是**折进它里面**的，而不是与它并列计分。因此，一个签核为绿但类型错误的包，无法靠在别处攒分而通过。

workflow 的门禁要求每个必需阶段都与一次隐藏重跑一致，*并且*下列类型化谓词成立：

- scenario 字段必须属于 scenario 轴，corner 字段必须属于 corner 轴；
- 两者都不得是 **PVT 描述符** —— 描述符指的是一个 scenario–corner *对*，永远不是任一轴的取值；
- 时钟必须**按精确身份**匹配，因此泛化的别名会被拒绝；
- 网表必须属于声明的家族。

下游标记（`TYPED_BINDING_OK`、`AXIS_SCHEMA_OK`、`PVT_LABEL_OK`，以及约束图命名）只是用不同名字重新报告已经被门禁裁定的结论。它们是诊断量，不是额外的通过机会：错误的 scenario 或 corner 早已让 `EVIDENCE_OK` 崩掉。

## 两种绝不合并的失败子类型

一次失败恰好被归入两类之一。论文全程把它们分开，因为它们是不同的认知错误，且干预对它们的作用不同：

| 子类型 | 定义 | 例子 |
|---|---|---|
| **错轴绑定失败** | 某个取值占据了**错误的类型化轴** | `func`/`slow` —— corner 的取值落在 scenario 角色上，反之亦然 |
| **角色条件取值选择失败** | 取值的轴与类型都合法，但填进角色的是**错误的成员** | `typ`/`func` —— 貌似合理、类型正确，但被权威否证 |

在 70 个 episode 的研究 I 台账中：41 正确、**24 错轴**、**5 角色条件** —— 全部 tool-green，仅被类型化 oracle 拒绝。把两者合并会掩盖论文的核心观察，因为该观察恰恰是关于*轴*错误的：BundleS 对应零例观察到的错轴失败，而歧义基线三次里错两次。

家族 A 的一个例子：可见证据证实 intent=`functional_close`、partition=`core`、check_mode=`setup`；agent 提交 (functional_close, core, **both**)。PrimeTime 返回绿灯且 `both` 类型合法 —— 但覆盖率权威证实的是 `setup`，因此 oracle 将其判为角色条件取值选择失败。

## 唯一性在评分之前就已确立，而非评分时确立

在声明的取值域上穷举是在构建期完成的，且必须恰好得到**一个**满足该实例约束的赋值 —— 工作实例是 294 个候选 → 1。因此"正确"由该实例的约束系统固定，评分器只做成员检查。没有评分器的主观判断，也没有余地在事后为"说得过去但不同"的答案争论。

## 权重

按家族给部分分。注意工具成功值多少。

**p14 workflow** —— `signoff` 0.10 · `final_state` 0.15 · `evidence_generation` 0.25 · `stage_chain` 0.10 · `provenance` 0.10 · `authority_consistency` 0.10 · `hazard_recovery` 0.10 · `explanation` 0.10

**p15 STA（家族 A）** —— `provenance_attested` 0.30 · `coverage_cell_consistent` 0.20 · `check_view_legal` 0.10 · `pt_signoff_green` 0.10 · `not_masking` 0.15 · `explanation` 0.15

**p16 SPICE（家族 B）** —— `semantic_binding` 0.30 · `evidence_provenance` 0.20 · `simulation_success` 0.10 · `numeric_validity` 0.10 · `artifact_completion` 0.15 · `protocol_completion` 0.15

`pt_signoff_green` 与 `simulation_success` 各占 0.10：工具必须跑起来，但相比正确绑定元组，"跑起来"几乎一文不值。`explanation` 从不占主导。

`not_masking` 值得一说。它抓的是这样一种 agent：靠*削弱检查*而不是靠正确绑定来换到绿色签核 —— 做法是统计声明例外的指令，并对超出那唯一一条预期例外的任何未声明削弱予以标记。这是"治症状而非解任务"的标志，论文中的掩蔽案例得 0.4，而 golden 得 1.0。

workflow 家族中"tool-green 错误绑定"的可识别分数特征是 `signoff = 1.0` 而 `evidence_generation = 0` —— 工具满意，链条不成立。

## 反作弊

先结构性，后黑名单。评测器会：

- 在执行前对禁改文件做 sha256 快照，执行后核验 —— `hidden/`、公共测试脚本、运行脚本；
- 拒绝**隐藏影子**：agent 不得伪造一个文件去遮蔽评测器叠加层提供的隐藏产物（评分器、oracle、golden 网表）；
- 洗净 agent 提供的 Tcl：可编辑的 `.sdc` 用 `read_sdc` 摄入（它会沙箱化 Tcl 的 `proc`/`exit`），再用 `write_sdc` 规范化重写；随后在一个不运行任何 agent 代码的独立阶段计算裁决。注入的 `proc incr {} {}`、`exit 0` 或 `echo CONSTRAINTS_OK` 都无法触及或伪造裁决；
- 另外在工具运行之前，把明显的注入尝试标为显式违规（硬零分并记录）。该黑名单是*次级*层 —— 它可以被间接手法绕过，而这正是"保证完整性的是上面的结构性洗净、而不是这张表"的原因。

实现在 `eda_agentbench/anti_cheat/guard.py`、`eda_agentbench/task/validator.py`；测试在 `tests/test_anti_cheat.py`、`tests/test_phase5_hidden_isolation.py`。

## 公平性门禁

在信任任何模型分数之前，先让**已知正确的解**走同一条路径。它必须得 ≈1.00。若达不到，说明评分器或环境正在扭曲测量，那条路径上的任何分数都毫无意义 —— 这道检查曾抓到一个真实的 shim 缺陷，它把某个 track 上的每个分数都变成了同一个错误数值。

逐任务的 golden−buggy 客观分差还必须 ≥ 0.15：未修复的输入不得像修复过一样得分。`scripts/validate_dataset.py` 把两者在整个家族上自动化。

## 测量效度高于评分

只有测量有效，分数才算结果。基础设施超时、网关错误或 worker 失败属于**测量无效**，绝不计为能力失败。反向规则被同样严格地执行，而且更要紧：**有效的错误分数是硬失败**，不许被重试掉。`scripts/fairness_retry.py` 只对基础设施故障放行重试；`scripts/episode_arbiter.py` 是"该 episode 是终态有效还是仅为恢复态"的权威。见 [`reproducibility.zh.md`](reproducibility.zh.md)。
