# p14 v4 0005 — DeepSeek preserved calibrated follow-up (1800s, k=2, preservation ON)

**Status: COMPLETE. Not committed (awaiting your review).** HEAD `f4ef140`.

Evidence-quality follow-up (not a statistical k=5 probe): run DeepSeek-only on
`workflow_handoff_0005` with the Phase-4I opt-in preservation enabled
(`EDA_BENCH_PRESERVE_FINAL_WORKSPACE=1`) so any wrong outcome can be **byte-confirmed**.
Result: **the preservation worked end-to-end and corrected a prior plausible-but-wrong
inference.** One clean solve, one byte-confirmed non-solve. Cost ¥16.13 / ¥30.

## Headline

- **Trial 1 — SOLVED, 1.0.** Final package = correct global authority; evidence chain
  byte-consistent across both stages.
- **Trial 2 — NOT solved, 0.20, byte-confirmed.** DeepSeek **diagnosed the global authority
  correctly** (final `flow_config` = `netlist_v2 / clk_main / slow / func`) but failed on
  **evidence-provenance consistency**: stage-1 evidence consumed `flow_config` hash `eb06ed2b`
  while stage-2 consumed `3a653363` — two different byte-versions of a semantically-correct
  `flow_config`. This is **not** decoy-following and **not** a wrong package.
- **Prior inference corrected.** The previous (un-preserved) calibrated trial-2 recorded the
  **same** `flow_config` hash `eb06ed2b` and was inferred to be "report_A-like, netlist_v2 +
  **wrong corner**, overconfident_wrong." Decoding that exact hash now shows the corner is
  actually **correct (`func`)** — the "wrong corner" guess was imprecise; the real failure is
  the broken chain. **This is exactly the value Phase-4I was built to deliver.**

## 1. Trial outcomes

| trial | outcome | total | passed | timed_out | protocol | conf | wall (s) | tool calls | PT-like runs | cost ¥ |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **SOLVED** | 1.00 | ✓ | no | ok | (n/a) | 1422 | 41 | 31 | 7.51 |
| 2 | **non-solve (abstain/protocol-incomplete)** | 0.20 | ✗ | no | budget_exhausted | "" | 1154 | 54 | 44 | 8.62 |

- Trial 2 is **NOT** timeout (1154s < 1800s), **NOT** overconfident_wrong (never FINISHed,
  no confidence — hit the 60-action cap → `budget_exhausted` / abstain), **NOT** infra/harness
  (anti-cheat clean, tools ran, grading completed).

## 2. Preserved-artifact status (both trials)

| check | trial 1 | trial 2 |
|---|---|---|
| `preserved_artifacts.json` present | ✓ | ✓ |
| editable files preserved (5) | ✓ | ✓ |
| sha256 hashes recorded | ✓ | ✓ |
| `secrets_excluded: true` | ✓ | ✓ |
| hidden truth / forbidden / secrets excluded | ✓ | ✓ |

Preserved set (declared editable only): `flow_config.json`, `constraints.sdc`,
`timing_report.rpt`, `evidence_manifest.json`, `stage2_summary.json`. Scan found **no**
blacklisted filename (handoff_truth, grade_workflow, netlists, tiny.lib/db, report_A/B,
evidence_C, prev_signoff, .env, model config) and **no** `HIDDEN_TRUTH/API_KEY/Bearer/BASE_URL`
string in either preserved tree. Captured copies live under
`runs/p14_v4_0005_deepseek_preserved/trial{1,2}/preserved_capture/` (runs/ is gitignored).

## 3. Byte-confirmation of the trial-2 failure

Final submitted `flow_config.json` (hash `eb06ed2b`) decodes to:
`{netlist: netlist_v2.v, clock: clk_main, scenario: slow, corner: func}` — **the correct global
authority**. Yet the chain is internally inconsistent:

| artifact | consumed `flow_config` hash |
|---|---|
| `evidence_manifest.json` (stage 1) | `eb06ed2b` (= final submitted file) |
| `stage2_summary.json` (stage 2) | `3a653363` (a different, golden-byte version) |

Grader components: `signoff=1.0`, `explanation=1.0`, but `final_state=0`, `evidence_generation=0`,
`stage_chain=0`, `provenance=0`, `authority_consistency=0`, `hazard_recovery=0` → **0.20**.

**Classification:** did **not** follow report_A / report_B / evidence_C / prev_signoff. The model
got the authority diagnosis right and then failed the **two-stage provenance discipline** — it
edited `flow_config` and did not re-run both ordered stages atomically against one byte-consistent
file (stage1=`eb06ed2b`, stage2=`3a653363`), running out of action budget before reconciling.

## 4. The solve (trial 1)

- time-to-solve 1422s; 41 tool calls; 31 PT-like runs.
- Final `flow_config` = correct authority; **chain byte-consistent**: both stages consumed
  `flow_config` hash `be471dcb`. `timing_report.rpt` hash `819e4544` matches the golden netlist_v2
  body. (flow_config bytes differ from the prior-recorded golden `3a653363` only in
  comment/formatting; the grader is semantic, so 1.0 is correct.)

## 5. Comparison with the prior 1800s calibrated follow-up

| | prior (un-preserved) | now (preserved) |
|---|---|---|
| trials | k=2 | k=2 |
| solve | 1 (1.0) | 1 (1.0) |
| non-solve | 1 (0.20), inferred **overconfident_wrong / report_A-like wrong corner** | 1 (0.20), **abstain/protocol-incomplete**, byte-confirmed **broken chain, correct corner** |
| confident-wrong recurred? | — | **No** — this episode never FINISHed / no confidence |
| evidence quality | inference only | **byte-confirmed; prior inference corrected** |

The clean confident-wrong mode (FINISH + high confidence on a wrong answer) **did not recur** in
these two trials. What recurred is the wrong final state — and preservation shows its true cause.

## 6. Final interpretation

- **Solved with more time** (trial 1, reproducibly clean).
- The non-solve is **not** timeout-limited and **not** decoy-following: DeepSeek diagnosed the
  global authority correctly. The discriminating difficulty of 0005 in this episode is the
  **evidence-provenance discipline** — regenerating both ordered stages against one byte-consistent
  `flow_config`. This is a real, byte-confirmed difficulty signal distinct from "followed a decoy."
- Episode 2 is **protocol-incomplete (budget_exhausted / abstain)**, not overconfident_wrong.

## Process going forward (methodology)

- **Preservation is now REQUIRED for any confident-wrong / wrong-package classification.** This
  episode is the proof: an un-preserved inference ("report_A-like wrong corner") was wrong, and only
  the preserved final submitted files + hashes could establish the true failure (broken
  evidence-provenance chain, correct corner). Future p14 reports must not classify a wrong outcome
  as decoy-following / wrong-package / confident-wrong **without** preserved-artifact byte-confirmation;
  inference-only labels should be marked as such.
- **Next hazard-design insight:** the discriminating axis is **atomic multi-stage evidence
  regeneration** (both ordered stages produced from one byte-consistent set of semantically-correct
  files), not only decoy rejection. Future hazards should stress provenance/regeneration discipline,
  not just authority selection.

## 7. Limitations / open items

1. **k=2 only** — not a statistical reproduction of the confident-wrong rate; that mode did not
   recur here.
2. **Phase-4I `grader_markers` is misleading and should be fixed (future Phase-4J).** It is
   presence-only substring matching against the combined log: trial-2's manifest listed
   `FINAL_STATE_OK / PROVENANCE_OK / SCENARIO_CORNER_AUTHORITY_OK` as "present" while `score.json`
   shows those components = 0.0. **`score.json` is authoritative**; the markers are a coarse pointer
   only. Recommend matching affirmative marker lines exactly, or dropping `grader_markers` in favor
   of the `score.json` component map. **Cosmetic — no scoring impact.**
3. **Action-trace richness unchanged** (sparse command fields), as accepted for this phase.

## Process compliance

DeepSeek-V4-Pro only (no Qwen/MiniMax/Kimi/GLM). `.env` symlink provisioned as runtime config and
**removed after**. No secrets printed; no shell tracing. **Not committed, not pushed.** Other
worktrees untouched. `runs/` and `configs/baseline_models.json` are gitignored and not staged.
