# Synthetic p14 v4 — workflow_handoff_0005 multi-conflict decoy capability probe

**Status: STOPPED at k=1 (cost cap).** trial1 = ¥14.90; k=2 projects ≈ ¥29.81 (only **¥0.19 under** the
¥30 cap — ~50% breach risk given token variance); k=3 ≈ ¥44.71 (over). Per the explicit stop condition
("cost projection exceeds ¥30") and cost discipline, trials 2–3 were **not** launched. What follows is a
**single-trial (k=1) capability read**; pass^k / flip over k≥3 are deferred.

## Required caveats (read first)

1. **k=1 only** — one trial per model (2 episodes), not the planned 6.
2. **Qwen3.7-Max SOLVES workflow_handoff_0005** (total_score 1.0, golden-matching workspace) — capability
   PASS in its single trial.
3. **DeepSeek-V4-Pro did NOT solve it in budget** — `budget_exhausted` at the 1200s wall (0.20). This is a
   **protocol/budget failure, NOT a clean decoy-follow capability failure**: its workspace held a
   golden-body (netlist_v2) `timing_report.rpt`, showing it was engaging the correct design, but it
   over-explored the decoys (33 PT runs) and never finalized a valid complete global chain.
4. **NOT a confirmed capability difficulty signal from k=1.** Qwen solves it; DeepSeek's miss is
   budget/protocol (capability indeterminate — it didn't finish). BUT 0005 is **materially harder than
   0004**: both models hit the ~1200s wall (Qwen 1182s, DeepSeek 1200s), where in the v3 probe both
   solved 0004 well under budget (Qwen 377s, DeepSeek 778s). This is an encouraging signal that the
   multi-conflict decoy structure stresses the frontier's exploration budget.
5. **No oracle failure / no harness bug.** The Phase-4H acceptance matrix (validated at this HEAD,
   ACCEPTANCE: PASS) shows every local decoy recovery fails and only full global recovery passes; no
   shortcut passed in this probe.
6. **No `.env` committed / no `runs/` committed / no secrets logged.** `.env` was a runtime symlink,
   removed after the run; working tree clean apart from these two report files.
7. **`overconfident_wrong = 0`.** DeepSeek abstained (empty confidence, budget_exhausted) — never a
   confident-wrong answer.
8. **pass^k / flip over k≥3 are NOT available** and are deliberately not reported as completed metrics.
9. **DeepSeek capability is indeterminate from this trial** (budget_exhausted, not a clean attempt); a
   k≥3 run (or a higher per-episode timeout) is needed to determine whether DeepSeek CAN solve 0005.
10. **A 2-trial top-up fits the remaining budget only razor-marginally** (~¥15.1 left, trial2 ~¥14.9) —
    offered as a follow-up decision, not run autonomously.

## Question

Does the p14 v4 multi-conflict partially-truthful-decoy hazard (`workflow_handoff_0005`) create a real
capability difficulty signal for top protocol-compliant agents, where p14 v1/v2/v3 were saturated?

## Scope

- Worktree `/data1/tongsb/eda-agentbench-synthetic-phase0a`, branch `synthetic-phase0a`, HEAD `310fbcf`.
- Task: `workflow_handoff_0005` only (resolved task list confirmed exactly that one; 0001–0004 excluded).
- Models: **Qwen3.7-Max, DeepSeek-V4-Pro** only (filtered 2-model config, no MiniMax/Kimi/GLM). k=3
  planned; **k=1 completed** (cost cap). temperature 0.7, `--elicit-confidence`, concurrency 2,
  max_tool_calls 60, timeout 1200s, cost cap ¥30.
- Fresh dir `runs/p14_v4_0005_capability_probe/trial1`.

## Pre-launch gates (all passed before any spend)

- `scripts/check` green: 2907/2907 structurally valid; `p14_workflow_handoff` 5/5.
- Task resolves to exactly `workflow_handoff_0005`.
- **b04 real-PT acceptance matrix (gate 3)** — validated at this HEAD during Phase-4H (ACCEPTANCE: PASS),
  committed 0005 byte-identical: golden global recovery 1.0; mutant 0.10; report_A (v2/test-typ) 0.20;
  report_B (v1/slow-func) 0.10; forged_manifest (v1 run claims v2) 0.10 (**forgery-resistant**);
  final_state_only 0.20; stage1_only 0.20; hand_edited 0.20; edit_manifest_down 0.0 (anti-cheat);
  forbidden_netlist 0.0 (anti-cheat). Every local decoy below pass; no shortcut passes.
- Env: no `.env` before; provisioned as a **symlink**, git-ignored, removed after. Model config
  out-of-repo, exactly 2 models, no secrets. Pre-flight auth ping: Qwen OK (3.6s), DeepSeek OK (1.2s).

## A. Capability result (k=1)

| model | valid trials | capability outcome | global-authority recovery | verdict |
|---|---|---|---|---|
| Qwen3.7-Max | 1/1 | **PASS (1.0)** | yes — golden-matching `timing_report.rpt`, valid chain | solves 0005 |
| DeepSeek-V4-Pro | 0 valid (budget_exhausted) | **indeterminate (0.20)** | partial — golden-body report (engaged netlist_v2) but no valid chain finalized | budget/protocol failure |

**Qwen** performed full global-authority recovery in its single trial: diagnosed the global tuple
(netlist_v2 / clk_main / slow / func), rejected the partially-truthful decoys, repaired `flow_config.json`
to the global authority (netlist + slow + func; clock clk_main already correct), reran stage1 then stage2,
and produced a golden-matching evidence chain (workspace `timing_report.rpt` hash == solution). It scored
**1.0 on every component**. (It hit the 1200s wall at ~1182s with no FINISH / empty confidence — a
protocol artifact, not a capability failure; total_score=1.0.)

**DeepSeek** did **not** solve 0005 within budget. It ran 33 PT commands over the full 1200s
(`budget_exhausted`) and its final workspace held a netlist_v2-body `timing_report.rpt` (engaging the
correct design) but **no valid complete global chain** (EVIDENCE_OK denied → 0.20). It did not cleanly
settle on a decoy package and declare done — it ran out of time mid-work. This is a budget/efficiency
failure, **not** a clean report_A/report_B/evidence_C decoy-follow.

## B. Protocol / reliability result (k=1)

| model | protocol_status | FINISH | confidence | signature |
|---|---|---|---|---|
| Qwen3.7-Max | budget_exhausted | no (deadline, ~1182s) | empty | solved at the budget edge; no FINISH/empty confidence |
| DeepSeek-V4-Pro | budget_exhausted | no (deadline, 1200s) | empty | over-explored decoys (33 PT runs); no valid chain finalized |

- Both models hit the **1200s wall** — 0005 is materially time/token-heavier than 0004 (v3: Qwen 377s,
  DeepSeek 778s, both solved).
- `overconfident_wrong`: **0** (DeepSeek abstained; never confident-wrong).
- No forbidden edits by either model. No infra/gateway failure (no HTTP 400; gateway healthy).

## Metrics (Phase-4F contract; k=1)

- **capability_pass** (total ≥ 0.5 AND not protocol/infra-excluded): Qwen 1/1; DeepSeek 0 valid trials
  (its 1 trial is `budget_exhausted` → protocol-excluded; capability indeterminate).
- **pass@1 / pass@k / pass^k** over valid capability trials: Qwen **1.00 / 1.00 / 1.00 (n=1)**;
  DeepSeek **n/a** (no valid trial).
- **protocol_clean** (FINISH + usable confidence): Qwen 0/1; DeepSeek 0/1.
- **flip rate**: n/a (k=1).
- **overconfident_wrong**: 0.
- **Infra/protocol-excluded episodes** (tracked, never capability): DeepSeek trial1 (budget_exhausted).
  (Qwen trial1 is a capability PASS with a protocol artifact — counted as capability, protocol reported
  separately.)

## Behavior matrix (per single trial)

| behavior | Qwen t1 | DeepSeek t1 |
|---|---|---|
| global-authority diagnosis (netlist_v2/clk_main/slow/func) | ✓ | partial (engaged netlist_v2) |
| repaired all lower sources to global authority | ✓ | ✗ (didn't finalize) |
| fresh ordered stage1→stage2 (valid global chain) | ✓ | ✗ |
| followed report_A (v2/test-typ) | ✗ | not cleanly (budget out mid-work) |
| followed report_B (v1/slow-func) | ✗ | not cleanly |
| followed evidence_C (syntactically valid, wrong pkg) | ✗ | not cleanly |
| trusted prev_signoff.log | ✗ | ✗ |
| final-state-only repair | ✗ | ✗ |
| stage1-only partial chain | ✗ | ✗ |
| stage2 from semantically wrong stage1 | ✗ | ✗ |
| hand-edited evidence | ✗ | ✗ |
| forbidden edit | ✗ | ✗ |
| budget_exhausted / no FINISH (protocol) | ✓ | ✓ |

## Qualitative failure signatures

- **Qwen3.7-Max:** *budget-edge solver.* Solved the multi-conflict hazard correctly (full global recovery,
  golden chain) but needed ~1182s / 54 actions / 638k tokens — right at the 1200s wall — and did not emit
  FINISH/confidence. Capability win, protocol artifact. The task is visibly heavier for Qwen than 0004
  (377s / 92k tokens in v3).
- **DeepSeek-V4-Pro:** *over-explore-then-budget-out.* Engaged the correct design (netlist_v2-body report
  in its workspace) but ran 33 PT commands across the full 1200s exploring the multi-conflict decoys and
  never converged on a valid complete global chain → 0.20, budget_exhausted. Contrast v3 (0004), where
  DeepSeek solved in 778s. The richer decoy structure measurably degrades DeepSeek's exploration
  efficiency. Not a clean decoy-follow, but a real budget/efficiency failure.

## Token / tool / wall / cost (trial1)

| model | tokens in | tokens out | tool calls (run) | wall (s) | cost (¥) |
|---|---|---|---|---|---|
| Qwen3.7-Max | 637,987 | 40,038 | 51 | 1182 | 9.10 |
| DeepSeek-V4-Pro | 357,785 | 63,041 | 33 | 1200 | 5.81 |
| **total** | **995,772** | **103,079** | 84 | — | **14.90** |

trial1 ¥14.90. k=2 projection ≈ ¥29.81 (¥0.19 under cap; ~50% breach risk); k=3 ≈ ¥44.71 (over cap).

## Final interpretation

**Not a confirmed capability difficulty signal from k=1 — but a credible budget/efficiency-stress
signal that warrants k≥3 with adequate budget.**

- By the stated rule, a clean difficulty signal requires a model to **fail/flip because it follows a
  decoy** (report_A/report_B/evidence_C/prev_signoff.log). That did **not** happen in trial1: Qwen solved
  it; DeepSeek budget-exhausted mid-work (engaging the correct design) rather than settling on a wrong
  package. So this is **not** the first clean p14 positive difficulty signal.
- However, 0005 is **materially harder** than 0004: **both** models hit the 1200s wall (Qwen 1182s,
  DeepSeek 1200s) vs v3 where both solved under budget (377s / 778s). DeepSeek, which solved 0004, fails
  to converge on 0005 in budget. This is a real **budget/exploration-efficiency degradation** on the
  multi-conflict decoy structure — an encouraging early signal, classified as **reliability/protocol**
  (not capability) until a clean k≥3 (or a higher timeout) shows whether DeepSeek *can* solve 0005.
- The non-pass is **protocol/budget** (DeepSeek budget_exhausted), classified separately from capability.
- **Harness clean:** acceptance matrix green at this HEAD (no shortcut passes, no oracle failure); no
  harness bug; gateway healthy (no infra failure).

## Next required experiment (calibrated follow-up — your call)

This probe is a **stress read, not a completed pass^k result**; it should **not** be cited as pass^k or
as a confirmed capability wall. The required follow-up, if pursued, is a **calibrated** experiment:

- **Scope:** DeepSeek-only **or** Qwen+DeepSeek on `workflow_handoff_0005`.
- **Budget:** an **explicit higher per-episode wall-time** (e.g. 1800s, vs the 1200s wall both models hit
  here) **and** an explicit higher cost cap (the current ¥30 cap admits only k=1 on this heavier task).
- **Goal:** distinguish **"cannot solve"** (a genuine capability gap) from **"needs more time"** (a
  budget/efficiency limit). DeepSeek's capability on 0005 is **indeterminate under the current 1200s
  budget** — it engaged the correct structure and produced evidence of work (golden-body netlist_v2
  report) but over-explored the decoys and did not finalize a valid global chain. Only a calibrated
  k≥3 run can say whether DeepSeek *can* solve 0005 or genuinely struggles.
- A 2-trial top-up under the **current** cap fits only razor-marginally (~¥15.1 left, trial2 ~¥14.9) and
  does **not** raise the wall-time that caused the budget_exhausted — so it would not resolve the
  indeterminacy. The follow-up must raise both the wall-time and the cap.

## What did not happen (per instructions)

No commit of this report (awaiting review). No push. No `workflow_handoff_0001–0004` run. No additional
p14 tasks generated. No harness/code modifications. No larger generator work. `.env` symlink removed;
working tree clean apart from these two report files.
