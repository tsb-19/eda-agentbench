# Phase-5A — Family / Task Specifications (deliverable 2)

**Date:** 2026-08-03 · **Branch:** `synthetic-phase0a` · **Status:** design-only, no implementation, no paid calls, stopped for review (no push).
**Companion:** `docs/synthetic_phase5a_design.md` (master), `…generator_grader_plans.md` (3), `…budget_risk_commit.md` (4+6+7), `reports/synthetic_phase5a_design.json`.

This document specifies the two new semantic-handoff families at task-level detail and gives the independence audit proving they share none of p14's signature structures. It is **design only**; no generator or grader is implemented in Phase-5A.

## Family A — STA constraint/exception handoff (PrimeTime; new track `p15_sta_handoff`)

### A.1 Scenario and semantic roles

A downstream signoff team hands the agent a **timing-exception signoff** whose binding is out of date. The agent receives a small synthesizable design (`design.v`), a single library (`tiny.db`/`tiny.lib`, corner-independent — the body's timing is marginally clean), a partial `constraints.sdc`, and an **authority chain** of artifacts: a micro-architecture **intent** document, a **CDC** (clock-domain-crossing) report, a **reset-domain** report, and a prior `signoff.log`. The agent edits `exception_config.json` to bind a set of timing exceptions, each to a typed triple:

- `intent_class ∈ {functional_close, cdc_isolate, reset_exempt, scan_override}` — the **timing intent** (what the exception is *for*).
- `target_partition ∈ {core, cdc_a, cdc_b, reset_ctrl, scan}` — the **constrained-object role** (which functional partition).
- `check_mode ∈ {setup, hold, both}` — the **analysis view / check type**.

The clock and netlist are **authority-anchored** (fixed, not bound by the agent) so the binding surface is exactly the three roles above — a different binding cardinality and vocabulary from p14's (scenario, corner).

### A.2 Authority/provenance chain (golden follows the chain)

The golden binding is **derived**, not stored as a flat tuple. It is the unique binding that is **attested** by the authority chain under a precedence order:

1. `intent_class` is named by the micro-architecture **intent** document (highest precedence), modulo a CDC/reset/scan override.
2. `target_partition` is pinned by the **CDC report** (for `cdc_*` intents) or the **reset report** (for `reset_exempt`) or the **scan** section.
3. `check_mode` is constrained by a **coverage matrix** (`coverage_matrix[partition][view][intent]`): only cells flagged `requires_exception` admit an exception, and some intents are setup-only or hold-only.

The golden is therefore the result of a **graph query** over the provenance DAG (authority nodes + derivation edges + trust levels) joined with the coverage matrix — **not** a constraint-intersection over a flat `axis_schema` (p14's representation).

### A.3 Tool success ≠ semantic correctness (the core property)

The design is healthy and marginally timed, so a **wrong** binding still produces a **green `report_timing`**:
- A wrong `intent_class` on the right partition applies a *different but legal* exception (e.g. `false_path` instead of `multicycle -2`) that relaxes a path which already has slack → still MET.
- A wrong `check_mode` (e.g. `hold` applied where `setup` was intended) leaves setup untouched (still MET) and may leave hold also MET (marginally clean) → still MET.
- A wrong `target_partition` applies the exception to a path that did not need it → no violation introduced.

So `report_timing` returns a clean signoff for the **wrong** binding. Only the **typed evidence/provenance oracle** (`grade_sta_handoff.py`) — which reads the authority chain — can reject it. The instance ships a baked **wrong-binding-green artifact** (`wrong_binding_signoff.rpt`, produced by the real PT on b04) proving the misbinding is signoff-feasible.

### A.4 Hidden-truth representation (`signoff_intent_truth.json`)

Distinct from p14's `handoff_truth.json`. No `axis_schema`, no `semantic_role_mapping`, no flat `global_authority_tuple`. Instead:

```json
{
  "authority_nodes": [
    {"id":"INT","artifact":"intent.md","clause":"§3.2","trust":"primary"},
    {"id":"CDC","artifact":"cdc_report.rpt","clause":"crossing#4","trust":"primary"},
    {"id":"RST","artifact":"reset_report.rpt","clause":"domain_B","trust":"primary"},
    {"id":"COV","artifact":"coverage.json","trust":"derived"},
    {"id":"PRIOR","artifact":"signoff.log","trust":"none (decoy)"}
  ],
  "derivation_edges": [
    {"from":"INT+CDC","to":"intent_class=cdc_isolate","rule":"override"},
    {"from":"CDC","to":"target_partition=cdc_b","rule":"crossing_pin"},
    {"from":"COV","to":"check_mode=setup","rule":"requires_exception[cdc_b][setup]"}
  ],
  "coverage_matrix": {"cdc_b": {"setup": {"cdc_isolate": "requires_exception"}, "hold": {}}},
  "golden_binding": {"intent_class":"cdc_isolate","target_partition":"cdc_b","check_mode":"setup"},
  "wrong_binding_green": {"intent_class":"functional_close","target_partition":"cdc_b","check_mode":"setup"},
  "decoy_sources": ["PRIOR","INT_stale","RST_misScoped"]
}
```

The grader **re-derives** the golden by walking the DAG (defensive: it does not trust `golden_binding` as a literal — it recomputes and asserts equality), so a tampered truth file is caught.

### A.5 Grader (`grade_sta_handoff.py`) — distinct from `grade_workflow.py`

No master `EVIDENCE_OK` gate. Instead, **separated checks**:
- `pt_signoff_green`: reads the laundered `applied_hidden.sdc` PT result (forge-resistant: grading reads only the laundered SDC, raw output `[apply]`-prefixed).
- `provenance_attested`: each role of the submitted binding has a supporting authority edge of sufficient trust (walks the DAG from the submitted triple).
- `coverage_cell_consistent`: the submitted (partition, view) is a `requires_exception` cell in the coverage matrix.
- `check_view_legal`: the submitted check_mode is legal for the intent (e.g. `scan_override`⇒`both`).
- `not_masking`: the submitted SDC does not weaken timing (`set_false_path`/`set_multicycle_path`/loosened `create_clock` ⇒ zero, as in p14's masking detector but on a different file set).

A binding can be `pt_signoff_green=True` yet `provenance_attested=False` (the misbinding case) — exactly the separation the property requires. The evaluator (`sta_handoff.STAHandoffEvaluator`, new) weights: provenance_attested 0.30, coverage_cell_consistent 0.20, check_view_legal 0.10, pt_signoff_green 0.10, not_masking 0.15, explanation 0.15 (weights finalized at generation; recorded in `metadata.json`).

### A.6 Decoy logic (authority-conflict; NOT p14's role-swap/stale-netlist/PVT)

Decoys create **authority conflict**, not field-swap:
- `intent_stale.md` — a prior revision of the intent document naming a **different** `intent_class` (stale authority; lower precedence).
- `cdc_report_misScoped.rpt` — a CDC report that lists the **wrong partition** as the crossing (scope mismatch).
- `reset_report_wrongDomain.rpt` — a reset report mis-scoping the exempt domain.
- `signoff.log` — a prior signoff **attesting the wrong binding** (plausible, non-authoritative).

Each decoy is internally consistent (real PT-backed timing bodies where applicable) and **pairwise-plausible**, but only the precedence-ordered authority chain yields the unique attested binding. This is conflict-by-authority, structurally unlike p14's intersection-of-typed-axes.

### A.7 Instances (1 dev + 3 eval)

| Instance | id | hidden golden (intent,partition,view) | value vocabulary | decoy structure |
|---|---|---|---|---|
| Dev/debug | `p15_dev_0000` | (cdc_isolate, cdc_a, setup) | base set | minimal (pilot only) |
| Eval 1 | `p15_eval_0001` | (reset_exempt, reset_ctrl, both) | base set | authority-conflict A |
| Eval 2 | `p15_eval_0002` | (scan_override, scan, both) | alt partition names | authority-conflict B (stale-intent-led) |
| Eval 3 | `p15_eval_0003` | (functional_close, core, setup) | alt intent names | authority-conflict C (mis-scope-led) |

`p15_dev_0000` is **excluded from primary analysis** by predeclared id. Each eval instance has a distinct golden, a distinct value vocabulary (renamed enum members), and a distinct decoy structure, so the instance set spans the design space rather than replicating one instance.

## Family B — SPICE model/measurement handoff (HSPICE; new track `p16_spice_handoff`)

### B.1 Scenario and semantic roles

A characterization team hands the agent a **measurement request**: "report the phase margin of the opamp under the slow corner at weak-drive load." The agent receives a circuit deck (`circuit.sp`, locked components — only the measurement configuration is editable), a `.lib` with multiple model corners, an **authority chain** (a characterization `spec` naming the metric, a PVT `mission_profile` naming the corner, a load `application_note` naming the load, a stale prior `measurement.log`), and edits `meas_config.json` to bind a typed triple:

- `corner ∈ {SS_0p9_-40, FF_1p3_125, TT_1p2_25, SS_0p9_125_cold}` — **process/model corner** (selects the `.lib` model section).
- `load_condition ∈ {light, nominal, heavy}` — **workload/operating mode** (selects the load element in the deck).
- `metric ∈ {gain, gbw, pm, slew, vdsat}` — **measurement target** (selects the `.measure`/analysis).

The analysis type (`.dc`/`.tran`/`.ac`) is **implied** by the metric (e.g. `pm`⇒`.ac`, `slew`⇒`.tran`) and must be inferred by the agent — a role-conditioned dependency, not deck syntax.

### B.2 Authority/provenance chain (golden is a relational join)

The golden binding is the **3-way join** of the request to its authority sources:
- `metric` ← characterization `spec` (which measurement was requested);
- `corner` ← PVT `mission_profile` (the signoff corner for this characterization);
- `load_condition` ← `application_note` (the operating load).

The representation is a **request-authority relational join** (`meas_request_truth.json`), not a graph (Family A) and not an axis_schema (p14).

### B.3 Tool success ≠ semantic correctness (wrong tuple still simulates, plausible number)

The deck runs and yields a **plausible number for any tuple**. A wrong binding — e.g. `metric=pm` at `FF_1p3_125` (fast) instead of the spec's `SS_0p9_-40` (slow), or `load=heavy` instead of `light` — still exits 0 and produces a phase margin like **62°** where the spec-correct binding gives **48°**. Both are physically reasonable opamp PM values; simulation success + numeric plausibility do **not** identify the semantic binding. The instance ships a baked **wrong-tuple-plausible artifact** (`wrong_tuple_measure.lis`, real HSPICE on b04) proving the wrong tuple simulates with a plausible number.

### B.4 Hidden-truth representation (`meas_request_truth.json`)

Distinct from p14 and Family A. No `axis_schema`, no DAG. A relational join:

```json
{
  "request": {"metric":"pm","requested_by":"char_spec","clause":"§4.1"},
  "authorities": {
    "metric": {"src":"char_spec","value":"pm","trust":"primary"},
    "corner": {"src":"mission_profile","value":"SS_0p9_-40","trust":"primary"},
    "load_condition":{"src":"application_note","value":"light","trust":"primary"}
  },
  "decoy_authorities": [
    {"role":"corner","src":"mission_profile_stale","value":"FF_1p3_125","trust":"none"},
    {"role":"load_condition","src":"load_note_swapped","value":"heavy","trust":"none"}
  ],
  "golden_join": {"corner":"SS_0p9_-40","load_condition":"light","metric":"pm"},
  "wrong_join_plausible": {"corner":"FF_1p3_125","load_condition":"heavy","metric":"pm"},
  "plausible_range": {"pm_min":40,"pm_max":75}
}
```

### B.5 Grader (`grade_spice_handoff.py`) — six separated dimensions (as required)

Per the directive, the grader reports **six** independent dimensions (no master gate):
1. `simulation_success` — HSPICE exit 0 + `.measure` result present.
2. `numeric_validity` — measured number in `plausible_range` (not NaN/absurd); **does not** equal semantic correctness.
3. `semantic_binding` — submitted (corner, load, metric) == re-joined golden.
4. `evidence_provenance` — each role's cited authority source == golden authority (the agent writes a `provenance_attestation.json`).
5. `artifact_completion` — measurement report artifact produced.
6. `protocol_completion` — voluntary FINISH.

A wrong tuple can score `simulation_success=1, numeric_validity=1` yet `semantic_binding=0` — the required separation. The evaluator (`spice_handoff.SPICEHandoffEvaluator`, new) weights: semantic_binding 0.30, evidence_provenance 0.20, simulation_success 0.10, numeric_validity 0.10, artifact_completion 0.15, protocol_completion 0.15.

### B.6 Decoy logic (authority-substitution; NOT p14's role-swap/stale-netlist, NOT Family A's authority-conflict)

Decoys **substitute** an alternative (still-valid) authority source:
- `mission_profile_stale.md` — a prior mission profile naming a **different corner** as the signoff corner.
- `load_note_swapped.md` — an application note with light/heavy **swapped** in the legend.
- `measurement.log` — a stale prior measurement with **consistent-but-wrong numbers** bound to the wrong tuple.

Substitution-by-source, structurally unlike p14's value-swap and unlike Family A's authority-conflict DAG.

### B.7 Instances (1 dev + 3 eval)

| Instance | id | hidden golden (corner,load,metric) | value vocabulary | decoy structure |
|---|---|---|---|---|
| Dev/debug | `p16_dev_0000` | (TT_1p2_25, nominal, gain) | base set | minimal (pilot only) |
| Eval 1 | `p16_eval_0001` | (SS_0p9_-40, light, pm) | base corners | substitution A (stale corner) |
| Eval 2 | `p16_eval_0002` | (SS_0p9_125_cold, heavy, slew) | alt corner naming | substitution B (swapped load) |
| Eval 3 | `p16_eval_0003` | (FF_1p3_125, light, gbw) | alt metric naming | substitution C (stale prior log) |

`p16_dev_0000` excluded from primary analysis by predeclared id. Distinct golden, vocabulary, and decoy structure per eval instance.

## §3. Independence audit (5 dimensions × 3 families)

| Dimension | p14 | Family A | Family B | all differ? |
|---|---|---|---|---|
| Text template | value-swap signoff-package regeneration | authority-chain exception-intent reconciliation | request-authority measurement join | ✅ |
| Role vocabulary | scenario×corner (+PVT, clock) | intent_class×partition×check_mode | corner×load_condition×metric | ✅ |
| Hidden-truth representation | `axis_schema`+`semantic_role_mapping`+flat `global_authority_tuple` | provenance **DAG** + coverage matrix | request-authority **relational join** | ✅ |
| Grader implementation | `grade_workflow.py` master `EVIDENCE_OK` + typed echecks | `grade_sta_handoff.py` provenance-attestation + coverage-cell (no master gate) | `grade_spice_handoff.py` 6-dimension separation | ✅ |
| Decoy logic | multi-source **intersection** (role-swap/stale-netlist/PVT) | **authority-conflict** (stale-intent/mis-scope) | **authority-substitution** (stale-profile/swapped-load) | ✅ |

**Conclusion of audit:** Family A and Family B share **none** of p14's five signature dimensions and differ from each other on all five. The new families therefore test **generalization of the BundleS mechanism** rather than re-testing p14's content. (The audit is re-verified mechanically at generation time by the independence-check tool described in `…generator_grader_plans.md` §6.)

## §4. Public-information disclosure audit (per family × instance × condition)

For each (family, instance, {Base, BundleS, TypedContract}), the generator emits `semantic_diff_audit.json` (see `…design.md` §5) recording `consistent_tuples_public`, `golden_in_public_set=True`, `uniquely_determined_by_public=False`, `bundle_discloses_golden=False`. An instance failing any assertion is rejected and regenerated at the pre-run freeze (deterministic fail-closed), never entering the paid set.

## §5. Wrong-binding feasibility evidence (real-tool, per instance)

Each instance ships a baked artifact (produced on b04 through the real tool, hash-recorded) proving the core property:
- Family A: `wrong_binding_signoff.rpt` — real PT `report_timing` on the wrong binding, header `signoff=OK`.
- Family B: `wrong_tuple_measure.lis` — real HSPICE `.measure` on the wrong tuple, number inside `plausible_range`.

These are the empirical proof that tool success ≠ semantic correctness for the specific instance; they are generated before the instance is admitted to the freeze.

## §6. Manifests and hashes (per family)

Each instance is covered by `canonical_integrity.freeze(repo, task_roots=[<instance dir>], code_files=[generator, grader, evaluator, fairness code], evidence_files=[freeze manifests])`. The per-family pre-run freeze emits the standard 6 manifests (`randomization_manifest`, `frozen_config`, `interpretation_table`, `membership_code_manifest`, `prerun_freeze_manifest`, `canonical_integrity_manifest`) plus the per-instance `semantic_diff_audit.json` and wrong-binding-feasibility artifact hashes. Custody byte-match (`MANIFEST.json`+`SHA256SUMS`) is produced by the pipeline for every preserved episode, identical contract to Phase-4Y.
