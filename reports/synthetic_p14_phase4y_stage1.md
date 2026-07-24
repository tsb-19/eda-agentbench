# p14 Phase-4Y Stage 1 — Schema (0018) vs Contract (0019), k=3 each, Qwen streaming — COMPLETE

**Status: COMPLETE.** Report-only commit. Code: pre-run freeze `50e2ded` (semantic-diff + disclosure +
fairness ALL_PASS). Model: Qwen3.7-Max, SSE streaming, frozen config. Cost **¥73.63** (Schema ¥33.78 +
Contract ¥39.85). FROZEN 3 blocked pairs (seed `phase4y_seed=20260723`): `Contract,Schema /
Contract,Schema / Schema,Contract` (position split Schema pos0=1/pos1=2, Contract pos0=2/pos1=1 —
inherent to 3 pairs). Run via the committed chain_executor (stdin-isolated, arbiter-driven,
durable run-state: 6/6 ACCEPT first attempt, 0 excluded, exit 0). No DeepSeek, no held-out, no C6,
no BundleD, no individual C1/C2/C4, no k=5, no non-streaming.

**Headline (accepted conclusion, review wording).** "Within Qwen3.7-Max, Schema (C1+C2+C4) shows a
directional advantage over Contract-only (C7) on the development task: typed-binding correctness is
2/3 versus 1/3. More importantly, the failure subtype shifts: both Contract failures are
`axis_binding_failure`, whereas Schema produces no axis-binding failures and its single failure is
`role_conditioned_value_selection_failure`. With k=3 and neither condition at a stable endpoint, this
is a **mechanism-localization signal rather than a clean component-effect verdict**."

**Two scope corrections (review):**
1. **Do NOT claim an additive C7 effect.** The prior BundleS 3/3 result is consistent with a possible
   Schema×C7 contribution, but these are small, separately collected samples — they do not identify an
   additive C7 increment (no "C7 adds the final 2/3→3/3" claim) or a Schema×C7 interaction.
2. **Do NOT attribute axis-error suppression to C1 specifically.** The Schema condition contains
   C1+C2+C4 jointly; the observed absence of axis-binding failures under Schema cannot be isolated to
   C1 from this condition. (Isolating C1 is exactly Phase-4Y Stage 2.)

## 1. Per-episode outcomes (frozen order)
| slot | cond@pos | tv | recov | term | FINISH | score | submitted | binding subtype | conf | act | rtok | ¥ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| b1p0 | Contract@0 | ✓ | 0 | finish | yes | 0.2 | **func/slow** | **axis_binding_failure** | high | 58 | 47811 | 14.27 |
| b1p1 | Schema@1 | ✓ | 0 | hard_kill | no | 0.2 | **typ/func** | **role_conditioned_value_selection_failure** | — | 47 | 79717 | 11.29 |
| b2p0 | Contract@0 | ✓ | 0 | finish | yes | 1.0 | slow/func | correct | high | 46 | 64187 | 11.26 |
| b2p1 | Schema@1 | ✓ | 0 | finish | yes | 1.0 | slow/func | correct | high | 46 | 75687 | 10.05 |
| b3p0 | Schema@0 | ✓ | 0 | finish | yes | 1.0 | slow/func | correct | high | 54 | 49911 | 12.44 |
| b3p1 | Contract@1 | ✓ | 0 | action_cap | no | 0.2 | **func/slow** | **axis_binding_failure** | — | 60 | 74056 | 14.32 |

All 6: anti-cheat clean, terminal_transport_valid=True, recovered_transport_degradation=False (clean
Qwen streaming, consistent with Phase-4W). Both transport dimensions reported independently; no
episode had recovered degradation.

## 2. Condition × position (typed-binding / artifact / FINISH)
| cell | typed-binding | artifact 1.0 | FINISH |
|---|---|---|---|
| Schema@pos0 | 1/1 | 1/1 | 1/1 |
| Schema@pos1 | 1/2 | 1/2 | 1/2 |
| Contract@pos0 | 1/2 | 1/2 | 2/2 |
| Contract@pos1 | 0/1 | 0/1 | 0/1 |
| **Schema margin** | **2/3** | 2/3 | 2/3 |
| **Contract margin** | **1/3** | 1/3 | 2/3 |

## 3. Predeclared interpretation (walked)
- *Schema succeeds, Contract fails → prioritize C1/C2/C4*: **directionally supported** (2/3 > 1/3) but
  weakened — Schema not clean 3/3, Contract not clean 0/3.
- *Schema fails, Contract succeeds*: not observed.
- *Both succeed*: not observed (neither 3/3).
- *Both fail*: not observed (Schema 2/3).
- *High instability → report recurrence*: partially — neither condition stable, but a consistent
  Schema-leaning direction exists. Reported as recurrence + directional signal.

**Applied verdict:** mechanism-localization signal (Schema-leaning direction + failure-subtype shift),
not a clean component-effect verdict. No additive C7 claim; no C1-specific attribution (Schema is
C1+C2+C4 jointly).

## 4. Separated conclusions
**(a) Transport — clean, two-dimension reporting.** 6/6 terminal-transport-valid; 0 recovered
degradation; 0 chat retries. (Qwen streaming is reliably clean on this family.)

**(b) Capability — mechanism-localization signal, not a component-effect verdict.** Schema (C1+C2+C4)
2/3 vs Contract (C7) 1/3: a directional Schema-leaning advantage. The prior BundleS 3/3 result is
consistent with a possible Schema×C7 contribution, but these small, separately collected samples do
not identify an additive C7 effect or a Schema×C7 interaction (no "C7 adds 2/3→3/3" claim). Within
Qwen3.7-Max (model-contingent candidate).

**(c) Failure-subtype shift (mechanistic hint; not attributed to C1).** Contract's failures: 2×
`axis_binding_failure` (func/slow) — the agent kept the cross-axis swap. Schema's failure: 1×
`role_conditioned_value_selection_failure` (typ/func) — type-valid values, wrong scenario value. The
Schema condition produced no axis-binding failures. This is a mechanism-localization signal, **not**
attributed to C1 specifically — the Schema condition contains C1+C2+C4 jointly, so the axis-error
absence cannot be isolated to C1 here (that is Phase-4Y Stage 2).

**(d) Reliability (descriptive).** FINISH 4/6 (Schema 2/3, Contract 2/3); all 4 FINISH episodes
elicited high confidence and were correct where binding was correct (1 overconfident-wrong:
Contract_b1p0 high-confidence on func/slow). Schema_b1p1 hit the task wall before FINISH on a wrong
binding; Contract_b3p1 hit the action cap on a wrong binding.

## 5. Sample-size + scope
k=3 per condition; one development pair; one model; 3 blocked pairs (position split 1/2 inherent to
the odd count). Point observations with wide uncertainty; the supported statements are the directional
Schema-leaning signal + the failure-subtype split, not effect estimates. Within Qwen3.7-Max
(model-contingent candidate). Position (pos0 2/3 vs pos1 1/3) is not interpreted at n=3.

## 6. Artifacts + SHA-256
Evidence root: `reports/evidence/p14_phase4y_episodes/` — 6 trials × 8 sanitized files + MANIFEST.json
+ SHA256SUMS; chain-of-custody byte-match verified for all 6. Pre-run gate (semantic-diff + disclosure
+ fairness + freeze hashes + membership manifest) at `reports/evidence/p14_phase4y/` (commit `50e2ded`).

---
*Compliance: Qwen3.7-Max streaming only; workflow_handoff_0018 + 0019 only; frozen 3 blocked pairs;
arbiter-driven (chain_executor, stdin-isolated, durable run-state); no DeepSeek/held-out/C6/BundleD/
individual-C1-C2-C4/k=5/non-streaming; `.env` removed; sanitized evidence + hashes; `scripts/check`
PASSED. Real PrimeTime grading (shim). Not pushed.*
