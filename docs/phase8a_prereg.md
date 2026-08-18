**English | [中文](phase8a_prereg.zh.md)**

# Phase-8A preregistration — powering the S2-F panel, and an S3 arm, on a replacement backend

This document is the preregistration. It is committed and its sha256 recorded **before the first
paid episode**. Nothing below may be changed after that commit; a change means a new phase with a
new preregistration.

## 1. Why this study exists

### 1.1 The frozen apparatus is no longer reachable

Every frozen configuration in `reports/evidence/*/frozen_config.json` pins the serving endpoint:

```json
"model": { "name": "Qwen3.7-Max", "endpoint_host": "llmapi.paratera.com",
           "api_base_env": "BASE_URL", "api_key_env": "API_KEY",
           "rates_cny_per_M": { "input": 12, "output": 36 } }
```

That endpoint, queried on 2026-08-17 with the same credential, now answers:

```
GET  /v1/models            -> 200, 8 models: PaddleOCR-VL-0.9B, GLM-4-Flash, GLM-CogView3-Flash,
                              GLM-Z1-Flash, Intern-S2-Preview, PaddleOCR-VL-1.5, GLM-4.5-Flash, GLM-4V-Flash
POST /v1/chat/completions  -> 403 "team not allowed to access model.
                              This team can only access models=[...the 8 above...]"
```

Neither `Qwen3.7-Max` nor `DeepSeek-V4-Pro` is entitled any more. **The frozen episodes therefore
cannot be extended on the apparatus that produced them.** The only route to those two model IDs is
now a different provider, `tokenrhythm.studio`, where `qwen3.7-max` and `deepseek-v4-pro` both
answer 200.

This is recorded as a finding in its own right. A measurement apparatus turned over within months
of the freeze, silently, and it is detectable only because the custody records pinned the endpoint
rather than just the model name. It is direct evidence for the paper's own thesis that the universe
of generalization contains facets nobody samples and nobody controls.

The **EDA apparatus is unchanged**, and that asymmetry matters: PrimeTime answers through
`/data1/tongsb/eda-remote-shim/EDA/soft2/synopsys/prime/V-2023.12/bin/pt_shell` and reports
`S-2021.06-SP5`, the version recorded 495 times under `reports/evidence/`. The grading chain
(`generators/p15_sta_handoff/grade_sta_handoff.py`, `eda_agentbench/evaluator/sta_handoff.py`) is
sha256-pinned and is reused byte-identical. Exactly one facet of the measurement changed, and we can
name it.

### 1.2 The claim this study targets, and why k is the binding constraint

Phase-7A measured 12 STA instances x 3 conditions at **k=2**. A per-instance rate can then only be
0, 0.5 or 1. That coarseness — not the instance count — is what produced the reported anatomy:

| Phase-7A, n=12, k=2 | count |
|---|---|
| instances where Base and BundleS both scored 0 ("floor") | 6 |
| instances where both scored 1 ("ceiling") | 1 |
| instances with a non-zero contrast ("informative") | 5 |

An instance whose true rate is 0.2 reads as (0, 0) about 64% of the time at k=2, so "floor" is not
established for any of those 6. The resulting estimate is +12.5 pp with a band of [-12.5, +41.7]
spanning zero, and the paper reports S2-F as **not established**.

The manuscript names the remedy itself (`submission/main.tex:324`): S2-F *"could be resolved toward
transfer by a prospectively frozen panel powered to distinguish a preregistered, practically
meaningful effect from zero."* Raising k on the same frozen instances is that remedy, and it is
cheaper than any alternative.

### 1.3 Why the money goes to the STA family

Measured per-episode cost differs by a factor of ~21 between the two families:

| family | measured | source |
|---|---|---|
| p14 workflow | **¥12.71/ep** (~856k input tokens/ep) | 8 ep = ¥101.67 |
| p15 STA | **¥0.605/ep** | 72 ep = ¥43.56 |

The ¥200 available buys ~15 workflow episodes, which cannot move S0/S1/S2-M off Fisher p=0.4; the
same ¥200 buys ~330 STA episodes, which is real power. Cost is not the reason the paper leaves S3
unmeasured — `main.tex:325` is explicit about that — but cost does decide which of the paper's own
named remedies is affordable, and only the STA one is.

## 2. Design

Carried over from Phase-7A **unchanged**: instances, conditions, blocking principle, analysis unit,
statistical hierarchy, episode parameters. Changed: k, and the backend.

- **Instances** — the same 12, `p15_eval_0004` .. `p15_eval_0015`, from
  `scripts/phase7a_sta12_specs.py`. Pilots `p15_eval_0001..0003` are excluded from primary, as in
  Phase-7A. No instance is added, regenerated or reworded.
- **Conditions** — `Base`, `BundleS`, `TypedContract`, i.e. task directories
  `tasks/p15_sta_handoff/{inst}_{base,bundles,typedcontract}`.
- **k = 6** per condition per instance (was 2).
- **Blocking** — block = (instance x model) = 18 slots. Each block is 6 concatenated permutations
  of the 3 conditions, so every condition appears exactly once per consecutive triple and exactly
  twice in each third of the block. Seeded (`20260817 + arm`), emitted by
  `scripts/phase8a_schedule.py`, frozen before any call.
- **Analysis unit** — task instance (n=12); the 6 reps are nested observations.
  **216 trajectories are not n=216.**
- **Primary** — `BundleS - Base`, instance-level paired: exact two-sided sign test over non-zero
  instance contrasts, plus a per-instance permutation sensitivity. **Secondary** — TypedContract vs
  Base, and TypedContract vs BundleS. This hierarchy is frozen here: no adaptive k, no
  trajectory-pooled p-value, no outcome-dependent reanalysis.
- **Episode parameters** — temperature 0.7, max_tokens 32000, max_actions 60, episode timeout
  1800 s, concurrency 1; matching `reports/evidence/p14_phase4y/frozen_config.json`.
- **Transport** — `EDA_BENCH_STREAM_RESPONSES=1` is mandatory. Both models emit a separate
  `reasoning_content` channel, and non-streaming transport censors thinking models mid-reasoning
  via the socket-inactivity timeout, recording a transport artifact as a model failure.
  Request inactivity timeout 120 s, hard request deadline 300 s, as frozen.

### 2.1 Arms

| arm | model (config name) | model_id | k | episodes | target claim |
|---|---|---|---|---|---|
| 1 — primary | `Qwen3.7-Max-TR` | `qwen3.7-max` | 6 | 216 | powers **S2-F** |
| 2 — secondary | `DeepSeek-V4-Pro-TR` | `deepseek-v4-pro` | cost-gated | <= 216 | populates **S3** |

Arm 2 is a second backend crossed with an independent family, which is what `main.tex:325` states
S3 requires. See §5 for why running it is not the practice that section forbids.

### 2.2 Budget: ¥200 cap, and a cost-only gate on arm 2

`deepseek-v4-pro` is advertised at two upstream tiers (¥12/¥24 and ¥3/¥6 per 1M in/out), so arm 2
costs somewhere between ~¥25 and ~¥98 and the total could breach ¥200. Arm 2's k is therefore fixed
by the following rule, evaluated **after arm 1 completes** and **before arm 2's first analysed
episode**:

```
remaining = 200 - spent_arm1 - 10            # ¥10 held back for replacements
r         = measured ¥/episode from one 6-episode DeepSeek cost probe
                                             # probe is COST-ONLY: excluded from all analysis, <¥3
k2        = max k in {6, 4, 2} such that 12 * 3 * k * r <= remaining
if no k qualifies: arm 2 is NOT run, and is reported as not run
```

The gate reads **cost only**. It never reads a score, a rate, a contrast or any outcome. k2 is
fixed before arm 2's first analysed episode and is never revised afterwards.

### 2.3 Stop rules

- Hard spend cap **¥200**. If projected spend would exceed it, stop.
- Replacement is arbiter-driven (`scripts/episode_arbiter.py` via `scripts/chain_executor.py`):
  terminal-invalid only, same slot, ordering unaltered, **max 2 replacements then STOP**. Recovered
  transport degradation never replaces.
- An infrastructure timeout, gateway error (including the transient 503 already observed on this
  provider) or worker failure is **measurement-invalid**, never a capability failure.
- A **valid wrong score is a hard failure and is never retried away.**
- Surplus budget is **not** spent on additional cells, instances, conditions or models. Spending a
  surplus because it exists is the outcome-adaptive practice this program exists to prevent.

## 3. What this study may and may not claim

- Its episodes are **not poolable** with the frozen 70 workflow or 72 STA episodes. Different
  backend means a different measurement. The two are reported side by side and are never summed,
  averaged, differenced or pooled into one n.
- A reproduction here is a reproduction **of the design on a new backend**. That is a stronger test
  than same-stack repetition, and it is the only test now available.
- Arm 2 populates S3 **for this study**. The submitted manuscript's S3 cell stays empty, and this
  result is never backfilled into it.
- The backend turnover documented in §1.1 is reported as a finding about measurement durability,
  not as a result about any model.

## 4. Verification obligations

- `scripts/check` must report its unchanged baseline: 0 failed, 84/84 structural,
  **1065 pins / 9 missing / 2 mismatch / 1 multi-sha**. No pinned byte may move.
- All four frozen analyses must still pass `--check`: `phase7c_study1_ledger` (70 episodes),
  `phase7c_claim_statistics` (12.5 / [-12.5, 41.7] / -16.7), `phase7d_semantic_proxy_gap` (169/82),
  `phase7e_answer_identifiability` (294 universe; 9-147).
- `submission/` must still rebuild byte-identically to the tagged PDF.
- The schedule must reproduce under `phase8a_schedule.py --check`, with position balance true for
  every block.
- Summed episode `cost_cny` must be <= ¥200 and must equal the reported total.
- Every episode must carry `terminal_transport_valid`; any invalid episode is arbiter-classified and
  never graded.

## 5. The one foreseeable objection, answered in advance

`submission/main.tex:325` declines to fill S3, in these words: *"We leave it unmeasured rather than
adding a cell after seeing the S2-F outcomes: expanding the evidence in response to an unfavourable
result is the outcome-adaptive practice this paper's standard exists to prevent, and it would not
have been preregistered."* Phase-8A includes an S3 arm. That apparent tension is answered, or the
arm's S3 reading is withheld:

1. What §325 forbids is **expanding a study's evidence in response to its own unfavourable result,
   un-preregistered.** Arm 2 is not an added cell in Phase-7A's analysis. That analysis is frozen
   and tagged, and re-derives byte-identically after this work — which §4 requires us to prove.
2. Arm 2's target, k rule, statistical hierarchy and stop rule are fixed in this document and
   hashed before the first paid call. It is preregistered in the only sense that carries weight.
3. Arm 2 **could not have been** a Phase-7A cell. The backend it runs on was not in the frozen
   program, and the backend that was no longer serves the model.
4. It is reported as **this study's** S3, never merged into the submitted paper's Table 2.

If all four cannot be stated truthfully once results exist, arm 2 is reported as having run and its
S3 reading is withheld. A finding is not upgraded to rescue a framing.

## 5A. Amendment 1 (2026-08-17, before the first analysed episode)

**What changed.** `max_chat_retries` is raised from the frozen **1** to **6**. Nothing else moves:
instances, conditions, k, blocking, analysis unit, hierarchy, temperature, max_tokens, max_actions,
episode timeout, concurrency, streaming, request-inactivity timeout and hard deadline all stay as
§2 states. So the differences from Phase-7A are now **three**: k, backend, and retry budget.

**Why.** The replacement backend throttles. Measured before any analysed episode:

| probe | result |
|---|---|
| 20 requests back-to-back | 13/20 ok — **35% failure** |
| 12 requests at 15 s spacing | 11/12 ok — **8.3% failure** |
| one full pilot episode | 15 logical requests took **38 physical attempts**; 23 failed; 433 s spent in retry backoff |

The driver backs off `3*2^attempt`, so at the frozen `--max-chat-retries 1` the two attempts land
3 s apart, inside the throttled regime. A pilot episode died exactly that way after one action. At
~15 calls per episode most episodes would have terminated as measurement-invalid and the
2-replacement cap would have stopped the chain inside the first block. At 6 retries the same
episode completed with `terminal_transport_valid: true`.

**Why this does not weaken the comparison.** A retry re-issues an identical request. It cannot
change the prompt, the task, the evidence, the tool or the grader, so it cannot change task
semantics or what a correct binding is. The arbiter remains the sole membership authority and still
classifies each episode. And this is the project's own rule applied rather than bent: an
infrastructure timeout or gateway error is measurement-invalid and must **never** be recorded as a
capability failure. Leaving retries at 1 on a backend that fails 35% of burst requests would have
recorded a throttle as a model failure — the exact error the rule exists to prevent.

**What it does cost.** Retry backoff dominates wall clock: a measured episode took 660 s, of which
433 s was sleeping. That is ~40 h per arm rather than the ~14 h the frozen pace implied. It does not
raise spend — measured cost is ¥0.447/episode, so 216 episodes is ≈¥97.

**Mechanism.** `scripts/phase5c_run.py` passes the flag on the command line and CLI beats env, so
the run goes through `scripts/chain_executor.py --runner scripts/phase8a_episode_runner.py`, which
leaves the retry budget env-configurable. chain_executor, episode_arbiter, llm_agent_driver, the p15
grader and the evaluator all remain pinned and byte-identical; the new per-episode runner decides
nothing about membership. Going through chain_executor additionally gains `--integrity-manifest`,
which verifies the canonical tree before the run, after **every** episode, and post-chain.

This amendment is recorded rather than folded into §2 silently: a preregistration that is edited to
match what was done is not a preregistration. It was decided and committed before the first episode
that enters the analysis.

## 5B. Amendment 2 (2026-08-18, before the next analysed episode)

**Nothing in the design moves.** Instances, conditions, k, blocking, analysis unit, statistical
hierarchy, episode parameters, transport and the ¥200 cap are all exactly as §2 and §5A state. This
amendment records one corrected measurement and one execution rule, both fixed in advance.

### 5B.1 The per-episode cost was underestimated by 2.15x

§5A projected **¥0.447/episode** from a single pilot. Block 00 — the first complete block, 18
episodes on `p15_eval_0004` — measured:

| | measured |
|---|---|
| block 00, 18 episodes | **¥17.3244** |
| per episode | **¥0.962** |
| by condition (mean) | Base ¥1.272, BundleS ¥0.742, TypedContract ¥0.873 |

The cause is retry billing. `phase8a_episode_runner._cost` sums every entry in
`request_telemetry`, and each retried attempt re-sends the whole prompt, so the retry budget
Amendment 1 raised to 6 is itself the multiplier. Amendment 1 asserted that retries "do not raise
spend"; on measurement that was wrong, and the estimate is superseded here rather than quietly
replaced.

### 5B.2 Consequence: the cap is unchanged, so the panel may stop short of 12 instances

At ¥0.962/episode the full arm projects to **12 x ¥17.3244 = ¥207.9**, above the cap. §2.3 says stop,
and stopping is what happens: **the ¥200 cap stays**, and arm 1 runs as many whole blocks as it buys.
Projected from the measured rate:

```
spent to date            ¥17.884   (block 00, plus block 01's aborted pass -- see 5B.3)
blocks still affordable   10        gate: start a block only if remaining > 18 x ¥0.962
panel delivered           n = 11    p15_eval_0004 .. p15_eval_0014
instance not run          p15_eval_0015
projected final spend    ~¥191.1   leaving ~¥8.9, i.e. below §2.2's ¥10 holdback
arm 2                     NOT RUN, and reported as not run
```

**Which instance is dropped was decided before any episode ran.** The block order is the frozen,
seeded schedule (`seed 20260818`, instance-ascending `p15_eval_0004 .. p15_eval_0015`), so the cap
truncates the *tail of a fixed list*, never a set chosen after seeing results. That is the whole
point of recording this now: an n=11 panel accepted in advance on arithmetic is a power limit, while
an n=11 panel selected afterwards would be the outcome-adaptive practice §5 exists to prevent.

The primary sign test is reported at whatever n the cap delivers, with n stated. No k is reduced to
buy the twelfth instance: k=6 is the entire reason this study exists, and trading it for breadth
would reintroduce exactly the k=2 coarseness §1.2 diagnoses.

`scripts/phase8a_run.py --per-slot` now defaults to the measured ¥0.962 rather than a guessed ¥0.7.
A projection below the true rate would let the gate authorise a block the budget cannot cover, so the
gate is cap-protecting only if it is fed the measurement.

### 5B.3 An aborted block pass is discarded whole, and re-executed whole

Block 01 (`p15_eval_0005`) aborted after 2 of 18 slots: the provider returned `502` on three
consecutive attempts at `Base/pos1` and the arbiter correctly reached STOP. That is a
measurement-invalid infrastructure fault, not a capability failure, and the block is re-run.

`chain_executor.py` restarts a block at position 0 and `phase8a_episode_runner.py` overwrites a
trial's custody directory, so a plain re-run would overwrite `p15_eval_0005_typedcontract_r1` — an
episode that had completed **validly**. Overwriting a valid episode is the shape of retrying away a
valid score, which this program forbids. The rule, fixed here:

1. An aborted pass is **archived**, not deleted, under `phase8a/evidence/aborted/<pass>/`, together
   with its `chain_executor` run state.
2. The block is then re-executed **whole**, in frozen order, as a single pass. Nothing is kept
   selectively from the aborted pass — the discard is all-or-nothing and therefore cannot depend on
   any episode's score.
3. The archived pass leaves the **analysis** and stays in the **ledger**: its ¥0.5597 counts against
   the cap (`_aborted_spend` in both `phase8a_run.py` and `phase8a_report.py`), because §4 requires
   summed episode cost to equal the reported total, and money paid is money paid.
4. The archive must sit outside `phase8a/evidence/episodes/`, whose `*/episode.json` glob is the
   grading glob. Nested inside it, the same trial would be graded twice — once from the discarded
   pass and once from the re-run.
5. The three `502` attempts stay visible to the report as measurement-invalid: the aborted run state
   is retained as `run_state_arm1_block01_attempt1.json`, which `phase8a_report._states()` still
   globs. An outage that vanished from the record would understate how much infrastructure noise this
   backend produced.

Point 2 is the part that matters for interpretation. The alternative — keeping the one valid episode
and resuming at position 1 — wastes nothing, but it makes the keep/discard boundary fall between two
episodes whose scores were already known. Discarding the pass whole removes that discretion.

## 6. Execution order

1. Freeze commit: this document, the schedules, the scripts and their tests, on a clean tree.
2. `scripts/phase8a_preflight.py` — zero model calls; every gate must pass.
3. Arm 1: 216 episodes via the pinned `scripts/chain_executor.py`. Report-only commit. Stop.
4. Cost probe, compute k2, arm 2. Report-only commit.
5. `scripts/phase8a_report.py`, then the findings write-up in both languages.

Halt and report if: preflight fails, the tree is dirty, projected spend passes ¥200, a slot needs a
third replacement, or a valid wrong score appears.
