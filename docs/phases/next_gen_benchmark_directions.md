# 下一代 EDA Agent Benchmark：方向调研存档

> **来源**：用户于 2026-06-22 提供的两份外部调研报告（会话 transcript 内有逐字原文）。
> **用途**：留存"将来可做的方向"+ 我（基于本项目实测）的批注。
> **定位**：这是**方向菜单，不是决策**。具体建哪条轨，待 P6/P7 复测结果落地 + 用户拍板后，
> 再写入 `benchmark_hardening_plan.md` §13 并更新记忆。
> **配套记忆**：`next-gen-benchmark-directions.md`（指针 + 蒸馏）。

---

## 0. 核心设计原则（两报告 + 本项目实测，三方收敛）

**一句话判据**：好任务里，**工具输出只提供"症状的投影"，根因永远是多个症状 / 设计意图的隐变量**。
工具反馈必须从"充分条件"降级为"必要条件"——给了它你仍不知道改哪、按什么顺序改、为什么。

报告二给的可证伪锚点（Phoenix-bench）：

- 同一 Agent 从 SWE-bench Verified 迁到 Phoenix-bench **掉 37–58%**。
- **完美的文件级 oracle 定位只 +1.4%**（被告知位置后反而去破坏不该改的文件）；
  **一轮 testcase 反馈却 +42–45%**。
- ⇒ 瓶颈不是"定位"，是"理解信号流因果"。

**工具反馈分层表（最有用的设计判据）**：

| 工具反馈类型 | 暴露根因? | 可被 ReAct 试错刷穿? | 典型任务 |
|---|---|---|---|
| 编译/语法错误行号 | ✅ 直接 | ✅ 极易 | VerilogEval、RTL Debug |
| 仿真失败 + 波形 | ⚠️ 症状非根因 | ⚠️ 中 | HWE-Bench、Phoenix |
| 时序/DRC/PPA 报告（只给指标值） | ❌ | ❌ 难 | PostEDA PPA-Multi |
| CDC/RDC violation 列表（不暴露意图） | ❌ | ❌ 难 | （尚无公开 benchmark） |
| 形式验证 counterexample | ⚠️ 反例非根因 | ⚠️ 中 | AssertLLM/2 |
| 综合 QoR 差异（只给指标） | ❌ | ❌ 难 | RTL-OPT、TuRTLe PPA |

**本项目实测正好填满最顶上"✅ 直接暴露 → 极易刷穿"那一行**（见 §3）。

---

## 1. 报告一要点（benchmark 现状调研 + 候选方向）

### 1.1 公开 benchmark 饱和度判断
- **饱和**（单模块生成 + 功能仿真 pass）：VerilogEval / RTLLM / RTLLM2.0 / OpenLLM-RTL / OpenROAD-Agent 脚本生成。
- **未饱和**（仓库级维护、物理后端、PPA 权衡、约束正确性）：RTL-BenchLS、AssertLLM2、HWE-Bench(SoC级)、Phoenix-bench、PDAgent-Bench、PostEDA-Bench、CVDP。
- 主轴判断：**别再延长 RTL codegen 赛道；切进 repository-scale / physical / post-EDA closure / formal-coverage / multi-tool handoff**。

### 1.2 候选方向（Top10）
1. **ConstraintRoot-Bench** — RTL/netlist/SDC/PT 间定位 setup/hold/exception 真根因
2. PostEDA-Closure-Bench — PPA 多目标收敛 + signoff DRC
3. FlowHandoff-Bench — 给一个被扰动的跨工具 handoff 包，恢复一致性
4. ECO-Causal-Bench — late-stage ECO，Formality 保等价
5. CDC-RCA-Bench — CDC violation/同步器/协议/waiver 间真诊断
6. FormalityMismatch-Bench — 综合/ECO 后 equivalence failure 根因
7. FormalCoverage-Closure-Bench — coverage gap → property → closure
8. AnalogRootCause-Bench — Spectre/StarRC pre→post-layout 寄生根因
9. RepoScale-HWFix-Bench — 仓库级硬件修复（需强 EDA oracle，否则退化成"软件基准的硬件皮肤"）
10. **ExceptionDebug-Bench** — false path/multicycle/generated clock 的语义误用

**报告一 Top5**：ConstraintRoot、PostEDA-Closure、FlowHandoff、FormalityMismatch、CDC-RCA。

### 1.3 其它要点
- 构造路线：mutation injection / constraint perturbation / flow-script corruption / formal-equivalence-as-oracle / hidden regression / metamorphic / golden-vs-mutant / 参数化 generator（RTL/timing/PD）。**最推荐**：constraint perturbation（SDC 是 handoff object，错约束跨阶段传播，工具不报正确修复）。
- 双轨发布：公开版（OpenROAD/开源 + 自动生成）+ 工业版（PT/ICC2/Innovus/StarRC/Spectre/Formality，体现 signoff/handoff 价值）。
- 评分以"能力诊断"为先：任务成功率 + 根因定位 + 修复最小性 + 跨变体鲁棒 + 资源效率，并标注 failure taxonomy。

---

## 2. 报告二要点（三大能力黑洞 + 量化弱区 + 候选 + 构造 + 防刷穿）

### 2.1 三大能力黑洞
1. **跨阶段因果归因**（CDC/RDC 根因、多症状归一）
2. **跨工具联合决策**（MCMM timing/DRC/PPA 多目标权衡修复）
3. **设计意图驱动的约束工程**（SDC/assertion/UPF 的*正确性*而非语法性）

### 2.2 量化弱区（外部 stack 数字，**对我仅作线索，须自测**，见 §3）
- PDAgent-Bench：根因分析 73.3%，**Innovus 脚本生成 42.2%**，长程多阶段弱。
- PostEDA-Bench：**DRC-Reasoning 36.66%，PPA-Multi 20.00%**（瓶颈是"权衡推理"非"knob 知识"）。
- HWE-Bench：小核 >90%，**SoC 级 <65%**。
- OpenROAD-Agent：脚本生成 94%（接近饱和）。
- AssertLLM：仅 18 设计，89% 语法/功能正确但"实际 bug 检测价值有限且不一致"。
- CVDP：Claude-4.5-opus Verilog 生成仅 30.74%。
- EDA log：o3-mini pass@5 达 100%（"解释错误行"已饱和）。
- RTL-BenchLS：1 万+ 形式验证设计（规模是现有 100×，证明参数化生成可行）。

### 2.3 候选方向（12 个，Top10 + 2 备选）
1. **CDC-IntentBench**（CDC/RDC 根因归因 + 意图推断；VC SpyGlass CDC）
2. **MCMM-TradeBench**（多角多模时序权衡修复；PT+StarRC+ICC2-ECO；≤20 PT run）
3. **SDC-AuditBench**（约束正确性审计；SpyGlass-Constraints+DC+PT；constraint perturbation）
4. ECO-CascadeBench（功能 ECO 级联一致性；Formality+PT+ICC2+StarRC+Voltus）
5. PPA-ParetoBench（PPA 帕累托优化；ICC2/Innovus+PT+Voltus；需预计算前沿）
6. FPV-IntentBench（形式属性反推；VC Formal/Jasper）
7. **CrossFlow-DiagBench**（跨工具流程诊断归因；DC+PT+ICC2+StarRC+SpyGlass）
8. DRC-CascadeBench（DRC 级联修复；Innovus+Calibre）
9. **LEC-AttributionBench**（LEC 失败归因；Formality+DC；mutation oracle）
10. Signoff-ConsistencyBench（签核工具一致性；PT+StarRC+Calibre+Voltus）
- 备选：Analog-SizeBench（Spectre）、Waiver-AuditBench（SpyGlass）

**报告二 Top5**：MCMM-Trade、CDC-Intent、SDC-Audit、LEC-Attribution、CrossFlow-Diag。

### 2.4 构造路线可行性（报告二 §4）
最推荐组合：**参数化 Generator 产 golden 设计 + Constraint Perturbation 扰动约束 + Mutation Injection 注缺陷 + Formal Equivalence 作修复正确性 oracle + Hidden Regression 作防作弊层**。完全不依赖真实工业数据，每层可自动扩展。（Mantra 等 19 个硬件 mutation 算子已验证。）

### 2.5 评分体系
- **学术**：主指标=根因定位准确率；辅=修复有效率 / Pareto 距离 / 推理链可解释性；防作弊=hidden mutation 检测率 / hidden corner 不恶化率；分能力维度雷达（归因/权衡/意图/跨工具/多目标）。
- **工业**：主指标=端到端签核级完成率；辅=PPA 改善 / 工程师时间节省 / TAT；可靠性=无 over-fix / 无 false-waive / 回归无回归；按工程角色视角评分。

### 2.6 Model / Harness / Tool 三层分离 + 三基线（**重要方法论**）
- **Model 能力**：固定 harness+工具，换 LLM。
- **Harness 能力**：固定 LLM+工具，换 harness（ReAct/Reflexion/ToT/Plan-Execute）。
- **Tool 能力**：固定 LLM+harness，换工具（OpenROAD vs ICC2）。
- 三基线：**Tool-only 上限**（工具自带最优解，如 PrimeClosure 自动 ECO）/ **Human 参照** / **Random Agent 下限**。
- 有效性判据：Model×Agent ≫ Random 且 ≈ Human 且 **Tool-only ≠ 100%**。

### 2.7 防刷穿武器库（10 条）
1. 根因隐藏在多症状交集（工具输出不含根因标记）
2. 多目标 Pareto 距离评分替 pass/fail（修一个恶化另一个则扣分）
3. **Hidden reverse-mutation**：藏一个"被错约束/错 waiver 掩盖的真 bug"，掩盖即判负
4. 参数化 generator 持续动态生成（季度更新隐藏集）
5. 工具调用次数上限（防暴力搜索；PostEDA 证明 iteration budget 是关键调节变量）
6. Contamination 检测（membership inference）
7. 分层发布（公开 easy 训练 / 隐藏 medium-hard 评测 / private 竞赛）
8. 能力维度分解报告（某维被刷穿，其它维仍区分）
9. 版本化（随工艺节点/工具版本年度更新）
10. 反向对抗（专训"对抗 Agent"刷分，刷穿的题降级）

---

## 3. 我的批注（实测衔接 + 算力可行性 + 搜索塌缩警告 + 纪律）

### 3.1 本项目实测如何印证两报告
- **P6（DC 约束 debug）**：前沿 3 模型（DeepSeek/GLM/Qwen）**真的跑了 dc_shell 并迭代**（DeepSeek 5/5 run→fix→re-verify），**仍全 1.00**。单症状 bug 一次工具运行就完全定位 ⇒ "工具反馈=充分条件"的教科书实例。
- **P5（deck-debug）**：连工具都不跑，纯静态阅读 16/16。
- **P7（PT-STA debug）**：更极端——**答案写在 prompt 里**（"Missing Clock"+周期+端口表+检查清单），落在 §0 表"编译错误行号"之下。
- **P4 sizing（damping/amp-slack/amp-bind）**：三个递增难度设计全在前沿塌缩 ⇒ **带模拟器的闭环搜索不抗前沿**（见 [[damping-track-frontier-collapse]]）。
- 结论：我的轨正好是两报告说的"饱和区"标本，且我有前沿模型的硬收据。

### 3.2 算力可行性过滤（b04 单台远程机）
重工具在并发下已 flake；本轮 Kimi 还被 LLM 网关 429 整列作废、MiniMax 漏 token。把"已接好且已 fairness-gate 验证"的 infra 一过滤：

| 候选 | 工具 | 对我的可行性 |
|---|---|---|
| **ExceptionDebug / SDC-Audit / ConstraintRoot** | DC+PT（已验证） | **near-term 首选**；需升级到"路径级 + hidden-holdout"oracle |
| **LEC-Attribution / FormalityMismatch** | Formality+DC | **near-term**；mutation oracle 天然干净；**待确认 `fm_shell` 在不在 shim** |
| CDC-Intent / CDC-RCA | VC SpyGlass CDC | 中期；有 SpyGlass-lint 痕迹，须确认 CDC 模式；需多时钟域 SoC 参数化 generator |
| MCMM-Trade / CrossFlow / ECO-Cascade / PPA-Pareto | PT+StarRC+ICC2(+Calibre/Voltus) | **最高价值但中期**；多工具闭环在单 flaky 机上构造+评测重，且有搜索塌缩风险（见 §3.3） |
| Analog-Size | Spectre | 中期；连续空间反向优化；报告自评 analog 扩展慢 |

### 3.3 ⚠️ 搜索塌缩警告（我替报告把的最重要的关）
报告二把 **MCMM-Trade 排 #1**。但它的形态是"驱动 ECO 让所有 corner 收敛，≤20 PT run"——本质是**带模拟器的闭环搜索**。我有*三个*独立结果证明前沿模型在多旋钮+竞争 spec 下会在预算内搜到近金标准。**"多目标"本身不抗搜索；真正抗搜索的是 agent 查询不到的东西——hidden corner + 工具永不报告的设计意图。** 承重件是 hidden holdout，不是 multi-objective。
⇒ **若要建 MCMM-Trade，必须先用便宜探针验证"hidden-corner 能否真把搜索者挡住"，否则极可能又一次 sizing 塌缩。**

### 3.4 纪律：外部难度数字 = 假设，不是事实
§2.2 的 20% / 36.66% / 42.2% 来自**别的 stack/模型/预算**。本项目第一原则：**没用我自己的 fairness gate + 我的前沿模型跑过我的路径之前，任何难度数字都不可信**（这条抓出过 P4 全 0.30 shim bug 和 P5 flatten bug，见 [[grading-fairness-gate]]）。任何候选轨：先金标准过门 → 再前沿探针 → 才敢称"难"。

### 3.5 与轨道无关、可立即采纳的硬化件
不管最后建哪条，这些都该上：
- **Hidden reverse-mutation 防作弊层** + **over-constrainer 对抗 agent** + **tool-only 上限基线** → 直接扩展现有 perfect-agent/noop-agent fairness gate。
- **三基线判据**（Tool-only / Human / Random）+ 能力维度雷达，作为"这条轨是否真区分能力"的验收门。
- **真 explanation 评分**（根因链 vs 实际改动一致性）替掉现在的 auto-1.0（P5/P6/P7 现都是装饰性 0.1）。
- 能用处用 **Pareto 距离**替 pass/fail；**工具调用次数上限**防暴力搜索；contamination 检测；版本化。

---

## 4. 三角化候选菜单（决策待定 — 等 P6/P7 + 用户拍板）

两报告独立收敛到大量同一任务族（名字不同），叠加我的算力可行性 + 搜索塌缩警告：

| 任务族 | 报告一名 | 报告二名 | 工具 | 对我排序 |
|---|---|---|---|---|
| 约束正确性 | ConstraintRoot / ExceptionDebug | SDC-Audit | DC+PT | **near-term #1** |
| LEC/等价归因 | FormalityMismatch | LEC-Attribution | Formality+DC | **near-term #2** |
| CDC 意图 | CDC-RCA | CDC-Intent | SpyGlass CDC | 中期 #3 |
| 跨工具归因 | FlowHandoff | CrossFlow-Diag | 多工具 | 中期（重） |
| ECO 级联 | ECO-Causal | ECO-Cascade | Formality+PT+ICC2 | 中期（重） |
| PPA/DRC 物理 | PostEDA-Closure | PPA-Pareto / DRC-Cascade | ICC2/Innovus | 中期（重 + 搜索塌缩风险） |
| MCMM 权衡 | （并入 ConstraintRoot） | **MCMM-Trade（报告二#1）** | PT+StarRC+ICC2 | 中期（重 + **须先验证搜索抗性**） |
| 形式覆盖 | FormalCoverage-Closure | FPV-Intent | VC Formal | 中期 |
| Analog | AnalogRootCause | Analog-Size | Spectre | 中期 |
| 仓库级修复 | RepoScale-HWFix | — | 多工具 | 待定 |

**我的初步建议（非决策）**：near-term 先做 **ExceptionDebug/SDC-Audit（DC+PT，已验证）**，并行确认 Formality 以备 **LEC-Attribution**；MCMM/CrossFlow 列为中期，前置一个"搜索抗性"廉价探针。

---

*最后更新：2026-06-22。下一步：P7 探针落地 → 把 P6/P7 矩阵 + 本菜单 + ExceptionDebug 重设计草案一起呈交 → 用户拍板 → 写 §13 + 更新记忆。*
