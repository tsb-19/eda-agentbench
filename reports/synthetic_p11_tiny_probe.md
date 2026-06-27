# p11 FlowHandoff — tiny falsification probe

**Question.** Does the two-variant p11 FlowHandoff family produce any *mechanism* signal beyond
protocol reliability, or is it already saturated for protocol-compliant frontier agents?

**Scope.** Worktree `eda-agentbench-synthetic-phase0a`, branch `synthetic-phase0a`, HEAD includes
`c27e2a9` (Variant A) + `1e3b1eb` (Variant C). Tasks `fhandoff_0001` (Variant A: manifest→stale
netlist) + `fhandoff_0002` (Variant C: stale clock / unconstrained false-clean). Models
Qwen3.7-Max, DeepSeek-V4-Pro, MiniMax-M3. k=3, temperature 0.7, `--elicit-confidence`,
concurrency 2, agentic path on real PrimeTime (b04). 18 episodes. **Cost ¥4.67** (trials ¥1.51 /
¥1.88 / ¥1.28), tokens 468,544 in / 17,997 out. Fresh result dirs (`runs/p11_tiny_probe/trial{1,2,3}`);
no reuse of the invalid Phase-0D p10 runs.

Pre-launch gate (all green): `scripts/check` PASSED (2900/2900); task list resolved EXACTLY to
`fhandoff_0001,fhandoff_0002`; real-PT re-validation golden=1.000 / buggy below pass for both
(margins 0.700 / 0.900); `.env` absent before provisioning, symlinked at runtime and removed after,
never committed; subset config untracked, 3 approved models only, no secrets/Kimi/GLM; p11 evaluator
dispatch intact; public verdicts visible at offset 0. No stop-condition tripped.

---

## 1–6. Reliability / calibration by model (k=3)

> Capability is read from the actual ScoreResult totals (the ground truth). The aggregator's
> pass@k columns fold one DeepSeek **protocol** episode (`budget_exhausted`, abstained, still
> scored 1.0) into its capability math, which understates DeepSeek — see the note below the table.

| model | pass@1 (score) | pass^k | flip | overconf-wrong | fmt | protocol-failures | trust* | tok | tools | wall_s |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.7-Max     | 1.00 (6/6) | 1.00 | 0.00 | 0 | 1.00 | none | 1.00 | 13.8k | 4.5 | 44.0 |
| DeepSeek-V4-Pro | 1.00 (6/6) | 1.00 | 0.00 | 0 | ~0.83 | budget_exhausted:1 | ~1.00 | 35.9k | 7.0 | 70.1 |
| MiniMax-M3      | 0.50 (3/6) | — | 1.00 | 0 | 0.50 | nocommit:3 | 0.40 | 31.4k | 7.7 | 63.9 |

\* `reliability_report` (which counts the DeepSeek abstain as a miss) prints DeepSeek pass@1=0.83 /
pass^k=0.50 / flip=0.50 / trust=0.77 and MiniMax pass^k=0.00. Those are the raw tool numbers; the
**capability-correct** reading (protocol excluded, per standing rule) is DeepSeek 6/6.

- **pass@1 / pass^k:** Qwen 1.00/1.00; DeepSeek 1.00/1.00 (by score); MiniMax 0.50/0.00.
- **flip rate:** 0.00 Qwen, 0.00 DeepSeek (capability), 1.00 MiniMax (flips on both tasks across trials).
- **overconfident-wrong:** **0** for all three models.
- **format compliance:** Qwen 1.00; DeepSeek ~0.83 (one missing confidence tail on the
  budget-exhausted episode); MiniMax 0.50.
- **protocol failures:** Qwen 0; DeepSeek 1 `budget_exhausted` (task still solved → not a
  capability miss); MiniMax 3 `nocommit`.
- **trust:** 1.00 / ~1.00 (capability) / 0.40.

## 7. Per-task success matrix (P=pass; otherwise total score; trials t1 t2 t3)

| task | Qwen | DeepSeek | MiniMax |
|---|---|---|---|
| fhandoff_0001 (Variant A) | P P P (3/3) | P P P (3/3) | 0.85 0.85 0.30 (2/3) |
| fhandoff_0002 (Variant C) | P P P (3/3) | P P P (3/3) | 0.10 0.10 1.00 (1/3) |

## 8. Per-variant summary

- **Variant A — stale manifest / provenance (`fhandoff_0001`):** Qwen 3/3, DeepSeek 3/3, MiniMax
  2/3. MiniMax's two passes are **0.85** (handoff_consistency + signoff OK, but `manifest_correctness`=0
  — it restored the consumed netlist + provenance but left a manifest metadata field, e.g. revision,
  inconsistent; still above the gate). Its one fail (0.30) is `nocommit`.
- **Variant C — stale clock / unconstrained false-clean (`fhandoff_0002`):** Qwen 3/3, DeepSeek 3/3,
  MiniMax 1/3. MiniMax's two fails are `nocommit` (0.10: the shipped stale-clock SDC yields
  SIGNOFF_FAIL/no_paths); its one commit scored **1.00**.
- **No difficulty asymmetry between A and C for the protocol-compliant models** — Qwen and DeepSeek
  solve both variants on every trial. MiniMax's A-vs-C difference (2/3 vs 1/3) is driven by *where*
  its 3 random `nocommit`s landed, not by a capability gap (it scored 1.0 on C when it committed).

## 9. Failure classification

| episode | model | task | score | class |
|---|---|---|---|---|
| t1,t2 fhandoff_0002 | MiniMax | C | 0.10 | **protocol / nocommit** |
| t3 fhandoff_0001 | MiniMax | A | 0.30 | **protocol / nocommit** (shipped mutant graded → PT green but wrong handoff) |
| t2 fhandoff_0001 | DeepSeek | A | 1.00 | protocol event (`budget_exhausted`/abstain) but **task solved** — not a failure |

- **Capability / root-cause failures: 0.** No model that committed a clean edit produced a wrong fix.
- **Protocol / nocommit failures: 3** (all MiniMax).
- **Overconfident-wrong failures: 0.**
- **Harness / infra failures: 0** (dispatch intact, verdicts at offset 0, golden re-validated 1.0).

## 10. Qualitative failure signatures

- **Qwen3.7-Max:** clean on both variants. Reads spec + netlists/SDC, identifies the current
  revision (A) or the real clock port (C), edits the single allowed file, runs public feedback,
  FINISH with `CONFIDENCE: HIGH`. Lowest tokens/tools (13.8k / 4.5) — efficient.
- **DeepSeek-V4-Pro:** solves both variants every trial (score 1.0), but ~2× Qwen's tokens/tools
  (35.9k / 7.0) and one episode exhausted the action budget before emitting the confidence tail
  (still committed the correct fix). A verbosity/efficiency signal, not a capability one.
- **MiniMax-M3:** capability intact (0.85–1.0 whenever it commits, on both variants) but **3/6
  nocommit** — it abstains/never commits a clean edit on ~half its episodes, flipping pass↔fail
  across trials. Same reliability/protocol signature seen in the p10 probe. On Variant A its
  successful commits are *incomplete* (manifest metadata field left stale → 0.85 not 1.0).

## 11. Cost

Total **¥4.67** / 18 episodes (~¥0.26/ep), 468,544 in / 17,997 out tokens. Well under the ¥30 cap.

## 12. Final interpretation

**Saturated for protocol-compliant frontier agents, with a reliability-only signal from MiniMax.**

- **Qwen and DeepSeek solve BOTH variants on every trial** (pass^k=1.0 by capability score, flip 0,
  trust ~1.0, zero overconfident-wrong). Per the pre-registered rule, hand-authored p11 is **likely
  still saturated** for top protocol-compliant agents — cross-artifact provenance (A) and
  clock-binding/coverage (C) are both one-step-diagnosable for them. Neither variant is harder than
  the other for these models, so **Variant C is not a stronger difficulty mechanism than A** at this
  scale (it is a *distinct* mechanism, valuable for coverage/diversity, not for difficulty).
- **MiniMax provides reliability/protocol signal, not capability difficulty.** All 3 of its failures
  are `nocommit`; it solves both mechanisms when it commits. This reproduces the p10 finding on a
  qualitatively different, real-tool mechanism family — evidence the p11 substrate is a good
  **reliability/protocol substrate**, consistent with its intended role.
- **Most-valuable failure mode (PT green but fails handoff consistency)** *did* appear — MiniMax
  `fhandoff_0001` t3 scored 0.30 (signoff OK, handoff/manifest 0). But it was produced by `nocommit`
  (the shipped mutant graded), not by a deliberate wrong edit, so it is a protocol manifestation of
  the failure mode, not a reasoning error. No model deliberately masked or mis-fixed.

**Recommendation.** Do not expect difficulty from hand-authored p11 against frontier
protocol-compliant agents; keep p11 as a clean two-mechanism real-tool reliability/protocol
substrate. If a p11 generator is pursued later, its value is breadth (more variants/instances for
the reliability layer), not raw difficulty. The next difficulty lever remains multi-step /
multi-artifact composition rather than single-artifact handoff drift.
