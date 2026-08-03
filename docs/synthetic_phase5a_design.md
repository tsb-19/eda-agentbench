# Phase-5A — Cross-Family External-Validity Design (p14 program, external-validity phase)

**Date:** 2026-08-03 · **Branch:** `synthetic-phase0a` · **Status:** design-only, NO paid model calls, NO task-generator/grader implementation, stopped for review (no push).
**Scope:** design two **genuinely independent** semantic-handoff task families and three harness conditions, pre-register the confirmatory experiment, and freeze the analysis plan. Execution (generators, graders, paid episodes) is a **separately authorized** later phase (Phase-5B). This document is deliverable **(1) Phase-5A design report** and **(5) predeclared analysis plan**; companions are `docs/synthetic_phase5a_family_specs.md` (2), `docs/synthetic_phase5a_generator_grader_plans.md` (3), `docs/synthetic_phase5a_budget_risk_commit.md` (4+6+7), and the machine-readable `reports/synthetic_phase5a_design.json`.

## 0. Program context (frozen)

The p14 workflow-handoff clarity-bundle program is **frozen** (Phase-4Z). Established: on the p14 controlled pair, the full clarity bundle suppresses a semantic-axis binding failure for both Qwen3.7-Max and DeepSeek-V4-Pro (Tier 1); the non-answer **BundleS** (C1+C2+C4+C7: canonical labels + disjoint-axis declaration, value-domain definitions, glossary+refs, procedural contract) suffices for **Qwen** on development and a pre-frozen held-out family, but is **not established** for DeepSeek under exact counterbalancing (Tier 2, model-contingent); no minimal component or two-component bundle is a stable mechanism (Tier 3). The external-validity question this phase addresses:

> **Does the BundleS effect — a model-contingent, non-answer-bearing, harness-information-structure effect — replicate on task content and tools that share NONE of p14's signature structures?**

This is not a re-test of p14. It is a test of **generalization of the mechanism** across task family, tool, role vocabulary, hidden-truth representation, grader, and decoy logic. Two families are constructed so that a replication (or a clean null) is informative about the *mechanism*, not about p14's particular content.

## 1. Non-goals (hard constraints, carried from the freeze)

- **No** additional C1/C2/C4/C7/C24 experiments on p14; **no** modification of any existing p14 task or report.
- **No** consumption or modification of held-out-family-2 (p14 tasks 0024–0027); it remains an untouched future-replication asset.
- **No** paid model calls and **no** task-generator/grader implementation in Phase-5A. (Design only.)
- **No** push.
- **No** adaptive k escalation and **no** task/wording change after the first model result (predeclared scope is binding).
- All future paid runs, fairness gates, evidence extraction, and custody execute from an **exact-commit integrity-guarded isolated worktree**; the root development workspace is non-authoritative; `chmod 444` is defense-in-depth only.

## 2. Independence contract — what the new families must NOT share with p14

Each new family is constructed to differ from p14 (and from each other) on **five** structural dimensions. Generic harness infrastructure is re-used (re-skinned), but the task-defining content is independent. The per-dimension audit is in `docs/synthetic_phase5a_family_specs.md` §3; summarized here:

| Dimension | p14 (frozen, not reused) | Family A (new) | Family B (new) |
|---|---|---|---|
| **Text template** | "resolve the semantic-role binding, infer the unique package, regenerate the fresh sign-off chain" (timing-signoff value-swap) | "reconcile the timing-exception signoff intent from the authority chain; bind (intent, partition, view)" | "bind the characterization measurement request to (corner, load, metric) by joining the request to its authority sources" |
| **Role vocabulary** | `scenario∈{slow,typ,fast}` × `corner∈{func,test,lowpower}` (+ PVT labels, clock axis) | `intent_class∈{functional_close,cdc_isolate,reset_exempt,scan_override}` × `target_partition∈{core,cdc_a,cdc_b,reset_ctrl,scan}` × `check_mode∈{setup,hold,both}` | `corner∈{SS,FF,TT}×V×T` × `load_condition∈{light,nominal,heavy}` × `metric∈{gain,gbw,pm,slew,vdsat}` |
| **Hidden-truth representation** | `handoff_truth.json`: `axis_schema` (typed_axes, C1–C5 constraints, expected_unique_assignment, uniqueness counts), `semantic_role_mapping`, `global_authority_tuple` (flat 4-tuple) | `signoff_intent_truth.json`: a **provenance DAG** (`authority_nodes`, `derivation_edges`, `trust_level`) + a `coverage_matrix` (partition×view×intent); binding = graph query | `meas_request_truth.json`: a **request-authority relational join** (`request→{metric,corner_authority,load_authority}`); golden = 3-way join, no graph, no axis_schema |
| **Grader implementation** | `grade_workflow.py`: typed-membership echecks folded into one master `EVIDENCE_OK` gate | `grade_sta_handoff.py`: **provenance-path attestation** + **coverage-cell consistency** (no master EVIDENCE_OK gate; signoff-green does NOT imply attested) | `grade_spice_handoff.py`: explicit **6-dimension separation** (sim success / numeric validity / semantic binding / evidence provenance / artifact completion / protocol completion) |
| **Decoy-generation logic** | partially-truthful multi-source **intersection** decoys: `report_A` role-swap + `report_B` stale-netlist + `report_C` PVT-label + `evidence_D` swapped-manifest + `prev_signoff.log` (pairwise-plausible, globally-unique-by-constraint-intersection) | **authority-conflict** decoys: stale uArch-intent revision + mis-scoped CDC report + wrong-domain reset report + prior-signoff attesting the wrong binding (conflict-by-authority, not by field-swap) | **authority-substitution** decoys: substituted corner mission-profile + swapped load note + stale prior measurement log with consistent-but-wrong numbers (substitution-by-source, not by value-swap) |

**Shared (re-used) generic infrastructure** (safe; not task-defining): `prompt.md`+`metadata.json`+`files/`/`hidden/`/`solution/` directory shape; `metadata.json` `tool`/`track`/`scoring.weights`/`files.{visible,editable,hidden,forbidden}` schema; `ToolEnvironmentDetector`/`EnvShim` PATH injection; `run_public.sh`/`run_hidden.sh` orchestrator + forge-resistant launder (`applied_*.sdc`, raw-output `[apply]` prefix); `BaseEvaluator` weighted-component pattern; generator `build_task_skeleton`(pure)+`bake_golden`(tool-backed) two-phase; the canonical-tree integrity guard (`canonical_integrity.py`/`run_chain_guarded.py`); `chain_executor`+`episode_arbiter`; freeze→pipeline→launcher pattern; custody byte-match; request-telemetry transport dimensions.

## 3. The two families (at a glance; detail in `…family_specs.md`)

**Family A — STA constraint/exception handoff (PrimeTime; new track `p15_sta_handoff`).** The agent receives a small design + a partial SDC + an **authority chain** (micro-architecture intent, a CDC report, a reset-domain report, a prior signoff log) and must edit `exception_config.json` to bind each timing exception to `(intent_class, target_partition, check_mode)`. The design is **marginally timed and healthy**: a *wrong* binding — e.g. an `cdc_isolate` intent bound to the `core` partition, or a `hold`-only check applied as `setup` — still produces a **green `report_timing`** (the wrong exception either relaxes a path that already has slack, or is a legal-but-different exception), so **tool success cannot distinguish correct from semantically incorrect execution**. A typed **evidence/provenance oracle** (`grade_sta_handoff.py`) walks the authority DAG and rejects any binding not attested by an authority edge of sufficient trust, *independently* of the PT signoff result.

**Family B — SPICE model/measurement handoff (HSPICE; new track `p16_spice_handoff`).** The agent receives a characterization measurement request + an authority chain (a characterization spec naming the metric, a PVT mission profile, a load/application note, a stale prior measurement log) and must edit `meas_config.json` to bind `(corner, load_condition, metric)`. The deck **runs and yields a plausible number for any tuple**: a wrong binding (e.g. `metric=pm` but at the `FF` fast corner instead of the spec's `SS` slow corner, or `load=heavy` instead of `light`) still exits 0 and produces a **plausible** measurement (e.g. 62° phase margin where the spec-correct binding gives 48° — both physically reasonable), so **simulation success + numeric plausibility ≠ semantic correctness**. Correctness depends on **role-conditioned evidence binding** (which corner/load/metric is *authoritative*), not on deck syntax. The grader (`grade_spice_handoff.py`) reports **six separated dimensions**: simulation success, numeric validity, semantic binding, evidence provenance, artifact completion, protocol completion.

Tool feasibility is **established** (not a risk): HSPICE, Spectre, and PrimeTime are all forwarded to b04 through `/data1/tongsb/eda-remote-shim/` (`synopsys/hspice/V-2023.12`, `cadence/SPECTRE21.10.582/V21`, `synopsys/prime/V-2023.12`); open-source simulators (ngspice/Xyce) are intentionally unsupported and are not used.

## 4. Three harness conditions (the experimental variable)

Identical hidden truth and grader across conditions within a family; the conditions differ **only in visible disclosure content**. Budgets (actions, tokens, tool access, timeout, feedback) are **matched** across conditions; the public feedback runner (`run_public.sh`) is byte-identical across conditions and gives **no semantic hint** (only "green signoff" / "measured number") — this is exactly the tool-success-≠-semantic property.

1. **Base** — ambiguous natural-language handoff; authority artifacts use **overloaded field labels** (Family A: a single `timing_tag` conflating intent/partition/view; Family B: a single `condition_id` conflating corner/load/metric). No glossary, no schema, no value-domain definitions, no procedural contract. The role mapping must be **inferred** from the evidence intersection.
2. **BundleS** — the established non-answer-bearing abstract components, **mapped mechanically** to the new family (no task-specific wording optimization, no C6 answer assertion, no golden values): (a) **canonical labels + disjoint-axis declaration** (≈C1), (b) **value-domain definitions** for each axis (≈C2), (c) **glossary + references** (≈C4), (d) **procedural contract** wording (≈C7). Delivered as natural-language/structured-prose files.
3. **TypedContract** — the **same information content** as BundleS (same labels, value-domains, glossary, contract) delivered as a **machine-readable typed schema** (JSON Schema declaring roles, axes, source-IDs, provenance precedence, types). **No golden values.** **No post-submission oracle/verifier feedback** (true of all three conditions; the agent submits once). Matched action/token/tool/timeout/feedback budgets to Base and BundleS.

BundleS and TypedContract are therefore **information-equivalent** and differ only in *representation* (NL prose vs. machine-readable schema). This isolates "machine-readable typed contract" as a variable from "non-answer disclosure content."

## 5. Semantic-diff audit (automatic; per family × instance × condition)

An automatic audit proves BundleS and TypedContract **do not disclose the golden tuple and do not uniquely determine it from public information**. For each (family, instance, condition), the generator (which knows the full truth) projects the **public** constraint set — the visible artifacts plus the condition's disclosure — and enumerates the tuples consistent with **public information only**:

- `consistent_tuples_public`: the satisfying set under the public slice;
- `golden_in_public_set`: True (the golden must remain *possible*; it is never contradicted by truth);
- `uniquely_determined_by_public`: **must be False** for Base, BundleS, and TypedContract (the binding is under-determined by public info; the agent must still *reason* across authority sources to single it out);
- `bundle_discloses_golden`: **must be False** (no BundleS/TypedContract file contains or entails the golden tuple as a literal or unique consequence).

The audit is emitted as `semantic_diff_audit.json` per (family, instance, condition) and is a **generation-time hard gate**: if any condition uniquely determines the golden from public info, or any bundle file discloses it, the instance is **rejected and regenerated** (deterministic fail-closed). This is the same *kind* of uniqueness accounting as p14's `uniqueness:{total_assignments,satisfying_count,exactly_one}`, but applied to the **public disclosure** (proving non-disclosure) rather than to the full truth, computed by separate code, and emitted as a separate artifact.

## 6. Pre-registered confirmatory design

| Parameter | Value |
|---|---|
| Models | Qwen3.7-Max, DeepSeek-V4-Pro (one gateway, SSE streaming) |
| Primary families | Family A (`p15_sta_handoff`, PT) **and** Family B (`p16_spice_handoff`, HSPICE) |
| Evaluation instances | **3 per family**, with distinct hidden truths, value vocabularies, and decoy structures |
| Dev/debug instance | **1 per family**, pilot-only, **never enters primary analysis** (excluded by predeclared id) |
| Conditions in core experiment | **Base** and **BundleS** |
| Repetitions | **2 stochastic** per task–model–condition (temperature 0.7, distinct provider seeds) |
| **Total core primary episodes** | **48** = 2 families × 3 instances × 2 models × 2 conditions × 2 reps |
| Unit of external-validity analysis | **task instance** (n=3 per family); episodes are nested replications |
| Counterbalancing | seeded exact-counterbalanced blocked randomization, frozen pre-run (position balance asserted) |
| k escalation | **none** (no adaptive k) |
| Task/wording changes after first result | **none** (frozen) |
| Secondary extension (TypedContract) | **24 episodes** = 2×3×2×1×2; **separately authorized**, **not executed in Phase-5A** |

No task or wording change is permitted after the first model result. If a generator instance fails its semantic-diff audit or fairness gate **before** the first paid result, it is regenerated/replaced at the **pre-run freeze** (still design-time); after the first paid result, the instance set is frozen.

## 7. Predeclared outcomes

**Primary (confirmatory):** **semantic-binding correctness** — the submitted bound tuple equals the hidden golden tuple (binary per episode).

**Co-primary diagnostic:** **failure subtype**. Two generic framings — `axis/role_binding_failure` (a value placed on the wrong typed role) vs `role_conditioned_value_selection_failure` (right roles, wrong values) — plus **family-specific subtypes**:

- **Family A:** `authority_unattested_binding` (no authority edge supports it), `coverage_cell_mismatch` (the (partition,view) cell is not the flagged `requires_exception` cell), `check_view_inversion` (setup⇄hold inverted), `scope_object_misbind` (right intent, wrong partition).
- **Family B:** `corner_authority_misbind`, `load_authority_misbind`, `metric_role_misbind` (right metric family, wrong metric), `analysis_implied_mismatch` (analysis type inconsistent with the metric, caught even when the number is plausible).

**Secondary (descriptive):** artifact/tool correctness (Family A: signoff component; Family B: 6-dimension sub-scores), numeric/signoff correctness (number in spec range / slack MET), evidence/provenance correctness (cited authority source == golden authority), protocol completion (voluntary FINISH), terminal transport validity, recovered transport degradation, actions/tokens/wall-time/cost.

## 8. Predeclared analysis plan (no unblocked pooled test as primary)

1. **Principal contrast (primary):** per-task paired **Base vs BundleS** outcomes, within instance, within model. Reported as a per-instance direction and a per-episode 2×2 (condition × correct) table. The instance is the unit; the headline is the **per-instance paired direction + raw counts**, not a pooled rate.
2. **Family-specific effects:** Family A vs Family B, reported separately (the two families are not pooled for the primary).
3. **Model-specific effects:** Qwen vs DeepSeek, reported separately.
4. **Interactions (descriptive):** model×harness and family×harness, given n=3 instances/family (directional only; explicitly labeled exploratory/descriptive).
5. **Uncertainty:** exact binomial intervals per cell and a **non-parametric bootstrap over the 3 instances** (instance is the resampling unit, since episodes are nested); reported as intervals, not p-values, for the primary.
6. **Significance testing (secondary, predeclared):** a **blocked** test only — an exact sign test / McNemar over **instance-level** paired Base-vs-BundleS outcomes (n=3 per family; underpowered by design) — reported as descriptive, **never as the primary headline**. **No unblocked pooled-over-episodes significance test is computed as a primary or secondary result** (episode pooling would inflate n and ignore nesting; it is predeclared out).
7. **Diagnostic enrichment:** failure-subtype bar per (family, model, condition), mapped to the family-specific subtypes above.
8. **Reliability layers:** the seven independent dimensions (semantic binding, artifact/tool, numeric/signoff, evidence/provenance, protocol completion, terminal transport validity, recovered degradation) + tool-health sentinel + source-tree integrity, reported separately, never collapsed.

The primary result is **descriptive and paired**: "for each instance, does BundleS change the semantic-binding direction relative to Base, for each model, in each family." Replication of the p14 BundleS effect would be: a consistent Base→BundleS improvement direction across the 3 instances of a family, for a given model. A clean null would be: no consistent direction. Either outcome is informative about external validity.

## 9. Infrastructure reuse (mandatory; detail in `…generator_grader_plans.md`)

- **Integrity guard:** every Phase-5B paid episode runs from an exact-commit isolated worktree via `run_chain_guarded.py`; `canonical_integrity.freeze(…)` over the new task roots + generator/grader/fairness code + freeze manifests; `verify` pre-run/post-episode/post-chain; any mutation → `FAILED_INTEGRITY` (exit 3), sidecar, no silent restore. (Identical contract to the Phase-4Y bridge.)
- **Sample-membership arbiter:** committed `episode_arbiter` is the sole membership authority; `measurement_valid = terminal_transport_valid AND workspace_gradeable`; all membership code committed+hashed in the pre-run freeze.
- **Durable executor + chain:** `chain_executor` with stdin isolation, atomic `RUNNING/COMPLETE/FAILED/FAILED_INTEGRITY` state, arbiter-driven ACCEPT/REPLACE/STOP.
- **Request telemetry + transport:** SSE streaming (`EDA_BENCH_STREAM_RESPONSES=1`); two independent transport dimensions (`terminal_transport_valid`, `recovered_transport_degradation`).
- **Tool-health sentinel + full-path measurement control:**
  - Family A: reuses the **PT** Level-1 sentinel (`pt_health_sentinel`) + Level-2 `fullpath_check`, re-pointed at a Family-A golden (new `REFERENCE_FC_HASH`); `measurement_control` block (L2 bookends; admissible iff both healthy; valid-but-unfavorable = hard fail, no retry).
  - Family B: a **new** `hspice_health_sentinel.py` (clone of `pt_health_sentinel` with the header assertion swapped for a `.measure`/metric-range assertion over a baked golden deck) + a SPICE Level-2 `fullpath_check` clone; same block-measurement-control contract. (Pattern is precedented: P4 damping/OTA already carry a real-Spectre calibration gate + agentic fairness gate.)
- **Custody:** pipeline byte-match against `preserved_artifacts.json["submitted_file_hashes"]`; `MANIFEST.json`+`SHA256SUMS` per evidence dir.

## 10. GO / NO-GO gates (before any Phase-5B paid call)

1. **Budget confirmation (binding):** core-48 projects to **≈ ¥563** (rate ¥11.72/ep derived from committed ledgers; range ¥528–578); secondary-24 ≈ ¥281; dev-pilot ≈ ¥94. Phase-4Z committed ¥682.25. The predeclared core-48 **must be confirmed against the current account balance** before execution — see `…budget_risk_commit.md`. If the account is the original ¥1000 (remaining ≈ ¥318), the core-48 does **not** fit; this is a budget decision for review, **not** an automatic k-cut (scope reduction requires explicit re-review and would reduce to 1 rep = 24 episodes ≈ ¥282, with the 2-rep design retained as the registered intent).
2. **Independence audit passes:** the 5-dimension audit (§2) shows no structural reuse of p14's signature; the semantic-diff audit (§5) shows no golden disclosure under any condition.
3. **Wrong-binding feasibility evidence:** each instance ships a baked artifact proving the misbinding still runs green (Family A) / still simulates with a plausible number (Family B) through the **real** tool on b04.
4. **Fairness gates healthy:** PT sentinel (A) and HSPICE sentinel (B) + full-path checks healthy on b04 at the pre-run freeze.
5. **Clean canonical tree** at the freeze commit; `cig.verify` passes.

## 11. Proposed commit sequence

**Phase-5A (this phase; docs-only, no paid calls):**
1. `docs(phase5a): cross-family external-validity design + predeclared analysis plan` (this doc) + `reports/synthetic_phase5a_design.json`.
2. `docs(phase5a): Family A & B task specifications + independence audit`.
3. `docs(phase5a): generator, grader, and fairness-gate plans`.
4. `docs(phase5a): budget table, risk register, commit sequence`.

**Phase-5B (separately authorized; NOT executed in Phase-5A):** Family A generator+grader+dev instance; Family B generator+grader+dev instance; `hspice_health_sentinel`+SPICE fullpath check; semantic-diff audit tooling; freeze scripts+manifests (`cig.freeze`); analysis code (instance-resampling, paired tables); pre-run review freeze; guarded execution (48 core episodes); pipeline+custody; report. The TypedContract secondary (24 episodes) is a **further** separately-authorized step.

Stop for review before any Phase-5B implementation or paid call.
