# p14 Phase-4W Run-1 — symmetric C6 ablation (V1=0010−C6, V9=0009+C6), k=3 each — COMPLETE

**Status: COMPLETE.** Report-only commit. HEAD `[SHA-TBD]`. Code: held-out `97fe789`, V1/V9 `0f38cc0`,
fairness gate `ee6f8a6` (all hard gates PASS). Model: Qwen3.7-Max, SSE streaming. Cost **¥60.71**
(V1 ¥30.82 + V9 ¥29.89). Frozen blocked-randomized order `block1:V1,V9 / block2:V9,V1 / block3:V1,V9`
(seed `phase4w_run1_seed=20260715`). No k=5, no DeepSeek, no held-out/other-variant/non-streaming calls.

**Headline (predeclared §7a cell): V1 remains STRONG (3/3) and V9 RECOVERS (3/3) → "C6 is sufficient
on 0009 but redundant within 0010."** Removing the answer-bearing C6 assertion from the clear bundle
did not degrade it (the non-C6 bundle components already suffice at the clear endpoint); adding C6
ALONE to the ambiguous baseline recovered it to 3/3. Since C6 is **answer-bearing**, its sufficiency
(V9) is an **answer-disclosure effect**, not isolated semantic-role-mechanism evidence.

## 1. Per-episode outcomes (frozen order; full dimension set)
| # | block | variant (task) | transport_valid | gradeable | protocol_complete | termination | FINISH | score | submitted | conf | actions | rtok | retries | tport_ev | cost ¥ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ep1 | block1 | V1 (0010−C6) | ✓ | ✓ | ✓ | finish | yes | 1.0 | slow/func | HIGH | 51 | 76479 | 0 | 0 | 11.83 |
| ep2 | block1 | V9 (0009+C6) | ✓ | ✓ | ✓ | finish | yes | 1.0 | slow/func | HIGH | 44 | 42855 | 1 | 0 | 8.57 |
| ep3 | block2 | V9 (0009+C6) | ✓ | ✓ | ✗ | action_cap | no | 1.0 | slow/func | — | 60 | 50651 | 0 | 0 | 12.93 |
| ep4 | block2 | V1 (0010−C6) | ✓ | ✓ | ✗ | task_wall | no | 1.0 | slow/func | — | 41 | 88758 | 0 | 0 | 8.39 |
| ep5 | block3 | V1 (0010−C6) | ✓ | ✓ | ✓ | finish | yes | 1.0 | slow/func | HIGH | 50 | 63076 | 0 | 0 | 10.60 |
| ep6 | block3 | V9 (0009+C6) | ✓ | ✓ | ✓ | finish | yes | 1.0 | slow/func | HIGH | 45 | 34273 | 0 | 0 | 8.39 |

All 6 episodes: anti-cheat clean, submitted the correct `slow/func` (typed-binding correct), signoff=1.0,
evidence_generation=1.0, **0 transport events**, 0–1 chat retries.

## 2. Condition tallies
| condition | k | artifact/typed-binding correct | protocol-complete FINISH | overconfident_wrong |
|---|---|---|---|---|
| **V1 (0010−C6)** — C6 necessity at clear endpoint | 3 | **3/3** | 2/3 (ep1,ep5) | 0 |
| **V9 (0009+C6)** — C6 sufficiency at ambiguous endpoint | 3 | **3/3** | 2/3 (ep2,ep6) | 0 |

Both conditions cleanly 3/3 → **no within-condition instability** (the §7a instability cell is not triggered).

## 3. C6 interpretation (predeclared §7a table)
| V1 (0010−C6) | V9 (0009+C6) | interpretation |
|---|---|---|
| **strong (3/3)** | **recover (3/3)** | **C6 is sufficient on 0009 but redundant within 0010** ← observed |
| degrade | recover | C6 dominant local driver (answer-disclosure) |
| strong | no recover | C6 not the primary driver |
| degrade | no recover | C6 necessary but insufficient (interaction) |

## 4. Separated conclusions
**(a) Transport validity.** All 6 episodes transport-clean (0 socket_timeout / 0 hard_deadline / 0 stream
errors; 1 chat retry on ep2, recovered). Streaming at `e1c36d2` over the Phase-4V2 model–harness config.

**(b) Capability — C6 (answer-bearing) local effect.** This Run-1 is a **local** two-endpoint ablation
(§1a framing — NOT a main effect): V1 estimates local *necessity* of C6 at the clear endpoint (not
necessary: 3/3 without it); V9 estimates local *sufficiency* of C6 at the ambiguous endpoint (sufficient:
3/3 with it alone). Because C6 is **answer-bearing** (it nearly publishes `slow/func`), its sufficiency
is an **answer-disclosure effect**: publishing the answer recovers the ambiguous task. This does NOT by
itself establish that the Phase-4V2 clarity-bundle effect is a semantic-role *inference* effect — that
requires the deferred **non-answer-bearing** controls (PC2 labeling, PC3 decoy-disambiguation, PC4
lexical), which have not been run. Note V1 staying 3/3 shows the non-C6 bundle components also suffice at
the clear endpoint, so the clear-endpoint effect is not solely answer-disclosure.

**(c) Calibration — illustrative anecdote, not a claim.** 4/6 episodes were protocol-complete with HIGH
confidence, all **correct** (no overconfident_wrong); 2/6 were gradeable-timeout (action-cap / task-wall)
with the correct config committed. With 4 confidence-bearing episodes, this is an anecdote, not a
calibration claim.

## 5. Sample-size + scope statement
k=3 per condition is a small local-ablation sample. The result is a **local** necessity/sufficiency
finding at two endpoints of one controlled pair, NOT a general main effect for C6 and NOT a
generalization claim (the held-out 0011/0012 pair is frozen but not yet run on a model). Rates are point
observations; no population claim.

## 6. Frozen execution order + provenance
Order `V1,V9,V9,V1,V1,V9` (blocks 1–3), generated under `phase4w_run1_seed=20260715` and FROZEN at
`ee6f8a6` before any result was observed (`reports/evidence/p14_phase4w_fairness/randomization_manifest.json`).
Run-to-commit: all 6 episodes ran at HEAD `ee6f8a6` (fairness gate) over task bytes committed at
`0f38cc0` (V1/V9) / `97fe789` (held-out).

## 7. Artifacts + SHA-256
Evidence root: `reports/evidence/p14_phase4w_run1/` — `V1_ep1/ V9_ep2/ V9_ep3/ V1_ep4/ V1_ep5/ V9_ep6/`
(6×8 sanitized files) + `MANIFEST.json` + `SHA256SUMS`. Per-episode evidence-chain copies byte-match the
grader's `submitted_file_hashes` (chain of custody). Fairness-gate evidence (the gate these episodes
passed) at `reports/evidence/p14_phase4w_fairness/`.

---
*Compliance: Qwen3.7-Max only (no DeepSeek/MiniMax/Kimi/GLM); 0013/0014 only (no held-out/other-variant
model calls); SSE streaming, no non-streaming fallback; no k=5 escalation; `.env` symlink removed after
runs; no secrets/raw reasoning in any artifact (worker strips reasoning at the IPC boundary; username →
`<USER>`; hygiene asserted per file). Real PrimeTime grading (b04 shim). Not pushed.*
