# Phase-5A — Family / Task Specifications (deliverable 2)

**Date:** 2026-08-03 · **Branch:** `synthetic-phase0a` · **Status:** design-only, no implementation, no paid calls, stopped for review (no push).
**Companion:** `docs/synthetic_phase5a_design.md` (master), `…generator_grader_plans.md` (3), `…budget_risk_commit.md` (4+6+7), `reports/synthetic_phase5a_design.json`.

This document specifies the two new semantic-handoff families at task-level detail and gives the independence audit that **operationally verifies structural independence under the five preregistered criteria** (it does not *prove* independence). It is **design only**; no generator or grader is implemented in Phase-5A.

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
    {"from":"INT+CDC","to":"intent_class=<G_intent>","rule":"override"},
    {"from":"CDC","to":"target_partition=<G_partition>","rule":"crossing_pin"},
    {"from":"COV","to":"check_mode=<G_view>","rule":"requires_exception[<G_partition>][<G_view>]"}
  ],
  "coverage_matrix": {"<G_partition>": {"<G_view>": {"<G_intent>": "requires_exception"}}},
  "golden_binding": {"intent_class":"<G_intent>","target_partition":"<G_partition>","check_mode":"<G_view>"},
  "wrong_binding_green": {"intent_class":"<W_intent>","target_partition":"<G_partition>","check_mode":"<G_view>"},
  "decoy_sources": ["PRIOR","INT_stale","RST_misScoped"]
}
```
*(illustrative **schema only**; `<G_*>` are the hidden golden tokens and `<W_*>` the wrong-but-green tokens. Concrete values are generated per-instance from committed seeds and frozen in this hidden file at the Phase-5B pre-run freeze — **never published in a design document**.)*

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

| Instance | id | golden region (hidden) | value vocabulary | decoy structure |
|---|---|---|---|---|
| Dev/debug | `p15_dev_0000` | R-dev (pilot only) | base set | minimal |
| Eval 1 | `p15_eval_0001` | R1 | base set | authority-conflict A |
| Eval 2 | `p15_eval_0002` | R2 (disjoint from R1) | alt partition names | authority-conflict B (stale-intent-led) |
| Eval 3 | `p15_eval_0003` | R3 (disjoint from R1,R2) | alt intent names | authority-conflict C (mis-scope-led) |

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

The deck runs and yields a **plausible number for any tuple**. A wrong binding — e.g. the requested metric evaluated at a fast corner instead of the spec's slow corner, or a heavy load instead of the spec's light load — still exits 0 and produces a phase margin like **62°** where the spec-correct binding gives **48°** (illustrative numbers). Both are physically reasonable opamp PM values; simulation success + numeric plausibility do **not** identify the semantic binding. The instance ships a baked **wrong-tuple-plausible artifact** (`wrong_tuple_measure.lis`, real HSPICE on b04) proving the wrong tuple simulates with a plausible number.

### B.4 Hidden-truth representation (`meas_request_truth.json`)

Distinct from p14 and Family A. No `axis_schema`, no DAG. A relational join:

```json
{
  "request": {"metric":"<G_metric>","requested_by":"char_spec","clause":"§4.1"},
  "authorities": {
    "metric": {"src":"char_spec","value":"<G_metric>","trust":"primary"},
    "corner": {"src":"mission_profile","value":"<G_corner>","trust":"primary"},
    "load_condition":{"src":"application_note","value":"<G_load>","trust":"primary"}
  },
  "decoy_authorities": [
    {"role":"corner","src":"mission_profile_stale","value":"<W_corner>","trust":"none"},
    {"role":"load_condition","src":"load_note_swapped","value":"<W_load>","trust":"none"}
  ],
  "golden_join": {"corner":"<G_corner>","load_condition":"<G_load>","metric":"<G_metric>"},
  "wrong_join_plausible": {"corner":"<W_corner>","load_condition":"<W_load>","metric":"<G_metric>"},
  "plausible_range": {"min":40,"max":75}
}
```
*(illustrative **schema only**; `<G_*>` hidden golden tokens, `<W_*>` wrong-but-plausible tokens. Concrete values are generated per-instance from committed seeds and frozen in this hidden file at the Phase-5B pre-run freeze — **never published in a design document**.)*

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

| Instance | id | golden region (hidden) | value vocabulary | decoy structure |
|---|---|---|---|---|
| Dev/debug | `p16_dev_0000` | R-dev (pilot only) | base set | minimal |
| Eval 1 | `p16_eval_0001` | R1 | base corners | substitution A (stale corner) |
| Eval 2 | `p16_eval_0002` | R2 (disjoint from R1) | alt corner naming | substitution B (swapped load) |
| Eval 3 | `p16_eval_0003` | R3 (disjoint from R1,R2) | alt metric naming | substitution C (stale prior log) |

`p16_dev_0000` excluded from primary analysis by predeclared id. Distinct golden, vocabulary, and decoy structure per eval instance.

## §3. Independence audit (5 dimensions × 3 families)

| Dimension | p14 | Family A | Family B | all differ? |
|---|---|---|---|---|
| Text template | value-swap signoff-package regeneration | authority-chain exception-intent reconciliation | request-authority measurement join | ✅ |
| Role vocabulary | scenario×corner (+PVT, clock) | intent_class×partition×check_mode | corner×load_condition×metric | ✅ |
| Hidden-truth representation | `axis_schema`+`semantic_role_mapping`+flat `global_authority_tuple` | provenance **DAG** + coverage matrix | request-authority **relational join** | ✅ |
| Grader implementation | `grade_workflow.py` master `EVIDENCE_OK` + typed echecks | `grade_sta_handoff.py` provenance-attestation + coverage-cell (no master gate) | `grade_spice_handoff.py` 6-dimension separation | ✅ |
| Decoy logic | multi-source **intersection** (role-swap/stale-netlist/PVT) | **authority-conflict** (stale-intent/mis-scope) | **authority-substitution** (stale-profile/swapped-load) | ✅ |

**Conclusion of audit (operational, not a proof):** under the five preregistered criteria, Family A and Family B show **no detected structural overlap** with p14 and differ from each other on all five. The mechanical checker (`scripts/phase5a_independence_check.py`, `…generator_grader_plans.md` §7) **operationally verifies structural independence under the five preregistered criteria** at generation time; it does **not** prove semantic novelty.

**Family × execution-tool confound (recorded).** Family A (STA) runs on PrimeTime and Family B (SPICE) on HSPICE, so family and tool are confounded: family-specific differences **cannot be attributed** to semantic domain versus tool environment. Inference is limited to the within-family, within-model Base-vs-BundleS contrast (tool held constant); cross-family comparison is descriptive only.

## §4. Public-information disclosure audit (per family × instance × condition)

For each (family, instance, {Base, BundleS, TypedContract}), the generator emits `semantic_diff_audit.json` (see `…design.md` §5) recording `consistent_tuples_public`, `golden_in_public_set=True`, `uniquely_determined_by_public=False`, `bundle_discloses_golden=False`. An instance failing any assertion is rejected and regenerated at the pre-run freeze (deterministic fail-closed), never entering the paid set.

## §5. Wrong-binding feasibility evidence (real-tool, per instance)

Each instance ships a baked artifact (produced on b04 through the real tool, hash-recorded) proving the core property:
- Family A: `wrong_binding_signoff.rpt` — real PT `report_timing` on the wrong binding, header `signoff=OK`.
- Family B: `wrong_tuple_measure.lis` — real HSPICE `.measure` on the wrong tuple, number inside `plausible_range`.

These are the empirical proof that tool success ≠ semantic correctness for the specific instance; they are generated before the instance is admitted to the freeze.

## §6. Manifests and hashes (per family)

Each instance is covered by `canonical_integrity.freeze(repo, task_roots=[<instance dir>], code_files=[generator, grader, evaluator, fairness code], evidence_files=[freeze manifests])`. The per-family pre-run freeze emits the standard 6 manifests (`randomization_manifest`, `frozen_config`, `interpretation_table`, `membership_code_manifest`, `prerun_freeze_manifest`, `canonical_integrity_manifest`) plus the per-instance `semantic_diff_audit.json` and wrong-binding-feasibility artifact hashes. Custody byte-match (`MANIFEST.json`+`SHA256SUMS`) is produced by the pipeline for every preserved episode, identical contract to Phase-4Y.

## §7. Information isolation — no literal goldens are published

These design documents and `reports/synthetic_phase5a_design.json` deliberately contain **no literal golden binding** for any instance. Instance tables and the machine-readable design carry only (a) an opaque disjoint-region tag (`R1`/`R2`/`R3`, plus `R-dev` for the excluded dev instance), (b) a vocabulary variant, and (c) a decoy recipe — enough to prove the three eval instances have **distinct** hidden truths drawn from **disjoint** regions of the role space, without disclosing any truth. Worked-example truth-file blocks use placeholder tokens (`<G_*>`, `<W_*>`) to illustrate **schema only**.

The actual golden tuples are:
- **generated** deterministically from committed per-instance seeds at Phase-5B generation time;
- **stored** only in the access-controlled per-instance hidden files (`hidden/signoff_intent_truth.json`, `meas_request_truth.json`), which are listed under `metadata.json` `files.hidden` + `files.forbidden` and are **never copied into the agent workspace** by `create_agent_workspace`;
- **frozen** (hash-pinned by `canonical_integrity.freeze`) at the Phase-5B pre-run freeze, under the exact-commit integrity-guarded worktree, **before the first paid episode** — which is the methodologically correct point to pre-register the goldens.

`reports/`, `docs/`, and the repo root are **not** in the agent's workspace scope; the `anti_cheat` `ForbiddenModificationGuard` and the custody byte-match (submitted editable files only; hidden truth/netlist/library/decoys/`.env`/model configs excluded) enforce that no agent-readable artifact carries a golden value. This was hardened on 2026-08-03 after an automated security review flagged that an earlier draft of `synthetic_phase5a_design.json` committed the literal eval-instance goldens (information-disclosure); the literal tuples were removed and replaced by the region tags above.
