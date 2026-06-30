# Synthetic p14 v4 — workflow_handoff_0005 DeepSeek calibrated follow-up (1800s)

**Status: COMPLETED k=2 at 1800s per-episode budget.** Calibrated follow-up to the 1200s stress probe,
DeepSeek-only, to distinguish "cannot solve" from "needs more time." Result: **mixed and significant** —
DeepSeek **solved trial1** (1737s, clean) but **confidently committed to a wrong decoy package in
trial2** (`overconfident_wrong`, deliberate finish at 1160s — NOT a timeout). This is the **first p14
task to elicit a clean confident-wrong failure**. 0005 is solvable by DeepSeek but unreliable, with a
confident-wrong failure mode on the multi-conflict decoys. Cost ¥16.87 / ¥30 cap.

## Required caveats (read first)

1. **k=2 only, DeepSeek-only, 1800s per-episode wall budget** (raised from 1200s). Both trials completed.
2. **DeepSeek CAN solve workflow_handoff_0005** (trial1: 1.0, golden-matching workspace, FINISH, high
   confidence, 1737s < 1800s) — so 0005 is **not a hard capability wall**.
3. **But DeepSeek also confidently fails** (trial2: 0.20, `overconfident_wrong=True`, FINISH with high
   confidence at 1160s — a deliberate stop on a wrong package, NOT a timeout/budget exhaustion).
4. **This is the first clean p14 v4 positive difficulty signal.** By the interpretation rule, a model
   that *commits to a locally-plausible-but-globally-wrong recovery* (report_A / wrong-corner package)
   with high confidence is exactly that signal. Trial2 is `overconfident_wrong`: high confidence on a
   0.20 (wrong) answer.
5. **Not a pure capability wall, and not saturated.** The two trials split (1 solve / 1 confident-wrong);
   pass^k = 0.50 over k=2. 0005 is at the frontier's edge: solvable but unreliable, with a confident-wrong
   mode elicited by the multi-conflict decoys — a real, if not absolute, difficulty signal.
6. **Trial2's exact wrong package is NOT byte-confirmed** (the driver does not log full command text; the
   eval workspace is cleaned post-grade). The classification rests on **strong inference**: netlist_v2-body
   `timing_report.rpt` (rules out the netlist_v1/report_B path), a flow_config hash that is **not** the
   golden global-authority hash (so wrong on scenario/corner or clock), high confidence, and a deliberate
   finish at 1160s — **consistent with a report_A-like locally plausible but globally wrong package**
   (netlist_v2 + wrong corner). This is phrased as "consistent with a report_A-like package," **not** as a
   byte-confirmed report_A package. The grader's forgery-resistant consumed-scenario/corner echeck denied
   EVIDENCE_OK. Stronger confirmation would require command-text logging or eval-workspace preservation.
7. **No oracle failure / no harness bug.** The acceptance matrix (validated at HEAD `310fbcf`, task
   unchanged) shows every local decoy recovery fails and only full global recovery passes; no shortcut
   passed in either trial.
8. **No infra/gateway failure** (auth OK; no HTTP 400; both trials finished within budget).
9. **pass^k over k=2 = 0.50** (1/2) — DeepSeek does NOT reliably solve 0005; flip across trials.
10. **k=2 is small** — the confident-wrong rate (1/2) is a point estimate with wide uncertainty; a larger
    k would sharpen it. But the signal (a clean `overconfident_wrong` on a decoy) is real and is the
    first of its kind in the p14 ladder.

## Question (calibrated)

Can DeepSeek-V4-Pro solve workflow_handoff_0005 with more time (1800s vs 1200s), or does the
multi-conflict decoy structure create a real capability/planning failure?

## Scope

- Worktree `/data1/tongsb/eda-agentbench-synthetic-phase0a`, branch `synthetic-phase0a`, HEAD `5678d11`.
- Task: `workflow_handoff_0005` only (resolved exactly; 0001–0004 excluded).
- Model: **DeepSeek-V4-Pro only** (filtered config, no Qwen/MiniMax/Kimi/GLM). k=2, temperature 0.7,
  `--elicit-confidence`, concurrency 1, max_tool_calls 60, **timeout 1800s**, cost cap ¥30.
- Fresh dirs `runs/p14_v4_0005_deepseek_calibrated/trial{1,2}`.

## Pre-launch gates (all passed)

- git clean; HEAD `5678d11`; `scripts/check` PASSED (2907/2907; p14 5/5).
- Task resolves to exactly `workflow_handoff_0005`.
- Runner supports 1800s (`--timeout` → `EDA_TIMEOUT`, passed to the agent subprocess deadline).
- Acceptance matrix (gate 5) holds — validated at HEAD `310fbcf`, 0005 byte-identical since.
- `.env` provisioned as symlink, git-ignored, removed after; DeepSeek-only config, no secrets. Auth ping OK (1.2s).

## A. Per-trial result

| trial | total | passed | protocol | FINISH | confidence | overconfident_wrong | wall (s) | acts | PT runs | cost (¥) | class |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **1.00** | ✓ | ok | yes | high | no | 1737 | 42 | 39 | 8.23 | **CLEAN SOLVE** (global recovery, golden chain) |
| 2 | **0.20** | ✗ | ok | yes | high | **yes** | 1160 | 50 | 45 | 8.64 | **CONFIDENT-WRONG** (committed to wrong netlist_v2/non-golden package) |

- **Trial1:** DeepSeek identified the global authority tuple (netlist_v2 / clk_main / slow / func),
  rejected the decoys, repaired `flow_config.json` to the global authority, reran stage1→stage2 in
  order, and produced a golden-matching evidence chain (workspace `timing_report.rpt` hash == solution).
  Clean solve in 1737s with FINISH + high confidence.
- **Trial2:** DeepSeek **finished at 1160s** (well under budget — this is NOT a timeout), declared
  **high confidence**, but scored **0.20**. Its workspace held a netlist_v2-body `timing_report.rpt`
  (engaging the correct design) and a `flow_config.json` whose hash is **not** the golden
  global-authority hash → the consumed package is wrong (**consistent with a report_A-like locally
  plausible but globally wrong package**: netlist_v2 + wrong scenario/corner). The grader's
  forgery-resistant consumed-scenario/corner echeck denied EVIDENCE_OK. This is a **clean wrong-answer
  with high confidence** (`overconfident_wrong`).

## B. Did DeepSeek follow a decoy? / global-authority diagnosis

| behavior | trial1 | trial2 |
|---|---|---|
| identified global authority (netlist_v2/clk_main/slow/func) | ✓ | ✗ (committed to wrong-corner netlist_v2 pkg) |
| repaired all lower sources to global authority | ✓ | ✗ |
| fresh ordered stage1→stage2 (valid global chain) | ✓ | ✗ (chain on wrong package; EVIDENCE_OK denied) |
| followed report_A (v2/test-typ) | ✗ | consistent (report_A-like: netlist_v2 + wrong corner) |
| followed report_B (v1/slow-func) | ✗ | ✗ (report body is netlist_v2, not v1) |
| followed evidence_C / prev_signoff | ✗ | not indicated |
| `overconfident_wrong` (high conf on wrong answer) | ✗ | **✓** |

(Trial2's exact package is inferred, not byte-confirmed — see caveat 6.)

## C. Failure classification (trial2)

Trial2 is **not** timeout/budget exhaustion (finished at 1160s < 1800s). It is:
- **wrong-authority / overconfident-wrong**: DeepSeek deliberately stopped on a locally-plausible,
  globally-wrong package (netlist_v2 + wrong corner) and declared high confidence → `overconfident_wrong`.
- NOT partial-chain (it produced a stage2), NOT hand-edited (anti-cheat clean), NOT infra (no error).

## D. Comparison with the 1200s stress run

| metric | 1200s stress (prior probe, trial1) | 1800s calibrated |
|---|---|---|
| DeepSeek outcome | 0.20, `budget_exhausted` (ran full 1200s) | trial1 **1.0 solve** (1737s); trial2 **0.20 overconfident_wrong** (1160s) |
| classification | indeterminate (ran out of time mid-work) | **mixed**: can-solve + confident-wrong |

Raising the wall from 1200s→1800s **resolved the indeterminacy**: DeepSeek CAN solve 0005 (trial1), but
also **confidently commits to a wrong decoy package** (trial2). The 1200s budget_exhaustion was partly a
time limit; the 1800s run reveals a genuine **confident-wrong failure mode** on the multi-conflict
decoys that more time alone does not eliminate.

## Metrics

- **capability pass^k (k=2)**: DeepSeek **0.50** (1/2). pass@1 = 1.0 (trial1); pass@k(any) = 1.0;
  pass^k(all) = 0.0.
- **overconfident_wrong**: **1** (trial2) — the first in the p14 ladder.
- **protocol_clean (FINISH + usable confidence)**: 2/2 (both finished with high confidence — but
  trial2's confidence was wrong).
- **flip rate**: 1 (trial1 pass → trial2 fail).
- **Infra/protocol-excluded episodes**: 0 (both are clean capability attempts, not infra/budget).

## Token / tool / wall / cost

| trial | tokens in | tokens out | tool calls | PT runs | wall (s) | cost (¥) |
|---|---|---|---|---|---|---|
| 1 (solve) | 530,488 | 77,700 | 42 | 39 | 1737 | 8.23 |
| 2 (confident-wrong) | 614,485 | 52,858 | 50 | 45 | 1160 | 8.64 |
| **total** | **1,144,973** | **130,558** | 92 | 84 | — | **16.87** |

## Final classification

**MIXED — first clean p14 v4 positive difficulty signal, but not a hard capability wall.**

- By the rule "if DeepSeek solves under 1800s → efficiency/exploration stress, not a clean wall":
  **trial1 satisfies this** — DeepSeek solves 0005 with more time. So 0005 is not an absolute wall.
- By the rule "if DeepSeek commits to a locally-plausible-but-globally-wrong recovery → first clean
  positive difficulty signal": **trial2 satisfies this** — DeepSeek `overconfident_wrong` on a wrong
  netlist_v2/non-golden package (consistent with report_A's wrong corner), finishing deliberately with
  high confidence.

**Synthesis:** workflow_handoff_0005 is the **first p14 task to elicit a clean confident-wrong failure**
(`overconfident_wrong`). DeepSeek is at the frontier's edge on this task — it CAN solve it, but does not
do so reliably, and on failure it **confidently commits to a decoy package rather than abstaining**. This
is a real, discriminating difficulty signal that the single-hazard p14 v1/v2/v3 tasks never produced
(those saturated cleanly). It is stronger than a pure budget/efficiency signal but weaker than a hard
wall. The multi-conflict partially-truthful-decoy structure is doing real work.

**Harness clean:** acceptance matrix green (**no forbidden-edit shortcut passed**, no shortcut passes, no
oracle failure); no harness bug; no infra failure. The `overconfident_wrong` is a genuine model behavior,
not an artifact.

## Open item / next step (your call)

- The right next step is **stronger evidence capture** (agent command-text logging or eval-workspace
  preservation) to byte-confirm the wrong-package failure mode — and **k=5 only if tighter statistics on
  the confident-wrong rate are needed**. It should **not** be more single-hazard p14 variants (v1/v2/v3
  are saturated; 0005 is where the signal is).
- k=2 is small (pass^k=0.50 ± wide uncertainty); a larger k at 1800s would sharpen the confident-wrong
  rate and confirm whether 0005 is a stable ~50% difficulty point for DeepSeek.
- Byte-confirming trial2's exact wrong package requires logging agent command text (a harness change) or
  preserving the eval workspace — currently neither is done by design.
- Qwen was not re-run here (it solved 0005 in the 1200s probe); a Qwen k≥3 at 1800s would show whether
  the confident-wrong mode is DeepSeek-specific or a frontier-wide effect of the multi-conflict decoys.

## What did not happen (per instructions)

No commit of this report (awaiting review). No push. No Qwen/MiniMax run. No `workflow_handoff_0001–0004`
run. No additional p14 tasks generated. No harness/code modifications. `.env` symlink removed; working
tree clean apart from these two report files.
