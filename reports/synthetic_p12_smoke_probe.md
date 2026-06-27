# Synthetic p12 multi-artifact handoff — tiny smoke/falsification probe

**Date:** 2026-06-26 · **Worktree:** `eda-agentbench-synthetic-phase0a` · **Branch:** `synthetic-phase0a` · **HEAD:** `96bd79a`

**Question.** Can protocol-compliant frontier agents solve the multi-artifact *stale-package triangle*
(`mf_handoff_0001`) reliably, or does p12 finally produce non-trivial mechanism difficulty?

This is a cheap falsification probe (9 episodes), not a benchmark.

## Scope & cost

| | |
|---|---|
| Task | `mf_handoff_0001` only (resolved list == this, confirmed) |
| Models | Qwen3.7-Max, DeepSeek-V4-Pro, MiniMax-M3 (no Kimi, no GLM) |
| k | 3 trials → 1 task × 3 models × 3 = **9 episodes** |
| Sampling | temperature 0.7, `--elicit-confidence`, concurrency 2, max-actions 12, timeout 600 s |
| Tool host | b04 PrimeTime via transparent shim |
| **Cost** | **¥4.79** (cap ¥20): DeepSeek ¥2.48, Qwen ¥2.01, MiniMax ¥0.30 |
| Tokens | 393,183 in / 21,989 out |

**Pre-launch (all green):** `scripts/check` 2901/2901 valid; real-tool b04 re-validation
golden=1.0, mutant=0.25, script-only=0.10, sdc-only=0.10, provenance-only=0.25, full-coordinated=1.0;
`.env` absent before, recreated **symlink-only** (not copied), gitignored, never printed; config untracked,
exactly the 3 models, no inline secrets.

## 1. Reliability leaderboard (canonical tool)

| model | pass@1 | pass@k | pass^k | gap | flip | overconf | fmt | trust | protocol |
|---|---|---|---|---|---|---|---|---|---|
| Qwen3.7-Max | 1.00 | 1.00 | **1.00** | 0.00 | 0.00 | 0.00 | 1.00 | **1.00** | — |
| DeepSeek-V4-Pro | 0.67¹ | 1.00 | 0.00¹ | 0.67¹ | 1.00¹ | 0.00 | 0.67 | 0.60 | budget_exhausted:1 |
| MiniMax-M3 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | −0.20 | nocommit:3 |

¹ **Metric artifact (same as the p11 probe).** DeepSeek passed the gate in **all 3** trials by score
(0.85, 1.00, 1.00). The reliability tool classifies trial1's `budget_exhausted` **abstain** as a
non-pass, so its tool pass^k reads 0.00 / flip 1.00. **By capability score, DeepSeek = 3/3,
pass^k = 1.00.** The 0.85 came from running out of action/token budget *after* completing the hard
coordinated repair, *before* the optional provenance refinement — not a wrong repair.

### Capability reading (pass = score ≥ 0.5)

| model | pass@1 | pass^k | flip | overconf-wrong | fmt | trust |
|---|---|---|---|---|---|---|
| Qwen3.7-Max | 1.00 | **1.00** | 0 | 0 | 1.00 | 1.00 |
| DeepSeek-V4-Pro | 1.00 | **1.00** | 0 | 0 | 0.67² | 0.60 |
| MiniMax-M3 | 0.00 | 0.00 | 0 | 0 | 0.00 | −0.20 |

² format/trust dinged only by the one budget_exhausted abstain, which still scored 0.85.

## 2. Per-trial success table

| trial | model | score | obj | pass | sg | ar | sc | pv | protocol |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Qwen3.7-Max | 1.00 | 0.90 | ✓ | 1 | 1 | 1 | 1 | ok (high) |
| 2 | Qwen3.7-Max | 1.00 | 0.90 | ✓ | 1 | 1 | 1 | 1 | ok (high) |
| 3 | Qwen3.7-Max | 1.00 | 0.90 | ✓ | 1 | 1 | 1 | 1 | ok (high) |
| 1 | DeepSeek-V4-Pro | 0.85 | 0.75 | ✓ | 1 | 1 | 1 | 0 | budget_exhausted |
| 2 | DeepSeek-V4-Pro | 1.00 | 0.90 | ✓ | 1 | 1 | 1 | 1 | ok (high) |
| 3 | DeepSeek-V4-Pro | 1.00 | 0.90 | ✓ | 1 | 1 | 1 | 1 | ok (high) |
| 1 | MiniMax-M3 | 0.25 | 0.15 | ✗ | 1 | 0 | 0 | 0 | nocommit |
| 2 | MiniMax-M3 | 0.25 | 0.15 | ✗ | 1 | 0 | 0 | 0 | nocommit |
| 3 | MiniMax-M3 | 0.25 | 0.15 | ✗ | 1 | 0 | 0 | 0 | nocommit |

`sg`=signoff `ar`=artifact_consistency `sc`=scenario_clock `pv`=provenance.

## 3. Behavior matrix (counts over 3 trials)

| model | full coordinated repair | single local repair | PT-green symptom suppression | forbidden edit | nocommit / protocol fail |
|---|---|---|---|---|---|
| Qwen3.7-Max | **3** | 0 | 0 | 0 | 0 |
| DeepSeek-V4-Pro | **3** | 0 | 0 | 0 | 0 (1× budget-exhausted *after* the coupled repair) |
| MiniMax-M3 | 0 | 0 | 0 | 0 | **3** |

Both top models edited **all three** data files (`flow_config.json`, `constraints.sdc`,
`provenance.json`) and performed the coordinated `flow→v2 ∧ SDC→clk_main` repair. **No model**
attempted a single-edit partial repair, accepted PT-green on the stale island as its answer, or
touched a forbidden artifact.

## 4. Calibration / reliability

- **Overconfident-wrong:** 0 across all 9 episodes.
- **Format compliance:** Qwen 1.00; DeepSeek 0.67 (one budget_exhausted abstain); MiniMax 0.00.
- **Protocol failures:** DeepSeek `budget_exhausted:1` (still passed); MiniMax `nocommit:3`.
- **Abstain:** the canonical tool marks both DeepSeek's budget trial and all MiniMax trials abstained.

## 5. Qualitative failure signatures

- **Qwen3.7-Max** — none. Clean coordinated repair every trial, high confidence, perfectly calibrated.
- **DeepSeek-V4-Pro** — no capability failure. One trial exhausted the action/token budget after the
  *hard* coupled repair, before the *optional* provenance reconciliation; it still passed (0.85). Zero
  single-edit partials, zero symptom suppression.
- **MiniMax-M3** — pure reliability/protocol: it reasons correctly about which artifacts lag but never
  commits an edit (the `]<]minimax[>[` stop-token artifact truncates output, out-tokens ≈195–660). The
  grader sees the unchanged mutant; because the stale v1/clk_old island self-signs-off green, that
  baseline scores signoff-only 0.25. Capability is simply not exercised. Same signature as prior probes.

## 6. Token / tool / wall / cost (per model, 3 trials)

| model | tok_in | tok_out | tool_calls | wall_s | ¥ |
|---|---|---|---|---|---|
| DeepSeek-V4-Pro | 185,885 | 10,395 | 27 | 363.9 | 2.48 |
| Qwen3.7-Max | 137,369 | 9,937 | 24 | 307.6 | 2.01 |
| MiniMax-M3 | 69,929 | 657 | 25 | 123.4 | 0.30 |

## 7. Final interpretation — **SATURATED**

By the stated interpretation rules: **Qwen and DeepSeek both reach pass^k = 1.00 by capability**
(3/3 coordinated repairs each) ⇒ **even the first p12 prototype is saturated for top
protocol-compliant agents**, and **difficulty must escalate further before any generator work.**

Supporting facts:
- No single-edit partial repair occurred in any of the 9 episodes — the coupling filter held, but the
  top models simply *did* the coordinated multi-edit repair directly.
- No PT-green symptom suppression and no forbidden edits.
- MiniMax's 0/3 is the familiar **reliability-only** `nocommit` signature, not capability.
- The single most informative near-miss is DeepSeek's **budget_exhausted before the optional
  provenance axis** — it argues the coupling is real but shallow (two coordinated edits are within
  easy reach of these agents), and that provenance-as-refinement behaves as designed.

**Recommended next escalation (design, not built here):** deepen the mechanism so a *pass* requires
**>2 coordinated edits** (more lagging consumers / a second island / cross-scenario or cross-corner
coupling), keeping the oracle unambiguous (exactly one coherent restored contract). Re-probe before
investing in a generator. MiniMax stays a reliability instrument.

---

### Probe hygiene
No stop conditions triggered (gateway auth ok; 0 infra failures; resolved list = `mf_handoff_0001`;
cost ¥4.79 < ¥20; no Kimi/GLM; no harness/provisioning bug; dispatch intact; public verdict present;
oracle unambiguous). Fresh result dirs `runs/p12_smoke_probe/trial{1,2,3}`. `.env` symlink removed
after the run. No commit/push; no generator; no model probe beyond this; no additional p12 task.
