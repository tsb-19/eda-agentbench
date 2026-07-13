# Synthetic p14 v3 — workflow_handoff_0004 scenario/corner conflict capability probe

**Status: COMPLETED. k=3 valid trials for BOTH models.** A DeepSeek-only top-up (2 trials) replaced
the 2 DeepSeek episodes that a transient gateway outage (HTTP 400 "Invalid model name") had killed
early. Final result: **Qwen3.7-Max and DeepSeek-V4-Pro both capability-pass workflow_handoff_0004 with
pass^k = 1.00 over valid trials → saturated for top protocol-compliant agents.** Total cost **¥16.22 /
¥30 cap** (8 episodes). The gateway outage is documented below as **infra exclusions, not capability
failures**.

## Required caveats (read first)

1. **Both top agents SOLVE workflow_handoff_0004** with full slow/func authority-consistent recovery.
   Qwen 3/3, DeepSeek 3/3 (over valid trials). **No hazard-recovery difficulty signal — saturated.**
2. **DeepSeek's k=3 required a top-up.** A transient gateway HTTP 400 "Invalid model name" struck
   during the original trial2/trial3, killing both DeepSeek episodes *early* (no work done). Per the
   Phase-4F contract these are **infra exclusions, not capability failures**. Two DeepSeek-only
   top-up trials (gateway recovered) gave 2/2 valid passes, completing a clean DeepSeek k=3.
3. **The HTTP 400 is intermittent and still grazing.** It hit *late* (post-solve, on the confidence/
   final call) on DeepSeek trial1, DeepSeek topup_trial2, and Qwen trial3 — those episodes **did
   solve** (counted CAP-PASS) but show a no-FINISH / empty-confidence **protocol artifact**. It hit
   *early* (pre-solve) only on DeepSeek original trial2/trial3 → infra-excluded.
4. **No oracle failure / no harness bug.** Acceptance matrix re-run on real b04 PT: golden 1.0, every
   adversarial shortcut ≤ 0.20 < 0.5, anti-cheat cases 0.0, determinism nonces match committed. An
   apparent "1.0 with no work" on Qwen trial3 was investigated and is a **real solve** (workspace
   `timing_report.rpt` mutant→golden) with a late-infra protocol artifact.
5. **No wrong-corner shortcut passed**, no hand-edited evidence passed, no stage2 passed without a fresh
   slow/func stage1 (acceptance matrix).
6. **No `.env` committed / no `runs/` committed / no secrets logged.** `.env` was a runtime symlink,
   removed after each run; working tree clean apart from these two report files (untracked).
7. **`overconfident_wrong = 0`.** Every non-pass was an infra abstention (empty confidence) — never a
   confident-wrong answer.
8. **Capability vs protocol cleanly separated.** `capability_pass` = total ≥ 0.5 AND not infra-
   excluded; `protocol_clean` reported separately; `missing_confidence` ≠ capability failure.

## Question

Does the p14 v3 scenario/corner provenance hazard (`workflow_handoff_0004`) create a real difficulty
signal for top protocol-compliant agents, or is it still saturated?

## Scope

- Worktree `/data1/tongsb/eda-agentbench-synthetic-phase0a`, branch `synthetic-phase0a`, HEAD `d8f37da`.
- Task: `workflow_handoff_0004` only (resolved task list confirmed exactly that one; 0001/0002/0003 excluded).
- Models: **Qwen3.7-Max, DeepSeek-V4-Pro** only (filtered configs; no MiniMax/Kimi/GLM — the source
  config contains no GLM/Kimi at all). temperature 0.7, `--elicit-confidence`, max_tool_calls 60,
  timeout 1200s. Concurrency 2 (DeepSeek-only top-up = 1 episode/invocation).
- **8 episodes**: Qwen × 3 (trial1–3) + DeepSeek × 3 original (trial1–3) + DeepSeek × 2 top-up
  (deepseek_topup_trial2, deepseek_topup_trial3). Fresh dirs under `runs/p14_v3_0004_capability_probe/`.
- Total cap ¥30; spent **¥16.22**.

## Pre-launch gates (all passed before any model spend)

- `scripts/check` green: 2906/2906 structurally valid; `p14_workflow_handoff` 4/4.
- Task resolves to exactly `workflow_handoff_0004`.
- **b04 real-PT acceptance matrix (load-bearing gate)**, re-run via the live grading internals:

  | case | LIVE total | EVIDENCE_OK | verdict |
  |---|---|---|---|
  | golden (slow/func recovery) | **1.000** | ✓ | pass |
  | mutant_bare (lying manifest, stale) | 0.200 | ✗ | below pass |
  | wrong_corner (rerun chain under test/typ) | 0.200 | ✗ | below pass — **SIGNOFF_OK but authority-denied** |
  | final_state_only (fix flow_config, no rerun) | 0.200 | ✗ | below pass |
  | stage1_only (no stage2) | 0.200 | ✗ | below pass |
  | hand_edited (corrupt report digest) | 0.200 | ✗ | below pass |
  | stage2_wrong (corrupt upstream digest) | 0.200 | ✗ | below pass |
  | edit_manifest_down (forbidden authority edit) | **0.000** | — | **anti-cheat zeroed** |
  | forbidden_netlist (forbidden design edit) | **0.000** | — | **anti-cheat zeroed** |
  | determinism | ref nonces `c1187b12b93d2d40` / `1db140b08848397f` == committed | — | OK |

  Every adversarial shortcut ≤ 0.20 < 0.5. The wrong-corner case signs off (`SIGNOFF_OK=True`, "green
  PT under wrong corner") yet totals 0.20 — the scenario/corner authority echeck denies `EVIDENCE_OK`.
  No shortcut passes → no oracle failure. (Determinism nonces match the Phase-4G committed solution.)
- Env: `.env` provisioned as a **symlink** to the main-worktree gateway `.env`, git-ignored, not in
  `git status`; removed after each run. Model configs out-of-repo, exactly the selected model(s), no
  embedded secrets. Pre-flight auth pings OK for both models.

## A. Valid capability trials

| model | valid trials | pass@1 | pass@k (any) | pass^k (all) | flip |
|---|---|---|---|---|---|
| Qwen3.7-Max | 3/3 | **1.00** | **1.00** | **1.00** | 0 |
| DeepSeek-V4-Pro | 3/3 (trial1 + 2 top-ups) | **1.00** | **1.00** | **1.00** | 0 |

Every valid trial performed **full slow/func authority-consistent recovery**: identified slow/func as
authoritative scenario/corner (manifest/spec authority hierarchy), repaired `flow_config.json`
scenario→slow / corner→func **upward** (did not touch the already-correct netlist_v2/clk_main, did not
edit the forbidden manifest/spec downward), reran `stage1` then `stage2` in order (stage2 bound the
fresh stage1 digest), and did not trust `prev_corner_signoff.log` or the lying `evidence_manifest.json`
/ wrong-corner evidence. All 6 CAP-PASS episodes scored **1.0 on every component** ⇒ `EVIDENCE_OK ∧
SCENARIO_CORNER_AUTHORITY_OK ∧ HAZARD_RECOVERY_OK ∧ ordered stage_chain`. Verified per-episode via
workspace snapshots (`timing_report.rpt` mutant-hash → golden-hash for every CAP-PASS episode):

| episode | model | total | class | timing_report == golden? |
|---|---|---|---|---|
| trial1 | Qwen3.7-Max | 1.00 | CAP-PASS (clean) | yes |
| trial1 | DeepSeek-V4-Pro | 1.00 | CAP-PASS (late-infra) | yes |
| trial2 | Qwen3.7-Max | 1.00 | CAP-PASS (clean) | yes |
| trial3 | Qwen3.7-Max | 1.00 | CAP-PASS (late-infra) | yes |
| deepseek_topup_trial2 | DeepSeek-V4-Pro | 1.00 | CAP-PASS (late-infra) | yes |
| deepseek_topup_trial3 | DeepSeek-V4-Pro | 1.00 | CAP-PASS (clean, FINISH) | yes |

## B. Infra-excluded trials (NOT capability failures)

| episode | model | total | reason |
|---|---|---|---|
| trial2 | DeepSeek-V4-Pro | 0.20 | **early HTTP 400 "Invalid model name"** — 3 actions, only `flow_config.json` written, no evidence chain, `timing_report.rpt` stayed mutant |
| trial3 | DeepSeek-V4-Pro | 0.20 | **early HTTP 400 "Invalid model name"** — same; no work done |

Both are excluded from capability per the Phase-4F contract (infra artifacts never counted as
capability). They are retained as evidence of the transient gateway outage.

## C. Protocol artifacts (status, not capability failure when total_score=1.0)

| model | protocol_clean (status=ok) | finish_status | confidence_status |
|---|---|---|---|
| Qwen3.7-Max | **2/3** | trial1,2 FINISH; trial3 no-FINISH (late infra) | trial1,2 `high`; trial3 empty (late infra) |
| DeepSeek-V4-Pro (valid trials) | **1/3** | topup_trial3 FINISH; trial1 & topup_trial2 no-FINISH (late infra) | all empty (confidence elicitation killed by late HTTP 400 or unparseable) |

- A capability-pass episode that fails to FINISH / has empty confidence due to a **late** gateway error
  is a **protocol artifact, not a capability failure** (total_score=1.0, workspace solved).
- `overconfident_wrong`: **0** across all 8 episodes.
- No forbidden edits by any model (anti-cheat clean on all 8).

## Metrics (Phase-4F contract)

- **capability_pass** (total ≥ 0.5 AND not infra-excluded): Qwen 3/3; DeepSeek 3/3 valid.
- **pass@1 / pass@k / pass^k** on `capability_pass` over valid trials: **Qwen 1.00 / 1.00 / 1.00;
  DeepSeek 1.00 / 1.00 / 1.00.**
- **protocol_clean** (separate): Qwen 2/3; DeepSeek 1/3 (valid trials).
- **flip rate**: Qwen 0; DeepSeek 0.
- **overconfident_wrong**: 0.
- **Infra-excluded episodes** (tracked, never capability): DeepSeek trial2, trial3 (early HTTP 400).

## Behavior matrix (per episode; ✓ observed)

| behavior | Qwen t1 | Qwen t2 | Qwen t3 | DS t1 | DS topup2 | DS topup3 |
|---|---|---|---|---|---|---|
| scenario/corner authority diagnosis (slow/func) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| lower-source repair upward to slow/func | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| fresh ordered stage1→stage2 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| wrong-corner recovery attempt | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| trust-decoy / consume typ/test | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| final-state-only without evidence | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| stage1-only partial chain | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| stale wrong-corner reuse | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| wrong-order evidence | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| hand-edited evidence | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| wrong-package evidence | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| forbidden edit | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| no-commit / protocol failure (no FINISH) | ✗ | ✗ | ✓(late infra) | ✓(late infra) | ✓(late infra) | ✗ |

(DeepSeek original trial2/trial3 omitted — no work done, infra-killed.)

## Qualitative failure signatures

- **Qwen3.7-Max:** *clean, consistent solver.* 3/3 with correct authority recovery. trial1 (19 acts,
  377s) and trial2 (36 acts, 976s) finished cleanly with `high` confidence. trial3 was a 37s minimal
  solve (fix flow_config → stage1 → stage2, byte-golden report) then a late gateway 400 on the
  confidence call → protocol artifact only.
- **DeepSeek-V4-Pro:** *capable; protocol-fragile and infra-grazed, but reliable on capability.*
  All 3 valid trials solved the hazard correctly. trial1 (44 acts, 778s) over-explored then hit a late
  gateway error before FINISH; topup_trial2 (12 acts, 200s) solved efficiently then late-infra; the
  cleanest, topup_trial3 (19 acts, 220s), solved AND finished cleanly (protocol ok). The two original
  trial2/trial3 were cut down at 3 actions by the early gateway outage — pure infra.

## Token / tool / wall / cost

| episode | model | tokens in | tokens out | tool calls (run) | wall (s) | cost (¥) |
|---|---|---|---|---|---|---|
| trial1 | Qwen3.7-Max | 92,331 | 12,374 | 15 | 377 | 1.55 |
| trial1 | DeepSeek-V4-Pro | 518,926 | 28,429 | 26 | 778 | 6.91 |
| trial2 | Qwen3.7-Max | 338,247 | 36,297 | 33 | 976 | 5.37 |
| trial2 | DeepSeek-V4-Pro | 5,550 | 447 | 2 | 11 | 0.08 (infra) |
| trial3 | Qwen3.7-Max | 9,076 | 376 | 4 | 37 | 0.12 |
| trial3 | DeepSeek-V4-Pro | 5,496 | 693 | 2 | 16 | 0.08 (infra) |
| topup_trial2 | DeepSeek-V4-Pro | 52,561 | 4,643 | 7 | 200 | 0.74 |
| topup_trial3 | DeepSeek-V4-Pro | 104,217 | 4,921 | 12 | 220 | 1.37 |
| **total** | | **1,126,404** | **88,180** | 101 | — | **16.22** |

Original 6-episode run ¥14.11; DeepSeek top-up ¥2.11. (Far under cap — 0004's concise hazard lets the
agents solve in a fraction of the 0003 probe's tokens.)

## Final interpretation

**Saturated for top protocol-compliant agents (capability); substrate validated; non-passes are infra.**

- By the stated rule — "if Qwen and DeepSeek both perform slow/func authority-consistent recovery with
  pass^k=1.00 over valid trials → saturated" — **workflow_handoff_0004 is NOT a capability-difficulty
  signal for the frontier.** Both models are 3/3 over valid trials (pass^k=1.0, flip=0). The
  scenario/corner provenance hazard does not exceed what top agents already handle.
- The hazard-recovery **substrate is validated**: golden 1.0, all adversarial shortcuts ≤ 0.20 < 0.5 on
  real b04 PT (incl. wrong-corner "green PT" denied at 0.20), anti-cheat edits 0.0, determinism stable.
  No wrong-corner shortcut passes; no hand-edited/stale evidence passes; no stage2 without fresh
  slow/func stage1. No oracle failure.
- The non-passes are **infra** (transient gateway HTTP 400 "Invalid model name"), excluded from
  capability. The recurring no-FINISH/empty-confidence on late-infra episodes (DeepSeek trial1,
  DeepSeek topup_trial2, Qwen trial3) are **protocol artifacts**, not capability failures (all
  total_score=1.0 with solved workspaces).
- The apparent Qwen-trial3 "1.0 with no work" was investigated and is a **real solve** (golden-matching
  workspace) with a late-infra protocol artifact — **not** a harness bug.
- This extends the p14 negative-results ladder: p10→p14 v1/v2/**v3** are all saturated for top
  protocol-compliant agents; the discriminating signal on these synthetic handoff tracks remains
  **reliability/protocol** (no-FINISH, infra fragility), not hazard-recovery capability.

## Next direction — stronger p14 hazards

The single-conflict, single-authority-source hazards (p14 v1/v2/v3) are saturated. To pursue a real
frontier signal on this substrate, the next hazards should be **structurally harder** (no search
shortcut, deeper cross-checking required), not just renamed:

- **multi-conflict** — several independent handoff faults (netlist + clock + scenario/corner + SDC)
  simultaneously, so the agent must localize a *set* rather than one drift;
- **partially truthful decoys** — evidence files that are *mostly* correct (right netlist, right clock)
  but wrong in one field, defeating the "find the one lie" heuristic that solves 0003/0004;
- **scenario/corner + netlist/clock cross-conflict** — combine the v2 (netlist/clock) and v3
  (scenario/corner) conflict axes in one task, so authority is split across sources and the agent must
  reconcile a multi-source authority graph, not read one manifest;
- **misleading but internally consistent reports** — a wrong-corner report whose digest/nonce chain is
  *self-consistent* (so it passes a naive freshness check) but contradicts the manifest authority,
  forcing a cross-source consistency check rather than a within-report check;
- **dependency-repair planning** — a hazard whose repair has an ordered dependency (must fix A before B
  before the chain reruns cleanly), where wrong order fails, testing planning over diagnosis;
- **constraint-graph-style distractors** — many plausible-but-wrong authority sources (a constraint
  graph of conflicting sign-offs) so the agent must reason about which source dominates, not grep for
  the single manifest.

Each of these keeps the validated oracle/anti-cheat machinery (fresh-ordered-chain gate, forbidden
authority edits, scenario/corner authority pinned to the hidden re-run) and only raises the *diagnostic*
difficulty — the direction the [[single-localization-saturation]] and [[reliability-calibration-pivot]]
findings already point to.

## What did not happen (per instructions)

No commit of this report (awaiting review). No push. No `workflow_handoff_0001/0002/0003` run. No
additional p14 tasks generated. No harness/code modifications. No larger generator work. No Qwen or
MiniMax rerun in the top-up. `.env` symlink removed; working tree clean apart from these two report files.
