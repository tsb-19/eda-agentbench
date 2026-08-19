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

## 5C. Amendment 3 (2026-08-18, before the next analysed episode)

**Nothing in the design changes.** Instances, conditions, k, blocking, analysis unit, statistical
hierarchy, episode parameters, transport settings and the ¥200 cap are all exactly as §2, §5A and §5B
state them. What is recorded here is why arm 1 halted, one measurement fact about billing, and the
application of an existing rule to a second occurrence.

### 5C.1 The binding constraint was the backend's balance, not the ¥200 cap

Arm 1 halted during block 02 (`p15_eval_0006`) with **¥164.07 of the cap unspent**. The provider
returned HTTP `402 {"code":"INSUFFICIENT_BALANCE","message":"余额不足"}` on three consecutive attempts
at `Base/pos12`. The driver classified it `non_retryable_http` and therefore spent no retry on it; the
arbiter reached STOP at the 2-replacement cap, as designed. Every attempt is recorded
`measurement_valid: false`, `classification_source: request_telemetry` — infrastructure, never
capability.

A sweep of all 17 model IDs the backend serves returned `402` for 15, `503 SERVICE_BUSY` for 2, and
`200` for none, while `GET /v1/models` still returned `200` with the full list. The credential was
valid; the account was empty. The exhaustion was **account-level, not per-model**, so no cheaper model
on the same backend was a fallback.

This is recorded as a measurement fact, not a result. **§2.2's ¥200 cap was never the operative stop
rule.** What stopped arm 1 was a backend running out of money while the budget gate reported ¥164.07
available. Note what the ledger figure is and is not: ¥35.9287 is denominated at the **frozen** rates
(¥12/M in, ¥36/M out) so that it stays comparable with the frozen 72 episodes — it is not the
provider's billing statement. The account emptied at ¥35.93 frozen-rate-equivalent, so either this
backend's true rates exceed the frozen ones or the account never held ¥200. The backend exposes no
balance endpoint (6 probed, all 404), so the two cannot be distinguished. The ¥200 figure is an upper
bound on **our ledger**, not a claim about purchasable capacity — and §5B.2's projection of an n=11
panel truncated by the cap is superseded on the facts, exactly as §5B.1 superseded §5A's cost claim.
The projections stay where they are; the outcomes are recorded beside them.

### 5C.2 `max_tokens` does not bound the reasoning channel

A liveness probe sent with `max_tokens: 1` drew **309 completion tokens** from `qwen3.7-max`, 295 of
them `reasoning_tokens`. The parameter bounds the visible completion, not the billed reasoning
channel. This changes no episode setting — §2 keeps `max_tokens` 32000 — but it removes `max_tokens`
as a cost bound and is part of why the balance drained ahead of the ledger's projection. The liveness
probes cost ~¥0.011 at frozen rates; they are probes, not episodes, and enter no analysis.

### 5C.3 The balance was restored, arm 1 resumes, and block 02 is archived under 5B.3

On 2026-08-18 the account was topped up: `qwen3.7-max` and `deepseek-v4-pro` both return `200`. Arm 1
resumes at block 02 under the unchanged design and the unchanged cap. The resumption crosses a
top-up boundary on the serving side; that is not an apparatus change — same endpoint, same model ID,
same rates in our ledger — but it is recorded, because §1.1's whole point is that quiet changes on
the serving side are the hazard this program has to be able to see.

Block 02 completed 12 of 18 primary slots before the `402`. It is an aborted pass, and **§5B.3
applies to it verbatim**: archived whole to `phase8a/evidence/aborted/block02_attempt1/`, re-executed
whole in frozen order, its **¥7.2848 kept in the ledger**, its run state retained as
`run_state_arm1_block02_attempt1.json` so the three `402` attempts stay countable as
measurement-invalid. No new rule is added here. An existing rule is applied to a second occurrence,
which is the entire point of having fixed it before it was needed.

One episode of that pass, `p15_eval_0006_base_r5`, is the third `402` attempt. It left a **gradeable
workspace scoring 0.5 with `total_cost` 0.0** — a score with no evidence of a model call behind it.
`phase8a_report.py:101` already excludes zero-cost episodes from grading, and `phase8a_run.py`'s
guard halted the chain on it rather than walking further into a dead backend. A 0.5 produced without
a model call is precisely what must never reach an analysis.

The ledger invariant holds across the archive: ¥17.3244 (block 00) + ¥10.7598 (block 01) live,
plus ¥0.5597 + ¥7.2848 archived, = **¥35.9287** — unchanged by the move.

Because the backend is purchasable again, §2.2's cost-only gate on arm 2 becomes live again once arm
1 finishes. It is evaluated then, on cost alone, and reported however it resolves.

## 5D. Amendment 4 (2026-08-19, before arm 2's first analysed episode)

**Nothing in the design changes.** Instances, conditions, blocking, analysis unit, statistical
hierarchy, episode parameters, transport settings and the ¥200 cap are exactly as §2 states them.
What is recorded here is the outcome of §2.2's cost gate, one deviation, and three defects found and
fixed before arm 2 could spend anything.

### 5D.1 The gate ran, and it returned k2 = 2

The 6-episode probe (`p15_eval_0001`, `p15_eval_0002`, all three conditions each, pilots only)
measured **r = ¥0.5009/episode** for `deepseek-v4-pro`. §2.2's formula, applied verbatim:

| k | episodes | 12·3·k·r | ≤ ¥67.1825 remaining? |
|---|---|---|---|
| 6 | 216 | ¥108.1944 | no |
| 4 | 144 | ¥72.1296 | **no, by ¥4.95** |
| 2 | 72 | ¥36.0648 | yes |

**k2 = 2. Arm 2 runs at k=2**, 72 episodes, projected ¥36.06 against ¥74.18 of headroom.

k=4 deserves its own sentence, because it is the rung where a preregistration either binds or does
not. It fits under the hard ¥200 cap (projected total ¥197.95) and fails only §2.2's formula, which
reserves ¥10 for replacements. Spending that holdback would have bought k=4 outright. It was not
spent. A gate that yields to a ¥4.95 shortfall is not a gate, and the whole reason k2 was made a
function of a measured quantity was so that this decision would not be mine to make after seeing how
close it came.

### 5D.2 The probe overran its own ceiling by ¥0.0054

§2.2 says the probe spends `<¥3`. It spent **¥3.0054** — 0.18% over. The ceiling is checked *between*
blocks, so a block already in flight cannot be stopped: block 1 ended at ¥1.3626, under the limit,
which authorised block 2, and block 2 cost ¥1.6428. A between-block check can always overshoot by up
to one block's cost; per-episode granularity or a ¥2 trigger would have held, and neither was in
place. It changes no decision (the hard-cap total moves from ¥161.882 to ¥161.888) and it is recorded
as a deviation rather than rounded to the stated figure. The gate's own output carries
`"within_ceiling": false`.

### 5D.3 What k=2 costs this arm, stated plainly

Phase-8A exists because Phase-7A ran at k=2, where a per-instance rate can only be 0, 0.5 or 1 — the
coarseness that produced 6 floor instances, 1 ceiling instance and only 5 informative contrasts.
**Arm 2 at k=2 returns to exactly that granularity.** It is therefore not a powered test of anything
and will not be reported as one. It is the last unfilled cell of the preregistered scope — one
prospective panel on a second model — and its result is descriptive at that resolution whether it
comes out positive, negative or mixed. §3's limits apply to it unchanged and with more force.

### 5D.4 Three defects fixed before arm 2's first episode

None of these had produced a wrong number yet; all three were on the path arm 2 was about to take.

1. **The k ladder below 6 was not executable.** `phase8a_schedule.py` refused any k not divisible by
   3, so k=4 and k=2 — two of §2.2's three preregistered values — could never have been generated. The
   guard's stated reason ("position balance is defined over thirds") was also wrong: blocks are `reps`
   concatenated permutations, so every consecutive *triple* is a permutation at any k, and the
   per-third count is implied whenever k is divisible by 3. The guard now admits exactly the
   preregistered ladder {6, 4, 2} and nothing else — tighter than before, since it previously waved
   through k=3 and k=9. Arm 1's committed schedule still reproduces byte-for-byte.

2. **Arm 2 would have overwritten 72 of arm 1's 216 episodes.** A trial directory is
   `<task_id>_r<rep>` and `rep` restarts at 1 in each arm, so arm 2 at k=2 generates precisely the 72
   names arm 1 wrote at reps 1–2. Both arms wrote `phase8a/evidence/episodes/`. Arm 2 would have
   replaced a third of arm 1's panel with a different model's episodes, and `phase8a_report.py`'s
   single `episodes/*/episode.json` glob would have graded the mixture as one arm — **§1.1's "a
   different backend is a different measurement, never pooled" broken by filename rather than by
   argument, with a report that still looked normal.** Arms now write separate trees; preflight
   proves the property by reading each episode's own `model_name` rather than trusting its path, and
   separately checks that the names an arm is about to write exist under no other arm.

3. **The cap was a flag rather than a property.** `--budget` defaulted to ¥200 while the spend it is
   compared against counts only the invoking arm's own episodes. For arm 1, the only spender, those
   were the same number. For arm 2 they differ by everything already paid, so the default would have
   authorised a second ¥200 on top of the first. The default is now `200 −` all other Phase-8A spend,
   which is ¥74.1771 for arm 2 and includes the cost probe: the probe's custody sits outside the
   *grading* glob so it can never become a panel point, but it must sit inside the *spend* glob, or
   the cap silently grows by whatever it cost.

Defects 2 and 3 are the same mistake in two places — an arm-scoped quantity written as a global — and
so is the `--models` default corrected earlier. That is worth naming: the failure mode of adding a
second arm is not new logic, it is old logic that silently assumed there was only ever one.

## 5E. Amendment 5 (2026-08-19, before arm 2's first analysed episode)

Arm 2 began at 03:31:01Z and stopped inside its first block. This amendment records the outage, the
two accounting defects it exposed, and — before the outcome is known — the rule for what happens if
the backend does not come back.

### 5E.1 A provider authentication outage, evidenced against an unbilled endpoint

Block 00 completed 2 of 6 slots and then failed all three attempts at `Base/pos2`, each exhausting
all 6 chat retries, on
`503 {"code":"SERVICE_BUSY","message":"API Key 鉴权服务暂时不可用，请稍后重试"}`. The arbiter
reached STOP at the 2-replacement cap, as designed. This is measurement-invalid — an infrastructure
fault, never a capability failure — and no retry of any *score* is involved.

The attribution is checked, not accepted. This backend has already produced two different terminal
faults: a transient `502` window (block 01) and `402 INSUFFICIENT_BALANCE` (block 02). The balance
outage is the dangerous look-alike, and during it `GET /v1/models` still returned `200` with the full
list, because listing models is not billed. Here `GET /v1/models` returns `503` with the same
authentication message. **An outage that blocks an unbilled endpoint cannot be a balance condition.**
The provider's error string is its account of itself; the unbilled canary is the evidence.

Nor is it ordinary throttling: the measured rate that motivated the raised retry budget (35%
back-to-back, 8.3% at 15 s spacing) is a per-request rate that 6 retries with 3/6/12/24/45 s backoff
reaches past. All 6 failed, three attempts running, across 29 minutes.

The pass is archived whole to `phase8a/evidence/aborted/arm2_block00_attempt1/` under §5B.3 and the
block will be re-executed whole. Two of its three episodes were valid, and one of them is this arm's
only 1.0 so far — which is exactly why the discard rule may not be decided now.

Recovery is monitored by polling the **unbilled** `GET /v1/models` every 4 minutes, and a recovery is
only accepted after 5 consecutive 1-token chat probes at 15 s spacing return `200`. One `200` is not
a recovery; polling the free endpoint means waiting costs nothing.

### 5E.2 What the telemetry guard caught

`p15_eval_0004_base_r1` was written to custody with `total_cost: 0.0`, `error: null`, and
**`total_score: 0.5`**. No model was called; `run_single_agentic` grades whatever is in the workspace,
and an untouched p15 workspace scores 0.5.

Unguarded, this arm would have recorded a provider auth outage as a mid-range capability score for
DeepSeek on instance 0004 under Base. Because replacements cluster during an outage, one bad hour
becomes a column of plausible scores that look collected. `_telemetry_faults` refuses to continue
past an episode with no evidence of a model call; that is why this stopped at block 00 and not at
block 12. The guard did the work the run was supposed to make it do.

### 5E.3 Defect: money paid for a replaced attempt left the ledger

A replacement re-runs the *same slot* under the *same trial name*, so
`<custody>/<trial>/episode.json` is overwritten. Only the last attempt's cost survives. Measured
here: `Base/pos2` attempt 1 cost **¥0.5468**, then two ¥0 attempts overwrote it, so the custody tree
reported ¥0 for a slot that was billed.

This loosens the cap exactly when that is most harmful. Replacements are caused by provider faults,
faults arrive in clusters, and each cluster erases more recorded spend — so the ¥200 cap slackens
during precisely the hours when money is being spent for no data. A cap that stops binding under load
is not a cap.

`scripts/phase8a_run.py` now harvests every superseded attempt's cost from the chain log into
`phase8a/evidence/replaced_attempt_ledger.json` immediately after each pass returns — before any
early exit, because a failing pass is the pass that replaced the most attempts. Both
`_program_spend()` and the per-arm `_spent_so_far()` count it, and
`phase8a_report.py` reports it as `spent_on_replaced_attempts_cny`. The pinned `chain_executor.py` is
not modified; it already logs every attempt's cost, and the driver reads it.

**Arm 1's figure is 0.0, and that is a gap, not a measurement.** Arm 1 had 6 replaced attempts, in
the aborted passes of blocks 01 and 02. Their per-attempt costs are irrecoverable: the ledger did not
exist, and each block's chain log was overwritten by its own re-run. The archived evidence bounds it
— block 02's three `402`s each failed in ~1.25 s with no billable call, and both slots' surviving
episodes record ¥0 — so the unrecorded amount is at most about ¥1.1 at that block's measured rate,
and probably ¥0. It is reported as a bound rather than folded into the total, because a number
invented to close an identity is worse than an acknowledged gap.

### 5E.4 Defect: the chain log was not arm-scoped

The executor log path was `runs/phase8a/chain_b<NN>.log`, with no arm in it, so arm 2's block 00
overwrote arm 1's. That log was the only per-attempt cost record for arm 1's block 00 — the defect
destroyed the very evidence §5E.3's ledger harvests. Arm 1 block 00 happened to have no replaced
attempt, so nothing was actually lost; that was luck. Now `chain_a<arm>_b<NN>.log`, and the archived
copy of a discarded pass's log is committed into the archive, because `runs/` is gitignored.

This is the **fourth** instance of one mistake: `--models`, the custody tree, the budget default, and
now the log path — each an arm-scoped quantity written as a global. The pattern is stable enough to
state as a rule: when a study grows a second arm, audit every path and every default that was written
while there was only one, because none of them will fail loudly.

### 5E.5 What this amendment does not change

- **k stays 2.** The gate ran once, on cost only, before arm 2's first episode (§5D.1). An outage is
  not a reason to revisit it, in either direction.
- **No valid score is retried.** Every exclusion here is transport telemetry with no model call.
- **Arm 2 is still the last cell.** It is not extended, re-scoped, or supplemented in response to
  what block 00 showed.
- **If the backend does not return, arm 2 is reported as incomplete — never as a smaller arm.**
  Blocks are instances, so a subset of blocks is a subset of *instances*, not a reduced k. Arm 1
  observed bidirectional instance-level heterogeneity, so analysing whichever instances happened to
  run before an outage would let the provider's downtime choose the sample. In that case the report
  states the blocks completed and draws no condition contrast from them.

## 6. Execution order

1. Freeze commit: this document, the schedules, the scripts and their tests, on a clean tree.
2. `scripts/phase8a_preflight.py` — zero model calls; every gate must pass.
3. Arm 1: 216 episodes via the pinned `scripts/chain_executor.py`. Report-only commit. Stop.
4. Cost probe, compute k2, arm 2. Report-only commit.
5. `scripts/phase8a_report.py`, then the findings write-up in both languages.

Halt and report if: preflight fails, the tree is dirty, projected spend passes ¥200, a slot needs a
third replacement, or a valid wrong score appears.
