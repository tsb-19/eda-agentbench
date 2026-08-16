**English | [中文](datacard.zh.md)**

# Dataset card — the three semantic-handoff families

## Summary

84 task directories across three independently constructed families plus one retained asset
substrate. They are **not** a benchmark leaderboard: each family instantiates one construct —
*semantic binding* — and the design is diagnostic, testing existence, recurrence, ceiling
behaviour and transfer direction. It cannot estimate population pass rates and does not try to.

| Family | Directory | Task dirs | Tool | Bound tuple | Paper role |
|---|---|---:|---|---|---|
| workflow | `tasks/p14_workflow_handoff/` | 27 | PrimeTime | (netlist, clock, scenario, corner) — PVT axes | Study I: S0, S1, S2-M |
| Family A — STA | `tasks/p15_sta_handoff/` | 46 | PrimeTime | (intent_class, target_partition, check_mode) from an authority provenance DAG | Study II: S2-F |
| Family B — SPICE | `tasks/p16_spice_handoff/` | 10 | HSPICE | (corner, load_condition, metric) from a request–authority join | Study II: S2-F ceiling |
| *substrate, not a family* | `tasks/p13_trajectory_handoff/` | 1 | — | — | read by the p14 generator; no claim rests on it |

p15's 46 directories are 15 instances × 3 conditions plus one dev instance; p16's 10 are 3 × 3 plus
one dev. The paper's prospective STA panel is instances 0004–0015 (*n*=12); 0001–0003 are the pilot
and are **never pooled** with the panel.

## The construct

Each task is a **semantic handoff**: bind a tuple to canonical typed roles from evidence that is
*role-misleading*. The difficulty is deliberately not retrieval. In the worked instance the
evidence files label their axis fields `op_point` and `mode`, and the ambiguous variant ships no
glossary and no axis declaration, so which logical axis each label denotes must itself be recovered
from the intersection of the sources.

The property that makes the construct measurable is **tool-green**: a wrong binding still produces
a green tool sign-off. In the worked instance all four shipped evidence sources sign off green under
PrimeTime, including the one whose two role fields are swapped. No tool signal separates them from
the truth — only the typed oracle does. A benchmark scoring this task by tool exit status would
score a wrong binding as a pass.

Correctness is decided by exhaustive enumeration at construction time, not by grader judgement: for
the worked instance, 294 candidate assignments over the declared domains, of which exactly one
satisfies the five recoverable constraints.

## Conditions

The same hidden truth and the same grader across all three; only the visible information differs.

| Condition | What the agent sees |
|---|---|
| **Base** | the ambiguous handoff. No disclosure of the instance's assignment, no glossary, no axis declaration |
| **BundleS** | canonical labels (C1), value-domain definitions (C2), glossary (C4), procedural contract (C7). **C6 withheld** — no golden values, no instance assignment |
| **TypedContract** | the same information as BundleS, expressed as a JSON Schema |

BundleS is **instance-answer-independent**, not "answer-free": it withholds the instance's target
tuple but deliberately discloses *task-level role semantics* — which axis a label denotes and what
values each axis admits. Calling it answer-free would understate it. Whether schema and generator
structure *jointly* permit recovering an assignment is a separate, open question; the paper names
the leakage check that would settle it and flags it as the single most informative experiment not
yet run.

Component definitions: [`synthetic_p14_phase4w_clarity_bundle_ablation_design.md`](synthetic_p14_phase4w_clarity_bundle_ablation_design.md).

## Directory shape

```
<instance>/
  prompt.md          the handoff brief
  metadata.json      machine-readable spec (see task_schema.md)
  files/             visible; a named subset editable. The evidence sources live here
  hidden/            never in the agent workspace: hidden truth, typed grader, trusted generators
  solution/          the golden submission
```

For the worked instance, `files/` carries 25 visible files of which 5 are editable, and `hidden/`
carries 11 — including `handoff_truth.json` and `grade_workflow.py`. The agent workspace is built
from visible+editable only; grading happens in a second workspace that overlays `hidden/`. See
[`agentic_runner.md`](agentic_runner.md).

## Family independence

Independence is defined by five pre-registered structural criteria — independent templates,
vocabularies, truths, graders, decoys — and checked mechanically rather than asserted:
`scripts/phase5a_independence_check.py` → `reports/synthetic_phase5_independence_check.json`. It
hashes each new generator/grader/evaluator and asserts that none imports the p14 grader or
generator, that role vocabularies are disjoint, that the new truth files share none of p14's keys,
that the grader module uses a distinct master-gate pattern, and that the decoy-recipe class
differs. A structural-overlap finding blocks the freeze.

A pass means *no detected overlap under those criteria* — it does not prove independence. And the
paper is explicit about the residual limitation: all three families are authored by us and all sit
within EDA, so cross-family transfer here is better read as cross-generator transfer inside one
designed universe than as domain transfer.

Specifications: [`synthetic_phase5a_family_specs.md`](synthetic_phase5a_family_specs.md),
[`synthetic_workflow_generator_spec.md`](synthetic_workflow_generator_spec.md).

## Admission gates

An instance is only admitted if it passes both:

- **uniqueness** — exhaustive enumeration yields exactly one assignment satisfying the constraints.
- **hard feasibility** — the bake must produce a wrong-binding artifact that the tool accepts,
  executes and signs off plausibly, that is nonetheless semantically wrong and *is* rejected by the
  typed oracle. A trivially tool-red or unparsable wrong binding makes the instance ineligible, and
  it is regenerated. Each instance records the five criteria and the grader's rejection in
  `hard_feasibility.json`.

## Scoring

Weights are per family; the master evidence gate folds the typed-membership predicates in, so a
sign-off-green but mis-typed package cannot pass regardless of the other components.

| Family | Components |
|---|---|
| p14 workflow | `signoff` .10 · `final_state` .15 · `evidence_generation` .25 · `stage_chain` .10 · `provenance` .10 · `authority_consistency` .10 · `hazard_recovery` .10 · `explanation` .10 |
| p15 STA | `provenance_attested` .30 · `coverage_cell_consistent` .20 · `check_view_legal` .10 · `pt_signoff_green` .10 · `not_masking` .15 · `explanation` .15 |
| p16 SPICE | `semantic_binding` .30 · `evidence_provenance` .20 · `simulation_success` .10 · `numeric_validity` .10 · `artifact_completion` .15 · `protocol_completion` .15 |

Note what `pt_signoff_green` is worth in p15: 0.10. Tool success is a component, never the verdict.
The two never-collapsed failure subtypes and the oracle's predicates are in
[`scoring.md`](scoring.md).

## Resource limits

All three families use the **standard** preset, difficulty `hard`. Timeouts: 600 s for p14 (it
regenerates a two-stage evidence chain), 300 s for p15 and p16.

## Provenance and known limitations

- **Frozen.** Every instance is at or before the experiment freeze HEAD; task semantics may not
  change. See [`provenance.md`](provenance.md).
- **Custody.** Per-episode byte-matching, canonical hash verification before and after each
  episode, and 1065 `path → sha256` membership pins verified by
  `scripts/frozen_membership_verify.py`.
- **Two generators drifted after their freeze.** The reported numbers derive from the pinned
  versions; the drift is reported rather than erased.
- **Nine pinned build products are absent.** `circuit_built.sp` under nine p16 instances is a
  gitignored HSPICE product; the manifests pinned it at run time.
- **Small panels.** S0, S1 and S2-M each rest on a single-instance cell at *k*=3–4. No cell reaches
  the paper's *generalized* tier.
- **No human validation.** Correctness is decided by executable oracles that are internally
  consistent and instance-unique, but have not been shown to agree with expert human judgement. The
  blinded human study was preregistered and never executed.
- **Not anonymised.** See [`REMOVED.md`](REMOVED.md).
