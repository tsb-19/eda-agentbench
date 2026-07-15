# reports/ — evidence index

This directory holds the benchmark's measurement artifacts and the synthetic-research probe
reports. **Top level = load-bearing evidence** (mechanism findings, failure modes, reliability
data, and the code-generated benchmark artifacts). **`archive/` = probes whose outcome was
"everything passed / saturated"** — kept for the record, digested by a synthesis, no longer
load-bearing. `evidence/` holds sanitized per-episode artifacts (submitted files, grader
breakdowns, stream diagnostics, hashes) for the probe reports that cite them.

Nothing in `archive/` was edited — files are moved verbatim; every entry is indexed below with
its verdict.

## What the research line demonstrates (paper-facing map)

**C1 — Multi-artifact EDA workflow benchmark with typed-binding oracles on real commercial
tools.** Agents must bind conflicting evidence to semantic roles (netlist/clock/scenario/corner)
and regenerate a real PrimeTime evidence chain; a typed-binding oracle makes *signoff-green but
semantically wrong* machine-detectable (the 0.20 signature: `signoff=1.0`,
`evidence_generation=0`). 294→1 uniqueness gates; anti-cheat (oracle isolation, tcl-injection,
hash, hidden-shadow checks).
→ `synthetic_p14_v5_0006_constraint_graph_probe.*`, task family under
`tasks/p14_workflow_handoff/`, designs in `docs/synthetic_*.md`.

**C2 — Clarity-bundle controlled-pair methodology.** `workflow_handoff_0009` (ambiguous) vs
`0010` (clear control): byte-identical hidden truth, grader, flow, mutant, decoys — differing ONLY
in the visible clarity bundle. Accepted primary conclusion (k=3 per cell, Phase-4V2): *the full
clarity bundle suppresses the scenario/corner wrong-axis binding failure for both models — DeepSeek
0/3→3/3, Qwen 1/3→3/3 — a replicated cross-model effect on this constructed pair, not yet a general
population success-rate estimate.* This establishes the effect of the complete bundle; it does not
isolate the causal component or generalize beyond 0009/0010 (Phase-4W ablation subject). Qwen × 0010
reached 3/3 artifact/typed-binding correctness but only 1/3 protocol-complete FINISH — role clarity
suppressed the binding error, not termination inefficiency.
→ `synthetic_p14_balanced_controlled_pair.*` (Phase-4V2, the balanced 2×2 × k=3 result),
`synthetic_p14_qwen_0009_stream_anchor.*` (Phase-4V1), `synthetic_p14_semantic_role_controlled_pair_probe.*`
(Phase-4U), evidence in `evidence/p14_qwen_0009_stream_anchor/` and `evidence/p14_qwen_0010_stream_anchor/`.

**C3 — Reliability/calibration layer over agentic capability.** pass@k / pass^k, run-to-run
variance at temperature>0, confidence elicitation, `overconfident_wrong`,
protocol-vs-capability failure classification. Instantiated concretely: a HIGH-confidence
wrong-axis submission (Qwen × 0009 trial1) and a byte-confirmed confident-wrong DeepSeek
episode on 0006/0005.
→ `reliability_phase2.*`, `reliability_phase2_repaired.*`,
`synthetic_p14_v5_0006_deepseek_k5_preserved.*`, `synthetic_p14_v4_0005_deepseek_calibrated.*`.

**C4 — Measurement-validity discipline.** Fairness anchors; infrastructure-invalid vs
capability classification; discovery that a NON-STREAMING transport censors long-reasoning
(thinking) models via the socket-inactivity timeout — and its resolution by dependency-free SSE
streaming (code `e1c36d2`), which reclassified the Phase-4V Qwen episodes as transport-invalid.
Process-isolated hard request deadlines bound slow-drip stalls.
→ `synthetic_p14_qwen_0009_fairness_anchor.*` (the unresolved→resolved arc),
`synthetic_p14_qwen_0009_stream_anchor.*`, `tests/test_llm_streaming.py`,
`tests/test_llm_driver_deadline.py`.

**C5 — Saturation discovery as a design method.** Systematic cheap probes showed frontier
models saturate single-fault localization and lookup-style tasks; each negative result
redirected design toward ambiguity/conflict mechanisms (don't publish the binding vocabulary —
make inference the task). The archived probes below are that chain's raw record; the syntheses
live in `docs/synthetic_p14_*_synthesis.md` and `docs/synthetic_negative_results_summary.md`.

## Top-level reports (kept — load-bearing)

| Report | Why it is load-bearing |
|---|---|
| `synthetic_p14_v5_0006_constraint_graph_probe` | Origin of the semantic-role binding mechanism: first real capability-difficulty signal (DeepSeek 2/3 + byte-confirmed confident-wrong; Qwen 3/3) |
| `synthetic_p14_v5_0006_deepseek_k5_preserved` | Reproducibility of the 0006 signal at k=5 (4/5, one byte-confirmed wrong-global-assignment) |
| `synthetic_p14_semantic_role_controlled_pair_probe` | Phase-4U controlled pair: DeepSeek 0009 0/3 vs 0010 3/3 — the clarity bundle produces the difference |
| `synthetic_p14_qwen_0009_fairness_anchor` | Phase-4V: the fairness anchor UNRESOLVED — measurement-invalid via non-streaming long-reasoning transport censoring (the C4 discovery) |
| `synthetic_p14_qwen_0009_stream_anchor` | Phase-4V1 (streaming, k=3): Qwen × 0009 anchor over the fixed transport — wrong-axis failure reproduces (2/3) |
| `synthetic_p14_balanced_controlled_pair` | Phase-4V2 balanced 2×2 × k=3: the full clarity bundle suppresses the wrong-axis failure for both models (DeepSeek 0/3→3/3, Qwen 1/3→3/3); effect of the complete bundle on this pair, not component-isolated |
| `synthetic_p14_v4_0005_deepseek_calibrated` / `_deepseek_k5_preserved` / `_deepseek_preserved_followup` | v4 0005 reliability chain: mixed solve + confident-wrong episodes (calibration evidence); digested in `docs/synthetic_p14_v4_post_k5_synthesis.md` |
| `reliability_phase2` / `reliability_phase2_repaired` | Reliability layer result: non-passes are dominantly protocol, trust discriminates models |
| `prompt_diversification_real_pilot` / `prompt_diversification_review_packet` | Prompt-diversification evidence (referenced by `tests/test_prompt_diversification.py` — do not move) |
| `baseline_summary`, `benchmark_summary`, `*.csv`, `task_inventory.*` | Generated benchmark artifacts — written at these fixed paths by `scripts/export_benchmark_summary.py` / `scripts/run_baseline_suite.py` (do not move) |

## archive/ (verbatim moves — outcome was saturation / merely-positive / superseded)

| Archived report | Verdict (from the report itself) |
|---|---|
| `synthetic_p11_tiny_probe` | early FlowHandoff smoke — saturated |
| `synthetic_p12_smoke_probe` | multi-artifact handoff smoke — saturated |
| `synthetic_p13_smoke_probe` | trajectory/evidence-generation smoke — saturated |
| `synthetic_p14_tiny_probe` | p14 v1 tiny probe — saturated |
| `synthetic_p14_v2_0003_probe` | stopped early at k=1 cost cap; completed episodes solved |
| `synthetic_p14_v3_0004_capability_probe` | k=3 valid, both models saturated |
| `synthetic_p14_v4_0005_capability_probe` | stopped at k=1 cost cap; superseded by the k5 chain |
| `synthetic_p14_v5_0006_qwen_k5_preserved` | Qwen robustly saturates 0006 (5/5, zero wrong) |
| `synthetic_p14_v6_0007_axis_binding_probe` | 0007 saturated at k=3 for both models (published axis schema → lookup) |
| `synthetic_p14_v7_0008_implicit_axis_binding_probe` | 0008 did not restore difficulty (6/6 correct) |
| `synthetic_phase0d_probe` | phase-0D constraint-drift family probe — superseded by the p14 line |

**Archive policy:** move whole files, never edit content; a report is archivable only when its
outcome is merely-positive/saturated AND a kept synthesis (in `docs/` or a kept report) carries
its lesson; anything with failure-mode, calibration, or mechanism signal stays at top level.
