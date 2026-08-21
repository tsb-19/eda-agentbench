**English | [中文](opencode_probe_analysis_plan.zh.md)**

# OpenCode external-scaffold probe — analysis plan

**Committed before any outcome field of any OpenCode episode has been read.** At the time of this
commit no OpenCode episode exists. This document fixes the questions, the outcome definitions, the
wording standard and the escalation rule *in advance*, so that none of them can be selected after
the fact. Its precedence is verifiable against git history, exactly as
[`phase8a_arm2_analysis_plan.md`](phase8a_arm2_analysis_plan.md)'s is.

**This is not a reopening of the `a89e084` programme.** That programme stays frozen and every number
the paper reports stays derived from ledgers at or before it. This is a separately named study with
its own plan, budget, ledger, evidence root and claim scope. Nothing here may be summed with,
averaged into, or differenced against a frozen number.

The integration surface this plan presupposes — versions, config pins, permissions, isolation, and
the nine structural checks that gate execution — is
[`opencode_scaffold_probe_scope.md`](opencode_scaffold_probe_scope.md). That document is a scope
audit and deliberately not a preregistration; this one is the preregistration.

## What the probe is, stated accurately

The manuscript (v20) studies a **task-information intervention** with the agent scaffold held fixed.
Every episode in the paper ran on our own single runner, so the paper's own §7 concedes that the
tool-green occupancy figure ("82 of 169") is a property of that runner. An independent scaffold is
therefore the paper's most load-bearing missing external validity.

What the probe does, in one sentence that does not overstate it:

> It matches model, task instances, treatment conditions, replication depth, grader and EDA
> environment to the existing DeepSeek (*k*=2) panel, while substituting the execution scaffold and
> the scaffold-implied interface framing.

It does **not** make the scaffold the only varied factor, and that phrasing may not be used. The
paper defines task information as *prompt, visible files, disclosure bundle, public tool feedback,
and action surface*. OpenCode necessarily replaces the action surface and the prompt frame, both of
which that definition counts as task information. So the row-to-row difference varies the scaffold
**and** two components of task information at once, by construction and not by oversight.

## The three layers, fixed now

### Layer 1 — primary external-validity question (existence and frequency)

> **Does semantic misbinding occur under the independent OpenCode scaffold while the professional
> tool still succeeds?**

This is a **descriptive existence-and-frequency** question. It requires no contrast, no condition
comparison and no significance test, and none will be computed for it. The reported quantities are
counts over valid episodes, using the Phase-7D instrument unchanged:

| Quantity | Definition |
|---|---|
| `n_valid` | episodes that completed and were scored, after the measurement-validity rules below |
| `n_semantic_wrong` | typed provenance/authority oracle **rejects** the submitted binding |
| `n_tool_green_wrong` | oracle rejects **and** `run_public.sh` returned green |

`n_tool_green_wrong` is the quantity of interest: it is the paper's central measurement finding, and
finding it on foreign scaffolding is what this layer buys.

**The strength of the claim is bounded by the count, and the bound is fixed here rather than after
seeing it.** A single tool-green wrong binding does establish existence — the failure mode is not
exclusive to our own runner — but a lone instance will be reported as exactly that and no more.
Reporting is by count, with no significance claim at any count:

| Observed | What may be written |
|---|---|
| 0 / `n_valid` | *"This failure mode was not observed in this independent-scaffold probe."* Reported with equal prominence; this outcome is not a null to be buried. |
| 1 / `n_valid` | existence only, explicitly as a single episode |
| several | the count and the rate, as a descriptive frequency, still not as a population estimate |

Both directions are authorized in advance. A probe that finds nothing is a result and will be
reported.

### Layer 2 — secondary within-scaffold question (the estimand)

> **Within OpenCode, does BundleS improve semantic correctness relative to Base?**

Here the scaffold is held constant, so this is a complete within-OpenCode task-information
intervention and the contrast is clean. **This, not the scaffold, is the probe's estimand.**

Analysis is the arm-2 machinery reused mechanically — same unit, same statistics, same code path,
no new estimator invented for this arm:

- unit of analysis is the **instance** (*n*=12); episodes aggregate within instance
- per-condition mean rates across instances
- improve / decline / tie counts
- exact two-sided paired sign test over non-zero instance differences
- instance-resampling uncertainty band
- permutation figure, **descriptive only**, never a population *p*-value
- panel anatomy: floor/floor, ceiling/ceiling and informative instance counts, always reported

No presumption that this must reach significance. See the wording standard below.

### Layer 3 — explicitly excluded question

> **What is the causal main effect of replacing our runner with OpenCode?**

**Not estimated. Not reported. Not derivable from any artifact this probe produces.**

The scaffold cannot be separated from the prompt frame and action surface it brings with it, so the
difference `OpenCode − controlled runner` is not a scaffold effect and no arithmetic will present it
as one. This exclusion is enforced, not merely stated: no report script may emit such a difference,
and `test_no_scaffold_main_effect_claim` in `tests/test_opencode_probe.py` fails if the prohibition
is deleted from this plan or from `CLAUDE.md`, or if a probe script grows a key that computes it.

Whether the within-OpenCode direction agrees in sign with arm 2's is a **descriptive cross-batch
observation**, subject to the full discipline the paper already imposes on its own cross-batch
concordance — including the degenerate-agreement audit that v18 established: floor/floor and
ceiling/ceiling agreements record shared instance difficulty, not shared response, and must be
removed before any concordance is quoted.

## Design — stage 1

| | Value |
|---|---|
| Model | `deepseek-v4-pro`, same as arm 2 |
| Instances | all 12 of `p15_eval_0004`–`p15_eval_0015`, **with no selection on prior informativeness** |
| Conditions | Base, BundleS |
| *k* | 2, same as arm 2 |
| **Episodes** | **48** |
| Grader | unchanged typed provenance/authority oracle; `run_public.sh` / `run_hidden.sh` unchanged |

**TypedContract is excluded from stage 1.** The reviewer objection this probe answers is whether the
phenomenon and the treatment survive on an external scaffold, not what the full ranking of three
treatments is under OpenCode. Adding it would make the arm 72 episodes and add a secondary contrast
to the paper for no gain against that objection.

*k*=2 carries **no magnitude claim**. Arm 1 measured, on this very family, 7 of 36 cells disagreeing
internally across six identical repetitions — roughly 19% of single trajectories are a coin flip
about their own cell. The stage-1 aggregate is therefore not to be set beside arm 1's *k*=6
aggregate as though equally resolved.

## Escalation to *k*=6 — the rule, fixed before any outcome

Stage 1 is fixed at *k*=2. Extension to *k*=6 on the **same twelve instances** happens if and only
if all three conditions hold, and then it happens **regardless of which condition scored higher**:

1. **Trajectory completeness** — 100% of planned episodes yield valid trajectories, after the
   measurement-validity rules below. No instance and no condition missing.
2. **Expressible range** — **at least 5 instances** are informative, i.e. neither floor/floor nor
   ceiling/ceiling across the compared pair. Five is the count arm 1 achieved on these same twelve
   instances at *k*=6; below it the panel has less expressible range than either existing panel, and
   arm 1 already established that *k*=6 buys within-cell resolution while leaving *n*=12 untouched.
3. **Cost** — the extension fits the probe's own cap with its own holdback intact, at a rate
   measured across a representative sample rather than projected.

**The direction of the stage-1 result is not an input to this decision.** The failure this rule
exists to prevent is the outcome-adaptive one: *"we saw +20 pp so we ran more to confirm it; we saw
0 so we stopped."* If the three conditions hold, escalation proceeds even when stage 1 favours Base;
if any fails, escalation does not proceed even when stage 1 favours BundleS.

## Measurement-validity rules, inherited unchanged

- An infrastructure timeout, gateway error or worker failure is **measurement-invalid** — never a
  capability failure.
- A **valid wrong score is a hard failure** and may not be retried away.
- Retries are granted for infrastructure faults only.
- Aggregates are withheld if and only if a planned instance is missing — a subset of blocks is a
  subset of *instances*, and comparing over whichever instances happened to finish lets the budget
  or the provider pick the sample.
- Anything that cannot be equalized against the controlled runner is **recorded as a scaffold
  difference in this plan's own record**, not quietly absorbed. The known ones are already named in
  the scope audit: multiple tool calls per turn, patch-based editing, `steps` counting iterations
  rather than actions, and the absence of a per-command timeout equivalent.

## Wording standard

Layer 2 uses the same three-part criterion the paper applies to itself. **"Supports" requires all
three**: *p* < 0.05 **and** the band excludes 0 **and** improvements outnumber declines. Anything
short of all three is **not established** — which is neither "no effect" nor "does not transfer".
Applying a looser standard to this probe than the paper applies to its own treatment effect
(*p*=0.45 → "not established") would be the exact failure the paper is about.

Layer 1 makes no significance claim at all, at any count.

## No pooling

Nothing from this probe is summed with, averaged into, or differenced against Phase-7A, Phase-8A
arm 1, or Phase-8A arm 2. No combined episode count, no combined *k*, no combined *n*. The probe is
a fourth separately reported execution, and the rule that already keeps the first three apart
extends to it without amendment.

## Budget and ledger

**The frozen programme cannot fund this.** It spent ¥183.9329 of its ¥200 cap, leaving ¥16.07. The
probe needs its own cap, its own ledger and its own gate, none of which draw on that ¥200.

The cap is an operator decision and is **not set by this document**; it must be fixed in writing
before the first formal episode and recorded here. What this document does fix is how it is used:
the dry run measures the per-episode rate, and any rate driving a gate must be **calibrated on a
sample representative of the panel it gates and must carry its own measured spread into the
decision rather than compressing it into a pooled mean**. That is the `ARM2_NOT_RUN` lesson in its
own currency — a gate calibrated on `p15_eval_0004` at ¥1.1094/ep, against a panel mean of ¥0.6266
and a cheapest instance of ¥0.3298, rejected an arm that was in fact affordable.

## Where the probe's artifacts live

**Evidence root: `opencode_probe/` at the repository root — never under `reports/`.** This is not a
layout preference. `frozen_membership_verify.py` scans all of `reports/` for `path → sha256` pairs,
so writing probe artifacts there changes the pin count and can silently resolve one of the two
expected mismatches. An early Phase-8A draft did exactly that and drove the count 1065 → 1979. The
probe mirrors Phase-8A's layout for the same reason Phase-8A has it.

`reports/evidence/` stays read-only. The probe adds nothing to it and rewrites nothing in it.

## Abort criteria

If the dry run cannot deliver checks 1, 5 and 8 of the scope audit — identical file exposure, an
unreachable oracle, and byte-unaltered artifacts — **the probe does not run**. Those three are not
alignment niceties; without them the arm does not measure what it claims to. A clean *"we could not
align an independent scaffold"* contributes more than a confounded number.

Checks 3, 4, 6, 7 and 9 may fail individually provided each failure is recorded here as a scaffold
difference before the formal arm begins, rather than discovered afterwards.

## What this plan does not authorize

- It does not authorize the 48-episode formal arm. Authorization so far is integration plus **one
  unscored, discarded paid dry run** on `p15_dev_0000`. The formal arm becomes authorized only after
  all nine structural checks pass.
- It does not authorize reading any Base/BundleS contrast out of the dry run. The dry run is read
  for exposure, action surface and grader fidelity only.
- It does not authorize a second model, further Bundle ablations, or SPICE. Each is another factor
  before the first scaffold observation exists.
- It does not authorize any manuscript change. The claim lattice would gain a fourth projection π_S,
  turning every existing verdict into a statement *at fixed scaffold* — that is a v20-class edit and
  it follows the probe rather than preceding it.

## Verification

```bash
python3 -m pytest tests/test_opencode_probe.py -q     # plan guards, incl. the excluded question
python3 scripts/slim_link_check.py                    # no dangling references
git log --diff-filter=A --format=%H -1 -- docs/opencode_probe_analysis_plan.md   # precedence
```

The precedence claim is checkable: the commit that added this file must precede the first commit
that adds any OpenCode episode artifact. `tests/test_opencode_probe.py` asserts that ordering
whenever probe outcomes exist.
