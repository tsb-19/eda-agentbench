# Phase-4Y Stage-3 — C2-only (0022) vs C4-only (0023), Qwen3.7-Max, k=4

**Date:** 2026-07-31 · **Branch:** synthetic-phase0a · **Status:** report-only, stopped for review (no push)
**Pre-run gate commit:** 3f058e1 · **Measurement-control infra:** f6a716e, 95aa33c (committed separately)

## Predeclared question

Stage-2 localized the strongest axis-stabilization signal to the **C2+C4 value-schema bundle (C24)**, not C1 (Stage-2 refuted C1-alone). Stage-3 decomposes C24 into its two components and asks: **does the axis-stabilization signal reduce to C2-alone (PVT-def) or C4-alone (glossary+refs), or does it require the bundle jointly?**

Predeclared interpretation cells (frozen before any paid result, `reports/evidence/p14_phase4y3/interpretation_table.json`): `c2_stable_c4_weak`, `c2_weak_c4_stable`, `both_stable`, **`both_weak`** (*axis stabilization requires the C2+C4 bundle jointly; do not attribute the Stage-2 C24 signal to C2 or C4 individually*), `c2_eliminates_axis_only`, `c4_eliminates_axis_only`, `substantial_instability`.

## Result → predeclared cell: **`both_weak`** (candidate interaction, not formally identified)

Neither C2-only nor C4-only reproduced the C24 axis-stabilization pattern. C2 produced 1/4 correct bindings with three axis-binding failures; C4 produced 0/4 with three axis-binding failures and one role-conditioned value-selection failure. Together with the prior C24 result of 3/4 and zero axis-binding failures, this supports a candidate C2×C4 interaction or joint-sufficiency effect. Because C24 and the singleton conditions were collected in separate stages, the result remains directional cross-stage evidence rather than a formally identified super-additive interaction.

This maps to the predeclared `both_weak` cell and is a predeclared-cell mapping, not a post-hoc interpretation. It does **not** claim that a super-additive interaction has been definitively established, nor that the mechanism is conclusively irreducible to either component.

## Per-condition table (primary: typed-binding; co-primary: failure subtype)

| condition | task | k | correct | axis_binding_failure | role_conditioned_value_selection_failure |
|---|---|---|---|---|---|
| **C2-only** (PVT-def) | 0022 | 4 | **1** | **3** | 0 |
| **C4-only** (glossary+refs) | 0023 | 4 | **0** | **3** | 1 |

Submitted bindings (golden = slow/func/netlist_v2; SCEN={slow,typ,fast}, CORNER={func,test,lowpower}):

| slot | cond | submitted (scenario/corner) | score | binding | termination | transport | confidence |
|---|---|---|---|---|---|---|---|
| b1:p0 | C4 | func/slow (swapped) | 0.2 | axis_binding_failure | finish_action | ok | high (overconfident) |
| b1:p1 | C2 | func/typ (swapped) | 0.2 | axis_binding_failure | action_cap | recovered | abstained |
| b2:p0 | C2 | **slow/func** | 1.0 | **correct** | task_wall_limit | ok | abstained |
| b2:p1 | C4 | func/typ (swapped) | 0.2 | axis_binding_failure | finish_action | recovered | high (overconfident) |
| b3:p0 | C4 | func/typ (swapped) | 0.2 | axis_binding_failure | task_wall_limit | recovered | abstained |
| b3:p1 | C2 | func/slow (swapped) | 0.2 | axis_binding_failure | action_cap | ok | abstained |
| b4:p0 | C2 | func/typ (swapped) | 0.2 | axis_binding_failure | task_wall_limit | ok | abstained |
| b4:p1 | C4 | typ/func (valid-axis, wrong pair) | 0.2 | value_selection_failure | action_cap | ok | abstained |

The dominant failure mode is the axis swap (scenario/corner reversed, e.g. `func/slow`): 6/8 submissions put a corner value in the scenario slot and vice versa. One C4 submission (`typ/func`) used valid-axis values in the wrong pair (value-selection failure). The single correct submission (C2) is the only slow/func binding.

## Cross-stage comparison (Stage-2 C24 → Stage-3 components)

| variant | components | correct (k=4) | axis_binding_failure | value_selection_failure |
|---|---|---|---|---|
| C24 (0021, Stage-2) | C2+C4 | 3/4 | **0** | 1 |
| C2-only (0022, Stage-3) | C2 | 1/4 | **3** | 0 |
| C4-only (0023, Stage-3) | C4 | 0/4 | **3** | 1 |

The bundle (C24) suppressed axis errors (0/4); each singleton component admitted 3/4 axis errors. This is consistent with a **candidate C2×C4 interaction or joint-sufficiency effect**, but because the C24 and singleton conditions were collected in separate stages the comparison is cross-run and directional (k=4, run-to-run variance), **not a formally identified super-additive interaction**. (Same base 0009, identical frozen C2/C4 wording, same model/transport/episode params.)

## Transport (2-dimension)

All 8 episodes **terminal_transport_valid** (8/8) — no censoring. Recovered transport degradation: C2 1/4, C4 2/4 (3/8 total); all recovered, none terminal-invalid. SSE streaming, inactivity 120s, hard deadline 300s, max 1 retry.

## Reliability (secondary)

Asymmetry between conditions: **C2** 4/4 abstained (no confidence commitment), 0/4 overconfident; **C4** 2/4 abstained, **2/4 overconfident_wrong** (both C4 confidence commitments were "high" and wrong). Abstention is high overall (6/8); when the model does commit confidence, it is overconfident and wrong (2/2). This is a calibration signal, secondary to the primary typed-binding result.

## Termination (6-dim)

finish_action 2/8 (both C4, both overconfident_wrong); action_cap (60 actions) 3/8; task_wall_limit (1800s) 3/8. The single correct episode (C2 b2:p0) terminated via task_wall_limit — i.e., the correct binding was reached but the agent did not voluntarily finish. All 8 anti-cheat clean (no forbidden-file edits, no hash mismatches, no TCL injection, no hidden shadows).

## Method & provenance

- **Fairness gate (block measurement-control):** reran under score-independent block control (full-path L2 → candidate subset → full-path L2 per task) on 2026-07-30. All three blocks (0009, 0022, 0023) admissible; exact score ladder (golden 1.0 / wrong_axis 0.2 / stale_decoy 0.1 / unchanged_mutant 0.1); no hard fairness fails. The prior 0022 flake (0.2/0.1) was fully explained by an external transient corruption of the frozen golden file (not the variant, not b04 — b04 was healthy throughout; the L2 frozen-hash invariant detected it). Recorded in memory (`l2-unhealthy-golden-corruption`).
- **Variants frozen:** 0022 (C2-only), 0023 (C4-only) — not regenerated or edited. Clause-level, frozen-wording, semantic-diff gated (gen_phase4y3.py).
- **Randomization:** seed 20260730; 4 exactly-counterbalanced 2-run blocks (each condition 2× per position). Frozen order: b1:C4,C2 · b2:C2,C4 · b3:C4,C2 · b4:C2,C4.
- **Run:** 8 Qwen3.7-Max streaming episodes, temp 0.7, max 60 actions, 1800s timeout, elicit-confidence. All ACCEPT on attempt 1 (no replacements); 0 invalid attempts; executor exit 0; ~3h53m wall. Cost ≈ **¥101.67** (6.85M in / 0.54M out tokens at 12/36 per M).
- **Evidence:** sanitized per-trial bundles + custody byte-match (8/8) + MANIFEST/SHA256SUMS under `reports/evidence/p14_phase4y3_episodes/`; per-episode rows + summary under `reports/evidence/p14_phase4y3/`.

## Scoped conclusion

Within Qwen3.7-Max and this p14 workflow-handoff family: neither C2-only nor C4-only reproduced the C24 axis-stabilization pattern (C2 1/4, C4 0/4 correct; 3/4 axis-binding failures each), while the prior C24 bundle result was 3/4 correct with zero axis-binding failures. This supports a **candidate C2×C4 interaction or joint-sufficiency effect**. Because C24 and the singleton conditions were collected in separate stages, the result remains **directional cross-stage evidence rather than a formally identified super-additive interaction**; it is not claimed that a super-additive interaction is definitively established or that the mechanism is conclusively irreducible to either component. A recurrence caveat applies: axis errors dominate (6/8 submissions), so single-component presentation remains instability-prone at this k. An in-window C24 (0021) k=4 bridge remeasurement is the natural next step to test whether the bundle pattern replicates across run windows before any held-out consumption.

## Exclusions respected

No held-out (either family), no DeepSeek, no C1/C3/C5/C6/C7, no k-escalation, no non-streaming, no push.

## Stop rule

Exactly 8 authorized episodes collected; report-only commit; stopped for review. Do not push.

## For review (not performed)

- One-shot confirmation of the bundle mechanism against held-out family-2 (fast/lowpower; frozen, no model calls yet) — the natural next confirmation of `both_weak`.
- Whether to re-measure C24 (0021) in this same run window to tighten the cross-stage comparison (currently cross-run).
- Reliability-layer follow-up on the C2-abstains / C4-overconfident asymmetry.
