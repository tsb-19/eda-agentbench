**[English](manuscript_repositioning_v13.md) | 中文**

# 手稿重新定位提案 —— 把测得的结果放到框架之前

## 状态：仅为提案。本文件不改动任何手稿。

`submission/` 依 `CLAUDE.md` 硬约束第 3 条冻结在手稿 v12，且当前可逐字节复现重建（`bbf948bf…`，
268 459 字节，15 页，已在 `make distclean` 之后验证）。把下面任何文字应用到 `submission/main.tex`
都会破坏这一逐字节可复现性，并使 `submission/FREEZE_HASHES.md` 中记录的哈希失效。那是需要作者明确
作出的决定，**这里不作**。本文件的存在，是为了让措辞可以被审阅和争论，而 v12 保持完好。

## 这次重新定位依据什么

一项冻结后的分析，只从实验冻结点及其之前已提交的记录重新推导——没有模型调用、没有 EDA 工具运行、
没有新 episode。来源：`scripts/phase7d_semantic_proxy_gap.py --check` →
`reports/synthetic_phase7d_semantic_proxy_gap.json`。

| 分层 | n | 语义正确 | 语义错误 | 工具代理接受 | 误接受 | 工具信号恒定 |
|---|---|---|---|---|---|---|
| workflow program-primary | 49 | 33 | 16 | 49 | 16/16 | 是 |
| STA 前瞻（7A） | 72 | 24 | 48 | 72 | 48/48 | 是 |
| STA phase-5C | 12 | 5 | 7 | 12 | 7/7 | 是 |
| STA phase-5D | 18 | 7 | 11 | 18 | 11/11 | 是 |
| SPICE phase-5D | 18 | 18 | 0 | 18 | ——（负对照） | 是 |

202 条纳入考虑的轨迹中保留 169 条；33 条被排除而非填补。工具成功信号接受了 **169/169**，其中包括
全部 **82** 条语义错绑。该结论逐层成立，因此从不依赖对一个异质总体的合并。

## 一句话概括这次改动

v12 的摘要开篇是 *"We introduce a claim-scope framework for harness interventions in LLM agents."*
这个框架是真实的、也应保留，但它是一种**限定论断的方式**——读者在见到任何结果之前，先见到了一种描
述方法。上面测得的发现是具体的、可核验的、好记的，而且直接关于基准设计，所以它应当排在前面。

## 建议的摘要开头

用两句替换第一句，v12 其余各句保持不变：

> In our tool-green semantic-binding benchmarks, professional tool success is insufficient to
> determine task correctness: across 169 frozen trajectories with pairing-verified tool outcomes,
> family-specific tool-success signals accepted every run, including all 82 semantically incorrect
> bindings. We therefore evaluate task success with typed provenance/authority oracles that attest
> whether submitted values occupy the correct semantic roles, rather than with tool success alone.

开头的限定短语 **"In our tool-green semantic-binding benchmarks"** 是承重的，不得为了精简而删去。
去掉它，这句话就会被读成关于智能体评测的普遍论断，而这些数据并不支持（见"不得主张什么"）。

## 建议的引言逻辑链

1. **问题。** 工具可以对一份配置签核通过，而该配置的取值被绑定到了错误的类型化语义角色，因此工具
   成功无法判定任务是否正确。
2. **解法，早已存在。** 类型化来源/权限 oracle，检查每个提交值是否是来自足够可信权威的边的目标——
   而不是看工具退出状态。这不是一项提案，它是整个实验程序所依赖的评分基座。
3. **量化。** 在 169 条已验证配对的冻结轨迹上工具信号是常量，因此测得的每一分判别力都来自 oracle。
   SPICE-5D 表明 oracle 不会制造分歧：当智能体把每个角色都绑对时，oracle 与工具 18/18 一致。
4. **然后才是科学问题。** 有了一个能看见这种失败的测量之后，harness 澄清干预究竟能迁移多远？
5. **答案。** 对 Qwen 在实例内观察到，并在一个预先冻结的留出实例上复现过一次；跨模型未确立，跨家族
   未确立，二者联合从未测量。
6. **两层权威性。** 工具判决必须绑定到它声称评判的产物；而 oracle 的权威性继承其隐藏参考标准的保管。

## 建议的贡献排序

1. **工具接地智能体的语义感知评测。** 在三个可执行 EDA 家族中把工具执行成功与语义任务正确分开，并
   量化出工具成功代理在 169 条已验证配对轨迹上没有判别力，其中包括全部 82 个真实智能体错绑。
2. **语义绑定失败本身。** 两个从未被合并的子类型——角色轴绑定错误，以及角色正确但取值选择错误——
   以真实的、工具通过的智能体轨迹呈现。
3. **harness 效应的适用范围。** 在上述测量之上研究：Qwen 局部与同族为正；DeepSeek 未确立；前瞻 STA
   面板未确立且方向与其试点相反；SPICE 处于无判别力的天花板。claim-scope 框架在这里发挥作用。
4. **测量的权威性。** 判决—产物配对与参考标准保管，作为实证展示，而不是一份事故清单。

## 58 之中那 9 条配对排除放在哪里

测量有效性一节，一句话，不进摘要：

> Hash-based pairing excluded 9 of 58 historical workflow episodes whose recorded tool verdict did
> not attest the final submitted artifact; tuple equality alone would have missed seven of the nine.

要把它写成原则，而不是缺陷计数：**只有当两个判决在来源链上绑定到同一个对象时，它们才可以互相比较。**
workflow 的智能体可以先对配置 A 跑证据链、拿到绿色工具结果，然后提交配置 B；那个绿色结果并不随之转移。
这与参考标准保管属于同一类问题，只是低一层。**不要**写成"我们有九个 episode 评分错了"——冻结 grader
早已通过 `stage_chain == 0.0` 独立标记了它们；新的东西是：**事后**做配对分析时，必须重新验证配对，
而不能假定它成立。

## 采用此定位之前必须引用的先行工作

其中两篇已在 `submission/references.bib`，三篇不在，而且近到审稿人会预期看到。

| 状态 | 工作 | 为何限定了我们的论断 |
|---|---|---|
| 已引（`abc`） | arXiv:2507.02825 —— *Establishing Best Practices for Building Rigorous Agentic Benchmarks* | 把任务有效性/结果有效性/报告整理为清单 |
| 已引（`protocolval`） | arXiv:2607.22368 —— *Do Agent Benchmarks Measure Capability? Protocol Validity in the Age of Agentic AI* | 形式化"目标能力是否仍为成功之必要"，并用 Mislead gap 量化分数膨胀 |
| **缺** | arXiv:2605.10448（2026-05-11），Gao & Zhou —— *Can Agent Benchmarks Support Their Scores? Evidence-Supported Bounds for Interactive-Agent Evaluation* | 其引例正是只验证表层事件（"点了 Save"）而未确立目标状态变更；提出证据层与 Pass / Fail / Unknown 标签，在五个公开基准上给出 evidence-supported score bounds |
| **缺** | arXiv:2605.11039（2026-05-11），Fan 等 —— *The Granularity Mismatch in Agent Security: Argument-Level Provenance…*（PACT） | 给工具参数赋予语义角色、跟踪来源、检查角色专属权限契约——概念空间紧邻，但目标是运行时安全强制，而非基准评分 |
| **缺** | arXiv:2607.24054（2026-07-27），Luo & Peng —— *Success Is Not Self-Explanatory: Auditing Success Provenance in Agent Evaluation* | 通过成对的 CLEAN / GOLD / SHAM 干预，审计正确结果是否来自被允许的信息 |

arXiv:2605.10448 早于 v12 冻结，且是三篇中最近的一篇；它在 v12 中的缺席是一个真实的暴露面，与是否
采用本次重新定位无关。

在这五篇之下站得住的边界表述：

> We do not claim to be first to observe that outcome success can be unearned. We study a specific
> value-to-role misbinding inside executable professional workflows: the agent submits a
> configuration a real commercial tool fully accepts, while the correct evidence is bound to the
> wrong typed semantic role. We identify these with provenance-attested semantic scoring, and
> measure that the tool-success proxy loses all discrimination on real agent trajectories.

## 不得主张什么

- 不是*"智能体基准存在 100% 的语义误接受率"*。这些家族本就被**构造**成错绑仍然工具通过。1.0 的比例
  表明构造按规格生效，并量化了它对测量的代价。
- 不是总体率。各分层跨越阶段、条件、模型与运行窗口，并不构成同一个抽样框；应分别报告。
- 不是两个发现。因为工具信号恒定，`Δ = S_tool − S_semantic ≡ 1 − S_semantic`。Δ 属于附录。
- 不是定理。"约束只容许唯一满足赋值时 oracle 会拒绝一切错误绑定"是生成器的**构造性质**（294 → 1），
  不是证明。把它包装成 theorem，只会招来"这不就是你自己构造的吗"这一正确反驳。

真正非平凡的部分是行为性的而非定义性的：工具通过但语义错误的区域不只是在生成器的候选空间里可达——
真实智能体进入了它 82 次。

## 本文件需要的那个决定

两条路，选择权在作者：

1. **让 v12 保持冻结。** 本文等待下一次投稿。逐字节可复现性与 `FREEZE_HASHES.md` 继续有效。
   2605.10448 的暴露面也继续存在。
2. **有意识地修订。** 应用摘要/引言/贡献列表的改动，加上三条缺失引用，并在同一个 commit 内重新推导
   `FREEZE_HASHES.md`，同时在 `docs/provenance.md` 中明确写出：v12 已投稿版本与 v12 在树版本自此不同。

无论选哪条，都不增加实验，也不改变任何冻结任务语义。上面每个数字都已提交，并可由
`python3 scripts/phase7d_semantic_proxy_gap.py --check` 重新推导。
