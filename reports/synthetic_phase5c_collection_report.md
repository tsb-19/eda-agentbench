# Phase-5C Collection Report — Qwen-only 24-episode core

**Status: complete 24/24.** Branch `synthetic-phase0a`. Model: Qwen3.7-Max (SSE streaming). No push. Machine-readable companion: `reports/synthetic_phase5c_collection_report.json`; durable run-state: `reports/evidence/phase5c_state.json`; episode evidence + SHA-256 custody: `reports/evidence/phase5c_episodes/<trial>/`.

## 1. Collection status
- **24/24 primary episodes collected; 0 invalid, 0 excluded, 0 replaced, 0 aborted.** All measurement-valid (terminal_transport_valid ∧ workspace_gradeable); no terminal-measurement-invalid replacements were needed.
- **Total cost: ¥7.7225** (remaining ledger ≈ **¥310.03** of ~¥317.75). Far under the ¥315 ceiling — actual per-episode cost was ~¥0.32 (Phase-5 episodes are far shorter than the Phase-4 ¥12.04/ep projection that sized the budget). No `incomplete_collection_budget_stop`.
- Replacement rule honored: recovered transport degradation = 0 everywhere; no episode was replaced for a wrong answer, low score, missing FINISH, long trajectory, or cost.

## 2. Instance-level analysis (PRIMARY = semantic-binding correctness, re-derived from the submitted config; instance is the unit; reps nested)

| Instance | Family | Base rate | BundleS rate | direction |
|---|---|---|---|---|
| p15_eval_0001 | A (STA) | 0.50 | 0.00 | decline |
| p15_eval_0002 | A (STA) | 1.00 | 1.00 | tie (ceiling) |
| p15_eval_0003 | A (STA) | 0.00 | 0.00 | tie (floor) |
| p16_eval_0001 | B (SPICE) | 1.00 | 1.00 | tie (ceiling) |
| p16_eval_0002 | B (SPICE) | 1.00 | 1.00 | tie (ceiling) |
| p16_eval_0003 | B (SPICE) | 1.00 | 1.00 | tie (ceiling) |

Family summaries (raw counts, descriptive — not a population rate; no pooled-trajectory headline test):
- **A (STA):** Base mean 0.50, BundleS mean 0.33, **0/3 instances improve**.
- **B (SPICE):** Base mean 1.00, BundleS mean 1.00, **0/3 improve (ceiling)**.

## 3. External-validity conclusion

**No cross-family support for generalization of the p14 BundleS effect.**

- **STA — null (clean data):** BundleS does **not** improve semantic binding for Qwen (0/3 improve; one instance declines, one is at ceiling, one at floor). The p14 BundleS effect does not transfer to the STA family. The dominant STA failure subtype is `coverage_cell_mismatch` (the agent binds a cell that is not a `requires_exception` cell) and occasional role-confusion (e.g. an exception type placed in the `check_mode` slot).
- **SPICE — ceiling on the primary outcome:** Qwen binds the SPICE tuple correctly in **all 12 episodes** (Base and BundleS). The SPICE Base instance is too easy for Qwen — the authority artifacts state the binding plainly enough that the Base (ambiguous) condition is already solved — so a BundleS benefit cannot be expressed (Base already 1.00). The effect is unmeasurable on this family at this difficulty.

Frozen-rule label: **ceiling** (driven by the SPICE Base mean ≥ 0.9). Cross-family composite: **no transfer** (STA null + SPICE ceiling).

## 4. Critical secondary finding — SPICE artifact scores are anti-cheat-contaminated (a task-design flaw)

All 12 SPICE episodes are **anti-cheat-zeroed** (`total_score = 0.0`, empty components): the agent **modified `circuit_built.sp`** (the deck), which is in the instance `forbidden` list — `anti_cheat.forbidden_files_modified = true`, `hash_mismatches = ["circuit_built.sp (modified)"]` in every SPICE episode. This is a **task-design / agent-convention conflict**: in the benchmark's existing SPICE tracks (P4/P5) the *deck* is the editable artifact, so the agent edits the deck by convention; in Family B the editable artifact is `meas_config.json` and the deck is forbidden, inverting that convention. The agent respects the `meas_config` binding (primary semantic_binding is correct) but also edits the forbidden deck, triggering the anti-cheat zero on the **secondary** artifact-correctness dimension.

Implications:
- The **primary** semantic_binding signal (SPICE ceiling) is **unaffected** — it is re-derived from `meas_config` and is independent of the anti-cheat channel.
- The SPICE **artifact/tool-correctness** (total_score) data is **not interpretable** (all 0.0 by anti-cheat, not by real grading). The STA artifact data is clean (0.4–1.0, no forbidden modifications).
- Per the directive ("complete the frozen schedule; do not change based on scientific outcomes"), the frozen run is reported as-is. The SPICE deck-editability design flaw is flagged for a possible generator fix + SPICE re-run under separate authorization (it is a task-design defect, not a scientific outcome to be silenced).

## 5. Per-episode data
All 24 episodes with family/instance/condition/rep+position, semantic-binding correctness, family-specific subtype, total_score, provenance/authority component, protocol completion + termination, terminal transport validity, recovered degradation, tokens, and cost are in the machine-readable companion. Headline per-episode facts: every episode `terminal_transport_valid = true`, `recovered_degradation = false`; STA `total_score ∈ {0.4, 0.5, 1.0}` (clean); SPICE `total_score = 0.0` (anti-cheat); semantic_binding as tabulated above.

## 6. Sanitized evidence + custody
Per-episode evidence under `reports/evidence/phase5c_episodes/<trial>/`: `<editable>.submitted.json`, `result.json`, `agentlog.sanitized.json`, `SHA256SUMS`. Durable run-state `reports/evidence/phase5c_state.json` (24 episodes, ¥7.7225). Integrity: prerun manifest `reports/evidence/phase5c_prerun_manifest.json` (anchored at the run commit); canonical tree unchanged (agent + grading ran on /tmp workspace copies; canonical `tasks/` never written). No model-call budget was consumed beyond the 24 frozen episodes.

## 7. What this means for the program
This is an honest external-validity **null**: the p14 BundleS effect — established (Qwen, model-contingent) on the p14 workflow-handoff family — does **not** generalize to the two structurally independent families here. STA shows no benefit; SPICE is at ceiling (Base already solved) and its secondary metric is anti-cheat-contaminated by a deck-editability design flaw. The Phase-4Z claim–evidence matrix is updated by **adding** a Phase-5 row (no existing p14 claim is altered retroactively).
