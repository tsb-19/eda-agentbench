# p14 Qwen × workflow_handoff_0009 streaming anchor, k=3 (Phase-4V1) — ANCHOR RESOLVED

**Status: COMPLETE — 3 valid episodes, 0 measurement-invalid. Committed as one report-only commit
(evidence + this report; SHA in the review message).**
Code: `e1c36d2` (SSE streaming infrastructure). Cost **¥37.57 (trial1 ¥11.16 + rep2 ¥12.82 + rep3 ¥13.59) + ~¥0.02 preflight**.
Model: Qwen3.7-Max only. Task: workflow_handoff_0009 only. Transport: SSE streaming (the ONLY change vs Phase-4V).

**Headline: 1/3 pass. The scenario/corner wrong-axis semantic-role failure REPRODUCES in Qwen (2 of 3
valid episodes) and spans BOTH wrong-binding variants previously observed in DeepSeek (func/slow and
func/typ). Transport was 100% clean across all three episodes + preflight (zero timeout/deadline/stream
events), so these are genuine capability observations.**

**Goal:** k=3 valid Qwen × 0009 episodes (trial1 from Phase-4V0 + predeclared rep2, rep3) to test whether
the scenario/corner wrong-axis binding failure observed in trial1 repeats.

## 1. All three episode outcomes + exact submitted bindings
| episode | valid | submitted (netlist/scenario/corner) | score | signoff | evidence_gen | confidence | outcome |
|---|---|---|---|---|---|---|---|
| trial1 (2026-07-12) | yes | netlist_v2 / **func** / **slow** (wrong-axis swap) | 0.20 | 1.0 | 0.0 | HIGH → overconfident_wrong | semantic-role failure |
| rep2 (2026-07-13) | yes | netlist_v2 / **slow** / **func** (CORRECT) | 1.00 | 1.0 | 1.0 | — (no FINISH; wall budget) | PASS |
| rep3 (2026-07-13) | yes | netlist_v2 / **func** / **typ** (wrong-axis) | 0.20 | 1.0 | 0.0 | — (no FINISH; wall budget) | semantic-role failure |

Golden tuple (frozen): `netlist_v2.v / clk_main / scenario=slow / corner=func`.
All three episodes are anti-cheat clean, netlist correct (v2), grading via real PrimeTime (b04 shim).
Both failures carry the 0.20 signature (`signoff=1.0`, `evidence_generation=0.0`, `explanation=1.0`):
signoff-green but semantically wrong — exactly what the typed-binding oracle exists to catch.

## 2. Counts, scores, confidence, actions, reasoning tokens, costs, wall times
| episode | actions | finished | edited | reasoning_tokens | tokens in/out | cost ¥ | wall s | chat_retries |
|---|---|---|---|---|---|---|---|---|
| trial1 | 47 | yes | flow_config.json | 60411 | 736360/64489 | 11.16 | 1550 | 0 |
| rep2 | 48 | no (wall budget after correct config) | flow_config.json | 76686 | 828765/79891 | 12.82 | 1780 | 0 |
| rep3 | 52 | no (wall budget with wrong config committed) | flow_config.json | 76663 | 891423/80393 | 13.59 | 1799 | 0 |

Success/failure count: **1/3 pass** (2 semantic-role failures, 0 other, 0 measurement-invalid).
Confidence was elicited only where the agent reached FINISH: trial1 (HIGH, wrong → `overconfident_wrong`).
rep2/rep3 consumed the full 1800 s episode budget without FINISH (protocol note; their capability
outcomes — one PASS, one failure — are read from the committed config at expiry, as graded).

## 3. Does the scenario/corner wrong-axis error repeat?
**Yes — 2 of 3 valid episodes, and not as a single fixed mistake.** trial1 submitted `func/slow`
(the value swap: both axis values present but role-inverted — DeepSeek's t2/t3 mode). rep3 submitted
`func/typ` (scenario wrong AND corner pulled from the stale-v1 decoy — DeepSeek's t1 mode). Between
them, Qwen reproduced **both** wrong-binding variants DeepSeek exhibited on this task. Across all five
cross-model failures (DeepSeek 3 + Qwen 2), `scenario` was misassigned to `func` every time — the
models consistently bind the functional-mode label to the scenario axis when the clarity bundle is
absent. rep2 shows the failure is **not deterministic**: an independent sample at identical settings
resolved the ambiguity correctly.

## 4. Comparison with Qwen × 0010 and DeepSeek k=3 controlled pair
| cell | valid k | result |
|---|---|---|
| DeepSeek × 0009 (ambiguous) | 3 | 0/3 pass — 3/3 semantic-role failures (func/typ; func/slow ×2) |
| DeepSeek × 0010 (clear) | 3 | 3/3 pass (slow/func) |
| Qwen × 0010 (clear) | 1 | 1/1 pass (slow/func) |
| **Qwen × 0009 (ambiguous, streaming)** | **3** | **1/3 pass — 2/3 semantic-role failures (func/slow; func/typ)** |

The ambiguous cell is now populated for both models with valid transport: 0009 degrades both
(DeepSeek 0/3, Qwen 1/3) while its byte-identical-truth control 0010 is passed by both (4/4 pooled).
The clarity bundle remains the only visible difference between the pair.

## 5. Separated conclusions
**(a) Transport validity.** RESOLVED. Across the preflight + all three full episodes: 0 socket-inactivity
timeouts, 0 hard request deadlines, 0 incomplete streams, 0 malformed streams, 0 chat retries, while
delivering 60,411 / 76,686 / 76,663 reasoning tokens per episode — the exact token band that the
non-streaming transport censored in Phase-4V. The Phase-4V non-streaming measurements remain classified
transport-invalid; SSE streaming at `e1c36d2` is the resolution.

**(b) Qualitative mechanism.** The first valid Qwen episode on 0009 reproduced the same scenario/corner
semantic-axis binding failure previously observed in DeepSeek. This falsifies the earlier unsupported
inference that Qwen would necessarily solve 0009 and establishes that the failure mode exists across both
models. With k=3 the picture sharpens: the mode **recurs** (2/3) and covers **both** DeepSeek variants
(func/slow swap; func/typ with stale-decoy corner), while rep2's clean pass shows it is a sampling-level
instability of ambiguity resolution, not a deterministic inability.

**(c) Quantitative reliability.** 1/3 pass, 1 `overconfident_wrong` (the only episode that reached FINISH
and stated confidence was HIGH-confident and wrong). Because Qwen has only k=3 valid 0009 episodes, this
is a small replication sample: it establishes that the failure mode recurs, but it does not estimate a
success rate or establish stable failure. No population claim is made.

## 6. Sample-size statement
k=3 is a small replication sample rather than a precise population-level success-rate estimate. Rates
reported here are point observations with wide uncertainty; no population claim is made.

## 7. Artifact paths + SHA-256
Evidence root: `reports/evidence/p14_qwen_0009_stream_anchor/`
- `MANIFEST.json` — commands, config, frozen settings, repetition IDs, seed note, per-episode
  classifications. sha256 `0f0e5ca84f1a…`
- `trial1/` — 8 files (result.json `2d35e94e…`, agentlog.sanitized.json `93057595…`,
  flow_config.submitted.json `c56b0aec…`, evidence_manifest.json `76489630…`, stage2_summary.json
  `a57d909a…`, timing_report.rpt `a1ccb20e…`, preserved_artifacts.json `79dc7fdc…`,
  stream_diagnostics.json `3ef39b46…`)
- `rep2/` — 8 files (result.json `630224b8…`, agentlog.sanitized.json `f3a5049c…`,
  flow_config.submitted.json `3695d644…`, evidence_manifest.json `6bc20cf7…`, stage2_summary.json
  `1cd649cc…`, timing_report.rpt `819e4544…`, preserved_artifacts.json `5cdff294…`,
  stream_diagnostics.json `3dc87a61…`)
- `rep3/` — 8 files (result.json `cfc4a15c…`, agentlog.sanitized.json `ef0b305b…`,
  flow_config.submitted.json `39de0e27…`, evidence_manifest.json `1e0640b5…`, stage2_summary.json
  `da9f142a…`, timing_report.rpt `25a653dd…`, preserved_artifacts.json `9c9d55ff…`,
  stream_diagnostics.json `898cb4e0…`)
Full hashes in `SHA256SUMS`. Per episode, the evidence-chain copies (flow_config / timing_report /
evidence_manifest / stage2_summary) are byte-identical to the grader's recorded
`submitted_file_hashes` (verified chain of custody).

## Repetition protocol (compliance)
Same committed code `e1c36d2`; same task bytes, prompt, model id, temperature 0.7, max-actions 60,
episode timeout 1800 s, request inactivity timeout 120 s, hard deadline 300 s, max chat retries 1,
grading, streaming config. Predeclared repetition IDs trial1/rep2/rep3. **Seed note:** the deployed
provider/config exposes no controllable sampling seed (adding one would change the request shape vs
trial1), so every parameter is byte-identical and independence comes from temperature-0.7 sampling.
Infrastructure timeout / gateway error / worker failure ⇒ measurement-invalid, not a semantic failure;
**no measurement-invalid episode occurred in Phase-4V0/4V1** (3 runs → 3 valid). No DeepSeek; no other
tasks; no non-streaming fallback; task and action budget unaltered; stopped at 3 valid.

---
*Compliance: Qwen3.7-Max only. `.env` symlink removed after runs; no secrets/raw reasoning in any
artifact (worker strips reasoning at the IPC boundary; username → `<USER>` in archived agent logs;
hygiene programmatically asserted per file). Real PrimeTime grading (b04 shim). Not pushed.*
