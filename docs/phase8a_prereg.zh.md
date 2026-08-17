**[English](phase8a_prereg.md) | 中文**

# Phase-8A 预注册 —— 在替代后端上为 S2-F 面板提供检验效能，并增设一个 S3 臂

本文件即预注册。它会在**第一个付费 episode 之前**提交，并记录其 sha256。该 commit 之后，下文任何内容都不得
修改；一旦修改，即意味着另起一个新阶段、另写一份新的预注册。

## 1. 这项研究为何存在

### 1.1 被冻结的测量装置已不可达

`reports/evidence/*/frozen_config.json` 中的每一份冻结配置都钉死了服务端点：

```json
"model": { "name": "Qwen3.7-Max", "endpoint_host": "llmapi.paratera.com",
           "api_base_env": "BASE_URL", "api_key_env": "API_KEY",
           "rates_cny_per_M": { "input": 12, "output": 36 } }
```

2026-08-17 用同一份凭据查询该端点，得到的是：

```
GET  /v1/models            -> 200，8 个模型：PaddleOCR-VL-0.9B、GLM-4-Flash、GLM-CogView3-Flash、
                              GLM-Z1-Flash、Intern-S2-Preview、PaddleOCR-VL-1.5、GLM-4.5-Flash、GLM-4V-Flash
POST /v1/chat/completions  -> 403 "team not allowed to access model.
                              This team can only access models=[...上述 8 个...]"
```

`Qwen3.7-Max` 与 `DeepSeek-V4-Pro` 均已无权限。**因此，冻结的 episodes 无法在产出它们的那套装置上继续扩展。**
目前通往这两个 model ID 的唯一通路是另一家服务商 `tokenrhythm.studio`，其 `qwen3.7-max` 与 `deepseek-v4-pro`
均返回 200。

这件事本身被作为一项发现记录下来。一套测量装置在冻结后数月内悄然更迭，而它之所以可被察觉，仅仅因为托管记录钉住
的是端点、而不只是模型名。这正是对本文核心论点的直接佐证：泛化的全域中包含着无人抽样、也无人控制的侧面。

**EDA 装置则未发生变化**，这种不对称很关键：PrimeTime 经
`/data1/tongsb/eda-remote-shim/EDA/soft2/synopsys/prime/V-2023.12/bin/pt_shell` 响应，报告版本
`S-2021.06-SP5`，与 `reports/evidence/` 下记录 495 次的版本一致。判分链
（`generators/p15_sta_handoff/grade_sta_handoff.py`、`eda_agentbench/evaluator/sta_handoff.py`）经 sha256
钉定，逐字节原样复用。测量中恰好只有一个侧面发生了变化，而我们能指名道姓地说出是哪一个。

### 1.2 本研究瞄准的论断，以及 k 为何是瓶颈

Phase-7A 在 **k=2** 下测量了 12 个 STA instance × 3 个条件。此时单个 instance 的正确率只能取 0、0.5 或 1。
正是这种粗粒度——而非 instance 数量——造就了已报告的面板构成：

| Phase-7A，n=12，k=2 | 数量 |
|---|---|
| Base 与 BundleS 均为 0 的 instance（"地板"） | 6 |
| 两者均为 1 的 instance（"天花板"） | 1 |
| 存在非零对比的 instance（"有信息量"） | 5 |

真实正确率为 0.2 的 instance，在 k=2 下约有 64% 的概率读出 (0, 0)，所以那 6 个"地板" instance 无一被真正确立。
由此得到的估计为 +12.5 pp，区间 [-12.5, +41.7] 跨越零点，论文将 S2-F 报告为**未确立**。

补救方案是论文自己点名的（`submission/main.tex:324`）：S2-F *"可以通过一个前瞻冻结、且其检验效能足以把预注册的、
具有实际意义的效应与零区分开的面板，向迁移方向得到解决。"* 在同一批冻结 instance 上提高 k 就是这个方案，而且它
比任何替代路径都便宜。

### 1.3 预算为何投向 STA 家族

两个家族的单 episode 实测成本相差约 21 倍：

| 家族 | 实测 | 依据 |
|---|---|---|
| p14 workflow | **¥12.71/ep**（约 856k 输入 token/ep） | 8 ep = ¥101.67 |
| p15 STA | **¥0.605/ep** | 72 ep = ¥43.56 |

可用的 ¥200 只够买约 15 个 workflow episode，无法把 S0/S1/S2-M 从 Fisher p=0.4 上撼动；同样的 ¥200 能买约 330
个 STA episode，那才是真正的检验效能。论文之所以不测 S3，原因并非成本——`main.tex:325` 对此写得很明确——但成本
确实决定了论文自己点名的诸项补救中哪一项负担得起，而只有 STA 那一项负担得起。

## 2. 设计

自 Phase-7A **原样沿用**：instance、条件、区组化原则、分析单元、统计层级、episode 参数。发生变化的是：k，以及后端。

- **Instance** —— 同样的 12 个，`p15_eval_0004` .. `p15_eval_0015`，取自
  `scripts/phase7a_sta12_specs.py`。与 Phase-7A 一致，先导 instance `p15_eval_0001..0003` 不计入主分析。
  不新增、不重新生成、不改写任何 instance。
- **条件** —— `Base`、`BundleS`、`TypedContract`，即任务目录
  `tasks/p15_sta_handoff/{inst}_{base,bundles,typedcontract}`。
- **k = 6**，每个 instance 每个条件（原为 2）。
- **区组化** —— 区组 =（instance × 模型）= 18 个 slot。每个区组由 3 个条件的 6 个排列拼接而成，因此每个条件在每
  连续三元组中恰好出现一次，在区组的每个三分之一段中恰好出现两次。带种子（`20260817 + arm`），由
  `scripts/phase8a_schedule.py` 生成，并在任何调用之前冻结。
- **分析单元** —— 任务 instance（n=12）；6 次重复为嵌套观测。**216 条轨迹不等于 n=216。**
- **主要分析** —— `BundleS - Base`，instance 级配对：对非零 instance 对比做精确双侧符号检验，另加 instance 内
  置换检验作敏感性分析。**次要分析** —— TypedContract vs Base，以及 TypedContract vs BundleS。该层级在此冻结：
  不做自适应 k，不做轨迹汇池 p 值，不做依赖结果的重新分析。
- **Episode 参数** —— temperature 0.7、max_tokens 32000、max_actions 60、episode 超时 1800 秒、并发 1；与
  `reports/evidence/p14_phase4y/frozen_config.json` 一致。
- **传输** —— `EDA_BENCH_STREAM_RESPONSES=1` 为强制项。两个模型都会输出独立的 `reasoning_content` 通道，而
  非流式传输会经由 socket 静默超时在推理中途截断思考型模型，把传输层假象记录成模型失败。请求静默超时 120 秒，
  硬性请求截止 300 秒，与冻结配置一致。

### 2.1 两个臂

| 臂 | 模型（配置名） | model_id | k | episodes | 目标论断 |
|---|---|---|---|---|---|
| 1 —— 主 | `Qwen3.7-Max-TR` | `qwen3.7-max` | 6 | 216 | 为 **S2-F** 提供效能 |
| 2 —— 次 | `DeepSeek-V4-Pro-TR` | `deepseek-v4-pro` | 受成本闸门约束 | <= 216 | 填充 **S3** |

臂 2 是"第二个后端与一个独立家族的交叉"，正是 `main.tex:325` 所述 S3 之所需。为何运行它并不属于该节所禁止的做法，
见 §5。

### 2.2 预算：¥200 上限，以及对臂 2 的纯成本闸门

`deepseek-v4-pro` 标注了两档上游价格（每 1M 输入/输出 ¥12/¥24 与 ¥3/¥6），故臂 2 的成本介于约 ¥25 到约 ¥98
之间，总额有可能突破 ¥200。因此臂 2 的 k 由下述规则确定，**在臂 1 完成之后、臂 2 的第一个计入分析的 episode 之前**
求值：

```
remaining = 200 - spent_arm1 - 10            # 预留 ¥10 用于替补
r         = 由一个 6-episode 的 DeepSeek 成本探针实测得到的 ¥/episode
                                             # 该探针仅用于测成本：不计入任何分析，花费 <¥3
k2        = 满足 12 * 3 * k * r <= remaining 的 {6, 4, 2} 中最大的 k
若无 k 满足：臂 2 不运行，并如实报告为未运行
```

该闸门**只读取成本**。它从不读取任何分数、正确率、对比量或任何结果。k2 在臂 2 第一个计入分析的 episode 之前确定，
此后绝不修改。

### 2.3 停止规则

- 硬性支出上限 **¥200**。若预计支出将超出，则停止。
- 替补由仲裁器驱动（`scripts/episode_arbiter.py`，经 `scripts/chain_executor.py`）：仅限终态无效、同槽位、
  不改动顺序、**最多 2 次替补随后 STOP**。已恢复的传输降级绝不触发替补。
- 基础设施超时、网关错误（包括已在该服务商上观察到的瞬时 503）或 worker 故障属于**测量无效**，绝不是能力失败。
- **一个有效的错误分数是硬失败，绝不允许用重试消解掉。**
- 结余预算**不得**用于追加任何 cell、instance、条件或模型。因为有结余就去花掉，正是本程序存在的意义所要防止的
  那种依结果调整的做法。

## 3. 本研究可以主张与不可主张的内容

- 其 episodes 与已冻结的 70 个 workflow、72 个 STA episodes **不可汇池**。后端不同即测量不同。二者并列报告，
  绝不相加、平均、相减，也绝不合并为同一个 n。
- 此处的复现是**该设计在新后端上的复现**。这比同栈重复是更强的检验，而且是目前唯一可行的检验。
- 臂 2 **为本研究**填充 S3。已投稿手稿的 S3 单元格保持为空，本结果绝不回填其中。
- §1.1 记录的后端更迭，作为关于测量耐久性的发现来报告，而非关于任何模型的结果。

## 4. 验证义务

- `scripts/check` 必须报出其未变的基线：0 failed、结构校验 84/84、
  **1065 pins / 9 missing / 2 mismatch / 1 multi-sha**。任何被钉定的字节都不得移动。
- 四项冻结分析必须仍然通过 `--check`：`phase7c_study1_ledger`（70 episodes）、
  `phase7c_claim_statistics`（12.5 / [-12.5, 41.7] / -16.7）、`phase7d_semantic_proxy_gap`（169/82）、
  `phase7e_answer_identifiability`（294 候选全域；9-147）。
- `submission/` 必须仍能逐字节重建出已打标签的 PDF。
- 该调度必须在 `phase8a_schedule.py --check` 下复现，且每个区组的位置平衡均为真。
- episode 的 `cost_cny` 总和必须 <= ¥200，且必须与报告的总额相等。
- 每个 episode 都必须带有 `terminal_transport_valid`；任何无效 episode 由仲裁器分类，绝不判分。

## 5. 预先回答那一个可预见的质疑

`submission/main.tex:325` 拒绝填充 S3，其原话是：*"我们宁可让它保持未测量，也不愿在看到 S2-F 的结果之后再补一个
单元格：为回应不利结果而扩充证据，正是本文的标准所要防止的那种依结果调整的做法，而且它本就不会是预注册过的。"*
而 Phase-8A 包含一个 S3 臂。这一表面张力必须得到回答，否则该臂的 S3 解读将被扣下不报：

1. §325 所禁止的，是**为回应某项研究自身的不利结果而在未预注册的情况下扩充其证据**。臂 2 并不是 Phase-7A 分析中
   新增的一个单元格。那份分析已冻结并打了标签，且在本工作之后仍逐字节复现——§4 要求我们证明这一点。
2. 臂 2 的目标、k 规则、统计层级与停止规则都固定在本文件中，并在第一个付费调用之前被哈希。就唯一有分量的意义而言，
   它是预注册过的。
3. 臂 2 **本就不可能**成为 Phase-7A 的一个单元格。它所运行的后端不在冻结程序之中，而当时所用的后端如今已不再提供
   该模型。
4. 它作为**本研究的** S3 来报告，绝不并入已投稿论文的表 2。

若在结果出来后这四条无法全部如实成立，则臂 2 只报告为"已运行"，其 S3 解读扣下不报。绝不为了挽救某个表述而抬升
一项发现。

## 6. 执行顺序

1. 冻结提交：本文件、两份调度、相关脚本及其测试，在干净工作树上提交。
2. `scripts/phase8a_preflight.py` —— 零模型调用；每一道闸门都必须通过。
3. 臂 1：经钉定的 `scripts/chain_executor.py` 运行 216 个 episode。仅报告提交。停下。
4. 成本探针，计算 k2，运行臂 2。仅报告提交。
5. `scripts/phase8a_report.py`，随后是双语的结论撰写。

出现以下情况即停止并报告：preflight 失败、工作树不干净、预计支出越过 ¥200、某个槽位需要第三次替补，或出现一个
有效的错误分数。
