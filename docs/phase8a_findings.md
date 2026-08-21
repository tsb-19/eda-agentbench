**English | [中文](phase8a_findings.zh.md)**

# Phase-8A findings — an STA power expansion on a replacement backend

Phase-8A put more power behind the semantic-binding study's cross-family cell and then filled its
joint model x family cell, after the frozen program endpoint stopped serving the models the study was
run on. Both arms are reported here in full, including how each came to exist and the four harness
defects they exposed.

Preregistration: [`phase8a_prereg.md`](phase8a_prereg.md), frozen before the first analysed episode,
with six numbered amendments. Every number below is re-derived from committed ledgers by the commands
in [Reproduction](#reproduction).

Arm 2 has a second, narrower governing document, because its episodes were executed after the
preregistered cost gate refused the arm and are therefore not covered by that preregistration:
[`phase8a_arm2_analysis_plan.md`](phase8a_arm2_analysis_plan.md), committed before any arm-2 outcome
field was read.

**Status in the paper.** Manuscript **v18** makes arm 1 the primary S2-F evidence and reports arm 2 at
the S3 coordinate, keeps the earlier k=2 batch as a separately reported study, and never pools any of
the three. The post-hoc cross-model concordance beside arm 2 is stated descriptively: 5 of its 10
class agreements are degenerate, and its non-degenerate content is 4 of 5 signs. v14 does not cite
Phase-8A at all — it was frozen first — and remains recoverable
byte-for-byte. The claim-to-file mapping is in
[`artifact_map.md`](artifact_map.md); the manuscript-facing numbers are re-derived by
`scripts/phase8a_claim_statistics.py --check`.

## What was and was not established

**Arm 1 (`qwen3.7-max`, 216 episodes, 12 instances × 3 conditions × k=6, ¥122.8175).**

> **No consistent BundleS advantage was established on this preregistered 12-instance, k=6 panel, and
> bidirectional instance-level heterogeneity was observed.**

That is the whole claim. In particular:

- **This is not evidence that BundleS is ineffective.** Non-significance is not proof of zero effect,
  and the section below shows the panel had range to detect an effect on fewer than half its
  instances.
- **The k=6 expansion did not settle the question it was built to settle.** It bought precision
  *within* instances; the unit of analysis is the instance, and n stayed 12.

**Arm 2 (`deepseek-v4-pro`, 72 episodes, the same 12 frozen instances × 3 conditions × k=2, ¥58.11).**

> **Joint model × family transfer was not established on this panel. The point estimate favours
> BundleS (+12.5 pp, 5 instances improve to 2 declining) but the sign test cannot distinguish that
> split from a coin (*p* = 0.45) and the resampling band spans zero (−16.7 to +41.7 pp).**

Read [Arm 2](#arm-2-the-joint-model--family-panel) for what that does and does not license, and
[the analysis plan](phase8a_arm2_analysis_plan.md) for the rules it was analysed under — fixed and
committed before any of its outcomes were read.

## Why the batches are never pooled

Phase-7A and Phase-8A are **independent executions**, the second a separately preregistered
higher-replication follow-up on the same twelve frozen instances, and Phase-8A's two arms run
different models. That, and not anything about where the model was served, is the reason nothing is
combined across any of them: no quantity is summed, averaged or differenced, their episode counts are
not added, and there is no k=8 panel and no n=24.

| | k | Base | BundleS | TypedContract |
|---|---|---|---|---|
| Phase-7A | 2 | 0.208 | 0.333 | 0.458 |
| Phase-8A arm 1 | 6 | 0.2778 | 0.25 | 0.3611 |
| Phase-8A arm 2 (DeepSeek) | 2 | 0.25 | 0.375 | 0.4167 |

Rows one and two order BundleS against Base in opposite directions. **That is not a replication
failure and not a reversal**, because a reversal requires one measurement and these are two. Row
three is a *different model* and so is not evidence about either of the others; the fact that both
k=2 rows land on the same +12.5 pp while the k=6 row does not is an observation about repetition
depth, made post hoc, and it pools nothing.

**The serving endpoint, disclosed and not treated as an experimental factor.** The frozen program
endpoint `llmapi.paratera.com` returns `403 team not allowed to access model` for both model IDs, so
Phase-8A ran through `tokenrhythm.studio`. We treat the model identities served by both as genuine;
what could change model behaviour is weights and version, sampling configuration, context and chat
template, and reasoning/tool-call settings, not an endpoint string. We held and recorded the API
parameters we control, and we **do not** claim the underlying serving implementation was identical,
because we cannot verify it. So the change is disclosed as a fact under model custody — and as a
finding about measurement durability, since an endpoint that stops serving a model ends the ability to
re-measure a frozen design — but it is **not** the reason the batches are reported separately, and it
is not a reason to downgrade Phase-8A.

*(An earlier draft of this document gave the endpoint change as the reason for not pooling. It is
corrected here rather than silently rewritten: the non-pooling rule is unchanged and always was
correct, but its stated justification was wrong, and a justification that overstates what an endpoint
string implies would license the opposite error elsewhere.)*

## Arm 1: the numbers, and why p = 1.0 says less than it looks like

Descriptive, instance-level (n=12), at the preregistered k=6:

| contrast | improve | decline | tie |
|---|---|---|---|
| **primary** BundleS vs Base | 2 | 3 | 7 |
| secondary TypedContract vs Base | 5 | 3 | 4 |
| secondary TypedContract vs BundleS | 4 | 1 | 7 |

Primary sensitivity: exact paired sign test, k⁺ = 2 of 5 non-zero instance differences, two-sided
**p = 1.0**. Permutation (10 000 MC, seed 20260817), observed sum −0.3333, p = 0.7176, descriptive
only and not a population-rate p-value.

**p = 1.0 here is close to uninformative, and the reason is worth more than the p-value.** Of the 12
instances, the primary contrast could only move on 5:

| | instances | why |
|---|---|---|
| both conditions at floor 0.0 | **6** | no room to differ in either direction |
| both conditions at ceiling 1.0 | **1** | same |
| informative | **5** | |

Four instances (`p15_eval_0005/0006/0008/0009`) score 0.0 in **all three** conditions: the family is
simply beyond this model there, and a scaffold cannot be credited or blamed for an outcome the
instrument cannot register.

On the 5 instances that *could* move, the differences were large and pointed both ways:

```
p15_eval_0004   B − Base = −1.0000     the full range, against BundleS
p15_eval_0007   B − Base = −0.8333
p15_eval_0013   B − Base = −0.1667
p15_eval_0012   B − Base = +0.6667
p15_eval_0011   B − Base = +1.0000     the full range, for BundleS
```

Two instances hit the **maximum possible magnitude in opposite directions**. That is the bidirectional
instance-level heterogeneity, at full scale. A sign test seeing 2 of 5 cannot distinguish this from a
coin, which is exactly why the claim above is "not established" rather than "no effect": a panel this
heterogeneous, with range on 5 instances, would fail to establish a real effect of moderate size just
as reliably as it fails to establish a null one.

### What k = 6 did buy

Within-cell replication was not wasted: **7 of 36 (instance, condition) cells disagree across their 6
identical reps.**

```
p15_eval_0007  Base           ✓✓✓✗✓✓
p15_eval_0010  TypedContract  ✓✓✗✓✓✓
p15_eval_0012  BundleS        ✓✓✗✓✓✗
p15_eval_0013  Base           ✗✗✓✓✗✓
p15_eval_0013  BundleS        ✗✗✓✗✗✓
p15_eval_0014  TypedContract  ✗✗✗✗✓✗
p15_eval_0015  TypedContract  ✓✗✗✗✗✓
```

`p15_eval_0013` Base is 3 of 6. A k=1 design would have recorded that cell as a clean ✓ or a clean ✗
with equal probability, and the same for six other cells. **Any single-trajectory result on this
family is a coin flip 19% of the time.** That is a measurement-validity finding independent of any
scaffold comparison, and it is the durable thing arm 1 produced.

Custody: 2 measurement-invalid attempts and 4 arbiter-replaced attempts, all transport faults, none of
them a score. No valid wrong score was ever retried.

## Arm 2: the joint model × family panel

This is the coordinate the claim lattice calls **S3**: a different model *and* a different family than
the setting where the effect was first observed. It is the combination a reader most wants and the one
a paper about generalization can least afford to leave empty.

**Provenance, stated plainly.** These 72 episodes are **not** the arm the preregistration sized. That
arm was refused by a cost gate before it ran (below), and these episodes were executed afterwards. The
sentence *"this k=2 S3 experiment was preregistered and executed according to the original
preregistration"* would be false, and it appears nowhere. What is claimed is narrower and enough: the
analysis rules were written down and committed before any outcome field was read, and they are arm 1's
rules running in arm 1's code.

**No rule was weakened to permit the analysis.** `scripts/phase8a_report.py` withholds condition
aggregates *if and only if* some planned instance is missing — because blocks are instances, so a
subset of blocks is a subset of *instances*, and a contrast over whichever instances happened to finish
would let the budget or the provider choose the sample. Arm 2 ran **12 of 12**. The precondition that
triggers withholding is simply not met; the control was satisfied, not relaxed. A regression test makes
the point in the other direction, by declaring a thirteenth planned instance and requiring the
aggregates to vanish again.

### The numbers

Descriptive, instance-level (n = 12), at k = 2:

| | Base | BundleS | TypedContract |
|---|---|---|---|
| mean rate over instances | 0.250 | 0.375 | 0.4167 |

| contrast | improve | decline | tie |
|---|---|---|---|
| **primary** BundleS vs Base | 5 | 2 | 5 |
| secondary TC vs Base | 4 | 1 | 7 |
| secondary TC vs BundleS | 2 | 1 | 9 |

Primary: Δ = **+12.5 pp**; exact two-sided paired sign test, k⁺ = 5 of 7 non-zero instance
differences, **p = 0.453**; instance-resampling band **−16.7 to +41.7 pp**; permutation p = 0.336
(descriptive only). Panel anatomy: **4** instances at floor in both compared conditions, **1** at
ceiling, **7** informative.

The plan fixed in advance which wording each outcome licenses, and the branch is evaluated in code
rather than chosen afterwards. Support required *all three* of: p < 0.05, a band excluding zero, and
improvements outnumbering declines. The third holds and the first two do not, so the branch is
**not established**.

That phrase is doing exact work in both directions:

- It is **not** "BundleS does not transfer." The point estimate favours BundleS and 5 of 7 informative
  instances improve. What is missing is discrimination, not effect.
- It is **not** evidence of a null effect either. Four instances sit at the floor in both conditions
  and one at the ceiling; a panel where five of twelve instances cannot express a difference fails to
  show one for reasons independent of whether one exists.

**k = 2 is the binding limit, and this study measured how badly.** Arm 1 found **7 of 36** cells
disagreeing across six identical repetitions on this same family — a single trajectory is a coin flip
about its own cell roughly 19% of the time. So no claim is made about the magnitude or stability of any
arm-2 cell value, and **arm 2's aggregate is not set beside arm 1's k=6 aggregate as though the two
were equally resolved.** They are not. One resolves its cells; the other does not.

### The same instances carry the effect under both models

Post hoc, not preregistered, and **confounded**: arm 1 and arm 2 differ in the model *and* in k, so
nothing here can be attributed to the model alone. With that said, the per-instance structure is
strikingly stable. **10 of 12** instances receive the same class under both arms, and among the 5
informative in both, the **sign agrees on 4**:

```
p15_eval_0004   arm1 −1.0000   arm2 −0.5000   agree (negative in both)
p15_eval_0007   arm1 −0.8333   arm2 −1.0000   agree (negative in both)
p15_eval_0011   arm1 +1.0000   arm2 +1.0000   agree (positive in both)
p15_eval_0012   arm1 +0.6667   arm2 +0.5000   agree (positive in both)
p15_eval_0013   arm1 −0.1667   arm2 +0.5000   DISAGREE (both small, near the floor)
```

The pre-committed model-dependence branch required disagreement on a *majority* of instances
informative in both; 1 of 5 does not fire it. The reading this supports is narrow and useful:
**the heterogeneity lives in the instances, not in the model.** The same tasks help or hurt in the same
direction whichever model runs them. It does **not** establish transfer of the aggregate effect, which
neither arm establishes.

One more thing worth noticing, and worth not over-reading: both k=2 batches land on **+12.5 pp** — the
Qwen k=2 batch of Phase-7A and this DeepSeek k=2 arm — while the one k=6 batch lands on −2.8 pp. The
k=2 → k=6 move is *within* one model, so the flip is clean there; whether DeepSeek would move the same
way at k=6 is simply unmeasured. Nothing is pooled to say this, and it is post hoc.

### Arm 2 was refused by a cost gate before it ran

This subsection and the next are **research-process history**, kept here and deliberately absent from
the manuscript. A reader of the paper does not need to know how the ¥200 cap was set or which block ran
at which hour; a maintainer of this repository does.

Arm 2's k was fixed by a cost-only gate (§2.2) evaluated before its first analysed episode. The gate
reads cost and never a score, a rate or a contrast.

A 6-episode probe on instances 0001–0002 measured **¥0.5009/episode**, giving k₂ = 2 and a projected
¥36 — affordable. Block 00 then ran on instance 0004 at **¥1.1094/episode**. Amendment 6 §5F.5 fixed
the resolution procedure *before* the deciding number existed: re-run block 00 whole, pool its six
episodes with the probe's six, and re-apply the frozen formula unchanged — whole arm, or none of it.

Pooled **r′ = ¥0.8051/episode** over 12 episodes:

| k | episodes | projected | remaining after the ¥10 holdback |
|---|---|---|---|
| 6 | 216 | ¥173.91 | ¥44.53 ✗ |
| 4 | 144 | ¥115.94 | ✗ |
| 2 | 72 | ¥57.97 | ✗ |

No k qualified → **`ARM2_NOT_RUN`**. k was already at the floor of the ladder and §5E.5 forbids a
partial arm, so the check could only ever return *run it whole* or *do not run it*.

**One input decided this, and it is recorded both ways.** The formula's first parameter is *named*
`spent_arm1`; fed arm 1's ¥122.8175 it still returns k = 2, because it cannot see the ¥19.65 arm 2 had
itself already paid for two archived passes and one valid block. Passing that figure would have been
literal and false — it hides real outlay from the cap whose only purpose is to see it. Both readings
sit side by side in [`arm2_gate_decision.json`](../phase8a/evidence/arm2_gate_decision.json), because
the difference between them *is* the decision.

The remaining blocks were executed afterwards, at the operator's direction. That is the honest account
of how the data came to exist, and it is why the analysis rests on a plan committed before its outcomes
were read rather than on the preregistration.

Because the gate fired at a moment and both of its inputs have since moved — the block-00 custody
directory now holds all 72 episodes, and programme spend has grown — `phase8a_arm2_gate.py --check` no
longer recomputes the decision. It **verifies** it: the rate and spend the record declares are pushed
back through the same preregistered formula and must yield the same ladder, the same k and the same
verdict. Three tamper cases (flipped verdict, altered rate, altered spend) are asserted to fail, so the
record stays falsifiable without pretending the world stood still.

### The gate refused an arm that was affordable

The realized cost is a finding in its own right, and it needs no condition contrast:

| | gate's projection | realized |
|---|---|---|
| rate r′ | ¥0.805125/episode (12-episode probe) | **¥0.6266/episode** (72 episodes) |
| the 66 episodes it was pricing | ¥53.1382 | **¥38.4582** |
| against ¥44.5253 after holdback | does not fit → `ARM2_NOT_RUN` | **fits, ¥6.07 to spare** |

The gate applied its preregistered rule correctly and its arithmetic was right. Its *rate estimator*
was calibrated on a sample that did not represent the panel it gated: r′ pooled the cost probe with
the one executed block, and that block is `p15_eval_0004` — the dearest of the twelve at ¥1.1094 per
episode, against a panel mean of ¥0.6266 and a cheapest instance at ¥0.3298, an instance-level spread
of 3.4×. The gate had already recorded the episode-level spread it was averaging away
(`rate.spread_factor 6.86`) and gated on the pooled mean anyway.

This is the study's own finding in a different currency. Panel composition — not run noise — decided
the estimate, and here it decided not an effect size but whether an experiment happened at all. The
lesson generalizes: *a cost gate must be calibrated on a sample that represents the panel it gates, and
must carry the spread it measures into the decision rather than reducing it to a pooled mean.*

Note what does **not** follow. "The refusal turned out to be too conservative" is not the justification
for analysing the arm; that would be revising eligibility because of what the outcome turned out to be.
The justification is the plan fixed before the outcomes were read. The two are easy to confuse and
worth keeping apart.

Programme spend: **¥183.9329 of ¥200**, ¥16.07 unspent — one figure, from the same `_program_spend()`
the runner uses. An earlier draft reported this as two (eligible-analysis ¥145.47 versus total realized
¥183.93) because arm 2's episodes were then excluded from analysis; now that they are analysed, every ¥
paid stands behind a reported number and one total is the honest presentation. Record:
[`../phase8a/evidence/arm2_cost_calibration.json`](../phase8a/evidence/arm2_cost_calibration.json),
verified by `python3 scripts/phase8a_arm2_cost_calibration.py --check`.

## Measurement-validity findings

These cost real money and are the more transferable half of the study.

**1. The harness graded work the agent had not finished.** `run_single_agentic` snapshotted and graded
the workspace the moment the agent command returned, while `llm_agent_driver.py` writes its log as its
*last* statement. When the driver overran, the runner read the log too early. Two faces:

- *no log yet* → cost derived as **¥0**, and the fail-open arbiter accepted the episode, so a grade of
  unfinished work entered the analysis;
- *a previous pass's log* → run directories are keyed by `(block, condition, position, attempt)` and
  reused on a whole-block re-run, so an attempt was charged **¥0.5468 against a true ¥2.2849** *and
  classified on the archived pass's 503s*. It had scored 1.0 and was replaced as measurement-invalid
  on telemetry belonging to a different run. Its replacement scored 0.5.

Both faces are one mistake: **absence of evidence recorded as evidence of absence.** No log became
cost zero; no telemetry became no fault. It fires when the driver overruns, and the driver overruns
when transport is degraded — so the accounting failed hardest in the hours that spent most for least.
Arm 1 was checked explicitly and is clean: 216/216 episodes with real logs and non-zero costs, 220/220
attempt directories with the log written before the result.

**2. A pass can be COMPLETE and still unusable.** §5B.3 covered a pass *stopped* part-way. Arm 2's
block 00 finished 6/6 and contained a phantom. Amendment 6 extended the discard rule, and the phantom
test is deliberately cost- and error-based, never score-based: were the criterion a score, archiving
would become a way to re-roll an outcome. This block also demonstrated **in the study's own data that
scores move under re-run** (1.0 → 0.5), which is precisely why the keep/discard boundary may never
fall between episodes whose scores are known.

**3. A transport fault and a harness fault can co-occur, and the harness fault hides behind the
transport one.** Block 00 survived a genuine 503 *and* was ruined by the race. `--require-transport-
fault` read the 503 and would have waved the pass through, filing a code defect as "the provider was
flaky" and re-running straight back into it. A phantom now disarms that flag unless the phantom's own
error names a transport category. This is the shape of
[`incident_golden_corruption.md`](incident_golden_corruption.md): a monitor inherits the custody of its
reference standard.

**4. A monitor can become the signal it is watching for.** The completion waiter for the block-00
re-run looped on `pgrep -f "p8a_block00_rerun.sh"`. `pgrep -f` matches full command lines, and the
string sat inside the waiter's own — so it always matched itself and never exited. The run had finished
correctly; the *notification* hung for 18 hours. Cost: ¥0 and 18 hours of wall clock, on a study whose
experiments were otherwise closed. Same shape as finding 3, one level up.

Recovery of finding 1 was done from the primary artifact, not by estimate: every attempt's
`*.agentlog.json` survives with its `usage` block, so the true cost was recomputed with the same
`_cost()` the runner would have used. The pass had booked ¥6.0690 against a true **¥11.0465 — 62%
understated.** No `episode.json` was rewritten; the originals stand, wrong figures included, and the
correction is a separate ledger entry. A discrepancy you can still see is worth more than a total that
quietly agrees with itself.

**5. The primary artifact was stored where it could be overwritten.** Those driver logs lived in
`runs/phase8a/`, which is gitignored, in directories keyed by
`(block, condition, position, attempt)` — and re-running block 00 *whole* legitimately reused those
directories and overwrote them. So the ¥4.9775 correction can no longer be recomputed from source.
It was correct when computed and it is still bound into the ¥200 cap, but the evidence behind it now
consists of the per-attempt breakdown stored in the ledger entry and the sanitized chain log
committed with each archived pass.

`phase8a_cost_reconcile.py --check` reports this as a third outcome, `SOURCE_GONE`, distinct from both
"reproduces" and "the ledger is wrong", and falls back to asking only whether the recorded breakdown
still adds up. That is a weaker check and is labelled as weaker. The lesson is the ordinary one, badly
learned: **a record that is the only evidence for a number must not live in a path that another
correct operation is entitled to reuse.**

## What may not be concluded from any of this

- Not that BundleS is ineffective, on this family or any other.
- Not that BundleS helps. Neither direction was established.
- Not that arm 1 replicates or fails to replicate Phase-7A. Different apparatus, different
  measurement.
- Not that BundleS transfers to `deepseek-v4-pro` on this family, and not that it fails to. Arm 2's
  point estimate favours it; its discrimination does not reach a conclusion either way.
- Not that arm 2 is a *negative* result. "Not established" and "shown absent" are different claims and
  only the first is supported.
- Not that the cross-model structural agreement (10/12 class, 4/5 sign) shows the model does not
  matter. It is post hoc, non-pooled, and confounded with k; what it locates is heterogeneity in the
  instances, nothing more.
- Not that k=6 is sufficient for this design. It is sufficient *within* a cell — 19% of cells needed
  it — and says nothing about the n=12 between-instance panel that carries the claim.
- Not that arm 2's k=2 aggregate is comparable in resolution to arm 1's k=6 aggregate. It is not, by
  this study's own measurement of cell instability.

The study's own object is the difference between a measurement and a claim about the world. These
limits are the result, not a hedge around one.

## Reproduction

No model calls. All commands are read-only re-derivations from committed ledgers.

```bash
python3 scripts/phase8a_report.py --arm 1 --check    # 216 graded, ¥122.8175
python3 scripts/phase8a_report.py --arm 2 --check    # 72 graded, ¥58.11, k=2
python3 scripts/phase8a_claim_statistics.py --check  # both panels; arm 2 +12.5 pp, band -16.7..41.7
python3 scripts/phase8a_arm2_gate.py     --check     # VERIFIES the recorded ARM2_NOT_RUN decision
python3 scripts/phase8a_arm2_cost_calibration.py --check   # projected ¥53.14 vs realized ¥38.46
python3 scripts/phase8a_cost_reconcile.py --arm 2 --block 0 --check   # all 3 passes; 2 SOURCE_GONE
scripts/check                                        # 1065 pins / 9 missing / 2 mismatch / 1 multi-sha
python3 -m pytest tests/test_phase8a.py -q
```

Artifacts: [`../phase8a/reports/`](../phase8a/reports/) for the two reports and the cost gate,
[`../phase8a/evidence/`](../phase8a/evidence/) for per-episode custody, run states, the archived
passes and the replaced-attempt ledger.
