# Phase-4Y C24 bridge — in-window C24/0021 k=4 remeasurement (under the canonical-tree integrity guard)

**Date:** 2026-08-03 · **Branch:** synthetic-phase0a · **Status:** report-only, stopped for review (no push)
**Freeze commit:** `9d76645` (freeze-base ancestor `4aef6a6`) · **Guard:** `d8fb7bd` (+`4aef6a6` eval-overlay fix)

## Predeclared question & rule

Stage-3 found neither C2-only nor C4-only reproduced the C24 axis-stabilization pattern, supporting a *candidate* C2×C4 interaction — but the C24 reference (Stage-2) was collected in a **different run window**. This bridge re-measures C24 (0021) **in-window** to test whether the bundle pattern replicates across windows BEFORE any held-out-family-2 consumption. Predeclared (`reports/evidence/p14_phase4y3_c24_bridge/interpretation_table.json`):

- **C24 ≥ 3/4 correct with 0/4 axis_binding_failure → replicated** across run windows; held-out-family-2 Base vs C24 may be proposed at the next review.
- **C24 ≤ 2/4, OR any axis_binding_failure recurs → not established**; do NOT consume held-out-family-2.
- Artifact/protocol completion secondary to typed binding + failure subtype.

## Result → predeclared cell: **`not_established`**

C24 = **2/4 correct, with 1 axis_binding_failure** (and 1 value-selection failure). This satisfies the `not_established` cell on **both** triggers (≤2/4 correct AND an axis failure recurred). The bundle axis-stabilization pattern did not replicate at the ≥3/4 + 0-axis threshold in this run window. **Stable C24 interaction evidence is not established; held-out-family-2 is NOT consumed.**

This is a predeclared-rule mapping, not a post-hoc interpretation.

## Per-episode table (golden = slow/func/netlist_v2)

| slot | submitted (scenario/corner) | score | binding | termination | transport |
|---|---|---|---|---|---|
| b1 | **slow/func** | 1.0 | **correct** | task_wall_limit | ok |
| b2 | **slow/func** | 1.0 | **correct** | task_wall_limit | ok |
| b3 | func/slow (swapped) | 0.2 | axis_binding_failure | task_wall_limit | ok |
| b4 | typ/func (valid-axis, wrong pair) | 0.2 | value_selection_failure | action_cap | ok |

**C24 (k=4): 2 correct / 1 axis_binding_failure / 1 role_conditioned_value_selection_failure.** Transport 4/4 terminal_transport_valid, 0/4 recovered, 0/4 overconfident_wrong. All 4 anti-cheat clean. The canonical-tree integrity guard held: **0 incidents** (no mutation pre-run / per-episode / post-chain; the worktree's canonical 0021 was never altered).

## Cross-window comparison

| C24 (0021) | window | correct (k=4) | axis_binding_failure | value_selection_failure |
|---|---|---|---|---|
| Stage-2 (cross-run reference) | 2026-07-28 | 3/4 | **0** | 1 |
| **Stage-3 bridge (in-window)** | 2026-08-02 | **2/4** | **1** | 1 |

The bundle's axis suppression did not replicate (0/4 → 1/4 axis) and correctness dropped 3/4 → 2/4. Note this is **within k=4 run-to-run variance** for a thinking model at temperature 0.7 (a one-episode swing); the predeclared threshold (≥3/4 + 0 axis) was simply not met in this window. The result does **not** refute a bundle effect — it shows the C24 reference is itself **not stable at ≥3/4 + 0 axis across windows at k=4**, so the directional cross-stage evidence from Stage-3 (singleton C2 1/4, C4 0/4 vs bundle) is **not strengthened** by in-window replication: the in-window gap between the bundle (2/4) and the singletons (C2 1/4, C4 0/4) is smaller than the cross-run comparison suggested and is within k=4 noise.

## Method & provenance

- **Canonical-tree integrity guard** (new, commits `d8fb7bd`/`4aef6a6`/`a1ce79e`): the run executed inside an **exact-commit isolated git worktree** (`git worktree add --detach` at `9d76645`); canonical task directories were made non-writable (`enforce`); SHA-256 hashes of task 0021 + run-time membership/control code + generators + evidence manifests were verified **pre-run, after every episode, and post-chain** (HEAD ancestor-or-equal check + content hashes). Zero incidents → canonical held throughout. A first guarded run hit an integration bug (eval-workspace overlay `PermissionError` → 0.00); it was stopped, the `_ensure_writable` ordering was fixed (`4aef6a6`, regression-tested), the freeze re-run, and the run repeated cleanly. The recurring external mutation of the **0009** golden (6× during this work) never touched the run — 0009 is outside the bridge scope and the run is isolated in its own worktree.
- **Variants frozen:** 0021 only (C24 = 0009 + C2 + C4), not regenerated. Single condition, k=4, no counterbalancing (4 slots, same task).
- **Run:** 4 Qwen3.7-Max streaming episodes, temp 0.7, 60 actions, 1800s, elicit-confidence — identical config to Stage-3. All ACCEPT on attempt 1; 0 replacements; 0 invalid attempts; executor exit 0; ~2h wall; cost ≈ **¥54.23** (3.63M in / 0.30M out tokens at 12/36 per M).
- **Evidence:** sanitized per-trial bundles + custody byte-match (4/4) + MANIFEST/SHA256SUMS under `reports/evidence/p14_phase4y3_c24_bridge_episodes/`; rows + summary under `reports/evidence/p14_phase4y3_c24_bridge/`.

## Scoped conclusion

Within Qwen3.7-Max and this p14 workflow-handoff family: the C24 bundle pattern did **not** replicate at the predeclared ≥3/4 + 0-axis threshold in-window (2/4 correct, 1 axis failure). Per the predeclared rule, **stable C24 interaction evidence is not established and held-out-family-2 is not consumed.** This tempers — does not refute — the Stage-3 candidate C2×C4 interaction: the difference between in-window C24 (2/4) and Stage-3 singletons (C2 1/4, C4 0/4) is within k=4 run-to-run variance, so no component or bundle effect is discriminable at this k.

## Exclusions respected

Single condition (C24/0021) only — no C2, C4, C1, baseline, DeepSeek, held-out (either family), k-escalation, or non-streaming fallback. No push.

## Stop rule

Exactly 4 authorized episodes collected under the integrity guard; report-only commit; stopped for review. Do not push.

## For review (not performed)

- Whether to raise k (e.g., k=8–10) on C24 and on the singletons to escape k=4 variance before any further bundle-vs-singleton comparison or held-out consumption.
- The C24 in-window result (2/4) suggests the bundle reference itself is noisy at k=4; a higher-k C24 re-baseline may be the prerequisite for any further decomposition work.
