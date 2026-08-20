**English | [中文](phase8a_arm2_analysis_plan.zh.md)**

# Arm-2 analysis plan — the joint model × family panel

This document fixes how the 72 `deepseek-v4-pro` episodes on the frozen 12-instance STA panel are
analysed. It was written and committed **before any outcome field of those episodes was read**. The
machine-readable form is [`../phase8a/evidence/arm2_analysis_plan.json`](../phase8a/evidence/arm2_analysis_plan.json);
the arm-2 report records that file's sha256, so an analysis cannot be produced without a plan present
and unmodified.

It exists for one reason. The episodes were executed **after** the Phase-8A cost gate had already
returned `ARM2_NOT_RUN`, so they are not the arm that preregistration sized, and nothing here claims
they are. What can honestly be claimed is narrower and sufficient: the analysis rules were fixed
before the numbers were seen, and they are the same rules, in the same code, that produced arm 1.

## What this is not

**It is not the preregistered arm 2.** The Phase-8A preregistration sized arm 2 through a cost ladder
and its gate refused the arm. These episodes came later. The sentence that must never appear anywhere
is *"this k=2 S3 experiment was preregistered and executed according to the original
preregistration."* It was not, and the paper does not say so.

**It is not a preregistration in the clinical sense.** It is the ordinary discipline of writing the
analysis down before looking: no instance dropped, no metric swapped, no test added, no secondary
contrast promoted, and the result reported whichever way it comes out.

## No rule was weakened to permit this

`scripts/phase8a_report.py` withholds condition aggregates **if and only if** some planned instance is
missing. That rule was written for §5E.5 of the preregistration, and its reason was specific: blocks
are instances, so a subset of blocks is a subset of *instances*, not a reduced `k` — and a contrast
drawn over whichever instances happened to finish would let the budget or the provider choose the
sample.

Arm 2 completed **12 of 12** planned instances. The condition that triggers withholding does not
hold, so the unmodified rule permits the aggregates. This matters: the analysis below is not the
product of relaxing a control, it is the product of the control's own precondition being satisfied.

```bash
python3 scripts/phase8a_report.py --arm 2 --check
```

## Inclusion

All **72** episodes: 12 instances × 3 conditions × k=2. No exclusions beyond the measurement-invalid
rule inherited unchanged from arm 1 — infrastructure timeout, gateway error or worker failure only,
and a valid wrong score is a hard failure that is never retried away. The run recorded **0 invalid
attempts**, so nothing is excluded. No instance and no condition may be dropped.

## Unit and metric

The unit of analysis is the **instance**, `n = 12`. Each `(instance, condition)` cell's rate is the
mean of its k=2 repetition booleans. Each episode's boolean is exact-correct from the frozen typed
provenance/authority oracle `generators/p15_sta_handoff/grade_sta_handoff.py`; the tool exit signal is
never read. The metric may not be substituted.

## Contrasts and tests

| | |
|---|---|
| Primary | BundleS − Base, instance-level |
| Secondary | TypedContract − Base; TypedContract − BundleS |
| Primary test | exact two-sided paired sign test over non-zero instance differences (`_sign_p`, the arm-1 implementation) |
| Sensitivity | instance-resampling band, 100 000 replicates, seed 20260820 — a band over instances, deliberately **not** a confidence interval |
| Permutation | per-instance label shuffle over that instance's own reps, 10 000 draws; descriptive only |
| Panel anatomy | the same `classify()`/`anatomy()` used for Phase-7A and arm 1 |

A secondary contrast **may not** become the primary one, whatever the outcomes look like. No test is
added after the outcomes are read.

## Nothing is pooled

No quantity is summed, averaged or differenced across arm 1 and arm 2, or across Phase-7A and either.
Different models, separate executions. There is no `n = 24` and no k=8 panel.

## Interpretation, fixed before the numbers

The mapping from outcome to wording is fixed here so it cannot be chosen afterwards.

- **Transfer observed** — requires *all* of: primary sign test two-sided *p* < 0.05, the resampling
  band excluding 0, and improvements outnumbering declines among informative instances.
- **Transfer not established** — fires if any of the above fails. It may **not** be worded as
  evidence that BundleS has no effect; a panel whose floor-limited instances cannot express a
  difference fails to show one for reasons that have nothing to do with whether one exists.
- **Model dependence** — fires if the sign of the primary instance-level difference disagrees between
  arm 1 and arm 2 on a majority of the instances informative in both. Reported as a descriptive
  observation; it needs neither arm to be significant.

Two constraints bind **every** branch:

**Repetition depth.** k=2 resolves a cell's own value poorly, and this is not a speculation — arm 1
established on this same family that **7 of 36** cells disagree across six identical repetitions, so a
single trajectory is a coin flip about 19% of the time. No claim about the magnitude or stability of an
arm-2 cell value is permitted, and arm 2's aggregate may not be set beside arm 1's k=6 aggregate as
though the two were equally resolved.

**Panel composition.** Instances at floor or ceiling in both compared conditions cannot express a
difference, so the effective *n* is below 12 and must be reported as such.

## Reporting commitment

The result is reported whichever direction it takes. Once the outcomes are read this plan is not
revised; any later analysis beyond it is labelled post hoc and reported as post hoc.

The internal budget history — how the ¥200 cap was set, which gate arithmetic was miscalibrated, which
block ran at which hour — is research-process management, not a scientific result. It stays in `docs/`
and `phase8a/evidence/`, where [`phase8a_findings.md`](phase8a_findings.md) records it in full. The
manuscript reports the final design and its results.
