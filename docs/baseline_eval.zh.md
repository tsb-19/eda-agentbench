**[English](baseline_eval.md) | 中文**

# 模型基线评测

如何让真实大模型跑 EDA-AgentBench,并产出模型之间的对比排行榜。

基准本身是「工具落地、离线」的:`evaluate-dataset` 只跑 `solution`/`buggy` 两种校准模式。
本基线工具补上了缺失的那座桥——**模型 → 提交 → 评分**——以两个独立脚本实现,**不改动评测核心**。

## 为什么推理与评分要分离

大模型推理是联网 API 调用,评分要跑商用 EDA 工具。把两者解耦,既让 harness 保持简单,也让每一步在
最合适/可行的地方运行:

1. **推理**——`generate_model_submissions.py` 对每道题各调一次模型,写出提交目录,之后**不再**调模型。
2. **评分**——`run_model_baseline.py grade` 只跑评分器(不调模型):
   - 读报告赛道(P3、P6 综合 QA、P8)无需工具 → 任何机器都能评;
   - 真跑工具赛道需要 EDA 工具在 `PATH` 上。

这是一次**单轮(single-shot)**基线:模型只看一次提示 + 文件就交出修改结果,**不**根据工具反馈迭代。
带工具反馈的 agentic 迭代评测是后续单独的赛道。

## 前置条件

1. 复制模型配置模板,填入要对比**哪些**模型(密钥从环境变量 / `.env` 读取,绝不写进文件):

   ```bash
   cp configs/baseline_models.example.json configs/baseline_models.json
   # 编辑:name、api_key_env、api_base、model_id、temperature、max_tokens
   ```

   `configs/baseline_models.json` 与 `.env` 均已 git 忽略。每个 spec 从 `api_key_env` 读取密钥;
   缺密钥时工具会**直接报错**,而不会悄悄退化成 mock(只在「仅验证链路」的空跑时用 `--allow-mock`)。

2. 导出密钥(或写进 `.env`):

   ```bash
   export MIMO_API_KEY=...      # 或 OPENAI_API_KEY=... 等
   ```

## 步骤

### 1. 生成提交(本地,会调用 API)

```bash
STAMP=$(date +%Y%m%d_%H%M%S)
python3 scripts/generate_model_submissions.py tasks \
    --models configs/baseline_models.json \
    --sample-per-track 15 --seed 42 \
    --out runs/baseline/$STAMP/submissions
```

产出 `runs/baseline/$STAMP/submissions/<模型>/<赛道>/<task_id>/<可编辑文件>`,外加每题一份
`transcript.json`(原始回复 + token 用量)和顶层 `manifest.json`(抽样任务 + 每赛道 `needs_tool`
标志)。抽样与 `evaluate-dataset --sample-per-track N --seed S` **完全一致**,同样的 `(seed, N)`
永远选到同一批题。

网关瞬时错误(HTTP 429 限流、5xx、超时)会按指数退避自动重试(`--max-retries`,默认 5);若某模型
被限流,可加 `--sleep 1` 在每次调用间节流。这关乎公平——未重试的 429 会把该模型记 0 分、污染其排名。

### 2. 本地评分读报告赛道

```bash
python3 scripts/run_model_baseline.py grade \
    --submissions runs/baseline/$STAMP/submissions --only local \
    --results runs/baseline/$STAMP/results
```

### 3. 评分真跑工具赛道

```bash
python3 scripts/run_model_baseline.py grade \
    --submissions runs/baseline/$STAMP/submissions --only tool \
    --results runs/baseline/$STAMP/results
```

真跑工具赛道(P1/P2/P4/P5/P6约束/P7)会调用真实 EDA 工具,因此 VCS、HSPICE、Design Compiler、
PrimeTime、SpyGlass **必须装在 `PATH` 上**。请在装有这些工具的机器上评分。读报告赛道与工具赛道的
结果会汇入同一个 `results/` 目录(每个 `模型/赛道/任务` 一份 JSON)。

> 环境说明:若你的 EDA 工具在另一台机器上,那属于环境特定问题——可自行提供一层透明的 `PATH` 垫片
> 把工具调用转发过去。这类垫片**不属于本基准**(基准默认工具在本机),请放在仓库之外。

### 4. 渲染排行榜

```bash
python3 scripts/run_model_baseline.py leaderboard \
    --results runs/baseline/$STAMP/results --stamp $STAMP
# 写出 reports/model_baseline_$STAMP.{md,csv}
```

报告按模型给出:**分赛道**的平均 `total_score` 与通过率、跨赛道宏平均、**各赛道的模型分差**
(哪些赛道最能区分强弱),以及所有推理/解析错误的明确清单(记为已评分,不会被悄悄丢弃)。

## 怎么读结果

- **PASS** = `total_score >= 0.5`(基准阈值)。
- 所有模型都 ~1.0 的赛道已**饱和**(太简单);分差大的赛道有**区分度**;全 ~0 的赛道**过难或提示
  有问题**。
- 解析失败(模型没按 `<<<FILE: ...>>>` 约定输出)会回退为「把整段回复当作文件内容」;其计数会被
  报告出来,便于区分「模型格式不守约」与「确实没做对」。

## 评分链路自检

为确认评分链路本身可靠,用同一套工具去评参考解 `solution/`,应处处得 1.0:

```bash
python3 -m eda_agentbench evaluate-dataset tasks \
    --sample-per-track 15 --seed 42 --submission-mode solution
```

## 可复现性与成本

- 相同 `--seed` / `--sample-per-track` → 完全相同的题集(已在 `tests/test_model_baseline.py`
  中断言)。配置里用 `temperature: 0.0` 让回复更稳定。
- 成本 ≈ `每赛道抽样数 × 10 赛道 × N 个模型` 次推理(15 时约 150/模型)。工具赛道评分为
  `7 个工具赛道 × 抽样 × N` 次评分器运行。
- 先用 `--track p3_timing_report_qa --allow-mock`(无密钥、零成本)验证链路是否打通。
