# Phase-7A Preregistration — Submission-Strengthening Extension

**Status:** PROSPECTIVE and SEPARATELY LABELED. The Phase-6 scientific freeze is **immutable**; no existing task, outcome, or claim is modified or reinterpreted in light of future results. **No paid model calls in Phase-7A.** No C1/C2/C4/C7/C24 mechanism search is authorized. Phase-7A only preregisters three strengthening studies; execution (paid episodes, human annotation, Terminal-Bench retrieval) is gated on review.

## Objective

Address the three remaining reviewer-level weaknesses without touching Phase-6 claims:
1. **Small task-instance count** → Study A (prospective STA confirmatory expansion to 12 instances).
2. **Construct-design circularity of semantic-binding labels** → Study B (independent *blinded human* annotation of committed trajectories).
3. **Audit protocol validated only inside our own benchmark family** → Study C (external application to Terminal-Bench 2.1).

## Shared invariants (all studies)

- Frozen Family-A semantic design and graders are reused **unchanged**.
- No modification to Base / BundleS / TypedContract / semantic-binding definitions / grader semantics / model config / action-token-tool budgets.
- The prior 3 STA eval instances (`p15_eval_0001..0003`) are **historical pilot** evidence; the new 12-instance batch is the prospective confirmatory dataset, analyzed independently before any combined descriptive summary.
- Phase-6 manuscript claims are **not** modified in Phase-7A. Any Phase-7 result that would bear on a Phase-6 claim is reported as a separate, prospective data point.

---

# Deliverable 1 — Study A: Prospective STA confirmatory expansion

## Design

Generate **12 NEW** STA primary instances (`p15_eval_0004..0015`) from the frozen generator (`generators/p15_sta_handoff_gen.py`) with frozen conditions. Diversity is **structural**, selected within the frozen typed space (intent × partition × check-mode × conflict-axis × decoy-recipe), not lexical relabeling. The frozen 12-spec table (`scripts/phase7a_sta12_specs.py`, emitted to `reports/evidence/phase7a_sta12_specs.json`) is fixed **before** generation and **before** any new model result.

**Stratum coverage (validated):** golden intent — all 4 (×3 each); golden partition — all 4 (`cdc/reset/scan/core`, ×3 each); golden check-mode — both legal views (`setup`, `both`; ×6 each); conflict axis — `partition` / `intent` / `intent+view`; decoy recipe — 5 distinct (`scope_drift, mis_scope, stale_intent, intent_swap, wrong_domain`); 12 distinct structural signatures (truth/authority/decoy/wrong-green).

## Hard gates (every instance must pass; unchanged Phase-5B criteria)

Deterministic fail-closed generation; real-PT golden execution; ≥1 tool-green semantic misbinding; nonzero timing paths; provenance rejection (not PT failure); disclosure audit over complete agent-visible tool output; ≥2 publicly plausible typed candidates (output-channel); hidden-evidence isolation; semantic-diff (no golden disclosure); information-equivalence (BundleS ≡ TypedContract facts, both omit golden); integrity/custody sha256 hashes.

## Generation + gate (Phase-7A, no model calls)

`scripts/phase7a_generate_sta12.py` builds 3 condition trees per instance, bakes golden+wrong on real PrimeTime (b04 shim), runs the 5-criterion `hard_feasibility` gate + the full audit suite, and emits `reports/synthetic_phase7a_sta12_construction.{json,md}`. **72 model episodes are NOT executed in Phase-7A.**

## Pre-registered execution (gated on review of the construction report)

- Model: Qwen3.7-Max.
- Conditions: Base, BundleS, TypedContract.
- 12 instances × 3 conditions × 2 stochastic reps = **exactly 72 primary episodes**.
- Task instance is the **principal unit**; repetitions nested.
- Exact position-balanced blocked randomization (every condition appears once in slots 0–2 and once in slots 3–5 of each 6-slot block), seeded, frozen at `reports/evidence/phase7a_sta72_schedule.json` (`scripts/phase7a_sta72_schedule.py`).
- **No adaptive k. No wording changes. No trajectory-pooled p-value.**

## Pre-registered analysis

- **Instance-level paired** contrasts (BundleS vs Base; TypedContract vs Base; TypedContract vs BundleS), reported as per-instance directions + raw counts.
- **Exact/randomization-based sensitivity** over the 12 instances (permutation of condition labels within instance) as a clearly-labeled descriptive sensitivity — *not* a population-rate claim; instance is the n, never trajectory count.
- Descriptive trajectory-stability (2-rep within-instance agreement), as in Phase-6C.
- The pilot 3-instance STA result is reported separately; a combined descriptive summary appears only after the prospective analysis is reported on its own.

---

# Deliverable 2 — Study B: Independent blinded semantic-binding validation

Construct-validity audit of the automated grader against **independent human** annotators on **already committed** trajectories. **No new model outputs.**

## Sampling (committed trajectories; ~72 episodes)

Stratified across workflow(P14) / STA / SPICE; Qwen + DeepSeek (where available); outcomes correct / axis_binding_failure / role_conditioned_value_selection / family-specific provenance-authority failures; Base / BundleS / TypedContract. Generator: `scripts/phase7a_annotation_packets.py` → `reports/evidence/phase7b_annotation/` (72 packets produced; labels **not** collected in Phase-7A).

## Blinding (each packet exposes ONLY)

Canonical authority chain + decoy + typed role/domain schema + the final submitted configuration. **Stripped:** model identity, Harness condition, automated-grader verdict, score, task identifiers exposing condition, report filenames exposing labels, and boilerplate `_comment` fields that would prime the annotator. Authority is rendered **canonically** (condition-blinded); the decoy prior signoff (attesting the wrong binding) is retained so judging is a real reasoning task, not equality with an answer key. Leak scan verified (0 model/condition/task-id/priming strings in any packet).

## Frozen rubric (frozen before labels collected)

For each packet the annotator answers independently:
1. Is the submitted semantic binding **correct**?
2. Is the evidence/provenance **sufficient** for that binding?
3. If incorrect, which **predeclared failure subtype** applies (axis_binding_failure / role_conditioned_value_selection / family-specific provenance-authority failure)?
4. Is the case **ambiguous** under the rubric?

## Annotators

≥2, preferably **3 independent human** annotators. The model used in the experiments is **not** a primary annotator. **Stop condition:** if human annotation cannot be obtained, this study STOPS — it is never silently replaced with an LLM-only validation claimed as independent construct validation.

## Pre-registered metrics

Raw inter-annotator agreement; **majority-label vs automated-grader agreement**; subtype confusion matrix; predeclared disagreement-adjudication rules. **No label is removed merely because it disagrees with the automated grader.** The key mapping packet→truth is held separately (`key.json`, adjudication only).

---

# Deliverable 3 — Study C: External application of the Audit Protocol (Terminal-Bench 2.1)

External validation of the four-layer protocol on an **independently developed public benchmark**. This is an audit of our protocol, **not** a claim that it caused/predicted Terminal-Bench's fixes.

## Zero-model-call retrospective audit (first; no trajectories)

1. **Freeze** the rubric from the four layers + an explicit `Other / not covered` bucket — frozen **before** inspecting any modification (`scripts/phase7a_terminalbench_audit.py` → `reports/evidence/phase7c_terminalbench/frozen_rubric.json`).
2. Retrieve Terminal-Bench 2.0→2.1 modifications for the 26 changed tasks (bugs / timeout-resource / reward-hacking robustness). *(Retrieval web-gated in Phase-7A — rate-limited to 2026-08-14; rubric + coding template are frozen and waiting.)*
3. Code each modification on the frozen rubric **without forcing** it into our taxonomy; per task record: nature of repair, affected layer (L1/L2/L3/L4/Other), whether our protocol would detect/prevent it, whether ABC/protocol-validity prior work already covers it, whether it lies outside our protocol.

## Optional runtime study (separately gated; NOT a BundleS test)

Purpose: test whether the **generic sampling/execution/integrity layers** instantiate on an unrelated public agent benchmark without changing task semantics.
- Harbor official Terminal-Bench 2.1 harness; 2 **excluded** development tasks for adapter validation; **8 preregistered evaluation tasks** selected by a rule fixed before trajectories are observed; Qwen3.7-Max; 2 reps = **16 primary episodes**.
- **Gates before any paid episode:** oracle runs successfully; adapter frozen; expected cost measured on excluded dev tasks; external static audit complete; **separate review authorizes the 16 episodes.**

---

# Deliverable 4 — Frozen statistical / analysis plan

- **Study A:** instance is the principal unit (n=12); reps nested; paired condition contrasts per instance + exact/randomization sensitivity over instances; descriptive trajectory-stability; pilot (n=3) reported separately before any combined summary. No trajectory-pooled p-value; no small-n bootstrap significance; no population-rate headline.
- **Study B:** annotator agreement (raw + majority-vs-grader) + subtype confusion matrix; adjudication by predeclared rule; no label dropped for disagreeing with the grader. Construct validity = the level of majority-human vs automated-grader agreement, reported honestly whatever it is.
- **Study C:** descriptive tally of modifications per layer; honest count of `Other / not covered`; no causal claim about our protocol vs Terminal-Bench fixes.

# Deliverable 5 — Cost / time estimate

| Item | Cost (CNY) | Notes |
|---|---|---|
| Study A: 72 episodes (Qwen) | ~¥10–14 | ~¥0.15–0.20/ep from Phase-5C/5D actuals; budget ceiling ¥20 |
| Study A: 12-instance generation + bake | ¥0 (no model) | real PT on b04; ~10–15 min wall |
| Study B: annotation packets | ¥0 (no model) | generation done; human annotator time is external |
| Study C: static audit | ¥0 (no model) | retrieval deferred (web) |
| Study C: 16-episode runtime (optional) | ~¥3 | only after 5 gates + separate review |
| **Total Phase-7 model spend if all executed** | **~¥13–17** | within the committed-ledger remainder |

# Deliverable 6 — Risk register

| Risk | Mitigation |
|---|---|
| 12-instance bake fails a hard gate | specs pre-validated; per-instance gate reported; failing instance is reported, not silently dropped |
| Phase-7 result reframes a Phase-6 claim | Phase-7 results reported as separate prospective data; Phase-6 claims untouched in Phase-7A |
| Human annotators unavailable (Study B) | **stop the study**; never substitute LLM-only validation |
| Terminal-Bench retrieval blocked | static rubric frozen; retrieval deferred to web-available; runtime separately gated |
| Budget overrun | hard ceilings per study; validity-only replacement; no adaptive k |
| Construct circularity remains | Study B is the pre-registered test; result reported whatever it is |
| b04 PT outage during bake | Phase-5C/5D sentinel + fullpath bookends reused; bake is resumable per instance |

# Deliverable 7 — Exact sequence of pre-run commits (Phase-7A; no push)

1. `feat(phase7a): Study A frozen 12-instance spec + generation + 72-ep schedule` — `scripts/phase7a_sta12_specs.py`, `scripts/phase7a_generate_sta12.py`, `scripts/phase7a_sta72_schedule.py`, emitted manifests.
2. `feat(phase7a): Study B blinded human-annotation protocol + packet generator` — `scripts/phase7a_annotation_packets.py`, packets + key + sampling report + frozen rubric.
3. `feat(phase7a): Study C Terminal-Bench external-audit protocol + frozen rubric` — `scripts/phase7a_terminalbench_audit.py`, rubric + template.
4. `docs(phase7a): master preregistration + analysis plan + cost/time + risk register` — this document.
5. `feat(phase7a): Study A 12-instance construction + gate report` (real-PT bake, no model calls) — `reports/synthetic_phase7a_sta12_construction.{json,md}` + `tasks/p15_sta_handoff/p15_eval_0004..0015_*`.

**No push. No paid model calls. Stop for review.**
