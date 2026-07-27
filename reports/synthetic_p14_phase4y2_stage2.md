# p14 Phase-4Y Stage 2 — C1/Axis-schema (0020) vs C24/Value-schema (0021), k=4 each, Qwen — COMPLETE

**Status: COMPLETE.** Report-only commit. Code: pre-run gate `05bb7cd` (semantic-diff + disclosure +
sentinel-guarded fairness ALL_PASS). Model: Qwen3.7-Max, SSE streaming. Cost **¥95.21** (C1 ¥45.55 +
C24 ¥49.66). FROZEN exact-counterbalanced 4 two-run blocks (seed `phase4y2_seed=20260724`):
`C1,C24 / C1,C24 / C24,C1 / C24,C1` (each condition exactly 2× at each position). Run via chain_executor
(stdin-isolated, arbiter-driven, durable run-state: 8/8 ACCEPT, 0 excluded, exit 0). No Contract/C7, no
full BundleS, no held-out, no DeepSeek, no C6, no k-escalation, no non-streaming.

**Headline (the decisive result is the co-primary failure-subtype diagnostic).** Isolating C1 from C24:
- **C1** (canonical labels + disjoint-axis declaration): 2/4 typed-binding, **2 axis_binding_failure, 0
  value-selection failures.**
- **C24** (C2 PVT-def + C4 glossary): 3/4 typed-binding, **0 axis-binding failures, 1
  role_conditioned_value_selection_failure.**

**This REFUTES the predeclared "C1 specifically eliminates axis_binding_failure" cell (cell 5): C1 did
NOT eliminate axis errors — it produced both of its failures as axis-binding errors.** The opposite
pattern holds: **C24 (the value-schema), not C1 (the axis labels), is associated with axis-error
suppression.** This confirms the Stage-1 caveat ("do not attribute axis-error suppression to C1
specifically") and localizes the axis-suppression mechanism to the value-schema (C2+C4: PVT definition
+ glossary). On the primary typed-binding count, **C24 (3/4) directionally exceeds C1 (2/4), but
neither condition is at a stable 4/4 endpoint (k=4)** — closest to the "report recurrence" cell for the
raw count, with the decisive signal being the subtype split.

## 1. Per-episode outcomes (frozen order)
| slot | cond@pos | tv | recov | term | FINISH | score | submitted | binding subtype | conf | act | rtok | ¥ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| b1p0 | C1@0 | ✓ | 0 | finish | yes | 1.0 | slow/func | correct | high | — | — | 14.14 |
| b1p1 | C24@1 | ✓ | 0 | action_cap | no | 1.0 | slow/func | correct | — | — | — | 14.38 |
| b2p0 | C1@0 | ✓ | 0 | action_cap | no | 0.2 | **func/slow** | **axis_binding_failure** | — | — | — | 13.98 |
| b2p1 | C24@1 | ✓ | 0 | task_wall | no | 1.0 | slow/func | correct | — | — | — | 9.35 |
| b3p0 | C24@0 | ✓ | 0 | finish | yes | 1.0 | slow/func | correct | high | — | — | 12.28 |
| b3p1 | C1@1 | ✓ | 0 | finish | yes | 1.0 | slow/func | correct | high | — | — | 12.86 |
| b4p0 | C24@0 | ✓ | 0 | action_cap | no | 0.2 | **typ/func** | **role_conditioned_value_selection_failure** | — | — | — | 13.65 |
| b4p1 | C1@1 | ✓ | 1 | hard_kill | no | 0.1 | **func/typ** | **axis_binding_failure*** | — | — | — | 4.57 |

All 8: anti-cheat clean, terminal_transport_valid=True. `*` b4p1 (C1) scored 0.1 (not 0.2) because it
hit the task wall during evidence regeneration (incomplete artifacts) after committing the wrong
func/typ axis binding; it also had 1 recovered (terminally-valid) transport failure. Its
typed-binding is still wrong (axis_binding_failure). (Action/reasoning-token columns omitted for
brevity; full data in the JSON + preserved evidence.)

## 2. Condition × position (typed-binding / artifact / FINISH) + failure subtypes
| cell | typed-binding | artifact | FINISH | axis_fails | value_fails |
|---|---|---|---|---|---|
| C1@pos0 | 1/2 | 1/2 | 1/2 | 1 | 0 |
| C1@pos1 | 1/2 | 1/2 | 1/2 | 1 | 0 |
| C24@pos0 | 1/2 | 1/2 | 1/2 | 0 | 1 |
| C24@pos1 | 2/2 | 2/2 | 0/2 | 0 | 0 |
| **C1 margin** | **2/4** | 2/4 | 2/4 | **2** | **0** |
| **C24 margin** | **3/4** | 3/4 | 1/4 | **0** | **1** |

## 3. Predeclared interpretation (walked)
- *c1_stable_c24_weak*: not observed (C1 2/4 is the weaker).
- *c1_weak_c24_stable*: **directionally supported** — C24 (3/4) is the stronger route, but not a clean
  4/4 stable endpoint; "confirm C24 on held-out" would be the next step if pursued at higher k.
- *both_stable*: not observed (neither 4/4).
- *both_weak*: partially — neither subset alone reaches the BundleS level (Stage-1 Schema 2/3, BundleS
  3/3), consistent with neither C1 nor C24 being individually cleanly sufficient.
- ***c1_eliminates_axis_only → REFUTED***: C1 produced 2 axis-binding failures (0 value errors); the
  axis-suppression pattern belongs to C24 (0 axis, 1 value).
- *substantial_instability*: applied to the raw typed-binding count (neither stable), with the
  decisive subtype signal reported separately.

**Applied verdict:** the co-primary failure-subtype diagnostic is decisive — **C1 does not eliminate
axis errors; C24 does** (refutes cell 5, confirms the Stage-1 C1-attribution caveat). On typed-binding,
C24 (3/4) directionally exceeds C1 (2/4), neither stable at k=4.

## 4. Separated conclusions
**(a) Transport — clean; two-dimension reporting.** 8/8 terminal-transport-valid; 1 episode (C1_b4p1)
had recovered degradation (1 recovered failure, terminally valid → accepted, no replacement); 0 chat
retries. (b04 was confirmed healthy by the sentinel before the run.)

**(b) Capability — value-schema (C24) is the stronger subset and the axis-suppressor.** C24 (C2+C4)
3/4 vs C1 (canonical labels + disjoint-axes) 2/4. Combined with Stage-1 (Schema C1+C2+C4 = 2/3;
BundleS C1+C2+C4+C7 = 3/3): the value-schema (C2+C4) carries the operative correctness mechanism;
C1 alone is insufficient and does not suppress axis errors.

**(c) Failure-subtype localization (decisive).** C1: 2 axis_binding_failure (func/slow, func/typ), 0
value. C24: 0 axis, 1 role_conditioned_value_selection_failure (typ/func). The explicit axis labels
(C1) do NOT prevent axis-binding errors; the value-schema (PVT definition + glossary) does. This is
the clean negative result on the C1-eliminates-axis hypothesis.

**(d) Reliability (descriptive).** FINISH C1 2/4, C24 1/4 — several correct episodes did not
protocol-complete (action_cap/task_wall) yet still bound correctly. All 3 FINISH episodes were
high-confidence and correct (no overconfident-wrong in this batch).

## 5. Sample-size + scope
k=4 per condition; one development pair; one model; exact-counterbalanced (2×2 balanced, n=2/cell).
The supported statements are the directional C24 advantage + the decisive failure-subtype split
(C1 axis-prone, C24 axis-free), not effect estimates. Within Qwen3.7-Max (model-contingent
candidate). Position (pos0 2/4 vs pos1 3/4) is mild and not interpreted at this n.

## 6. Artifacts + SHA-256
Evidence root: `reports/evidence/p14_phase4y2_episodes/` — 8 trials × 8 sanitized files + MANIFEST.json
+ SHA256SUMS; chain-of-custody byte-match verified for all 8. Pre-run gate (semantic-diff + disclosure
+ sentinel-guarded fairness + freeze + membership manifest) at `reports/evidence/p14_phase4y2/`
(commit `05bb7cd`).

---
*Compliance: Qwen3.7-Max streaming only; workflow_handoff_0020 + 0021 only; exact-counterbalanced
frozen order; arbiter-driven (chain_executor, stdin-isolated, durable run-state); sentinel-guarded
fairness (infra-only retry); no Contract/C7/full-BundleS/held-out/DeepSeek/C6/k-escalation/non-streaming;
`.env` removed; sanitized evidence + hashes; `scripts/check` PASSED. Real PrimeTime grading (shim).
Not pushed.*
