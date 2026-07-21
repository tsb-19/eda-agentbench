# p14 Phase-4X Stage 1 — DeepSeek streaming × dev pair (0009 Base vs 0015 BundleS), k=3 valid each — COMPLETE

**Status: COMPLETE.** Classification (review-assigned): **confirmatory experiment with a disclosed
execution-protocol deviation** (§4e, §5). Report-only commit; interpretation amended per review. Code:
pre-run freeze `4977c48` (preflight PASS 13/13, frozen config/order/rules); mid-run deviation
reconciliation `4856189` (fully disclosed, §4e). Model: DeepSeek-V4-Pro, SSE streaming,
transport-homogeneous with the Qwen Phase-4V2/4W chains (identical env + driver args; only the model
differs). Cost: primary six **¥73.79** (Base ¥35.63 + BundleS ¥38.16) + extra episode ¥15.25 + aborted
partial ~¥12 (est) + preflight <¥0.01. FROZEN restricted order `block1:BundleS,Base /
block2:Base,BundleS / block3:BundleS,Base` (seed `phase4x_dev_seed=20260720`). Phase-4U non-streaming
DeepSeek episodes = historical reference ONLY.

**Headline (accepted conclusion, review wording; predeclared cell: high within-condition instability →
report recurrence only).** "Cross-model replication of the BundleS effect was **not established** for
DeepSeek in Stage 1. The nominal Base 2/3 versus BundleS 1/3 contrast is not directionally
interpretable because all three primary failures occurred at within-block position 0 and all three
passes occurred at position 1." The result is **neither positive replication evidence nor clean
evidence against BundleS**. The reportable recurrence: all three failures are
**`semantic_binding_failure/axis_binding_failure` with the SAME submitted tuple `func/slow`**
(both conditions; no `role_conditioned_value_selection_failure` observed). BundleS remains established
only within Qwen3.7-Max on this task family.

**Position-outcome pattern (unplanned anomaly; descriptive only; NO significance claim).** The
block-respecting descriptive pattern is **three of three blocks with position-0 failure and position-1
success**, across both conditions (condition and position are unconfounded by design — each condition
appears at both positions). A naive ~0.05 value can be computed only as a one-sided Fisher-style
calculation that ignores the blocked structure; it is **not used as inferential evidence**. The
anomaly is investigated by the Stage-1B no-call position-nuisance audit before any further paid data
collection.

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
ungraded, no agentlog (partial cost ~¥12 est). All graded episodes: anti-cheat clean, **0 terminal
transport events**; **7 recovered retried attempts across the run** (agentlog `retries`: ep1=2,
ep2=1, ep3=2, ep4=1, ep5=1, ep6=0, extra=0 — recovered per-request failures characterized in Stage
1B); 0 chat-retry exhaustions; failures show signoff=1.0 / evidence_generation=0.0 (signoff-green,
typed-binding-rejected).

**ERRATUM (Stage-1B follow-up).** The original version of this report stated "0 chat retries" and
`chat_retries: 0` for every episode. That was an authorship error: the extraction rows recorded the
correct per-episode retry counts (above), but the report was written without the automated
row-vs-report cross-check used in the Phase-4W finalize. The driver's episode-level retry accounting
was and is CORRECT; what the agentlog lacks is per-request failure detail (categories/timestamps),
which exists only in the stderr diagnostics — addressed by the Stage-1C instrumentation. No score,
binding, tally, or interpretation is affected.

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
  condition-level success, and the contrast is not directionally interpretable (position-outcome
  pattern, §Headline). No directional conclusion is drawn in either direction.
- ***high within-condition instability → report recurrence only* — APPLIED.** Both conditions mixed;
  the reportable recurrence is the failure signature itself: `axis_binding_failure` with tuple
  `func/slow`, 3/3 of failures, both conditions.

## 4. Separated conclusions
**(a) Transport validity.** 7/7 graded episodes free of terminal transport failures (0 terminal
markers; streamed throughout; 7 recovered retried attempts, see erratum + Stage 1B). The two
`task_wall_hard_kill` terminations are task-level (in-flight request straddled the 1800 s wall with
active token flow; 0 terminal transport events) — valid measurements under the frozen rule,
termination mode reported separately.

**(b) Capability — cross-model replication not established in Stage 1.** Within Qwen3.7-Max, BundleS
was 3/3 on this pair (Run-2) and 3/3 held-out; for DeepSeek streaming, replication was **not
established** (accepted conclusion, headline verbatim): the nominal contrast is not directionally
interpretable given the position-outcome pattern, and the result is neither positive replication
evidence nor clean evidence against BundleS. In the three failing episodes the schema/contract
components did not suppress the recurring `func/slow` axis binding. BundleS remains a Qwen-established
mechanism on this family. The DeepSeek held-out pair was not run; further paid DeepSeek data
collection is deferred pending the Stage-1B audit and review (a Stage-1C counterbalanced replication
is proposed there, not executed).

**(c) Protocol/reliability — notable descriptive observation only.** 0/7 FINISH and 0/7 confidence
elicited across all graded DeepSeek episodes (terminations: 3 action_cap, 2 task_wall, 2 hard_kill);
every artifact success arrived without protocol completion. For context, the corresponding Qwen runs
showed 3/6 FINISH — recorded as a descriptive difference only; **no cross-model reliability ranking
is made from these small samples**.

**(d) Transport regimes are not pooled.** "The descriptive difference between the old non-streaming
0/3 baseline and the new streaming 2/3 baseline reinforces the decision not to pool transport
regimes, but does not independently establish a causal streaming effect on capability."

**(e) Deviation disclosure and infrastructure rule (see `deviation_log.json`, commit `4856189`).**
Stage 1 is classified as a **confirmatory experiment with a disclosed execution-protocol deviation**.
The uncommitted validity helper was stricter than the frozen rule (`timed_out` unconditional vs
"timeout attributable to transport"), mislabeling two transport-clean PASS episodes at block1:Base and
triggering unauthorized replacements. The authoritative primary data are the **frozen attempt-1
slots**; the unauthorized extra graded episode is preserved as **excluded evidence**; the aborted
partial attempt is an **operational deviation**; neither enters the primary condition counts.
Benchmark infrastructure rule (promoted from this deviation): **"All paid-episode validity and
replacement arbiters must be implemented, tested, and committed inside the pre-run freeze. No
uncommitted helper may determine whether a paid episode is valid, replaced, or excluded."**

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
PASSED. Real PrimeTime grading (b04 shim). Held-out DeepSeek NOT run; further paid DeepSeek data
collection deferred to review (Stage-1B no-call audit first). Not pushed.*
