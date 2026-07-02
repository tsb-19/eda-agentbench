# p14 v4 0005 — DeepSeek k=5 preserved reliability probe

**Status: COMPLETE (k=5, all valid). Not committed (awaiting review).** HEAD `326961b`.

Preserved reliability quantification of DeepSeek-V4-Pro on `workflow_handoff_0005` — the first p14
positive-signal task — now that Phase-4I preservation + Phase-4J affirmative markers are in place.

## Headline

**DeepSeek solved 5/5 (pass^5 = 1.0).** The earlier k=2 broken-provenance non-solve **did not recur**
across 5 preserved trials. Per the interpretation rule, this reclassifies 0005 from "unreliable
frontier-edge" to **efficiency / protocol stress, NOT a difficulty wall** — for DeepSeek. The only
signal that survives at k=5 is **protocol-cleanliness**: 4/5 trials solved the workspace but ran out of
action-budget/time before emitting a clean FINISH+confidence (2 hit the 1800s wall). Cost ¥49.74 / ¥60.

## 1. Valid-trial count
**5 / 5** (all clean capability attempts; no infra exclusions).

## 2. Capability metrics
- **pass@1 = 1.0**, **pass@k = 1.0**, **pass^k (all-5) = 1.0**. All trials `total_score = 1.0` with
  every gated component at 1.0.

## 3–5. Outcome / confidence / protocol counts

| metric | value |
|---|---|
| solved | 5 |
| non-solved | 0 |
| timeout (1800s wall) | 2 (trials 2, 5) |
| budget_exhausted (protocol) | 4 (trials 2–5) |
| confident-wrong | 0 |
| abstain / protocol-incomplete | 4 |
| clean FINISH + confidence | 1 (trial 1) |
| **overconfident_wrong** | **0** |
| **protocol_clean rate** | **1/5** |

Capability is saturated (5/5 correct); protocol-cleanliness is the residual discriminator.

## 6–9. Per-trial detail

| trial | score | passed | protocol | conf | FINISH | timed_out | tool calls | PT-like runs | wall (s) | cost ¥ | class |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1.0 | ✓ | ok | high | yes | no | 49 | 32 | 982 | 8.91 | **CLEAN SOLVE** |
| 2 | 1.0 | ✓ | budget_exhausted | — | no | yes | 57 | 37 | 1800 | 10.83 | solved, protocol-incomplete (1800s wall) |
| 3 | 1.0 | ✓ | budget_exhausted | — | no | no | 50 | 30 | 1391 | 12.16 | solved, protocol-incomplete (60-action cap) |
| 4 | 1.0 | ✓ | budget_exhausted | — | no | no | 47 | 36 | 1771 | 8.52 | solved, protocol-incomplete |
| 5 | 1.0 | ✓ | budget_exhausted | — | no | yes | 48 | 34 | 1800 | 9.32 | solved, protocol-incomplete (1800s wall) |

All 5 produced a **golden global-authority package with a byte-consistent evidence chain** (all gated
components 1.0). Trials 2–5 reached that correct final state but did not spend a remaining action on the
FINISH/confidence step within budget.

## 10. Byte-confirmed failure classification
**N/A — there were no non-passes.** No decoy-following (report_A/report_B/evidence_C), no broken atomic
stage1→stage2 provenance, no final-state-only, no stage1-only, no hand-edited evidence, no forbidden
edit, no timeout-as-failure (the 2 timeouts still scored 1.0 on final state), no infra failure.

## 9 (detail). Preserved-artifact status (all 5 trials)

| check | trials 1–5 |
|---|---|
| `preserved_artifacts.json` present | ✓ |
| editable files preserved (5) | ✓ |
| sha256 hashes recorded | ✓ |
| `component_scores` present (authoritative) | ✓ (all 1.0) |
| `affirmative_grader_markers` present | ✓ (all fired affirmatively) |
| `secrets_excluded: true` | ✓ |
| hidden truth / forbidden / secrets excluded | ✓ |

**Phase-4J confirmed in the wild:** on every trial `component_scores` (all 1.0) and
`affirmative_grader_markers` agree — no presence-only false positives. Security scan found no forbidden
filename and no `HIDDEN_TRUTH`/`API_KEY`/`BASE_URL`/`Bearer` string in any preserved tree. Captured
copies live under `runs/p14_v4_0005_deepseek_k5_preserved/trial{1..5}/preserved_capture/` (gitignored).

## 11. Comparison to the previous calibrated follow-up

| | prior k=2 | now k=5 |
|---|---|---|
| solves | 1 | 5 |
| non-solves | 1 (byte-confirmed **broken atomic stage1→stage2 provenance**) | 0 |
| pass^k | 0.50 | **1.0** |
| confident-wrong | 0 | 0 |

The broken-chain non-solve **did not recur** in 5 preserved trials → consistent with the prior single
non-solve being **run-to-run variance / a protocol slip**, not a stable failure mode for DeepSeek.

## 12. Final interpretation

**EFFICIENCY / PROTOCOL STRESS, NOT A DIFFICULTY WALL** (for DeepSeek).

- Interpretation rule applied: *"If DeepSeek solves all valid trials → efficiency stress but not
  difficulty."* DeepSeek solved **5/5 (pass^5 = 1.0)**. 0005 is not a hard wall and not
  capability-unreliable for DeepSeek at k=5.
- The residual, real signal is **protocol/efficiency**: 4/5 solved but did not finish cleanly within the
  60-action / 1800s budget (2 hit the wall). Correctness is saturated; the surviving discriminator is
  protocol-cleanliness, not correctness.
- Not a provenance-discipline *capability* failure (it did not recur); not decoy-following; not
  infra-invalid; no oracle failure.

## Caveats

1. **Single model.** DeepSeek's saturation does not imply other models saturate — a weaker model could
   still fail 0005 on correctness. This probe measures DeepSeek reliability only.
2. **Protocol-incompleteness is a budget interaction**, not a capability failure: final-state grading
   scored 1.0 for all. The confidence/overconfidence axis is under-measured on this task at these
   budgets (only 1/5 emitted a usable confidence).
3. **n=5**: pass^5=1.0 is a strong reliability signal but still bounds rather than eliminates a rare
   failure tail (cf. the k=2 broken-chain slip).
4. This run also **confirms Phase-4I/4J are working** (byte-confirmable artifacts, non-misleading
   markers), so future confident-wrong / wrong-package claims on other models can be trusted.

## Next direction

- **Do NOT run more DeepSeek `workflow_handoff_0005` trials.** Capability is saturated for DeepSeek
  (pass^5 = 1.0); additional trials add cost without new capability signal.
- Choose one of:
  1. **Design a harder `workflow_handoff_0006`** with a stronger dependency/constraint-graph structure
     (deeper multi-stage coupling, more interacting constraints) to re-open a genuine capability gap; or
  2. **Adopt `workflow_handoff_0005` as an efficiency / protocol-stress benchmark** — track wall time,
     tool calls, PT runs, protocol_clean rate, and no-FINISH/budget_exhausted rate rather than
     correctness (which is saturated for DeepSeek).

## Process compliance

DeepSeek-V4-Pro only (no Qwen/MiniMax/Kimi/GLM). `.env` symlink provisioned as runtime config and
**removed after**. No secrets printed; no shell tracing. **Not committed, not pushed.** Other worktrees
untouched. `runs/` and `configs/baseline_models.json` gitignored and not staged.
