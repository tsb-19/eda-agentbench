# p14 v7 0008 — implicit axis-binding capability probe (preserved, k=3)

**Status: COMPLETE (k=3, all 6 valid). Not committed (awaiting review).** HEAD `565f9c2`.

Preserved capability probe on `workflow_handoff_0008` (implicit_axis_binding): does **hiding `axis_schema.json`**
(while keeping the typed-binding oracle) restore the axis-binding difficulty that `workflow_handoff_0007` lost
by publishing the schema?

## Headline — 0008 DID NOT RESTORE AXIS-BINDING DIFFICULTY

Both models **inferred the implicit typed assignment correctly in all 6 episodes** (6/6 byte-confirmed
`netlist_v2/clk_main/slow/func`); **0 axis-binding / wrong-assignment failures**. **Qwen 3/3 pass; DeepSeek
2/3 pass.** The single DeepSeek non-pass (trial2, 0.20) is a **protocol/chain failure — stale `input_hashes`
because DeepSeek edited `flow_config.json` after generating evidence without re-running the generators —
NOT an axis-binding error** (the submitted assignment was correct and every typed-binding echeck passed).

Hiding the schema did **not** make the typed-axis inference harder for the frontier. The residual DeepSeek
signal is **reliability/protocol** (the capable-but-unreliable pattern from the reliability-calibration
thesis), **not a restored capability-difficulty signal.** Cost **¥54.73 / ¥60**.

## 1. Valid-trial count
**6/6** (Qwen 3, DeepSeek 3; no infra exclusions).

## 2. Capability pass@1 / pass@k / pass^k
| model | pass@1 | pass@k | pass^k | correct assignment | axis-binding failures |
|---|---|---|---|---|---|
| Qwen3.7-Max | 1.00 | 1.00 | 1.00 | 3/3 | 0 |
| DeepSeek-V4-Pro | 0.67 | 1.00 | 0.67 | **3/3** | **0** |

DeepSeek's pass^3 = 0.67 is from a **protocol/chain** failure, not an axis-binding failure.

## 3–5. Outcome / confidence / protocol counts
| metric | value |
|---|---|
| solved | 5 |
| non-solved | 1 (t2 DeepSeek — chain failure) |
| timeout | 0 |
| budget_exhausted (protocol) | 2 (t1 Qwen, t3 DeepSeek — both scored 1.0) |
| confident-wrong | 1 (t2 DeepSeek, high confidence) |
| clean FINISH + confidence | 4 |
| **overconfident_wrong** | **1** |
| **protocol_clean rate (FINISH)** | **4/6** (note: t2 DeepSeek FINISHed cleanly by protocol but scored 0.20) |

## 6–8. Per-trial detail
| trial | model | score | submitted assignment | FINISH | conf | tools | wall (s) | cost ¥ |
|---|---|---|---|---|---|---|---|---|
| 1 | Qwen3.7-Max | 1.0 | slow/func/clk_main ✓ | no | — | 60 | 1087 | 11.53 |
| 1 | DeepSeek-V4-Pro | 1.0 | slow/func/clk_main ✓ | yes | high | 36 | 1122 | 8.07 |
| 2 | Qwen3.7-Max | 1.0 | slow/func/clk_main ✓ | yes | high | 38 | 904 | 5.88 |
| 2 | DeepSeek-V4-Pro | **0.2** | slow/func/clk_main ✓ (**chain fail**) | yes | high | 51 | 1562 | 11.45 |
| 3 | Qwen3.7-Max | 1.0 | slow/func/clk_main ✓ | yes | high | 38 | 1147 | 7.50 |
| 3 | DeepSeek-V4-Pro | 1.0 | slow/func/clk_main ✓ | no | — | 58 | 1113 | 10.30 |

## 9. Preserved-artifact status (all 6 episodes)
All 6 preserved: manifest + exactly the 5 editable files + hashes + `component_scores` +
`affirmative_grader_markers` + `secrets_excluded=true`. No hidden truth / `axis_schema.json` / netlists /
library / `.env` / secrets in any preserved tree. (Preservation writes to the runner's temp runs_root;
collected post-trial into `runs/.../trialN/preserved_capture/`, gitignored.)

## 10. Byte-confirmed failure classification
**Only one non-pass: trial2 DeepSeek (score 0.20) — a PROTOCOL/CHAIN failure, NOT axis-binding.**

- **Submitted assignment:** `netlist_v2/clk_main/slow/func` — **CORRECT** (matches expected).
- **EVIDENCE_DETAIL** (re-run on the preserved submission): `input_hashes_match_ref=WRONG`,
  `run_nonce_matches_ref=WRONG` (stage1 + stage2). **Every other echeck passed**, including all typed-binding
  echecks (`typed_scenario_in_scenario_axis`, `typed_corner_in_corner_axis`, `typed_clock_identity`,
  authority, provenance, signoff, `stage2_binds_fresh_stage1`).
- **Root cause:** DeepSeek edited `flow_config.json` (its `_comment` differs from the golden) **after**
  generating the evidence, so the manifest's `input_hashes`/`run_nonce` no longer match the final submitted
  file. The evidence itself is a **genuine fresh PT regeneration** (report-body digest `389cdd5f065c` ==
  golden), not hand-edited.
- **Classification:** broken typed evidence chain (stale input_hashes from a post-generation edit) — a
  **reliability/protocol** failure, overconfident (high confidence). PT signoff was green (`signoff=1.0`);
  the rejection was the input-hash binding, not the typed-binding oracle.

The other 5 episodes solved cleanly with the correct assignment — no value-swap, PVT-substitution,
wrong-clock, typed-field-mismatch, decoy-following, broken-chain, final-state-only, stage-only,
hand-edited, forbidden-edit, timeout, or infra failure.

## 11–12. Inferred assignment / typed constraints
**6/6** inferred the unique typed assignment `[netlist_v2, clk_main, slow, func]` (both models 3/3). **6/6**
submitted assignments satisfy all typed-binding constraints (the 1 non-pass failed on `input_hashes`/nonce,
not on any typed-binding echeck).

## 13. Comparison to 0006 and 0007
| task | axis schema | Qwen | DeepSeek | result |
|---|---|---|---|---|
| **0006** (implicit tuple) | readable report labels | 8/8 | **6/8, 2 axis-binding failures** | **positive frontier split** |
| **0007** (published schema) | `axis_schema.json` shipped | 3/3 | 3/3, 0 axis-binding failures | **saturated** (vocabulary lookup) |
| **0008** (implicit schema) | schema hidden | 3/3 | **2/3** (1 protocol/chain fail), **3/3 correct assignment** | **NOT restored difficulty** |

**Verdict: 0008 is NOT stronger than 0007 on axis-binding capability.** On capability (axis-binding
inference) both 0007 and 0008 saturate — DeepSeek infers the correct typed assignment 3/3 in both. 0008's
1 DeepSeek non-pass is a reliability/protocol failure, not a capability failure.

## 14. Final interpretation — CAPABILITY SATURATED on axis-binding inference; residual is RELIABILITY/PROTOCOL
Per the interpretation rules: DeepSeek's single failure was **not** a value-swap, PVT-substitution,
wrong-clock, value-invention, or wrong-assignment — it was a stale-input-hash chain failure with a
**correct assignment**. So this is **not** a restored-axis-binding-difficulty signal. Both models inferred
the implicit typed assignment in 6/6 episodes; the typed-binding oracle never rejected a package on binding
grounds (only on the input-hash chain). **Hiding `axis_schema.json` did not restore the difficulty that
produced DeepSeek's 0006 failures.**

**Why 0008 didn't restore difficulty (two plausible reasons, not distinguishable at k=3):**
- 0008's reports use `op_point`/`mode` labels + PVT notation + a coverage fact + a partial glossary, which
  together give DeepSeek enough structure to bind correctly even without a published schema; OR
- small-sample variance — DeepSeek's 0006 axis-binding rate was ~25%, and 0 axis-binding failures in 3
  trials (P(0/3 | 25%) ≈ 0.42) is consistent with a residual rate this sample didn't surface.

**Secondary signal (reliability, not capability):** DeepSeek trial2 is a genuine reliability/protocol
failure — it FINISHed with **HIGH confidence** on a package whose evidence chain was broken (stale
input_hashes from a post-generation edit). This is the same "capable but unreliable / overconfident" pattern
from the reliability-calibration thesis (DeepSeek trust ≈0.88 best but still slips), **not** an axis-binding
capability gap. Qwen showed no capability or reliability failures (3/3, 0 overconfident_wrong).

**No oracle failure:** the 1 signoff-green non-pass was **correctly rejected** (0.20) by the input-hash
chain check; the oracle behaved exactly as designed. No local decoy shortcut or signoff-green-but-mis-typed
shortcut passed.

## Cost / cap note
Per-trial: trial1 ¥19.60, trial2 ¥17.33, trial3 ¥17.81. **Total ¥54.73 / ¥60 cap** (the cost guard projected
¥55.39 < 60 after trial2, so trial3 ran; no cap overrun, no user authorization needed).

## Caveats (honest)
1. **k=3 is small.** 0 axis-binding failures is consistent with a residual DeepSeek axis-binding rate
   (~25% on 0006; P(0/3 | 25%) ≈ 0.42). A larger k would sharpen whether 0008 truly saturates axis-binding.
2. **The 1 DeepSeek failure is byte-confirmed as protocol/chain (stale input_hashes), NOT axis-binding.**
   This is an honest negative result for the "0008 restores axis-binding difficulty" hypothesis.
3. **Task/family-specific**, not a universal model ranking. DeepSeek outperforms Qwen on other tracks.
4. PT runs/episode not parsed from the agentlog (format); tool_calls (36–60) and wall_sec (904–1562s) reported.

## Design lesson (schema visibility alone does NOT explain 0006)
The 0006→0007→0008 arc shows that **schema visibility alone does not explain the 0006 axis-binding split**:
- **0007** published the schema → saturated (binding became vocabulary lookup).
- **0008** hid the schema → **still saturated on axis-binding inference** (both models infer the implicit
  typed assignment 3/3; 0 axis-binding failures).
- Yet **0006** — also an implicit tuple, with report labels — produced DeepSeek's 2 axis-binding failures.

So the 0006 difficulty is **not** simply "schema published vs hidden." It likely depends on the **specific
implicit-tuple / report-label interaction** in 0006 (how the scenario/corner values were conveyed and
cross-checked there), not on schema visibility in general. **Future designs should study that specific
interaction** (what exactly about 0006's implicit tuple made DeepSeek mis-bind) rather than only toggling
schema publication/hiding — which 0007 and 0008 have now shown is insufficient to reproduce the split.

## Process compliance
Qwen3.7-Max + DeepSeek-V4-Pro only (no MiniMax/Kimi/GLM). `.env` symlinked to the gateway as runtime config
and **removed after**. No secrets printed; no shell tracing; no code modified. **Not committed, not pushed.**
Other worktrees untouched. `runs/` and `configs/baseline_models.json` gitignored and not staged.

## Next direction
- **Write a synthesis comparing 0006 / 0007 / 0008** — the three together form a clean ablation arc (0006
  positive split → 0007 saturated by publishing the schema → 0008 saturated by hiding it), and the open
  question is what specifically about 0006's implicit tuple/report-label interaction produced the split.
- **Do NOT run more 0008 trials immediately** — 0 axis-binding failures across k=3 establishes the
  qualitative result (implicit-axis inference is frontier-solvable); more trials only tighten an already-
  zero axis-binding rate.
- **Do NOT claim 0008 as a positive difficulty result.** It is an ablation showing that hiding the schema
  alone is insufficient to restore the 0006 difficulty.
- DeepSeek trial2 (stale input_hashes, overconfident) is a real **reliability/protocol** data point feeding
  the reliability-calibration layer, not a capability result.
- **Do not start 0009 without review.** A genuinely harder axis-binding task likely needs deeper ambiguity
  (axis membership recoverable only through tool-derived facts / multi-step provenance, not readable report
  labels at all) — and the 0006 interaction should be understood first.
