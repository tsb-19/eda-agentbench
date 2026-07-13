# Synthetic p14 Tiny Probe — Workflow / Multi-Stage Evidence-Chain Handoff

**Tasks:** `workflow_handoff_0001` (evidence_steps=1, p13-style baseline) · `workflow_handoff_0002`
(evidence_steps=2, cross-stage digest chain), track `p14_workflow_handoff`.
**Git HEAD:** `1d71221 feat: add workflow handoff generator prototype`
**Date:** 2026-06-26
**Question:** Does the generated two-stage workflow_handoff family finally produce non-trivial mechanism
difficulty, or is it still saturated for protocol-compliant frontier agents?

| Parameter | Value |
|---|---|
| Models | Qwen3.7-Max, DeepSeek-V4-Pro, MiniMax-M3 (no Kimi, no GLM) |
| k | 3 (trial1 retained + trial2/3 fresh) |
| Episodes | 2 tasks × 3 models × 3 trials = **18** |
| Sampling | temperature 0.7, `--elicit-confidence`, concurrency 2, **max-actions 60**, timeout 600 s |
| Cost cap | ¥50 (raised from ¥40) · **actual ¥49.71** |
| Results | `runs/p14_tiny_probe/trial{1,2,3}` |

**Pre-launch gates (all green):** `scripts/check` 2904/2904; gate-3 real-PT re-validation (below);
trial1 confirmed valid (6 episodes, max-actions 60, correct p14 dispatch, no infra errors, **no
chain-bypass**); `.env` symlink-only (removed post-run); model config outside repo, no secrets, exactly
the 3 models; `max_tool_calls=60` not lowered; concurrency unchanged.

> **Note on the earlier halt:** the first attempt was stopped at k=1 because the projected 3-trial cost
> (~¥48) exceeded the original ¥40 cap. Cap raised to ¥50 per direction; trial1 retained as valid;
> trials 2–3 run fresh. A separate one-off launch that omitted `--max-actions` (defaulting to 12) was
> caught and killed before meaningful spend, then relaunched with `--max-actions 60`.

---

## Gate 3 — p14 real-tool re-validation on b04 PrimeTime

| State | 0001 (steps=1) | 0002 (steps=2) |
|---|---|---|
| golden / repair+ordered-chain | **1.00 / 1.00 PASS** | **1.00 / 1.00 PASS** |
| mutant | 0.25 fail | 0.25 fail |
| final-state-only | 0.25 fail | 0.25 fail |
| hand-edited stage-1 report | 0.25 fail | 0.25 fail |
| stage1-only (partial chain) | — | 0.25 fail |
| stage2-from-stale-stage1 | — | 0.25 fail |
| wrong-order (stage2→stage1) | — | 0.25 fail |

Determinism: stage1 nonce `ce80c718`, stage2 nonce `91ce214d` bit-identical. **Forgery invariant
(live):** 0 of 18 episodes passed without the full fresh evidence chain; no stage2-without-fresh-stage1
pass.

---

## A. Score / capability result vs. B. Protocol / reliability result

The probe deliberately separates **did it score 1.0 and complete the ordered chain** (capability) from
**did it finish cleanly with confidence** (protocol). The dominant protocol signature here is
`budget_exhausted` / empty-confidence appearing on episodes that **scored 1.0** — the work was done and
the chain verified, but no clean FINISH+CONFIDENCE was emitted. **Capability must be read from
`total_score`, not `protocol_status`.**

---

## 1. pass@1 / pass@k / pass^k by model

| Model | task | scores (k=3) | pass@1 | pass@k | pass^k |
|---|---|---|---|---|---|
| Qwen3.7-Max | 0001 | 1.0, 1.0, 1.0 | 1.000 | 1.0 | **1.00** |
| Qwen3.7-Max | **0002** | 1.0, 1.0, 1.0 | 1.000 | 1.0 | **1.00** |
| DeepSeek-V4-Pro | 0001 | 1.0, 0.25, 1.0 | 0.667 | 1.0 | 0.00 |
| DeepSeek-V4-Pro | **0002** | 1.0, 1.0, 1.0 | 1.000 | 1.0 | **1.00** |
| MiniMax-M3 | 0001 | 1.0, 0.25, 1.0 | 0.667 | 1.0 | 0.00 |
| MiniMax-M3 | **0002** | 0.25, 0.1, 0.25 | 0.000 | 0.0 | 0.00 |

**The load-bearing result:** Qwen **and** DeepSeek both achieve **pass^k=1.00 on the chain task
(0002)**, performing the full ordered stage1→stage2 evidence chain in all 3 trials.

## 2. Trust score by model

| Model | trust | note |
|---|---|---|
| Qwen3.7-Max | 0.70 | all passes, but confidence not cleanly emitted (budget_exhausted) → +0.7 not +1.0 |
| DeepSeek-V4-Pro | 0.55 | 5/6 pass; one `empty` 0-action response |
| MiniMax-M3 | −0.10 | nocommit + execution miss on 0002 |

## 3. Flip rate by model

| Model | 0001 | 0002 |
|---|---|---|
| Qwen3.7-Max | 0 | 0 |
| DeepSeek-V4-Pro | 1 (empty-response trial) | 0 |
| MiniMax-M3 | 1 (budget trial) | 0 (consistently fails) |

## 4. Overconfident-wrong count

**0 across all 18 episodes.** No model asserted high/medium confidence on a failing episode (failures
came with empty/abstained confidence).

## 5. Format compliance

Confidence was **largely not emitted** under the long two-stage trajectory: most passing episodes show
empty `confidence_decision` with `protocol_status=budget_exhausted`. One MiniMax 0002 episode shows
`confidence_format_ok=False`. This is a **format/compliance** finding, not a scoring finding.

## 6. Protocol failures

| Model | protocol_status counts (6 episodes) |
|---|---|
| Qwen3.7-Max | budget_exhausted ×6 (all on **scored-1.0 passes**) |
| DeepSeek-V4-Pro | ok ×1, empty ×1, budget_exhausted ×4 |
| MiniMax-M3 | ok ×1, nocommit ×1, budget_exhausted ×4 |

`budget_exhausted` here is the **metric artifact** documented since p11: the agent completed and scored,
but did not emit a clean FINISH+confidence within 60 actions, so the reliability layer tags it.

## 7. Per-task / per-trial success table

| Model | task | trial1 | trial2 | trial3 |
|---|---|---|---|---|
| Qwen3.7-Max | 0001 | 1.0 ✓ | 1.0 ✓ | 1.0 ✓ |
| Qwen3.7-Max | 0002 | 1.0 ✓ | 1.0 ✓ | 1.0 ✓ |
| DeepSeek-V4-Pro | 0001 | 1.0 ✓ | 0.25 ✗ (empty resp) | 1.0 ✓ |
| DeepSeek-V4-Pro | 0002 | 1.0 ✓ | 1.0 ✓ | 1.0 ✓ |
| MiniMax-M3 | 0001 | 1.0 ✓ | 0.25 ✗ (budget) | 1.0 ✓ |
| MiniMax-M3 | 0002 | 0.25 ✗ (nocommit) | 0.10 ✗ (signoff-fail) | 0.25 ✗ (stage1-only) |

## 8. Behavior taxonomy (per episode)

| Behavior | Qwen | DeepSeek | MiniMax |
|---|---|---|---|
| full repair + stage1 evidence (0001 pass) | 3/3 | 2/3 | 2/3 |
| full repair + **ordered stage1/stage2 chain** (0002 pass) | **3/3** | **3/3** | 0/3 |
| final-state-only, no evidence | 0 | 0 | 1 (0002 t1) |
| stage1-only partial chain | 0 | 0 | 1 (0002 t3) |
| stale stage1 reuse | 0 | 0 | 0 |
| wrong-order evidence | 0 | 0 | 0 |
| hand-edited evidence | 0 | 0 | 0 |
| wrong-package evidence | 0 | 0 | 0 |
| PT-green symptom suppression (masking) | 0 | 0 | 0 |
| forbidden edit | 0 | 0 | 0 |
| no-commit / protocol failure | 0 | 1 (empty) | 2 (nocommit, +budget flips) |

Every passing 0002 episode genuinely **ran both `run_evidence_stage1.sh` and `run_evidence_stage2.sh`**
and committed `flow_config.json`+`constraints.sdc` — verified in the agent action logs. **No pass
bypassed the chain.**

## 9. Qualitative failure signatures

- **Qwen / DeepSeek 0002:** correct, repeatable ordered chain. The only blemish is the `budget_exhausted`
  tag on scored-1.0 passes (no clean FINISH+confidence within 60 actions). Capability: solved.
- **DeepSeek 0001 trial2 — `empty`:** a 0-action empty response (gateway/decode hiccup), scored 0.25
  on signoff alone. Protocol/infra artifact, not capability; it solves 0001 in the other two trials.
- **MiniMax 0002 — the instructive set:** (t1) `nocommit` — finished=False, edited=[], signed off the
  stale island but produced no fresh evidence → 0.25; (t3) `stage1-only` partial chain — ran stage1,
  never stage2 → 0.25 (the oracle's `STAGE_CHAIN_OK`/`EVIDENCE_OK` both denied); (t2) a genuine
  **execution miss** — it edited both files and ran both stages but the final state failed sign-off
  (signoff=0.0), so every gated axis is 0 → 0.10. All three are **oracle-caught**, none is a forgery.
- **Most valuable p14-specific catch:** MiniMax t3 stage1-only is exactly the partial-chain failure the
  cross-stage coupling was built to reject, observed live.

## 10. Token / tool / wall / cost

| | tokens_in | tokens_out | est cost |
|---|---|---|---|
| trial1 | 1,892,133 | 105,672 | ¥16.00 |
| trial2 | 987,171 | 80,263 | ¥12.19 |
| trial3 | 1,978,220 | 156,546 | ¥21.52 |
| **total** | **4,857,524** | **342,481** | **¥49.71** (cap ¥50) |

Tool-calls ranged ~15–60/episode; the 60-action two-stage workflow drives high input-token accumulation
(cost is token-driven, hence the cap pressure). Per-episode cost detail in
`synthetic_p14_tiny_probe.json`.

## 11. Final interpretation

**Classification: SATURATED (capability) for top protocol-compliant agents; generator substrate
validated; pervasive `budget_exhausted`/empty-confidence protocol artifact.**

Per the interpretation rules: **Qwen AND DeepSeek both reach pass^k=1.00 on `workflow_handoff_0002` and
perform the ordered stage1→stage2 evidence chain in every trial** ⇒ the p14 generator-contract tasks
are **still saturated** for top agents. The cross-stage `upstream_evidence_digest` coupling did not
create a capability wall for them. **But the generator substrate is validated**: the contract holds live
(0/18 chain-bypass passes; partial-chain/stale/wrong-order/hand-edit/wrong-package all fail; golden=1.0
deterministic), and it cleanly discriminates a reliable chain-completer (Qwen) from a partial/nocommit
agent (MiniMax).

Secondary signals:
- **No early workflow-chain *capability* difficulty** for Qwen/DeepSeek — they plan and sequence the
  two stages reliably. The chain is the right *mechanism* but not yet a difficulty source at depth 2 on
  this tiny design.
- **MiniMax remains a reliability/protocol story** (nocommit, partial chain, one execution miss) — its
  0/3 on 0002 is *not* the chain being hard, it's MiniMax not completing the protocol.
- **The `budget_exhausted` artifact is now pervasive** (every Qwen pass): confidence elicitation rarely
  survives a 60-action two-stage trajectory. Worth a harness fix (e.g. a FINISH/confidence prompt that
  fires before the action budget is consumed) before any k=5 — otherwise trust/format metrics
  understate genuinely-correct agents.
- **Not invalid due to harness/infra:** dispatch correct, verdict present, oracle unambiguous, no
  forgery pass; the single `empty` response is an isolated gateway hiccup, not a systematic bug.

**Implication for the generator program:** depth-2 chains on the tiny `acc_stage` substrate validate the
mechanism but don't yet load capability for frontier agents. The next difficulty lever is **deeper /
wider chains or genuine cross-stage ambiguity** (Phase-4 spec §11), not more two-stage tasks — plus a
confidence/FINISH harness fix so the protocol artifact stops masking capability.
