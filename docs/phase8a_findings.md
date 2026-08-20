**English | [中文](phase8a_findings.zh.md)**

# Phase-8A findings — an STA power expansion on a replacement backend

Phase-8A was a two-arm attempt to put more power behind one preregistered cell of the semantic-binding
study, after the frozen program endpoint stopped serving the models the study was run on. It is
reported here in full, including the arm that did not run and the four harness defects it exposed.

Preregistration: [`phase8a_prereg.md`](phase8a_prereg.md), frozen before the first analysed episode,
with six numbered amendments. Every number below is re-derived from committed ledgers by the commands
in [Reproduction](#reproduction).

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

**Arm 2 (`deepseek-v4-pro`) did not run.** The preregistered cost gate refused it. One block of twelve
executed and is reported with **no condition contrast**. See [Arm 2](#arm-2-the-gate-refused-it).

## Apparatus, and why the two measurements are never pooled

The frozen program endpoint `llmapi.paratera.com` returns `403 team not allowed to access model` for
both model IDs. Phase-8A ran on `tokenrhythm.studio`. Same design, different serving stack, therefore
a **different measurement**. Phase-7A and Phase-8A are reported side by side and are never summed,
averaged, differenced or pooled into one n.

| | backend | k | Base | BundleS | TypedContract |
|---|---|---|---|---|---|
| Phase-7A | `llmapi.paratera.com` (now 403) | 2 | 0.208 | 0.333 | 0.458 |
| Phase-8A arm 1 | `tokenrhythm.studio` | 6 | 0.2778 | 0.25 | 0.3611 |

The two rows order BundleS against Base in opposite directions. **That is not a replication failure
and not a reversal**, because a reversal requires one measurement; these are two, on different
apparatus. Neither row is evidence about the other's backend. The backend turnover itself is reported
as a finding about measurement durability, not as a result about any model.

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

## Arm 2: the gate refused it

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
partial arm, so the check could only ever return *run it whole* or *do not run it*; it can never
return a smaller arm.

**One input decided this, and it is recorded both ways.** The formula's first parameter is *named*
`spent_arm1`; fed arm 1's ¥122.8175 it still returns k = 2, because it cannot see the ¥19.65 arm 2 had
itself already paid for two archived passes and one valid block. Passing that figure would have been
literal and false — it hides real outlay from the cap whose only purpose is to see it. Both readings
sit side by side in [`arm2_gate_decision.json`](../phase8a/evidence/arm2_gate_decision.json), because
the difference between them *is* the decision.

Crediting the block already paid for, the remainder misses by **¥1.39** and clears only if the ¥10
holdback is abandoned — 2.6% of its own projection, against a pooled per-episode spread of **6.9×**
(¥0.38–¥2.60, sd ¥0.63). That is noise, not margin. Spending it after seeing the number would be
lowering the standard.

Arm 2 is therefore reported as **the one preregistered cell that could not be filled within budget** —
not as untried, and not as tried-and-null.

### The one block that ran is not a result

`p15_eval_0004`, 6 episodes, was executed and graded. Its aggregates are **withheld** under §5E.5, and
`scripts/phase8a_report.py` now refuses to compute them rather than leaving the rule to a reader's
discipline: blocks are instances, so a subset of blocks is a subset of *instances*, not a reduced k.
With bidirectional heterogeneity established in arm 1, a contrast from whichever instance the budget
happened to reach would be a sample chosen by the budget. The record is
`phase8a_sta_report_arm2.md`, in [`../phase8a/reports/`](../phase8a/reports/).

Program spend: **¥145.4747 of ¥200.** The remaining ¥54.53 is not spent on additional cells,
instances, conditions or models (§2.3). Spending a surplus because it exists is the outcome-adaptive
practice this program exists to prevent.

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
- Not anything about `deepseek-v4-pro` on this family. Arm 2 did not run, and one block is not a
  contrast.
- Not that k=6 is sufficient for this design. It is sufficient *within* a cell — 19% of cells needed
  it — and says nothing about the n=12 between-instance panel that carries the claim.

The study's own object is the difference between a measurement and a claim about the world. These
limits are the result, not a hedge around one.

## Reproduction

No model calls. All commands are read-only re-derivations from committed ledgers.

```bash
python3 scripts/phase8a_report.py --arm 1 --check    # 216 graded, ¥122.8175
python3 scripts/phase8a_report.py --arm 2 --check    # incomplete arm, aggregates withheld
python3 scripts/phase8a_arm2_gate.py     --check     # ARM2_NOT_RUN, r′ = ¥0.8051/episode
python3 scripts/phase8a_cost_reconcile.py --arm 2 --block 0 --check   # all 3 passes; 2 SOURCE_GONE
scripts/check                                        # 1065 pins / 9 missing / 2 mismatch / 1 multi-sha
python3 -m pytest tests/test_phase8a.py -q
```

Artifacts: [`../phase8a/reports/`](../phase8a/reports/) for the two reports and the cost gate,
[`../phase8a/evidence/`](../phase8a/evidence/) for per-episode custody, run states, the archived
passes and the replaced-attempt ledger.
