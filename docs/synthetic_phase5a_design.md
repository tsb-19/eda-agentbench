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

### 2a. Operational scope of the independence check + family×tool confound *(amendment 1)*

The mechanical checker (`scripts/phase5a_independence_check.py`) **does not prove independence**. It **operationally verifies structural independence under the five preregistered criteria** (no `grade_workflow`/p14-generator import; role vocabularies disjoint from p14's; truth-file schema free of p14's `axis_schema`/`semantic_role_mapping`/`global_authority_tuple` keys; grader module distinct; decoy-recipe class distinct). A pass means no *detected* structural overlap under those criteria — not a proof of semantic novelty.

**Family × execution-tool confound (recorded, not resolved).** Family A (STA) is executed through **PrimeTime** and Family B (SPICE) through **HSPICE**. Family and tool are therefore **confounded**: any family-specific difference *cannot be separately attributed* to semantic domain versus tool environment. Inference is limited to the **within-family, within-model Base-vs-BundleS contrast** (tool held constant); cross-family comparison is descriptive only and is never used to attribute effects to the semantic domain.

## 3. The two families (at a glance; detail in `…family_specs.md`)

**Family A — STA constraint/exception handoff (PrimeTime; new track `p15_sta_handoff`).** The agent receives a small design + a partial SDC + an **authority chain** (micro-architecture intent, a CDC report, a reset-domain report, a prior signoff log) and must edit `exception_config.json` to bind each timing exception to `(intent_class, target_partition, check_mode)`. The design is **marginally timed and healthy**: a *wrong* binding — e.g. an `cdc_isolate` intent bound to the `core` partition, or a `hold`-only check applied as `setup` — still produces a **green `report_timing`** (the wrong exception either relaxes a path that already has slack, or is a legal-but-different exception), so **tool success cannot distinguish correct from semantically incorrect execution**. A typed **evidence/provenance oracle** (`grade_sta_handoff.py`) walks the authority DAG and rejects any binding not attested by an authority edge of sufficient trust, *independently* of the PT signoff result.

**Family B — SPICE model/measurement handoff (HSPICE; new track `p16_spice_handoff`).** The agent receives a characterization measurement request + an authority chain (a characterization spec naming the metric, a PVT mission profile, a load/application note, a stale prior measurement log) and must edit `meas_config.json` to bind `(corner, load_condition, metric)`. The deck **runs and yields a plausible number for any tuple**: a wrong binding (e.g. the requested metric evaluated at a fast corner instead of the spec's slow corner, or a heavy load instead of the spec's light load) still exits 0 and produces a **plausible** measurement (e.g. a phase margin of 62° where the spec-correct binding gives 48° — both physically reasonable, illustrative numbers), so **simulation success + numeric plausibility ≠ semantic correctness**. Correctness depends on **role-conditioned evidence binding** (which corner/load/metric is *authoritative*), not on deck syntax. The grader (`grade_spice_handoff.py`) reports **six separated dimensions**: simulation success, numeric validity, semantic binding, evidence provenance, artifact completion, protocol completion.

Tool feasibility is **established** (not a risk): HSPICE, Spectre, and PrimeTime are all forwarded to b04 through `/data1/tongsb/eda-remote-shim/` (`synopsys/hspice/V-2023.12`, `cadence/SPECTRE21.10.582/V21`, `synopsys/prime/V-2023.12`); open-source simulators (ngspice/Xyce) are intentionally unsupported and are not used.

## 4. Three harness conditions (the experimental variable)

Identical hidden truth and grader across conditions within a family; the conditions differ **only in visible disclosure content**. Budgets (actions, tokens, tool access, timeout, feedback) are **matched** across conditions; the public feedback runner (`run_public.sh`) is byte-identical across conditions and gives **no semantic hint** (only "green signoff" / "measured number") — this is exactly the tool-success-≠-semantic property.

1. **Base** — ambiguous natural-language handoff; authority artifacts use **overloaded field labels** (Family A: a single `timing_tag` conflating intent/partition/view; Family B: a single `condition_id` conflating corner/load/metric). No glossary, no schema, no value-domain definitions, no procedural contract. The role mapping must be **inferred** from the evidence intersection.
2. **BundleS** — the established non-answer-bearing abstract components, **mapped mechanically** to the new family (no task-specific wording optimization, no C6 answer assertion, no golden values): (a) **canonical labels + disjoint-axis declaration** (≈C1), (b) **value-domain definitions** for each axis (≈C2), (c) **glossary + references** (≈C4), (d) **procedural contract** wording (≈C7). Delivered as natural-language/structured-prose files.
3. **TypedContract** — the **same information content** as BundleS (same labels, value-domains, glossary, contract) delivered as a **machine-readable typed schema** (JSON Schema declaring roles, axes, source-IDs, provenance precedence, types). **No golden values.** **No post-submission oracle/verifier feedback** (true of all three conditions; the agent submits once). Matched action/token/tool/timeout/feedback budgets to Base and BundleS.

BundleS and TypedContract are therefore **information-equivalent** and differ only in *representation* (NL prose vs. machine-readable schema). This isolates "machine-readable typed contract" as a variable from "non-answer disclosure content."

### 4a. TypedContract information-equivalence audit *(amendment 5)*

For **every** BundleS/TypedContract pair, a **machine-readable information inventory** (`info_equiv_audit.json`) enumerates every semantic fact — role names, value domains, source identifiers, authority relations, provenance structure, legal types — and asserts each fact is **present in both or absent from both**. Golden values, answer-bearing assertions, and post-submission verifier feedback must be **absent from both**. Token count and surface format need **not** match; however **every semantic addition or omission between the pair must be disclosed** in the inventory. The audit is a generation-time hard gate (fail-closed regenerate). This makes "information-equivalent" a checked property, not an assertion.

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
| Primary families | Family A (`p15_sta_handoff`, PT) **and** Family B (`p16_spice_handoff`, HSPICE) |
| Evaluation instances | **3 per family**, with distinct hidden truths, value vocabularies, and decoy structures |
| Dev/debug instance | **1 per family**, pilot-only, **never enters primary analysis** (excluded by predeclared id) |
| Conditions in core experiment | **Base** and **BundleS** |
| Repetitions | **2 stochastic** per task–model–condition (temperature 0.7, distinct provider seeds) — within-task stochastic replication is preserved in **both** budget variants |
| Core model scope (budget-conditional) | **Binding core = Qwen3.7-Max only** under the committed-ledger balance (~¥318 remaining ⇒ core-24). The **full-budget variant** adds DeepSeek-V4-Pro (core-48), selected **only if** ≥¥650–700 usable is confirmed at review. Both schedules are pre-frozen; the review selects. The two-model/one-repetition fallback is **not** used. |
| **Core primary episodes (binding)** | **24** = Qwen-only: 2 families × 3 instances × 1 model × 2 conditions × 2 reps |
| Core primary episodes (full-budget variant) | **48** = 2 families × 3 instances × 2 models × 2 conditions × 2 reps |
| DeepSeek extension | **24 episodes** = DeepSeek × 2 families × 3 instances × Base+BundleS × 2 reps; **separately frozen**, across **all** tasks (never selectively on favorable families); authorized later |
| Unit of external-validity analysis | **task instance** (n=3 per family); stochastic repetitions are **nested observations**, not independent instances |
| Counterbalancing | seeded exact-counterbalanced blocked randomization, frozen pre-run (position balance asserted) |
| k escalation | **none** (no adaptive k) |
| Task/wording changes after first result | **none** (frozen) |
| Secondary extension (TypedContract) | separately authorized; **not** part of the current core |

No task or wording change is permitted after the first model result. If a generator instance fails its semantic-diff / information-equivalence / hard-feasibility gate **before** the first paid result, it is regenerated/replaced at the **pre-run freeze** (still design-time); after the first paid result, the instance set is frozen.

### 6a. Freeze the treatment mapping before evaluation generation *(amendment 3)*

Before any primary evaluation instance is generated, the following are **frozen (committed + hash-pinned)**: (i) the **family-independent abstract definitions** of C1 (canonical labels + disjoint-axis declaration), C2 (value-domain definitions), C4 (glossary + references), C7 (procedural contract); (ii) the **deterministic STA mapping** (abstract components → Family-A roles/files); (iii) the **deterministic SPICE mapping** (abstract components → Family-B roles/files). The mapping is mechanical (no task-specific wording optimization) and identical-in-spirit across families. Evaluation instances are generated **only after** this mapping is frozen, so no instance content can retroactively reshape the treatment.

**Dev-instance constraint.** The excluded development instance may be used to expose **implementation, generator, grader, or tool-path defects** (and to validate the real-tool golden + wrong-binding feasibility). It **must not** be used to optimize condition wording based on model performance. (In Phase-5B there are no model calls, so the dev instance is used purely for implementation/tool-path validation.)

## 7. Predeclared outcomes

**Primary (confirmatory):** **semantic-binding correctness** — the submitted bound tuple equals the hidden golden tuple (binary per episode).

**Co-primary diagnostic:** **failure subtype**. Two generic framings — `axis/role_binding_failure` (a value placed on the wrong typed role) vs `role_conditioned_value_selection_failure` (right roles, wrong values) — plus **family-specific subtypes**:

- **Family A:** `authority_unattested_binding` (no authority edge supports it), `coverage_cell_mismatch` (the (partition,view) cell is not the flagged `requires_exception` cell), `check_view_inversion` (setup⇄hold inverted), `scope_object_misbind` (right intent, wrong partition).
- **Family B:** `corner_authority_misbind`, `load_authority_misbind`, `metric_role_misbind` (right metric family, wrong metric), `analysis_implied_mismatch` (analysis type inconsistent with the metric, caught even when the number is plausible).

**Secondary (descriptive):** artifact/tool correctness (Family A: signoff component; Family B: 6-dimension sub-scores), numeric/signoff correctness (number in spec range / slack MET), evidence/provenance correctness (cited authority source == golden authority), protocol completion (voluntary FINISH), terminal transport validity, recovered transport degradation, actions/tokens/wall-time/cost.

## 8. Predeclared analysis plan (instance is the unit; descriptive, not population)

1. **Principal contrast (primary):** **instance-level paired Base vs BundleS** outcomes, within instance, within model. Reported as a per-instance paired direction and a per-instance 2×2 (condition × correct) table of raw counts. The **task instance is the primary experimental unit**; stochastic repetitions are **nested observations** and are **not** counted as independent task instances.
2. **Family-specific effects:** Family A vs Family B, reported separately as **raw counts** (the two families are not pooled for the primary).
3. **Model-specific effects:** the binding core is Qwen-only; DeepSeek is reported only in the separately-frozen extension (all tasks). Model effects are never pooled across the core/extension boundary.
4. **Interactions (descriptive):** model×harness and family×harness, given n=3 instances/family (directional only; explicitly labeled exploratory/descriptive).
5. **Uncertainty:** exact binomial intervals per cell. A **non-parametric bootstrap over the 3 instances** (instance = resampling unit; repetitions are nested, not independent) is reported as **descriptive only — not as a headline, and no bootstrap p-value is reported as a headline**. **No precise population-level success rate is claimed** (n=3 instances/family supports directional, not population, inference).
6. **Significance testing:** **no pooled trajectory-level (episode-level) significance test and no bootstrap p-value is used as a headline.** A blocked exact sign test / McNemar over **instance-level** paired outcomes (n=3/family; underpowered by design) may be reported as descriptive, **never as the primary result**. Episode pooling is predeclared out (it would inflate n and ignore nesting).
7. **Diagnostic enrichment:** failure-subtype bar per (family, model, condition), mapped to the family-specific subtypes above.
8. **Reliability layers:** the seven independent dimensions (semantic binding, artifact/tool, numeric/signoff, evidence/provenance, protocol completion, terminal transport validity, recovered degradation) + tool-health sentinel + source-tree integrity, reported separately, never collapsed.

The primary result is **instance-level paired outcomes + family-specific raw counts**, and is **descriptive**: "for each instance, does BundleS change the semantic-binding direction relative to Base, for each model, in each family." Replication of the p14 BundleS effect would be: a consistent Base→BundleS improvement direction across the 3 instances of a family, for a given model. A clean null would be: no consistent direction. Either outcome is informative about external validity. **No precise population-level success rate is claimed.**

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

1. **Budget (binding, per committed ledger):** the committed ledger is the binding source (Phase-4Z ¥682.25 of ¥1000 ⇒ ≈¥318 remaining). Under that balance the **binding core is Qwen-only, 24 episodes** (≈¥282, fits). The **full 48-episode** variant (≈¥563) is pre-frozen and selected **only if** ≥¥650–700 usable is confirmed at review. The two-model/one-repetition fallback is **not** used. DeepSeek-24 is a separately-frozen, all-tasks extension. The next review selects Qwen-24 vs full-48 by the actual balance.
2. **Independence (operational):** the checker **operationally verifies structural independence under the five preregistered criteria** (it does not *prove* independence); the family×tool confound (§2a) is recorded.
3. **Hard feasibility gate *(amendment 4)*:** every primary instance contains **at least one semantic misbinding** that (a) is **accepted by the tool syntax**, (b) **executes successfully**, (c) **produces a plausible signoff or numeric output**, (d) **remains semantically incorrect**, and (e) is **rejected by the typed provenance/authority grader** — evidenced by a baked real-tool artifact on b04. If the wrong binding is trivially tool-red, unparsable, NaN, or otherwise obvious, the instance is **ineligible**.
4. **Disclosure gates:** semantic-diff audit (§5, no golden disclosure under any condition) **and** information-equivalence audit (§4a, every BundleS/TypedContract semantic fact present-in-both-or-neither) pass.
5. **Fairness gates healthy:** PT sentinel (A) and HSPICE sentinel (B) + full-path checks healthy on b04 at the pre-run freeze.
6. **Clean canonical tree** at the freeze commit; `cig.verify` passes; treatment mapping (§6a) frozen before any eval instance generation.

## 11. Commit sequence

**Phase-5A (done; docs-only):** the four design docs + `reports/synthetic_phase5a_design.json`, the information-disclosure security fix, and this amendment pass.

**Phase-5B (authorized, NO paid model calls; real EDA-tool runs for golden/wrong-binding baking are required):**
1. `docs(phase5a): apply conditional-acceptance amendments (1–5)` (this pass) — wording, experimental-unit posture, treatment-freeze ordering, hard feasibility gate, information-equivalence, budget logic.
2. `feat(phase5b): freeze treatment mapping` — abstract C1/C2/C4/C7 + deterministic STA + SPICE mappings, hash-pinned **before** eval generation.
3. `feat(phase5b): Family A generator + grader + evaluator + dev instance` (baked on real PT).
4. `feat(phase5b): Family B generator + grader + evaluator + dev instance` (baked on real HSPICE).
5. `feat(phase5b): fairness gates` — PT re-point (A) + `hspice_health_sentinel` + SPICE fullpath (B).
6. `feat(phase5b): independence checker + semantic-diff + information-equivalence audit tooling` (+ tests).
7. `feat(phase5b): 3 eval instances/family` (baked; hard-feasibility + disclosure gates per instance).
8. `feat(phase5b): integrity manifests (cig.freeze) + analysis code + frozen schedules` (Qwen-24 core **and** full-48 variant **and** DeepSeek-24 extension, all pre-frozen; none executed).
9. `chore(phase5b): gate report` — every primary instance passes hard feasibility / disclosure / fairness / independence / reproducibility. **Stop for review.**

The review then selects Qwen-24 vs full-48 by the actual balance and authorizes the (separately-scoped) paid execution. TypedContract remains a separately-authorized secondary. **No push** at any step.
