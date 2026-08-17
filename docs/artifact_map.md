**English | [中文](artifact_map.zh.md)**

# Artifact map — every paper claim to the files that produce it

This document exists so a reader arriving from the paper can locate the evidence for any claim
without guessing. Section and table numbers refer to `submission/main.tex` (manuscript v14, the
frozen ICLR 2027 submission; build it with `cd submission && make`).

Nothing in the paper is a transcribed number. The two derived-table scripts read the frozen
per-episode records and emit LaTeX that `main.tex` `\input`s, so a table cannot drift from its
records:

```bash
python3 scripts/phase7c_study1_ledger.py --check       # -> submission/tables/study1_ledger.tex
python3 scripts/phase7c_claim_statistics.py --check    # -> submission/tables/claim_stats.tex, sta_pilot.tex
```

`--check` recomputes and diffs against the committed output, exiting non-zero on drift.

## The three task families

The paper's object of study is a **semantic handoff**: bind a tuple to canonical typed roles from
role-misleading evidence, where a wrong binding still produces a green tool sign-off
(*tool-green*), so only a typed provenance/authority oracle rejects it.

| Paper name | Directory | Instances | Tool | Grader (the typed oracle) |
|---|---|---|---|---|
| workflow family (§3, Study I) | `tasks/p14_workflow_handoff/` | 27 | PrimeTime | `<instance>/hidden/grade_workflow.py` |
| Family A — STA (Study II, S2-F) | `tasks/p15_sta_handoff/` | 15 × 3 conditions + dev | PrimeTime | `generators/p15_sta_handoff/grade_sta_handoff.py` |
| Family B — SPICE (Study II, S2-F) | `tasks/p16_spice_handoff/` | 3 × 3 conditions + dev | HSPICE | `generators/p16_spice_handoff/grade_spice_handoff.py` |

Generators: `generators/p14_workflow_handoff_gen.py`, `p15_sta_handoff_gen.py`,
`p16_spice_handoff_gen.py`. Evaluators (the harness side):
`eda_agentbench/evaluator/{workflow,sta,spice}_handoff.py`.

The five structural independence criteria the operational-independence appendix asserts (independent templates,
vocabularies, truths, graders, decoys) are checked mechanically by
`scripts/phase5a_independence_check.py` → `reports/synthetic_phase5_independence_check.json`.
Family designs: `docs/synthetic_phase5a_family_specs.md`,
`docs/synthetic_workflow_generator_spec.md`.

## Main text

| Paper location | Claim | Where the evidence lives |
|---|---|---|
| §1, Fig. 1 | the five supports S0 / S1 / S2-M / S2-F / S3 | prose framework; the cells it names resolve through the rows below |
| §3.1, Table 1 | claim-qualification standard | prose only — a stated standard, not a measurement |
| §3, Table 6 (App. A) | the worked instance: 4 shipped evidence sources, each pairwise plausible, each PrimeTime-green | `tasks/p14_workflow_handoff/workflow_handoff_0009/files/report_A_role_swap.rpt`, `report_B_role_stale.rpt`, `report_C_role_pvt.rpt`, `evidence_D_role_mismatch.json` |
| §3 | 294 candidate assignments, exactly one satisfies K1–K5 | uniqueness enumeration in `generators/p14_workflow_handoff_gen.py`; hidden truth at `workflow_handoff_0009/hidden/handoff_truth.json`. **Naming:** the paper says **K1–K5** for the five *task constraints*; the frozen task files number the same five C1–C5, which collides with the *clarity components* C1–C7 — constraint K5 (sign-off pair) is what component C6 asserts. The stimuli keep their own numbering because rewording them would change the measurement |
| §3 | how the oracle adjudicates; the two never-collapsed failure subtypes | `workflow_handoff_0009/hidden/grade_workflow.py` |
| §3 | conditions Base / BundleS / TypedContract | the per-instance `files/` visible sets; component definition in `docs/synthetic_p14_phase4w_clarity_bundle_ablation_design.md` |
| §4 | Base 1/3 → BundleS 3/3 at S0; the same direction at S1 | `reports/synthetic_p14_phase4w_run1.*` (S0), `_heldout.*` (S1), `_run2.*` (repeat window) |
| §4 | ledger partition: 70 episodes → 41 correct, 24 axis-binding, 5 role-conditioned | `reports/synthetic_p14_study1_ledger.json` |
| §4 | no stable minimal component (C1, C2-only, C4-only, C24 bridge all failed) | `reports/synthetic_p14_phase4y_stage1.*`, `_phase4y2_stage2.*`, `_phase4y3_stage3.*`, `_phase4y3_c24_bridge.*` |
| §4 | three condition–model pairs disagree with themselves across run windows | the duplicate rows of Table 7; see `reports/README.md` on why they are not deduplicated |
| §5, Table 2 row 3 | S2-M: DeepSeek 3/4 = 3/4, not established | `reports/synthetic_p14_study1_ledger.json` (controlled-pair rows) |
| §5, Table 2 row 4 | S2-F STA: Base .208 / BundleS .333 / TypedContract .458 over 12 instances | `reports/synthetic_phase7a_sta72_report.json` |
| §5 | +12.5 pp, sensitivity band −12.5 to 41.7; sign test p=1.0; permutation p=0.31 | `scripts/phase7c_claim_statistics.py` → `reports/synthetic_p14_claim_statistics.json` |
| §5 | the 3-instance pilot reversed direction (−16.7 pp) | `reports/synthetic_phase5d_collection_report.json` |
| §5, Table 2 row 5 | S2-F SPICE: Base = BundleS = TypedContract = 1.00 ceiling | `reports/synthetic_phase5c_collection_report.json` |
| §3, App. G | the tool-success signal is **constant** (accept) over 169 pairing-verified trajectories, accepting all 82 semantically wrong bindings, so the typed oracle carries all measured discrimination; SPICE-5D is the negative control (18/18 correct, oracle and tool agreeing) | `scripts/phase7d_semantic_proxy_gap.py --check` → `reports/synthetic_phase7d_semantic_proxy_gap.json`; regression `tests/test_phase7d_semantic_proxy_gap.py` |
| §4, App. F | BundleS does not uniquely identify the golden assignment from its own disclosure: 9–147 of 294 candidates survive (the bracket spans the two readings), never 1, at S0 and at the pre-frozen held-out instance; the answer-bearing component C6 collapses the (scenario, corner) projection to 1. Closes direct answer disclosure only | `scripts/phase7e_answer_identifiability.py --check` → `reports/synthetic_phase7e_answer_identifiability.json`; regression `tests/test_phase7e_answer_identifiability.py` |
| §5, App. C | prospective panel anatomy (post hoc): 6 floor-limited, 1 ceiling-limited, 5 informative instances; leave-two-out (*n*=10) is −5.0 pp | `scripts/phase7c_claim_statistics.py --check` → `sta_finite_panel.panel_anatomy` in `reports/synthetic_p14_claim_statistics.json` |
| §6 | 9 of 58 workflow episodes excluded because the recorded tool verdict did not attest the final submitted artifact; tuple equality would have caught 2 of the 9 | same JSON — `per_episode[].pairing_verified` and `exclusion_reason` |
| §6, Table 3 | the seven audit incidents | one row each, below |
| §6 | model custody: episode span, snapshot retention, per-episode transport records | `scripts/phase7c_claim_statistics.py` (`resolved_snapshot_retained`, diag-episode counts) over `reports/evidence/` |
| §6 | Terminal-Bench 2.0→2.1: 1 direct / 21 partial / 4 outside; sampling 0 | `scripts/phase7c_tb21_audit.py`, `scripts/phase7a_terminalbench_audit.py`, `reports/synthetic_phase7c_terminalbench_audit.md`, `reports/evidence/phase7c_terminalbench/` (frozen rubric + PR-53 snapshots) |

### Table 3, row by row

Each row is a threat, the control that caught it, and the artifacts that show both.

| Threat (layer) | Control | Artifacts |
|---|---|---|
| Tool-success proxy (capability) | typed provenance/authority oracle, never tool exit status | `grade_workflow.py`, `grade_sta_handoff.py`, `grade_spice_handoff.py` |
| Non-streaming transport censoring (execution) | SSE streaming + terminal-transport arbiter | `eda_agentbench/llm/openai_provider.py`, `scripts/episode_arbiter.py`, `tests/test_llm_streaming.py`, `tests/test_llm_driver_{timeout,deadline}.py`; the incident arc is `reports/synthetic_p14_qwen_0009_fairness_anchor.*` (unresolved) → `_stream_anchor.*` (resolved) |
| Position confounding (sampling) | exact position-balanced blocking | `scripts/phase4w_randomize.py`, `scripts/phase5b_schedules.py`, `scripts/phase7a_sta72_schedule.py` |
| Recovered degradation (execution) | terminal-valid vs recovered split | `scripts/episode_arbiter.py`, `tests/test_transport_telemetry.py` |
| PrimeTime corrupted measurement (execution) | tool-health sentinel with run bookends | `scripts/pt_health_sentinel.py`, `scripts/hspice_health_sentinel.py`, `tests/test_pt_health_sentinel.py` |
| SPICE action-surface false positive (artifact) | immutable core + forensic audit | `scripts/phase5c_spice_forensic_audit.py`, `reports/synthetic_phase5c_spice_forensic_audit.json`, `tests/test_phase5_spice_repair.py`, `tests/test_phase5_hidden_isolation.py` |
| Canonical-source mutation (artifact) | exact-commit worktree + canonical hash guard | `scripts/canonical_integrity.py` (`FAILED_INTEGRITY` stop), `scripts/chain_executor.py`, `scripts/run_chain_guarded.py`, `tests/test_canonical_integrity.py`, and the tripwire `test_canonical_golden_fingerprint_intact` in `tests/test_fullpath_check.py` |

§6's "a monitor is only as trustworthy as the custody of its reference standard" is the last row
told in full: [`incident_golden_corruption.md`](incident_golden_corruption.md). The monitor was
correct and its mismatch was real; the attribution was wrong, because the reference artifact had
been rewritten by a component of the test harness rather than by the remote tool server.

## Appendices

| Appendix | Content | Where |
|---|---|---|
| A | worked instance evidence sources | `tasks/p14_workflow_handoff/workflow_handoff_0009/files/` |
| B | Study I per-instance ledger; per-cell exact intervals; the pooled figure set aside | `scripts/phase7c_study1_ledger.py` → `reports/synthetic_p14_study1_ledger.json` → `submission/tables/study1_ledger.tex` |
| C | prospective STA per-instance table; pilot table; frozen statistical procedure; post-hoc band; **panel anatomy** | `reports/synthetic_phase7a_sta72_report.json`, `reports/synthetic_phase5d_collection_report.json`, `submission/tables/sta_pilot.tex`, `sta_finite_panel.panel_anatomy` in `reports/synthetic_p14_claim_statistics.json` |
| D | what would change each conclusion — the seven falsification conditions, one per verdict | prose; the S0–S1 item now reports the Appendix F result instead of promising it |
| E | claim-qualification standard, full tier definitions | prose — a stated standard, not a measurement |
| F | **disclosure-only answer identifiability** of the treatment conditions | `scripts/phase7e_answer_identifiability.py --check` → `reports/synthetic_phase7e_answer_identifiability.json`; regression `tests/test_phase7e_answer_identifiability.py` |
| G | semantic/tool discrimination: exclusion accounting and pairing sensitivity | `scripts/phase7d_semantic_proxy_gap.py --check` → `reports/synthetic_phase7d_semantic_proxy_gap.json` |
| H | the full 26-task Terminal-Bench coding | `reports/synthetic_phase7c_terminalbench_audit.md`, `reports/evidence/phase7c_terminalbench/` |
| I | operational independence (the five structural criteria), freeze points, exploratory vs confirmatory, program accounting (58/24/36/72 episodes; ¥745.29) | `scripts/phase5a_independence_check.py`, `reports/synthetic_p14_phase4z_freeze_manifest.json`, `docs/phase7/phase7a_preregistration.md`, and the `prerun_freeze_manifest.json` / `membership_code_manifest.json` files under `reports/evidence/` |
| J | infrastructure and custody; the pre-flight grading-path bug caught before the prospective run | `docs/phase7/phase7a_preflight.md`, `docs/phase7/phase7a_sta_bug_audit.md`, `scripts/fullpath_check.py`, `scripts/spice_fullpath_check.py`, `scripts/measurement_control.py`, `scripts/fairness_retry.py` |
| K | positioning relative to prior work | `submission/references.bib` |
| Ethics | Study B (blinded human construct validity) preregistered but unexecuted | `docs/phase7/phase7b_annotation_freeze.md`, `scripts/phase7a_annotation_packets.py` |
| Reproducibility | frozen manifests, schedules, custody hashes, per-episode evidence | `reports/evidence/`, verified by `scripts/frozen_membership_verify.py` |

## How to read the Phase-7D result (cited by §3 and §6 of v13)

Phase-7D is a **retrospective, post-freeze** derived analysis: specified after the experimental
program closed, not preregistered, re-derived entirely from records committed at or before the
experiment freeze — no model call, no EDA tool run, no new episode. The manuscript labels it as such
wherever it appears, and so must any summary of it.

Two things must travel with that number, and both are recorded inside the JSON rather than left to
prose:

- **Scope.** These families are *constructed* so that a wrong binding stays tool-green. A
  false-accept rate of 1.0 therefore shows the construction working as specified and quantifies its
  cost to measurement; it is **not** an estimate of false-accept prevalence in agent benchmarks
  generally. The strata are reported separately and never pooled — they span stages, conditions,
  models and run windows and are not one sampling frame. What is non-trivial is behavioural, not
  definitional: real agents actually entered the tool-green-but-wrong region 82 times.
- **Δ is not a second finding.** Because the tool signal is constant,
  `Δ = S_tool − S_semantic ≡ 1 − S_semantic`. Δ is emitted for the appendix only.

33 of the 202 considered trajectories are **excluded rather than imputed**: 12 controlled-pair
episodes exist only as cell counts, 12 SPICE-5C episodes have no frozen tool component, and 9
workflow episodes fail verdict-to-artifact pairing. That last gate is substantive — a tool verdict
may only be compared with a semantic verdict when both describe the same final submission.
STA/SPICE satisfy this by construction (the hidden runner produces the tool verdict at grading time
from the submitted binding), but a workflow agent runs its evidence chain mid-episode and may edit
`flow_config.json` afterwards. `stage2_summary.json` records `input_hashes["flow_config.json"]`, so
pairing is decided by hash: 9 of 58 fail, and tuple equality would have caught only 2 of the 9 —
the other 7 agree on `(scenario, corner, netlist)` while consuming a different file. The frozen
grader flags these independently (`stage_chain == 0.0`).

## How to read the Phase-7E result (cited by §4 and Appendix F of v14)

Phase-7E is the same class of analysis as Phase-7D: **retrospective, post-freeze**, specified after
the experimental program closed, not preregistered, re-derived entirely from files committed at or
before the experiment freeze — no model call, no EDA tool run, no new episode.

It answers exactly one question: *reading only what a condition discloses, and never the task
evidence, is the golden assignment already pinned to a single candidate?*

- **What it closes.** Direct answer disclosure. BundleS leaves 9–147 of 294 candidates and never
  one, so the S0/S1 result cannot be explained by the treatment simply publishing the answer. The
  probe is shown to be capable of detecting disclosure: component **C6** is found in exactly the two
  instances the ablation design says carry it (`0010`, `0014`) and in none of the other twelve, and
  it collapses the (scenario, corner) projection to one under both readings. `main()` exits non-zero
  if that positive control ever stops firing, so the negative result cannot be reported from a
  probe that has gone blind.
- **What it does *not* close.** Softer information leakage, prior narrowing, prompt-induced
  heuristic cues, accidental lexical correlation, model-specific exploitation. Do **not** describe
  this as "no leakage" — the correct name is *direct-answer disclosure* or
  *answer-identifiability*.
- **It is not an equal-information comparison.** BundleS is *designed* to reduce semantic
  ambiguity; on the leakage-favourable reading it narrows the typed grid from 49 candidates to 9.
  That is a substantial informational advantage that stops short of publishing the answer, and both
  halves of that sentence must travel together.
- **Bounds, not mechanism.** The probe bounds a condition's informational advantage. It does not
  identify the behavioral mechanism, and the survivor ratio must not be restated as one — under the
  strict reading BundleS does not shrink the candidate set at all relative to Base.
- **Report the bracket, not a point.** 9 is the leakage-favourable bound and 147 the strict one.
  Quoting only 9 overstates how much the treatment narrows; quoting only 147 understates it.

The read discipline is executable rather than promised: the probe reads only `prompt.md`,
`spec.md`, `glossary.md` and `public_check_summary.json`, and the reports, `evidence_D`,
`prev_signoff`, `flow_config.json`, the handoff manifest, the netlists and everything under
`hidden/` raise `ForbiddenRead`. Nine tests assert those refusals fire. The candidate universe is
asserted byte-identical across all fourteen conditions, and the golden tuple loads through a
separate accessor called only after every survivor set is already fixed.

## What the paper does *not* claim, and where that shows in the tree

- **S3 (different model *and* different family) was never measured.** No report exists for it, by
  design. Its absence in `reports/` is the claim. It stays unmeasured deliberately: adding the cell
  after seeing the S2-F outcomes would make the evidentiary ladder outcome-adaptive, which is the
  practice the paper's own standard exists to prevent. Cost is not the reason — the 72-episode STA
  panel cost ¥43.56 of ¥745.29.
- **Softer information leakage is not excluded.** Phase-7E closes *direct answer disclosure* only
  (BundleS leaves 9–147 of 294 candidates, never 1). Prior narrowing, prompt-induced heuristic cues,
  accidental lexical correlation and model-specific exploitation remain open, and the Base/BundleS
  contrast is deliberately **not** an equal-information comparison.
- **No production-harness transfer.** "Harness" in the paper means the *task-level information
  structure* (§2) — prompt, visible files, disclosure bundle, public tool feedback, action surface —
  not the agent scaffold. Every episode ran through `scripts/llm_agent_driver.py` and
  `eda_agentbench/agentic/`; no production coding agent was tested. §7 states this, so the 82-of-169
  occupancy rate is scoped to that runner. What is *not* scaffold-dependent is the discrimination
  result itself: that a tool-success field cannot separate correct from incorrect role binding is a
  property of the task and its oracle, which is why it is stated as a benchmark/evaluator finding.
- **No human construct validation.** `docs/phase7/phase7b_annotation_freeze.md` is a
  preregistration; there are no annotation results, because no qualified independent annotators
  were available and no LLM was substituted.
- **Model identity is a provider alias, not a resolved snapshot.** `phase7c_claim_statistics.py`
  reports `resolved_snapshot_retained: false`. The paper states this as a limitation it incurred
  (a fifth Layer-4 requirement), not a control it exercised.
- **Two generators drifted after their freeze.** `scripts/frozen_membership_verify.py` reports
  exactly 2 mismatches and 9 missing pinned files; all are pre-existing and explained in
  `docs/frozen_membership_baseline.json`. The reported numbers derive from the pinned versions.

## Reproducing without commercial tools

Everything derived — every table, interval, band and *p*-value — recomputes from the frozen
records with no EDA tool, no network and no model call:

```bash
scripts/check                                          # tests + structure + custody pins
python3 scripts/phase7c_study1_ledger.py --check
python3 scripts/phase7c_claim_statistics.py --check
python3 scripts/phase7d_semantic_proxy_gap.py --check   # 169 included / 82 tool-green wrong bindings
python3 scripts/phase7e_answer_identifiability.py --check  # 294 universe; BundleS 9–147, never 1
cd submission && make distclean && make                # 20 pp (main text 9), byte-reproducible
python3 scripts/submission_page_limit_check.py         # main text ends on p9 (ICLR limit 9)
```

Re-running the *episodes* is a different matter and is not possible from this repository: it needs
PrimeTime and HSPICE plus paid API access, and the experimental program is permanently closed at
the frozen experiment HEAD (see [`provenance.md`](provenance.md)).
