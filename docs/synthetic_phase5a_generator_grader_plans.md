# Phase-5A — Generator, Grader, and Fairness-Gate Plans (deliverable 3)

**Date:** 2026-08-03 · **Branch:** `synthetic-phase0a` · **Status:** design/plans only — NO code implemented in Phase-5A, no paid calls, stopped for review (no push).
**Companion:** `…design.md` (master), `…family_specs.md` (2, the task content this implements), `…budget_risk_commit.md` (4+6+7), `reports/synthetic_phase5a_design.json`.

This document plans the generators, graders, evaluators, and fairness gates for the two new families. It re-uses the generic two-phase generator pattern (`build_task_skeleton` pure + `bake_golden` tool-backed) and the `BaseEvaluator` weighted-component pattern, but implements **new** generator/grader/evaluator modules per family. **Nothing here is implemented in Phase-5A**; this is the build plan for the separately-authorized Phase-5B.

## 1. Family A generator — `generators/p15_sta_handoff_gen.py` (new)

Mirror the p14 generator's architecture (pure skeleton + tool-backed bake), with new content.

- **`build_task_skeleton(out, task_id, seed, intent, partition, view, decoy_recipe, condition)`** (pure, no tool): writes the deterministic instance tree:
  - `prompt.md`, `metadata.json` (`track:"p15_sta_handoff"`, `tool:["pt"]`, `scoring.weights`, `files.{visible,editable,hidden,forbidden}`, `generator` params, `condition∈{Base,BundleS,TypedContract}`);
  - `files/exception_config.json` (editable; ships **mis-bound** in Base — wrong intent/partition/view per the instance's `wrong_binding_green`);
  - `files/constraints.sdc`, `design.v`, `tiny.db`, `tiny.lib`, `pt_signoff.tcl`, `run_public.sh`/`run_public.tcl`, the authority-chain artifacts (`intent.md`, `cdc_report.rpt`, `reset_report.rpt`, `signoff.log`) **with condition-dependent labels** (Base = overloaded `timing_tag`; BundleS/TypedContract = canonical labels + value-domains/glossary/contract or typed schema);
  - `hidden/signoff_intent_truth.json` (DAG + coverage matrix + golden + wrong_binding_green + decoy_sources — §A.4);
  - `hidden/grade_sta_handoff.py` (new grader, §3); `hidden/run_hidden.sh` (5-phase PT orchestrator: launder→coverage→signoff→regen→grade).
- **`bake_golden(task_dir, pt_cmd, evidence_steps)`** (tool-backed, real PT on b04): runs the golden binding AND the `wrong_binding_green` through real `pt_shell` to produce the baked timing bodies (`wrong_binding_signoff.rpt`) — the empirical wrong-binding-feasibility evidence. Deterministic given the seed.
- **Determism/fail-closed:** all randomness from a single `seed` (RNG, no `time`/`random` globals); any tool failure during bake aborts the instance (no partial instance written). Generation is reproducible: same seed ⇒ byte-identical tree (asserted in the generator's self-test).

### A — Semantic-diff audit emitter
After skeleton+bake, the generator computes `semantic_diff_audit.json` (project public constraints → `consistent_tuples_public`, assert `uniquely_determined_by_public=False` and `bundle_discloses_golden=False`); on failure, raise (fail-closed) and regenerate with a different decoy draw.

## 2. Family B generator — `generators/p16_spice_handoff_gen.py` (new)

Same architecture, SPICE content.

- **`build_task_skeleton(out, task_id, seed, corner, load, metric, decoy_recipe, condition)`** (pure): writes `meas_config.json` (editable; ships mis-bound per `wrong_join_plausible`), `circuit.sp` (locked components — R/C/topology fixed; only the measurement-config block editable), `model.lib` (multi-corner sections), the authority chain (`char_spec`, `mission_profile`, `application_note`, `measurement.log`) with condition-dependent labels, `hidden/meas_request_truth.json` (relational join — §B.4), `hidden/grade_spice_handoff.py` (§4), `hidden/run_hidden.sh` (HSPICE orchestrator: run deck under submitted config → `.measure` → grade).
- **`bake_golden(task_dir, hspice_cmd)`** (tool-backed, real HSPICE on b04): runs the golden join AND the `wrong_join_plausible` through real `hspice` to bake `wrong_tuple_measure.lis` (a plausible number in range). Deterministic given seed.
- **Fail-closed + reproducibility:** identical contract to Family A.

### B — Semantic-diff audit emitter
Same shape; asserts the public slice under-determines the join and no bundle/typed-schema file discloses a golden value.

## 3. Family A grader — `tasks/…/<inst>/hidden/grade_sta_handoff.py` (new)

Distinct from `grade_workflow.py` (no master `EVIDENCE_OK` gate). Stdlib-only; reads the laundered `applied_hidden.sdc` PT result (forge-resistant) and `signoff_intent_truth.json`:

1. **re-derive golden** by walking the DAG (defensive: assert == `golden_binding`; tamper-caught).
2. `pt_signoff_green` — parse signoff header.
3. `provenance_attested` — submitted triple has a supporting authority edge of sufficient trust.
4. `coverage_cell_consistent` — (partition, view) is a `requires_exception` cell.
5. `check_view_legal` — check_mode legal for intent.
6. `not_masking` — SDC not weakened.
Emits markers; the evaluator (`eda_agentbench/evaluator/sta_handoff.py`, new, `STAHandoffEvaluator`) maps to weighted components (§A.5 weights).

## 4. Family B grader — `tasks/…/<inst>/hidden/grade_spice_handoff.py` (new)

Distinct six-dimension grader (§B.5). Stdlib + reads HSPICE `.lis`. Computes `simulation_success`, `numeric_validity` (number in `plausible_range`), `semantic_binding` (join == golden), `evidence_provenance` (agent's `provenance_attestation.json` cited sources == golden authorities), `artifact_completion`, `protocol_completion`. Evaluator `eda_agentbench/evaluator/spice_handoff.py` (`SPICEHandoffEvaluator`, new) maps to weights (§B.5).

## 5. Fairness gates

- **Family A (PT):** reuse `scripts/pt_health_sentinel.py` + `scripts/fullpath_check.py` + `scripts/measurement_control.py`, re-pointed at a Family-A golden instance (new `REFERENCE_FC_HASH`); the Level-1 sentinel stages the instance golden + runs `run_evidence_stage1.sh`, asserts `signoff=OK`; Level-2 runs the full reference path and asserts the metric invariants; `measurement_control` block = L2 bookends, admissible iff both healthy, valid-but-unfavorable = hard fail (no retry). **No new PT fairness code** beyond re-pointing.
- **Family B (HSPICE):** **new** `scripts/hspice_health_sentinel.py` — a clone of `pt_health_sentinel.py` with the PT header assertion swapped for a `.measure`/metric-range assertion over a baked golden deck (`hspice -i circuit.sp -o …`, parse `.lis`). A new SPICE Level-2 `fullpath_check` clone asserts the golden measurement number is in range through the full run→measure→parse path. Same `measurement_control` block contract. (Precedented: P4 damping/OTA already carry a real-Spectre calibration gate + agentic fairness gate; `calibrate_p4_{amp,damping}.py` are the analogues.) This is the only genuinely **new** fairness infrastructure in the program.

## 6. Forge-resistance + integrity

- **Family A:** grading reads only the laundered `applied_hidden.sdc` (clock/SDC) and the submitted `exception_config.json`; raw PT output `[apply]`-prefixed so an injected marker cannot match; `anti_cheat/guard.py` `ForbiddenModificationGuard` snapshots `run_public.sh`/`run_hidden.sh`/authority artifacts.
- **Family B:** locked deck components (R/C/topology) enforced by `run_hidden.sh` (mirrors P4 damping's lock check); grading reads the submitted `meas_config.json` + the real `.lis`; authority artifacts forbidden.
- **Integrity guard (both):** `canonical_integrity.freeze` over instance roots + generator/grader/evaluator/fairness code + freeze manifests; `run_chain_guarded.py` runs every paid episode from an exact-commit isolated worktree; verify pre-run/post-episode/post-chain; mutation ⇒ `FAILED_INTEGRITY` (exit 3), sidecar, no silent restore.

## 7. Independence-check, information-equivalence, and hard-feasibility tools (mechanical audits at generation)

**Independence checker** (`scripts/phase5a_independence_check.py`). It **operationally verifies structural independence under the five preregistered criteria** — it does **not** prove independence. It hashes the new generator/grader/evaluator source and asserts: (a) none imports `grade_workflow`/`p14_workflow_handoff_gen`; (b) the role vocabularies are disjoint from p14's `{slow,typ,fast,func,test,lowpower}` ∪ PVT labels; (c) the new truth files contain none of p14's `axis_schema`/`semantic_role_mapping`/`global_authority_tuple` keys; (d) the grader module is distinct (no `EVIDENCE_OK` master-gate pattern); (e) the decoy-recipe class is distinct. A pass = no *detected* structural overlap under those criteria. Fail-closed: a structural-overlap finding blocks the freeze.

**Information-equivalence audit** (planned as `scripts/phase5_info_equiv_audit.py`; **as built** it is part of `generators/phase5_audits.py`, per BundleS/TypedContract pair). Emits `info_equiv_audit.json`: enumerates every semantic fact (role names, value domains, source identifiers, authority relations, provenance structure, legal types) and asserts each is **present in both or absent from both**; golden values, answer-bearing assertions, and post-submission verifier feedback must be **absent from both**; token count and surface format need not match but **every semantic addition/omission is disclosed**. Fail-closed regenerate.

**Hard-feasibility bake gate** (amendment 4; enforced inside each generator's `bake_golden`). For every primary instance, the bake must produce a wrong-binding artifact that (a) is accepted by the tool syntax, (b) executes successfully, (c) produces a plausible signoff (A) / plausible numeric output (B), (d) remains semantically incorrect, (e) is **rejected** by the typed provenance/authority grader. If the wrong binding is trivially tool-red, unparsable, NaN, or otherwise obvious, the instance is **ineligible** and is regenerated (fail-closed). The bake writes the per-instance `hard_feasibility.json` recording all five criteria + the grader's rejection.

## 8. Build sequence (Phase-5B; separately authorized)

1. Family A generator + grader + evaluator + dev instance + re-pointed PT fairness gate.
2. Family B generator + grader + evaluator + dev instance + `hspice_health_sentinel` + SPICE fullpath check.
3. `scripts/phase5a_independence_check.py` + semantic-diff audit wiring.
4. Smoke both dev instances through the real tools on b04 (golden=1.0, wrong-binding-green / wrong-tuple-plausible confirmed) — the Phase-5A fairness-gate analogue of the "grade the known-correct solution through the same path" gate.
5. Freeze scripts + manifests (`cig.freeze`); analysis code (instance-resampling, paired Base-vs-BundleS tables, six-dimension separation for B); pre-run review; guarded execution.

Nothing in §1–§8 is implemented in Phase-5A.
