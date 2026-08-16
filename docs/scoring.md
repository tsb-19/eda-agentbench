**English | [中文](scoring.zh.md)**

# Scoring — how correctness is decided

The one rule that matters: **semantic correctness is never inferred from tool success.** Not from
exit status, not from a hidden numeric answer, not from the aggregate artifact score. It is decided
solely by whether the submitted tuple matches the binding attested by an independent
provenance/authority oracle.

This is not a stylistic preference. In the worked instance, *every* shipped evidence source signs
off green under PrimeTime — including the one whose two role fields are swapped. A grader reading
tool exit status would score a wrong binding as a pass, and the paper's entire failure class would
be invisible.

## The master evidence gate

Each family's grader has a master gate — `EVIDENCE_OK` in the workflow family — and the typed
predicates are **folded into it** rather than scored alongside it. A sign-off-green but mis-typed
package therefore cannot pass by accumulating credit elsewhere.

The workflow gate requires every required stage to match a hidden re-run, *and* the typed
predicates below to hold:

- the scenario field must belong to the scenario axis, and the corner field to the corner axis;
- neither may be a **PVT descriptor** — a descriptor denotes a scenario–corner *pair* and is never
  a value of either axis;
- the clock must match by **exact identity**, so a generic alias is rejected;
- the netlist must be in the declared family.

Downstream markers (`TYPED_BINDING_OK`, `AXIS_SCHEMA_OK`, `PVT_LABEL_OK`, the constraint-graph
names) re-report the already-gated verdict under different names. They are diagnostics, not
additional chances to pass: a wrong scenario or corner has already collapsed `EVIDENCE_OK`.

## The two failure subtypes, never collapsed

A failure is classified into exactly one of two kinds. The paper keeps them separate throughout,
because they are different cognitive errors and the intervention affects them differently:

| Subtype | Definition | Example |
|---|---|---|
| **axis-binding failure** | a value occupies the **wrong typed axis** | `func`/`slow` — a corner value in the scenario role and vice versa |
| **role-conditioned value-selection failure** | the value is axis- and type-valid, but the **wrong member** fills the role | `typ`/`func` — plausible, correctly typed, contradicted by the authority |

Across the 70-episode Study I ledger: 41 correct, **24 axis-binding**, **5 role-conditioned** — all
tool-green, rejected only by the typed oracle. Collapsing the two would have hidden the paper's
central observation, which is specifically about *axis* errors: BundleS is associated with zero
observed axis-binding failures where the ambiguous baseline fails two of three.

A worked Family A example: visible evidence attests intent=`functional_close`, partition=`core`,
check_mode=`setup`; the agent submits (functional_close, core, **both**). PrimeTime returns green
and `both` is type-valid — but the coverage authority attests `setup`, so the oracle rejects it as
a role-conditioned value-selection failure.

## Uniqueness is established before grading, not during

Exhaustive enumeration over the declared domains runs at construction time and must yield **exactly
one** assignment satisfying the instance's constraints — 294 candidates → 1 for the worked
instance. "Correct" is therefore fixed by the instance's constraint system, and the grader only
checks membership. No grader judgement, and no room for a defensible-but-different answer to be
argued about after the fact.

## Weights

Partial credit, per family. Note how little tool success is worth.

**p14 workflow** — `signoff` 0.10 · `final_state` 0.15 · `evidence_generation` 0.25 ·
`stage_chain` 0.10 · `provenance` 0.10 · `authority_consistency` 0.10 · `hazard_recovery` 0.10 ·
`explanation` 0.10

**p15 STA (Family A)** — `provenance_attested` 0.30 · `coverage_cell_consistent` 0.20 ·
`check_view_legal` 0.10 · `pt_signoff_green` 0.10 · `not_masking` 0.15 · `explanation` 0.15

**p16 SPICE (Family B)** — `semantic_binding` 0.30 · `evidence_provenance` 0.20 ·
`simulation_success` 0.10 · `numeric_validity` 0.10 · `artifact_completion` 0.15 ·
`protocol_completion` 0.15

`pt_signoff_green` and `simulation_success` are each 0.10: the tool has to run, but running is
nearly worthless next to binding the tuple correctly. `explanation` never dominates.

`not_masking` deserves a note. It catches an agent that reaches a green sign-off by *weakening the
check* rather than by binding correctly — counting exception-declaring directives and flagging any
undeclared weakening beyond the single expected exception. It is the signature of solving the
symptom instead of the task, and the paper's masking case scores 0.4 against a golden 1.0.

The recognised score signature of a tool-green wrong binding in the workflow family is
`signoff = 1.0` with `evidence_generation = 0` — the tool is happy and the chain is not.

## Anti-cheat

Structural first, denylist second. The evaluator:

- snapshots sha256 of forbidden files before execution and verifies them after — `hidden/`, public
  test scripts, run scripts;
- refuses **hidden shadows**: an agent may not fabricate a file that shadows a hidden artifact
  (grader, oracle, golden netlist) the evaluator overlay provides;
- launders agent-supplied Tcl: an editable `.sdc` is ingested with `read_sdc` (which sandboxes Tcl
  `proc`/`exit`) and re-emitted canonically with `write_sdc`; the verdict is then computed in a
  separate phase that runs no agent code. An injected `proc incr {} {}`, `exit 0` or
  `echo CONSTRAINTS_OK` cannot reach or forge the verdict;
- additionally flags obvious injection attempts as an explicit violation (hard zero, recorded)
  before the tool runs. That denylist is the *secondary* layer — it can be evaded by indirection,
  which is exactly why the structural laundering above, not the list, is what guarantees integrity.

Implementation: `eda_agentbench/anti_cheat/guard.py`, `eda_agentbench/task/validator.py`; tests in
`tests/test_anti_cheat.py`, `tests/test_phase5_hidden_isolation.py`.

## The fairness gate

Before trusting any model score, grade the **known-correct solution** through the same path. It
must score ≈1.00. If it does not, the grader or the environment is distorting the measurement and
no score from that path means anything — this check has caught a real shim bug that turned every
score on a track into the same wrong number.

Per-task, the golden−buggy objective margin must also be ≥ 0.15: an unfixed input must not score
like a fix. `scripts/validate_dataset.py` automates both across a family.

## Measurement validity beats scoring

A score is only a result if the measurement was valid. An infrastructure timeout, gateway error or
worker failure is **measurement-invalid** and is never counted as a capability failure. The
converse is enforced just as hard and matters more: a **valid wrong score is a hard failure** and
may not be retried away. `scripts/fairness_retry.py` grants retries for infrastructure faults only;
`scripts/episode_arbiter.py` is the authority on whether an episode was terminal-valid or merely
recovered. See [`reproducibility.md`](reproducibility.md).
