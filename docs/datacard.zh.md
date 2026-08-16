**[English](datacard.md) | 中文**

# 数据卡 —— 三个语义交接家族

## 概要

84 个任务目录，分属三个独立构建的家族，外加一份保留的资产底料。它们**不是**基准排行榜：每个家族实例化同一个构念 —— *语义绑定* —— 而设计是诊断性的，检验存在性、复现性、天花板行为与迁移方向。它无法估计总体通过率，也不试图去估计。

| 家族 | 目录 | 任务目录数 | 工具 | 待绑定元组 | 论文角色 |
|---|---|---:|---|---|---|
| workflow | `tasks/p14_workflow_handoff/` | 27 | PrimeTime | (netlist, clock, scenario, corner) —— PVT 轴 | 研究 I：S0、S1、S2-M |
| 家族 A —— STA | `tasks/p15_sta_handoff/` | 46 | PrimeTime | 由权威溯源 DAG 得出的 (intent_class, target_partition, check_mode) | 研究 II：S2-F |
| 家族 B —— SPICE | `tasks/p16_spice_handoff/` | 10 | HSPICE | 由请求–权威联接得出的 (corner, load_condition, metric) | 研究 II：S2-F 天花板 |
| *底料，不是家族* | `tasks/p13_trajectory_handoff/` | 1 | — | — | 供 p14 生成器读取；无任何论断依赖它 |

p15 的 46 个目录是 15 个实例 × 3 个条件加一个 dev 实例；p16 的 10 个是 3 × 3 加一个 dev。论文的前瞻 STA 面板是实例 0004–0015（*n*=12）；0001–0003 是试点，**从不**与面板合并。

## 构念

每个任务都是一次**语义交接**：从*角色误导性*的证据中，把一个元组绑定到规范的类型化角色上。难点刻意不是检索。在工作实例中，证据文件把它们的轴字段标为 `op_point` 与 `mode`，而歧义变体不附术语表也不附轴声明，因此"每个标签指哪个逻辑轴"本身就必须从各来源的交集中还原出来。

让该构念可被测量的性质是 **tool-green**：错误的绑定仍会产生绿色的工具签核。在工作实例中，随附的四份证据源在 PrimeTime 下全部签核为绿，包括那份两个角色字段被互换的。没有任何工具信号能把它们与真值区分开 —— 只有类型化 oracle 能。一个按工具退出码给这个任务计分的基准，会把错误绑定判为通过。

正确性在构建期由穷举决定，而非由评分器判断：对工作实例而言，在声明的取值域上有 294 个候选赋值，其中恰有一个满足五条可还原的约束。

## 条件

三个条件的隐藏真值与评分器完全相同；只有可见信息不同。

| 条件 | agent 能看到什么 |
|---|---|
| **Base** | 歧义的交接。不披露该实例的赋值，无术语表，无轴声明 |
| **BundleS** | 规范标签（C1）、取值域定义（C2）、术语表（C4）、流程契约（C7）。**不含 C6** —— 没有 golden 值，没有实例赋值 |
| **TypedContract** | 与 BundleS 相同的信息，表达为 JSON Schema |

BundleS 是**与实例答案无关**，而不是"无答案"：它扣留该实例的目标元组，但刻意披露*任务级的角色语义* —— 某个标签指哪个轴、每个轴接受哪些取值。称其"无答案"会低估它。schema 与生成器结构*联合起来*是否允许还原出某个赋值，是另一个尚未解决的问题；论文点明了能解决它的泄漏检查，并把它标为尚未进行的、信息量最大的那一个实验。

组件定义见 [`synthetic_p14_phase4w_clarity_bundle_ablation_design.md`](synthetic_p14_phase4w_clarity_bundle_ablation_design.md)。

## 目录形态

```
<instance>/
  prompt.md          交接简报
  metadata.json      机器可读规格（见 task_schema.zh.md）
  files/             可见；其中指名的子集可编辑。证据源放在这里
  hidden/            永不进入 agent 工作区：隐藏真值、类型化评分器、可信生成器
  solution/          golden 提交
```

对工作实例而言，`files/` 有 25 个可见文件，其中 5 个可编辑；`hidden/` 有 11 个 —— 包括 `handoff_truth.json` 与 `grade_workflow.py`。agent 工作区只由可见+可编辑文件构建；评分在第二个工作区中进行，那里叠加了 `hidden/`。见 [`agentic_runner.zh.md`](agentic_runner.zh.md)。

## 家族独立性

独立性由五条预注册的结构性准则定义 —— 独立的模板、词汇、真值、评分器、诱饵 —— 且是机械核验而非口头声明：`scripts/phase5a_independence_check.py` → `reports/synthetic_phase5_independence_check.json`。它对每个新的生成器/评分器/评测器做哈希，并断言：没有一个导入 p14 的评分器或生成器；角色词汇互不相交；新的真值文件不含 p14 的任何键；评分器模块使用不同的主门禁模式；诱饵配方类别不同。一旦发现结构重叠，冻结即被阻止。

通过意味着*在这些准则下未检测到重叠* —— 它不证明独立性。而论文对残余局限直言不讳：三个家族都由我们自己撰写，且都在 EDA 之内，所以这里的跨家族迁移更应读作"同一设计宇宙内的跨生成器迁移"，而不是跨领域迁移。

规格见 [`synthetic_phase5a_family_specs.md`](synthetic_phase5a_family_specs.md)、[`synthetic_workflow_generator_spec.md`](synthetic_workflow_generator_spec.md)。

## 准入门禁

一个实例只有同时通过两项才被接受：

- **唯一性** —— 穷举恰好得到一个满足约束的赋值。
- **硬可行性** —— 烘焙必须产出一个错误绑定的产物，它能被工具接受、能执行、能给出貌似合理的签核，却在语义上是错的，并且*确实*被类型化 oracle 拒绝。一个平凡地工具报红或无法解析的错误绑定会使该实例不合格并被重新生成。每个实例都把这五条准则与评分器的拒绝结果记入 `hard_feasibility.json`。

## 评分

权重按家族划分；主证据门禁把类型化成员判定折进去，因此一个签核为绿但类型错误的包无论其他分项如何都无法通过。

| 家族 | 分项 |
|---|---|
| p14 workflow | `signoff` .10 · `final_state` .15 · `evidence_generation` .25 · `stage_chain` .10 · `provenance` .10 · `authority_consistency` .10 · `hazard_recovery` .10 · `explanation` .10 |
| p15 STA | `provenance_attested` .30 · `coverage_cell_consistent` .20 · `check_view_legal` .10 · `pt_signoff_green` .10 · `not_masking` .15 · `explanation` .15 |
| p16 SPICE | `semantic_binding` .30 · `evidence_provenance` .20 · `simulation_success` .10 · `numeric_validity` .10 · `artifact_completion` .15 · `protocol_completion` .15 |

请注意 p15 中 `pt_signoff_green` 值多少：0.10。工具成功只是一个分项，绝不是裁决。两种绝不合并的失败子类型以及 oracle 的判定谓词见 [`scoring.zh.md`](scoring.zh.md)。

## 资源限制

三个家族都用**standard** 预设，难度 `hard`。超时：p14 为 600 秒（它要重新生成两阶段的证据链），p15 与 p16 为 300 秒。

## 溯源与已知局限

- **已冻结。** 每个实例都处于实验冻结 HEAD 或其之前；任务语义不得改动。见 [`provenance.zh.md`](provenance.zh.md)。
- **保管。** 逐 episode 字节比对、每个 episode 前后的规范哈希核验，以及由 `scripts/frozen_membership_verify.py` 核验的 1065 条 `path → sha256` 成员钉。
- **两个生成器在冻结之后漂移。** 论文报告的数字来自被钉住的版本；漂移被如实报告而非抹去。
- **九个被钉住的构建产物缺失。** 九个 p16 实例下的 `circuit_built.sp` 是被 gitignore 的 HSPICE 产物；清单在运行时钉住了它。
- **面板很小。** S0、S1、S2-M 各自只依赖单实例单元、*k*=3–4。没有任何单元达到论文的*已泛化*层级。
- **没有人类验证。** 正确性由可执行 oracle 判定，它们内部自洽且实例唯一，但未被证明与专家人类判断一致。盲法人类研究已预注册但从未执行。
- **未匿名化。** 见 [`REMOVED.zh.md`](REMOVED.zh.md)。
