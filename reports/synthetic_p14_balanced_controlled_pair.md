# p14 balanced semantic-role controlled pair, 2×2 × k=3 (Phase-4V2) — COMPLETE

**Status: COMPLETE.** Balanced Qwen side of the `workflow_handoff_0009` (ambiguous) / `0010` (clear
control) controlled pair to k=3 under SSE streaming. HEAD `[SHA-TBD]`.
This completes the matrix the Phase-4V1 report could only qualify as "recurrent failure-mode evidence"
(Qwen × 0010 was k=1 there).

**Headline: the clear-role `0010` task SUPPRESSES the scenario/corner wrong-axis binding failure for
BOTH models.** DeepSeek 0009 0/3 → 0010 3/3; **Qwen 0009 1/3 (2 wrong-axis) → 0010 3/3 (0 wrong-axis)**.
0009/0010 share identical hidden truth + grader + flow + mutant + decoys; the ONLY visible difference
is the clarity bundle — and removing it (0009) is what induces the failure in both models.

## 0. Matrix (2 models × 2 tasks, each cell k=3)
| cell | transport | k | pass | wrong-axis fails | submitted tuples |
|---|---|---|---|---|---|
| DeepSeek × 0009 (ambiguous) | non-streaming (Phase-4U frozen) | 3 | **0/3** | 3 | func/typ; func/slow; func/slow |
| DeepSeek × 0010 (clear) | non-streaming (Phase-4U frozen) | 3 | **3/3** | 0 | slow/func ×3 |
| Qwen × 0009 (ambiguous) | **streaming** (Phase-4V1) | 3 | **1/3** | 2 | func/slow; slow/func; func/typ |
| Qwen × 0010 (clear) | **streaming** (Phase-4V2) | 3 | **3/3** | 0 | slow/func ×3 |

Golden tuple (frozen, both tasks): `netlist_v2.v / clk_main / scenario=slow / corner=func`.
Pass counts are point observations, not rate estimates (k=3; see §6).

## 1. Per-episode outcomes (12 episodes, 6-dim termination classification)

### DeepSeek × 0009 (Phase-4U, non-streaming, frozen)
| trial | transport_valid | workspace_gradeable | protocol_completed | termination_reason | FINISH | score | submitted | act | rtok | cost ¥ | wall s | retries |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| t1 | false* | true | false | late_socket_timeout (aborted; work done) | false | 0.20 | func/typ | 53 | 71998 | 11.36 | 1586 | 0 |
| t2 | false* | true | false | late_socket_timeout (aborted; work done) | false | 0.20 | func/slow | 48 | 74715 | 8.91 | 1800 | 2 |
| t3 | true | true | false | action_cap | false | 0.20 | func/slow | 60 | 68384 | 15.84 | 1800 | 3 |

### DeepSeek × 0010 (Phase-4U, non-streaming, frozen)
| trial | transport_valid | workspace_gradeable | protocol_completed | termination_reason | FINISH | score | submitted | act | rtok | cost ¥ | wall s | retries |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| t1 | true | true | **true** | finish_action | true | 1.00 | slow/func | 57 | 69657 | 10.92 | 1654 | 2 |
| t2 | true | true | false | action_cap | false | 1.00 | slow/func | 60 | 73738 | 12.47 | 1624 | 1 |
| t3 | false* | true | false | late_socket_timeout (aborted; work done) | false | 1.00 | slow/func | 29 | 27435 | 3.46 | 757 | 0 |

`*` **late-socket_timeout episodes are gradeable, not measurement-invalid.** The (wrong/correct)
config was committed BEFORE the socket_timeout aborted the episode, so the capability outcome is a
real observation (the typed-binding oracle grades the committed workspace state). This is distinct
from the Phase-4V Qwen × 0009 *early*-abort case (socket_timeout before any repair edit → no valid
repair action → measurement-invalid). 3 of 6 DeepSeek episodes had a late socket_timeout; all 6 are
gradeable capability measurements.

### Qwen × 0009 (Phase-4V1, streaming)
| trial | transport_valid | workspace_gradeable | protocol_completed | termination_reason | FINISH | score | submitted | act | rtok | cost ¥ | wall s | retries |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| trial1 | true | true | **true** | finish_action | true | 0.20 | func/slow | 47 | 60411 | 11.16 | 1550 | 0 |
| rep2 | true | true | false | task_wall_limit | false | 1.00 | slow/func | 48 | 76686 | 12.82 | 1780 | 0 |
| rep3 | true | true | false | task_wall_limit | false | 0.20 | func/typ | 52 | 76663 | 13.59 | 1799 | 0 |

### Qwen × 0010 (Phase-4V2, streaming)
| trial | transport_valid | workspace_gradeable | protocol_completed | termination_reason | FINISH | score | submitted | act | rtok | cost ¥ | wall s | retries |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| stream_trial1 | true | true | false | action_cap | false | 1.00 | slow/func | 60 | 42939 | 11.43 | 1465 | 0 |
| stream_rep2 | true | true | false | action_cap | false | 1.00 | slow/func | 60 | 47518 | 11.48 | 1522 | 0 |
| stream_rep3 | true | true | **true** | finish_action | true | 1.00 | slow/func | 44 | 33755 | 7.57 | 1065 | 0 |

All 3 Qwen × 0010 episodes submitted the correct `slow/func`, scored 1.00 (all 8 components = 1.0),
anti-cheat clean, 0 transport events, 0 chat retries. `stream_rep3` is protocol-complete (FINISH,
HIGH confidence, **correct** — a confident-correct solve, not overconfident); the other two hit the
60-action cap with the correct config already committed (gradeable action-cap PASS).

## 2. Normal-completion vs timeout/action-cap termination
- **Protocol-complete (FINISH issued): 3/12.** DeepSeek×0010 t1 (1.00, high-confidence correct);
  Qwen×0009 trial1 (0.20, HIGH-confidence WRONG → `overconfident_wrong`); Qwen×0010 stream_rep3
  (1.00, high-confidence correct). → The two confident solves on the CLEAR task were correct; the one
  confident solve on the AMBIGUOUS task was wrong.
- **Action-cap (60 actions, no FINISH): 4/12.** DeepSeek×0009 t3 (0.20); DeepSeek×0010 t2 (1.00);
  Qwen×0010 stream_trial1 (1.00); Qwen×0010 stream_rep2 (1.00).
- **Task-wall-limit (harness `deadline`): 2/12.** Qwen×0009 rep2 (1.00), rep3 (0.20).
- **Late socket_timeout (aborted, work done; gradeable): 3/12.** DeepSeek×0009 t1/t2 (0.20);
  DeepSeek×0010 t3 (1.00).

## 3. Binding-error variants (wrong-axis)
Across both models on 0009, `scenario` was misassigned to `func` in every wrong-axis failure:
- DeepSeek × 0009: `func/typ` (t1), `func/slow` (t2, t3).
- Qwen × 0009: `func/slow` (trial1, value swap = DeepSeek t2/t3 mode), `func/typ` (rep3, stale-decoy
  corner = DeepSeek t1 mode).
- Qwen reproduced BOTH DeepSeek wrong-binding variants on 0009.
- On 0010 (clear control): **0 wrong-axis failures for either model** — DeepSeek 3/3 correct,
  Qwen 3/3 correct. The clarity bundle suppresses the wrong-axis error in both.

## 4. Pass counts (point observations, not rate estimates)
| cell | pass@observed | overconfident_wrong | measurement-invalid |
|---|---|---|---|
| DeepSeek × 0009 | 0/3 | 0 | 0 (3 late-socket_timeout are gradeable, work-done) |
| DeepSeek × 0010 | 3/3 | 0 | 0 (1 late-socket_timeout, gradeable) |
| Qwen × 0009 | 1/3 | 1 (trial1) | 0 |
| Qwen × 0010 | 3/3 | 0 | 0 |

## 5. Separated conclusions
**(a) Transport validity.** The Qwen row is fully streaming (Phase-4V1 + 4V2): **0 transport events
across all 6 episodes** (0 socket_timeout / 0 hard_deadline / 0 incomplete_stream / 0 malformed_stream
/ 0 chat retries), delivering 33K–77K reasoning tokens each — the band the non-streaming transport
censored. The DeepSeek row is Phase-4U frozen (non-streaming): 3 of 6 episodes had a late
socket_timeout AFTER work was done (gradeable; capability outcomes unaffected). The streaming fix
(`e1c36d2`) is what made the Qwen row transport-clean; the DeepSeek row is retained under its frozen
condition per spec. The 3 Qwen × 0010 streaming episodes confirmed 0 transport events.

**(b) Capability — does 0010 suppress the wrong-axis failure? YES, for both models.** DeepSeek:
0009 0/3 (3 wrong-axis) vs 0010 3/3 (0 wrong-axis). Qwen: 0009 1/3 (2 wrong-axis, both DeepSeek
variants) vs **0010 3/3 (0 wrong-axis)**. The clarity bundle — the only visible difference between
0009 and 0010 — removes the semantic-role binding failure in both models. This is a cross-model,
k=3-per-cell replication of the controlled-pair mechanism.

**(c) Reliability / calibration.** Confidence tracks correctness on the clear task and breaks on the
ambiguous one: the only protocol-complete Qwen × 0010 episode (stream_rep3) was HIGH-confidence and
**correct** (calibrated), whereas the only protocol-complete Qwen × 0009 episode (trial1) was
HIGH-confidence and **wrong** (`overconfident_wrong`). On 0009 the two gradeable-timeout rows split
one PASS / one failure — a sampling-level ambiguity-resolution instability, not a deterministic
inability. k=3 establishes the mechanism (0010 suppresses; 0009 does not) but not a success rate.

## 6. Sample-size statement
k=3 per cell is a small replication sample. Pass counts are point observations with wide uncertainty;
no population success-rate claim is made. The controlled-pair signal (0009 degrades, 0010 does not)
is qualitative mechanism evidence replicated across two models at k=3 each, not a rate estimate.

## 7. Historical reference (excluded from primary cell)
The single Phase-4U Qwen × 0010 episode (`historical_phase4u_nonstream`) was NON-streaming and
action-cap-terminated (transport-valid, no censoring; 1.00 slow/func, 2 chat-retries). It is
**excluded** from the primary Qwen × 0010 streaming k=3 cell to avoid transport confounding
(streaming vs non-streaming is itself contribution C4). Preserved at
`reports/evidence/p14_qwen_0010_stream_anchor/historical_phase4u_nonstream/`
(transport_mode=non_streaming, transport_valid=true, protocol_completed=false,
termination_reason=action_cap, workspace_gradeable=true, score=1.00). Discussed only as
transport-sensitivity / historical-consistency context; its outcome (1.00 slow/func) is consistent
with the 3 fresh streaming passes.

## 8. Artifacts + SHA-256
- Qwen × 0009 streaming evidence: `reports/evidence/p14_qwen_0009_stream_anchor/` (Phase-4V1, audit-
  amended; MANIFEST sha256 `9552bc3b…` + 3×8 files + SHA256SUMS).
- Qwen × 0010 streaming evidence: `reports/evidence/p14_qwen_0010_stream_anchor/` (Phase-4V2):
  MANIFEST sha256 `d9ea2574…`; `stream_trial1/` `stream_rep2/` `stream_rep3/` (3×8 files) +
  `historical_phase4u_nonstream/` (8 files) + SHA256SUMS (33 files). Per-episode evidence-chain
  copies (flow_config/timing_report/evidence_manifest/stage2_summary) byte-identical to the grader's
  `submitted_file_hashes` (verified chain of custody for all 4 dirs).
- DeepSeek × 0009/0010 evidence: Phase-4U, `runs/p14_phase4u_srb_probe_v3/` (frozen; not re-run).
- Audit amendment to the Phase-4V1 report: `synthetic_p14_qwen_0009_stream_anchor.{md,json}` (§0a
  0af5d32 audit, §2a 6-dim termination, corrected seed wording, controlled-pair qualification).

## Repetition protocol (compliance)
Qwen × 0010 streaming: same committed code `e1c36d2`, same frozen settings as the 0009 anchor
(model Qwen3.7-Max, temperature 0.7, max-actions 60, episode timeout 1800 s, request inactivity
timeout 120 s, hard deadline 300 s, max chat retries 1, elicit-confidence, real-PT grader, streaming).
Predeclared IDs `stream_trial1`/`stream_rep2`/`stream_rep3`; 0010 task bytes unchanged since Phase-4U
(commit `622d07c`). **Seed note:** stochastic replications under an identical exposed benchmark
configuration; the provider exposed no controllable sampling seed, so statistical independence cannot
be guaranteed or directly audited; identical task/harness/model config/decoding params/budgets/
scoring, naturally differing transcripts. 3 runs → 3 valid (0 measurement-invalid); stopped at 3.
No DeepSeek; no other tasks; no non-streaming fallback; task and action budget unaltered.

---
*Compliance: Qwen3.7-Max (streaming, ¥30.48 for the 3 × 0010 episodes) + DeepSeek-V4-Pro (Phase-4U
frozen). `.env` symlink removed after runs; no secrets/raw reasoning in any artifact; username →
`<USER>`; hygiene asserted per file. Real PrimeTime grading (b04 shim). Not pushed.*
