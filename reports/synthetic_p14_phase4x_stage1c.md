# p14 Phase-4X Stage 1C — exact-counterbalanced DeepSeek streaming replication (0009 vs 0015), 8 primary valid episodes — COMPLETE

**Status: COMPLETE.** Report-only commit. Classification: **confirmatory experiment with two disclosed
execution deviations** (§5). Code: instrumentation `616573d`, pre-run freeze `65e0b55`. Model:
DeepSeek-V4-Pro, SSE streaming, frozen config. Cost: primary 8 **¥81.44** + excluded attempt ¥7.73 =
**¥89.17**. FROZEN exact-counterbalanced order (seed `phase4x_stage1c_seed=20260721`): block1 Base→BundleS,
block2 BundleS→Base, block3 BundleS→Base, block4 Base→BundleS (each condition exactly 2× at each
within-block position). No held-out, no Qwen, no other variants, no k escalation, no non-streaming.
Validity/replacement driven entirely by the committed arbiter (`scripts/episode_arbiter.py`).

**Headline (accepted conclusion, review wording).** "Cross-model replication of the BundleS benefit
was not established for DeepSeek. Under the exact-counterbalanced Stage-1C design, Base and BundleS
both achieved 3/4 typed-binding correctness. The prior within-block position anomaly did not reproduce
with a stable direction, and the new request-level telemetry does not support recovered transport
degradation as the cause of the observed semantic-binding failures. The remaining DeepSeek errors are
best reported as trajectory-level stochastic instability under this model–harness configuration." The
treatment comparison is **null/inconclusive, not a clean negative effect** — BundleS is **not** stated
to be ineffective for DeepSeek.

**Mechanism scope (updated, review wording).** "BundleS is a **model-contingent harness mechanism
candidate**. It has replicated development and pre-frozen held-out evidence within Qwen3.7-Max, while
no detectable development benefit was established for DeepSeek-V4-Pro under the tested streaming
configuration."

**The complete 2×2 condition-by-position table (primary outcome = typed-binding correctness):**

| | position 0 | position 1 | margin |
|---|---|---|---|
| **Base** | 2/2 | 1/2 | **3/4** |
| **BundleS** | 2/2 | 1/2 | **3/4** |
| margin | **4/4** | 2/4 | 6/8 |

- **Treatment is tied (Base 3/4 = BundleS 3/4).** Null/inconclusive — neither positive replication
  evidence nor a clean negative effect.
- **Predeclared cell applied: "both conditions unstable without a consistent position pattern → report
  DeepSeek trajectory instability; do not claim for or against BundleS."** The within-1C position edge
  (pos0 4/4 vs pos1 2/4) is **direction-inverted from Stage 1** (Stage 1 had all failures at pos0) → no
  stable positional mechanism, exactly as Stage-1B's no-root-cause audit predicted.
- **Transport dimensions kept distinct.** Stage-1C provides evidence that recovered degradation was
  **not** the proximate explanation for the two binding failures: both degraded episodes were correct,
  while both binding failures had zero recovered degradation (§3).
- No unblocked post-hoc significance test is used as the headline; the 2×2 table and its margins are
  descriptive (n=8).

## 1. Per-episode outcomes (frozen order; primary slots)
| slot | cond@pos | tv | recov failed / hard-dl | term | FINISH | score | submitted | binding subtype | conf | rtok | wall(s) | ¥ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| b1p0 | Base@0 | ✓ | 0/0 | task_wall | no | 1.0 | slow/func | correct | — | 107920 | 1764 | 7.85 |
| b1p1 | BundleS@1 | ✓ | 0/0 | hard_kill | no | 0.2 | **setup/slow** | **axis_binding_failure** | — | 87308 | 1800 | 15.81 |
| b2p0 | BundleS@0 | ✓ | 1/1 | task_wall | no | 1.0 | slow/func | correct | — | 72507 | 1782 | 11.13 |
| b2p1 | Base@1 | ✓ | 0/0 | task_wall | no | 1.0 | slow/func | correct | — | 88490 | 1764 | 12.84 |
| b3p0 | BundleS@0 | ✓ | 0/0 | finish | **yes** | 1.0 | slow/func | correct | high | 38891 | 588 | 4.13 |
| b3p1 | Base@1 | ✓ | 0/0 | finish | **yes** | 0.2 | **func/slow** | **axis_binding_failure** | **high** | 44799 | 533 | 8.39 |
| b4p0 | Base@0 | ✓ | 1/0 | finish | **yes** | 1.0 | slow/func | correct | high | 87914 | 1182 | 11.86 |
| b4p1 | BundleS@1 | ✓ | 0/0 | finish | **yes** | 1.0 | slow/func | correct | high | 45426 | 667 | 9.43 |

All 8: anti-cheat clean, terminal-transport-valid (the new two-dimension telemetry: every episode
`terminal_transport_valid=true`). Excluded attempt: `block2:BundleS pos0 attempt1` runner produced no
graded result (FileNotFoundError) → arbiter REPLACE → replaced by attempt2 (above); cost ¥7.73,
preserved as excluded operational evidence.

## 2. Per-cell secondaries (typed-binding / artifact / FINISH / failure subtype)
| cell | typed-binding | artifact 1.0 | FINISH | failure subtype |
|---|---|---|---|---|
| Base@pos0 | 2/2 | 2/2 | 1/2 | — |
| Base@pos1 | 1/2 | 1/2 | 1/2 | 1 × axis_binding_failure (func/slow) |
| BundleS@pos0 | 2/2 | 2/2 | 1/2 | — |
| BundleS@pos1 | 1/2 | 1/2 | 1/2 | 1 × axis_binding_failure (setup/slow) |

Both failures are `semantic_binding_failure/axis_binding_failure`; no `role_conditioned_value_selection_failure`
in this run. One failure is the classic `func/slow` role-swap kept; the other (`setup/slow`) is a new
cross-axis value — "setup" is a timing-check *type*, not a PVT scenario member (a literal type error).

## 3. Transport — the new telemetry, and a clean negative for the Stage-1B correlate
The two independent dimensions (terminal_transport_valid / recovered_transport_degradation) now reported
per episode:
- **2/8 episodes had recovered degradation; both terminally valid.** `BundleS_b2p0` recovered one
  hard-request-deadline (cumulative retry wall **303 s**) and still produced a **correct** binding;
  `Base_b4p0` recovered one failed attempt (5.5 s) and was correct.
- **Both pos1 FAILURES had ZERO recovered degradation.** So recovered transport degradation did **not**
  cause the 1C binding failures — a clean negative for the Stage-1B correlate (which was a suspected
  but unproven channel). Degradation co-occurred only with *successful* episodes here.
- All 8 episodes terminal-transport-valid; 0 replacements triggered by transport (the one replacement
  was a runner `missing_results`, handled by the arbiter).

## 4. Separated conclusions
**(a) Treatment — null/inconclusive (not a clean negative).** Stage 1's contrast was uninterpretable
(position-confounded). Stage 1C removed the confound by counterbalancing and got a clean **tie**
(Base 3/4 = BundleS 3/4): the treatment comparison is **null/inconclusive** — BundleS is **not** stated
to be ineffective for DeepSeek; no detectable development benefit was established under this
configuration. Mechanism scope: BundleS is a **model-contingent harness mechanism candidate**
(replicated within Qwen3.7-Max; no detectable benefit for DeepSeek-V4-Pro here).

**(b) Position — no stable mechanism (inverted across stages).** 1C's pos0=4/4 vs pos1=2/4 edge is
direction-inverted from Stage 1 (pos0 worse there). Across the two stages there is no consistent
positional association — consistent with Stage-1B's verdict (no credible positional root cause; the
Stage-1 pattern was an unplanned anomaly). Position is not pursued further as a mechanism.

**(c) Reliability — DeepSeek can protocol-complete here (3/8 FINISH vs Stage 1's 0/7).** A descriptive
within-run observation (not a cross-run ranking given small n and Stage 1's deviation contamination).
One overconfident-wrong episode: `Base_b3p1` FINISHed with **high** confidence on a wrong
(axis-binding) answer — a reliability-layer flag (1/8). Recovered transport degradation did not impede
the correct outcomes (incl. a 303 s retry wall → still correct).

**(d) Transport instrumentation validated in production.** Per-request telemetry + the
terminal/recovered two-dimension split rendered every episode's transport quality measurable in-band;
the arbiter's single replacement was a real `missing_results`, and recovered degradation correctly did
NOT trigger any replacement.

## 5. Disclosed execution deviations (two; both reconciled, primary data = frozen slots)
1. **Instrumentation erratum lineage (committed `94f8892`).** Stage-1/1B had a false "agentlog
   retries=0" claim (report-authorship error; driver accounting was correct). Corrected before Stage 1C;
   the real gap (per-request detail) is what the new telemetry closes.
2. **Executor stdin bug → premature DONE after block2 (this run).** The original chain's
   `while read <<< "$SCHEDULE"` shared stdin with `run_agentic_baseline.py`, which consumed the
   remaining schedule lines; the loop printed DONE after block2 (4/8 slots). Arbiter + telemetry worked
   correctly throughout (incl. the block2:BundleS REPLACE→ACCEPT). Fixed via array iteration + `</dev/null`;
   blocks 3–4 resumed against the UNCHANGED frozen schedule/arbiter/config. Membership-code hashes
   re-verified intact before resume. No slot re-run; no extra episodes beyond the 8 authorized. Lesson:
   the chain executor is membership-adjacent infra — the generalized rule's spirit (committed/tested
   before the first paid call) extends to it; a future freeze should commit and hash the executor too.

## 6. Sample-size + scope
8 primary valid episodes; one development pair; one model; exact-counterbalanced (2×2 balanced). The
2×2 cells are n=2 each — descriptive; the tie and the inverted position signal are the supported
observations, not effect estimates. Qwen conclusions unchanged and remain Qwen-scoped.

## 7. Artifacts + SHA-256
Evidence root: `reports/evidence/p14_phase4x_stage1c_episodes/` — 8 trials × 8 sanitized files +
MANIFEST.json + SHA256SUMS; chain-of-custody byte-match verified for all 8. Pre-run gate (frozen config
+ counterbalanced randomization + interpretation + membership-code manifest + freeze hashes) at
`reports/evidence/p14_phase4x_stage1c/` (commit `65e0b55`).

---
*Compliance: DeepSeek-V4-Pro streaming only; workflow_handoff_0009 + 0015 only; exact-counterbalanced
frozen order; validity/replacement by the committed arbiter (recovered degradation never replaces);
excluded attempt preserved; `.env` removed; sanitized evidence + hashes; `scripts/check` PASSED. Real
PrimeTime grading (shim). Held-out DeepSeek NOT run. Not pushed.*
