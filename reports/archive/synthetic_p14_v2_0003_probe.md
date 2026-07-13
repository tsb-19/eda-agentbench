# Synthetic p14 v2 — workflow_handoff_0003 cross-source-conflict probe

**Status: STOPPED EARLY at k=1 (cost cap).** trial1 = ¥17.02; full k=3 ≈ ¥51 > ¥30 cap; even a
single additional trial would reach ≈¥34 > ¥30. Per the explicit stop condition ("cost projection
exceeds ¥30"), trials 2 and 3 were **not** launched. What follows is a single-trial (k=1) **capability**
read; the **reliability** axes (pass^k, flip-rate, trust) require the full k≥3 run and are deferred.

## Required caveats (read first)

This is a **k=1 smoke probe, NOT a completed reliability probe.**

1. **k=1 only** — exactly one trial per model (3 episodes total), not the planned 9.
2. **Trials 2–3 were not run** because the projected cost exceeded the approved ¥30 cap (k=2 ≈ ¥34,
   k=3 ≈ ¥51).
3. **pass^k / flip-rate / trust over k=3 are NOT available** and are not reported as completed metrics.
4. This is a **smoke probe**, not a completed reliability probe; do not cite it as one.
5. **Qwen and DeepSeek capability success is based on one trial each only** — not a repeated-run result.
6. **MiniMax's failure is classified as protocol/reliability** (malformed-command collapse), **not** an
   authority-diagnosis capability failure.
7. **No wrong-authority shortcut passed** (verified on real PT in the pre-launch acceptance matrix).
8. **No oracle failure occurred** — golden passes, every adversarial shortcut scores below the pass gate.
9. **No hidden leak / no `.env` committed / no `runs/` committed** — the `.env` symlink was removed after
   the run and the working tree is clean apart from these two report files.
10. **The next full k=3 probe requires either a higher cost cap or a cheaper setup** (the b04 forwarder's
    per-call ssh+rsync round trips make each episode ~20 min and ~¥5–6).

## Question

Does the p14 v2 cross-source-conflict / wrong-authority recovery task (`workflow_handoff_0003`) create a
real difficulty signal for top protocol-compliant agents, or is it still saturated?

## Scope

- Worktree `/data1/tongsb/eda-agentbench-synthetic-phase0a`, branch `synthetic-phase0a`, HEAD `a7c9267`.
- Task: `workflow_handoff_0003` only (resolved task list confirmed = exactly that one).
- Models: Qwen3.7-Max, DeepSeek-V4-Pro, MiniMax-M3 (no Kimi, no GLM).
- Planned k=3 (9 episodes); **completed k=1 (3 episodes)**.
- temperature 0.7, `--elicit-confidence`, concurrency 2, max_tool_calls 60, cost cap ¥30.

## Pre-launch gates (all passed before any spend)

- `scripts/check` green: 2905/2905 structurally valid; `p14_workflow_handoff` 3/3.
- Task resolves to exactly `workflow_handoff_0003`.
- **b04 real-PT acceptance matrix (the load-bearing gate):**

  | case | total (no-expl) | EVIDENCE_OK | verdict |
  |---|---|---|---|
  | golden | 0.90 (=1.0 live) | ✓ | pass |
  | golden re-run (determinism) | 0.90; nonces s1 `ce80c718` / s2 `91ce214d` match committed | ✓ | deterministic |
  | mutant (bare files) | 0.10 | ✗ | below pass |
  | wrong-authority (consume v1) | 0.00 | ✗ | below pass |
  | final-state-only (no chain) | 0.10 | ✗ | below pass |
  | stage1-only (no stage2) | 0.10 | ✗ | below pass |
  | stage2-from-stale-stage1 | 0.10 | ✗ | below pass |
  | hand-edited (semantic value change) | 0.10 | ✗ | below pass |
  | hand-edited (comment append only) | 0.90 | ✓ | *expected* — canonicalization strips volatile/comment lines from `report_digest`; not a leak |
  | trust-decoy (lying v2-claiming manifest) | 0.10 | ✗ | below pass |

  Golden scores 0.90 in this offline harness because the explanation component (0.10) is text-marker
  based in the live run and not submitted here; the live harness adds it → 1.0. Every adversarial
  shortcut lands ≤ 0.10 < 0.5 pass gate. No wrong-authority shortcut passes → no oracle failure.

- Env: no `.env` before; provisioned as a **symlink** (not a copy) to the main worktree `.env`,
  git-ignored, not shown in `git status`; removed after the run. Model config lives out-of-repo at
  `/data1/tongsb/eda-synthetic-local-configs/baseline_models_phase0d.json`, no embedded secrets, exactly
  the 3 allowed models. A stray identical `configs/baseline_models_phase0d.json` was found inside the
  repo and moved out (not committed).

## A. Capability result (k=1)

| model | total | passed | authority diagnosis | repair upward to v2 | fresh ordered s1→s2 | avoided decoy / stale v1 |
|---|---|---|---|---|---|---|
| Qwen3.7-Max | **1.0** | ✓ | yes | yes | yes | yes |
| DeepSeek-V4-Pro | **1.0** | ✓ | yes | yes | yes | yes |
| MiniMax-M3 | **0.2** | ✗ | no | no | no | n/a (never built a chain) |

Component breakdown (raw): Qwen and DeepSeek = 1.0 on **all** of signoff / final_state /
evidence_generation / stage_chain / provenance / authority_consistency / hazard_recovery / explanation.
MiniMax = signoff 1.0 + explanation 1.0 only; every gated axis 0 (no EVIDENCE_OK).

Both top agents identified `handoff_manifest.json` as authority, repaired `flow_config.json` to
`netlist_v2.v`, ran `run_evidence_stage1.sh` then `run_evidence_stage2.sh` in order (stage2 bound the
fresh stage1 digest `389cdd5f…`), and did **not** trust the lying v2-claiming `evidence_manifest.json`
decoy or the stale v1 / `prev_signoff.log`.

## B. Protocol / reliability result (k=1)

| model | protocol_status | FINISH | confidence | signature |
|---|---|---|---|---|
| Qwen3.7-Max | ok | yes | high (format ok) | clean — the only fully clean episode |
| DeepSeek-V4-Pro | budget_exhausted | no (deadline) | empty | correct recovery, then over-elaborate Tcl JSON-parse verification → hit 1177s wall deadline before FINISH; one out-of-workspace write correctly refused |
| MiniMax-M3 | budget_exhausted | no (action limit) | empty | 30/60 actions malformed (command-injection-like garbage, e.g. `run_public.sh 2>&1]<]minimax[>[`); never produced a valid chain |

- `overconfident_wrong`: 0 for all (MiniMax abstained/empty rather than confidently wrong).
- No forbidden edits by any model. DeepSeek's `write_refused` on `/tmp/debug.tcl` shows the
  out-of-workspace guard working.

## Metrics (k=1 — single trial)

Only a single trial ran, so the only available metric is the one-shot capability outcome:

- one-shot capability outcome: Qwen 1.0 (pass), DeepSeek 1.0 (pass), MiniMax 0.0 (fail).

**pass^k, flip-rate, and trust over k=3 are NOT available** and are deliberately not reported as
completed metrics — they require the full k≥3 reliability run, which was not performed (see cost-cap
stop). Do not read the single one-shot outcome as pass^k.

## Behavior matrix (per single trial)

| behavior | Qwen | DeepSeek | MiniMax |
|---|---|---|---|
| authority diagnosis | ✓ | ✓ | ✗ |
| lower-source repair upward | ✓ | ✓ | ✗ |
| wrong-authority repair | ✗ | ✗ | ✗ |
| trust-decoy / consume stale v1 | ✗ | ✗ | ✗ |
| final-state-only without evidence | ✗ | ✗ | ✗ |
| stage1-only partial chain | ✗ | ✗ | ✓ |
| stale stage1 reuse | ✗ | ✗ | ✗ |
| wrong-order evidence | ✗ | ✗ | ✗ |
| hand-edited evidence | ✗ | ✗ | ✗ |
| wrong-package evidence | ✗ | ✗ | ✗ |
| forbidden edit | ✗ | ✗ | ✗ |
| no-commit / protocol failure | ✗ | ✓ | ✓ |

## Qualitative failure signatures

- **DeepSeek-V4-Pro:** *success-then-overrun.* Solved the hazard correctly early, then burned the
  remaining budget on increasingly baroque Tcl experiments to re-parse `flow_config.json` (multiple
  `pt_shell -x`/regexp attempts, several rc≠0) and never emitted FINISH before the deadline. Capability
  win, reliability loss.
- **MiniMax-M3:** *malformed-command collapse.* Roughly half its actions were unparseable — strings with
  injected `]<]minimax[>[` markers producing `/bin/sh: Bad fd number`. It edited `flow_config.json` twice
  but never ran a coherent evidence chain. Pure protocol failure, not an authority-shortcut failure.

## Token / tool / wall / cost (trial1)

| model | tokens in | tokens out | tool calls | wall (s) |
|---|---|---|---|---|
| Qwen3.7-Max | 427,741 | 40,583 | 41 | 1138 |
| DeepSeek-V4-Pro | 690,287 | 60,736 | 42 | 1177 |
| MiniMax-M3 | 158,020 | 1,281 | 30 | 203 |
| **total** | 1,276,048 | 102,600 | 113 | — |

trial1 est cost **¥17.02**. k=3 projection ≈ **¥51** (cap ¥30).

## Final interpretation

**Saturated for top protocol-compliant agents (capability) + reliability-only signal (DeepSeek/MiniMax).**

- Both Qwen and DeepSeek reached capability `total_score=1.0` with authority-consistent recovery in their
  single trial. By the stated rule ("if Qwen/DeepSeek both perform authority-consistent recovery →
  conclude p14 v2 0003 is still saturated for top protocol-compliant agents, but the substrate is
  validated"), **p14 v2 0003 is not a capability-difficulty signal for the frontier.** The
  hazard-recovery substrate itself is validated: golden 1.0, all eight adversarial shortcuts below pass
  on real PT, determinism stable, no wrong-authority shortcut passes (no oracle failure).
- The non-passes are **reliability/protocol**, classified separately from capability: DeepSeek's
  no-FINISH/budget_exhausted and MiniMax's malformed-command collapse. This is consistent with the prior
  reliability finding that frontier non-passes on these synthetic handoff tracks are protocol, not
  capability.
- **Single-trial caveat:** this is a capability read only. Whether the difficulty is truly absent (vs.
  flips across trials) needs the full k≥3 run, which was deliberately not done to respect the ¥30 cap.
- **Harness clean:** dispatch did not regress, public verdict was present (`WORKFLOW_PUBLIC: …`), the
  evidence/provenance oracle behaved unambiguously, and no shortcut passed.

## What did not happen (per instructions)

No commit of this report (awaiting review). No push. No `workflow_handoff_0001`/`0002` run. No additional
p14 tasks generated. No larger generator work. `.env` symlink removed; working tree clean.
