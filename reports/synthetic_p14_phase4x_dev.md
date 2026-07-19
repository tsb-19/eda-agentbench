# p14 Phase-4X Stage 1 — DeepSeek streaming × dev pair (0009 Base vs 0015 BundleS), k=3 valid each — COMPLETE

**Status: COMPLETE.** Report-only commit. Code: pre-run freeze `4977c48` (preflight PASS 13/13,
frozen config/order/rules); mid-run deviation reconciliation `4856189` (fully disclosed, §5). Model:
DeepSeek-V4-Pro, SSE streaming, transport-homogeneous with the Qwen Phase-4V2/4W chains (identical
env + driver args; only the model differs). Cost: primary six **¥73.79** (Base ¥35.63 + BundleS
¥38.16) + extra episode ¥15.25 + aborted partial ~¥12 (est) + preflight <¥0.01. FROZEN restricted
order `block1:BundleS,Base / block2:Base,BundleS / block3:BundleS,Base` (seed
`phase4x_dev_seed=20260720`). Phase-4U non-streaming DeepSeek episodes = historical reference ONLY.

**Headline (predeclared cell applied: high within-condition instability → report recurrence only).**
Cross-model replication of the BundleS development effect is **NOT supported** on this pair at k=3.
Typed-binding: **Base 2/3, BundleS 1/3** — no BundleS improvement over the ambiguous baseline was
observed, and both conditions were internally unstable (Base 1.0/0.2/1.0; BundleS 0.2/1.0/0.2), so no
condition met a stable-outcome criterion. All three failures are
**`semantic_binding_failure/axis_binding_failure` with the SAME submitted tuple `func/slow`**
(recurring in BOTH conditions; no `role_conditioned_value_selection_failure` observed). Per the
review's scoping: this reinforces that BundleS is **not a general cross-model harness mechanism** —
its stable effect remains established only within Qwen3.7-Max.

**Position-outcome alignment caveat.** In the realized allocation, all three failures landed at
within-block position 0 and all three passes at position 1, across both conditions (probability ≈0.05
under exchangeability). Condition and position are unconfounded by design (each condition appears at
both positions), and outcome tracked POSITION, not condition — so the nominal 2/3-vs-1/3 condition
contrast carries no interpretable direction in this sample. Reported as an observed alignment only;
no causal claim.

## 1. Per-episode outcomes (frozen order; primary slots)
| # | block:pos | cond (task) | tv | pc | termination | FINISH | score | submitted | binding | conf | act | rtok | tport | ¥ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ep1 | b1:0 | BundleS (0015) | ✓ | ✗ | action_cap | no | 0.2 | **func/slow** | **axis_binding_failure** | — | 60 | 76196 | 0 | 11.19 |
| ep2 | b1:1 | Base (0009) | ✓ | ✗ | task_wall_hard_kill | no | 1.0 | slow/func | correct | — | 60 | 101332 | 0 | 12.28 |
| ep3 | b2:0 | Base (0009) | ✓ | ✗ | task_wall | no | 0.2 | **func/slow** | **axis_binding_failure** | — | 52 | 90019 | 0 | 10.49 |
| ep4 | b2:1 | BundleS (0015) | ✓ | ✗ | action_cap | no | 1.0 | slow/func | correct | — | 60 | 66928 | 0 | 13.23 |
| ep5 | b3:0 | BundleS (0015) | ✓ | ✗ | task_wall | no | 0.2 | **func/slow** | **axis_binding_failure** | — | 55 | 65998 | 0 | 13.74 |
| ep6 | b3:1 | Base (0009) | ✓ | ✗ | action_cap | no | 1.0 | slow/func | correct | — | 60 | 67087 | 0 | 12.86 |

Extra (disclosed, EXCLUDED from tallies per `deviation_log.json`): `Base_ep2_extra_a2` = 1.0,
slow/func correct, task_wall_hard_kill, ¥15.25. Aborted `a3`: experimenter-terminated mid-episode,
ungraded, no agentlog (partial cost ~¥12 est). All graded episodes: anti-cheat clean, 0 transport
events, 0 chat retries; failures show signoff=1.0 / evidence_generation=0.0 (signoff-green,
typed-binding-rejected).

## 2. Condition tallies (primary outcome + secondaries)
| condition | k | typed-binding correct | artifact 1.0 | FINISH | semantic_binding_failure (subtype) |
|---|---|---|---|---|---|
| **Base** (0009 ambiguous) | 3 | **2/3** | 2/3 | 0/3 | 1 × axis_binding_failure (func/slow) |
| **BundleS** (0015 = 0009+C1/C2/C4/C7) | 3 | **1/3** | 1/3 | 0/3 | 2 × axis_binding_failure (func/slow ×2) |

## 3. Predeclared interpretation (all 5 cells walked; `reports/evidence/p14_phase4x_dev/interpretation_table.json`)
- *baseline recurrent failures + BundleS stable correct* → **not observed** (BundleS 1/3, not stable).
- *both succeed (saturated)* → **not observed** (neither 3/3).
- *both fail* → **not observed** (Base 2/3).
- *baseline succeeds while BundleS degrades* → **not established**: Base 2/3 is not a stable
  condition-level success, and the 2/3-vs-1/3 contrast is fully absorbed by the position-outcome
  alignment (§Headline caveat). Reported as a directional observation only: no BundleS benefit seen.
- ***high within-condition instability → report recurrence only* — APPLIED.** Both conditions mixed;
  the reportable recurrence is the failure signature itself: `axis_binding_failure` with tuple
  `func/slow`, 3/3 of failures, both conditions.

## 4. Separated conclusions
**(a) Transport validity.** 7/7 graded episodes transport-clean (0 markers, 0 retries; SSE streamed
throughout). The two `task_wall_hard_kill` terminations are task-level (in-flight request straddled
the 1800 s wall with active token flow; 0 transport events) — valid measurements under the frozen
rule, termination mode reported separately.

**(b) Capability — no cross-model replication of the BundleS effect.** Within Qwen3.7-Max, BundleS
was 3/3 on this pair (Run-2) and 3/3 held-out; for DeepSeek streaming it is 1/3, with no improvement
over the 0009 baseline (2/3). The recurring DeepSeek failure is the same `func/slow` axis binding
across both conditions — the schema/contract components did not suppress it. Consistent with the
accepted scoping: BundleS is a Qwen-established mechanism on this family, not (yet) a model-robust
harness mechanism. Per the review's gate, a DeepSeek held-out confirmation is **not** supported for
consideration (the development comparison did not support the BundleS direction).

**(c) Protocol/reliability signature — DeepSeek never protocol-completes here.** 0/7 FINISH, 0/7
confidence elicited (terminations: 3 action_cap, 2 task_wall, 2 hard_kill). Sharp contrast with Qwen
(3/6 FINISH, HIGH-and-correct when finishing). DeepSeek's artifact success (3 primary 1.0s) always
arrived without protocol completion — a reliability-layer discriminator, reported separately from
capability.

**(d) Historical contrast vindicates the transport rule.** DeepSeek streaming Base = 2/3 vs Phase-4U
non-streaming Base = 0/3 (historical reference only, transport-contaminated 3/6 episodes). The
transport regime materially changes DeepSeek's measured baseline — reusing the Phase-4U episodes as a
primary baseline would have manufactured a spurious "BundleS rescues DeepSeek" conclusion.

**(e) Deviation disclosure (see `deviation_log.json`, commit `4856189`).** The uncommitted validity
helper was stricter than the frozen rule (`timed_out` unconditional vs "timeout attributable to
transport"), mislabeling two transport-clean PASS episodes at block1:Base and triggering unauthorized
replacements (one extra graded episode, one aborted). Reconciled per the authoritative frozen text
BEFORE resuming (slot = attempt 1; extra preserved + excluded; corrected checker committed as
`scripts/phase4x_validity.py`). Prevention: paid-episode arbiters must ship in the pre-run freeze.

## 5. Sample-size + scope
k=3 valid per condition; one development pair; one model; point observations with wide uncertainty.
The supported statement is the recurrence report (§3), not an effect estimate. Qwen conclusions are
unchanged and remain scoped to Qwen.

## 6. Frozen execution order + provenance
Frozen at `4977c48` (seed 20260720, restricted balanced; first triple accepted). Episodes ran at HEAD
`4977c48` (block1) and `4856189` (blocks 2–3, after the reconciliation commit — task bytes identical,
verified by the freeze-manifest hashes; no task/grader/scoring/randomization change between them).

## 7. Artifacts + SHA-256
Evidence root: `reports/evidence/p14_phase4x_dev_episodes/` — 7 trials × 8 sanitized files (6 primary
+ 1 extra) + MANIFEST.json + SHA256SUMS; chain-of-custody byte-match verified for all 7. Pre-run gate
(preflight + frozen config + randomization + interpretation + historical reference + freeze hashes +
deviation log) at `reports/evidence/p14_phase4x_dev/` (commits `4977c48`, `4856189`).

---
*Compliance: DeepSeek-V4-Pro streaming only; workflow_handoff_0009 + 0015 only (no 0011/0017-DeepSeek
/ individual C-ablations / C6 / BundleD / Qwen / k=5 / non-streaming); frozen order; preflight before
any benchmark episode; `.env` removed after runs; sanitized evidence + hashes; `scripts/check`
PASSED. Real PrimeTime grading (b04 shim). Held-out DeepSeek NOT run and NOT supported for
consideration. Not pushed.*
