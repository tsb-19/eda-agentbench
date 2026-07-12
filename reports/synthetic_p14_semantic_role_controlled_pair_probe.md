# p14 semantic-role controlled-pair probe (Phase-4U, canary-gated) — DeepSeek k=3 + Qwen pilot

**Status: COMPLETE. Not committed (awaiting review).** HEAD `08d573e`. Cost **¥77.51 / ¥90**.

First **k=3 controlled reproduction test** of the `workflow_handoff_0006` mechanism: does the
**ambiguous** clarity bundle (`workflow_handoff_0009`) induce DeepSeek semantic-role binding failures,
and does the **clear-control** presentation (`workflow_handoff_0010`) remove them? Both tasks share the
identical hidden tuple `[netlist_v2, clk_main, slow, func]`, 294→1 uniqueness, byte-identical grader +
oracle + PrimeTime flow + evidence chain + scoring + mutant + decoy structure; they differ ONLY in the
visible clarity bundle.

## Headline — PRELIMINARY CONTROLLED MECHANISM SIGNAL on DeepSeek at k=3

- **DeepSeek × 0009 (ambiguous): 0/3 pass.** All 3 valid trials submitted a **wrong semantic-role
  binding** — varied: t1 `func/typ` (value-swap, the exact 0006 Failure A), t2/t3 `func/slow`
  (wrong-axis). All signoff-green but typed-binding rejected → **0.20**.
- **DeepSeek × 0010 (clear control): 3/3 pass.** All 3 submitted the correct `slow/func`.
- **Qwen × 0010: 1/1 pass** (fairness anchor on the clear control).
- **Qwen × 0009: 0 valid** — 2 infrastructure-invalid attempts (gateway `socket_timeout` on Qwen's
  read-only exploration before any repair edit). **Does not count** as a Qwen failure; 0009
  solvability is supported by Qwen×0010 PASS here + the 0006 reference (Qwen 8/8 on the analogous task).
- **DeepSeek × 0009 trial3 ran the FULL 60-action budget with no timeout** and still submitted
  `func/slow` → the wrong binding is a **genuine capability failure, not a timeout artifact**.

The 0006 semantic-role-binding difficulty **reproduced on 0009 and was removed by 0010's clarity bundle**.

## 1. Valid / infrastructure-invalid counts
7 valid episodes (DeepSeek 0009 ×3, DeepSeek 0010 ×3, Qwen 0010 ×1) + 2 infrastructure-invalid (Qwen 0009 ×2). All 9 preserved.

## 2. The three historical pre-probe stalls
Three earlier DeepSeek × 0009 attempts (pre-Phase-4U0b) stalled in the request path before any agent
action — infrastructure-invalid, excluded from k/pass/capability/protocol, not reused. Resolved by the
Phase-4U0b process-isolated hard deadline; this probe's canary completed with no hard-deadline stall.

## 3. Hard-deadline diagnostics
- **0 `hard_request_deadline` events** (the 300 s wall deadline never fired).
- 5 episodes had a **classified `socket_timeout`** at the 120 s op-timeout: 3 late (after work done:
  DS0009 t1/t2, DS0010 t3) + 2 early infra-invalid (Qwen 0009 t1/r2). All classified; **0 unclassified stalls.**
- Abandoned requests: killing the local worker on op-timeout abandons the local request; **remote
  billing/cancellation status is unknown** (flagged separately). 0 requests exceeded the 300 s hard wall.

## 4. Actual cost / cap
¥77.51 / ¥90. Per-episode in the JSON. No overrun. (Canary ¥11.36; DS0009 t2 ¥8.91 / t3 ¥15.84;
DS0010 t1 ¥10.92 / t2 ¥12.47 / t3 ¥3.46; Qwen 0010 ¥12.60; Qwen 0009 infra ¥0.80 + ¥1.15.)

## 5. Abandoned / deadline requests (separately)
- `hard_request_deadline` (wall 300 s): **0**.
- operation-timeout abandoned (op 120 s, both retries): 5 episodes (see §3). Remote billing status unknown.

## 6. Model/task matrix + 7. pass metrics + 8. protocol/budget counts
| model × task | valid | pass@1 | pass^k | semantic-role fails | submitted tuple(s) |
|---|---|---|---|---|---|
| DeepSeek × 0009 | 3 | 0.00 | 0.00 | **3** | func/typ; func/slow; func/slow |
| DeepSeek × 0010 | 3 | 1.00 | 1.00 | 0 | slow/func ×3 |
| Qwen × 0010 | 1 | 1.00 | 1.00 | 0 | slow/func |
| Qwen × 0009 | 0 (2 infra) | — | — | — | unmodified mutant (infra) |

- `protocol_clean` (clean FINISH + confidence): **1/9** (DeepSeek × 0010 t1, high confidence, correct).
- `budget_exhausted` / action-cap no-FINISH: 3 (DS0009 t3, DS0010 t2, Qwen 0010 hit 60 actions).
- late `socket_timeout` after work done: 3 (DS0009 t1/t2, DS0010 t3). early infra `socket_timeout`: 2 (Qwen 0009).
- **overconfident_wrong: 0** (no episode FINISHed with confidence on a wrong score; the one FINISH was a correct PASS).

## 9. Exact submitted tuple per valid episode (byte-confirmed from preserved)
| trial | submitted | expected | score |
|---|---|---|---|
| DS0009 t1 | `netlist_v2 / func / typ` | `netlist_v2 / slow / func` | 0.20 |
| DS0009 t2 | `netlist_v2 / func / slow` | slow/func | 0.20 |
| DS0009 t3 | `netlist_v2 / func / slow` | slow/func | 0.20 |
| DS0010 t1 | `netlist_v2 / slow / func` ✓ | slow/func | 1.00 |
| DS0010 t2 | `netlist_v2 / slow / func` ✓ | slow/func | 1.00 |
| DS0010 t3 | `netlist_v2 / slow / func` ✓ | slow/func | 1.00 |
| Qwen 0010 | `netlist_v2 / slow / func` ✓ | slow/func | 1.00 |

## 10. Preservation result
All 9 episodes: manifest + exactly the 5 editable files + hashes + `component_scores` + affirmative
markers + `secrets_excluded=true` + hidden/forbidden excluded. **Secret scan:** no API key / Bearer /
handoff_truth-content / grade_workflow-content / netlist / library in any of the 45 preserved editable
files. (`preserved_artifacts.json` lists excluded *filenames* like `grade_workflow.py` /
`handoff_truth.json` as a manifest of what was NOT copied — benign, not leaked content.)
**No preservation failure occurred** (all 9/9 preserved cleanly). **No oracle shortcut / forbidden-edit
shortcut passed** in any episode (every pass required the genuine golden tuple + a fresh real-PT evidence
chain; every non-pass was floored by the typed-binding oracle or was infrastructure-invalid).

## 11. Byte-confirmed classification of each non-pass
- **DS0009 t1** → *capability/semantic-role: scenario/corner **value swap*** (func∈corner in scenario
  slot, typ∈scenario in corner slot; signoff-green semantic mismatch) — the exact 0006 Failure A.
- **DS0009 t2** → *capability/semantic-role: **wrong semantic role / wrong-axis assignment*** (func in
  scenario slot, slow∈scenario in corner slot).
- **DS0009 t3** → *capability/semantic-role: wrong-axis assignment* (func/slow). Full-budget (60/60) run.
- **Qwen 0009 t1 / r2** → *infrastructure/excluded: operation timeout before a valid repair action*
  (gateway socket_timeout during read-only exploration; submitted the unmodified mutant; not a capability failure).

**Primary-classification counts (reported separately):** capability/semantic-role **3** (all DeepSeek × 0009);
evidence-chain reliability **0**; protocol/efficiency-only **0**; infrastructure/excluded **2** (Qwen × 0009).
(No evidence-chain-reliability or protocol-only primary failure occurred among the valid DeepSeek trials; the
no-FINISH / action-cap / late-socket_timeout notes on DeepSeek × 0009 are secondary signals layered on a
capability failure, not the primary class.)

## 12. DeepSeek 0009 vs 0010
Same hidden tuple/oracle/flow/chain/scoring/mutant/decoys; differ only in the clarity bundle. DeepSeek
binds the scenario/corner axes **wrong in 3/3** on the ambiguous 0009 (varied wrong values) and
**correct in 3/3** on the clear 0010. The controlled difference is reproduced at k=3.

## 13. Qwen fairness anchor
0010 PASS (clear control is solvable). 0009 **incompletely confirmed** — 2 infra-invalid gateway
stalls. Solvability of 0009 is supported by Qwen×0010 PASS + the 0006 reference (Qwen 8/8 on the
analogous implicit-tuple task), but a clean Qwen × 0009 success was not obtained in this probe.

## 14. Comparison to workflow_handoff_0006
0006: DeepSeek 6/8 with 2 axis-binding failures (func/typ; func + PVT + clk-alias); Qwen 8/8.
**0009 (ambiguous): DeepSeek 0/3, 3 semantic-role failures — reproduced + amplified.**
**0010 (clear): DeepSeek 3/3 PASS — difficulty removed.** First k=3 controlled reproduction of the
0006 mechanism.

## 15. Clarity-bundle causal caveat
This experiment tests the **bundled** clarity intervention (report-label ambiguity + glossary +
public_check_summary + spec wording + 2 extra visible files), **not label naming alone**. Isolating the
individual factors requires later 0009c/0009d ablations (not run). Additional caveats: Qwen × 0009
fairness incompletely confirmed (infra); late socket_timeouts ended 3 episodes without FINISH
(reliability notes, not confounds — the binding was committed before the timeout, and DS0009 t3's
full-budget run is definitive); k=3 is small with wide uncertainty.

## 16. Final interpretation
**"The clarity bundle produces a preliminary controlled difference in semantic-role binding."**
Supported on DeepSeek at k=3 (0009: 3/3 semantic-role failures; 0010: 3/3 PASS), with the fairness
caveat above. **Do not** claim label naming alone is causal, a universal model ranking, or that the
exact external cause of the Qwen0009 gateway stalls is proven. This is a **preliminary** result (k=3 is
small; rates are point estimates with wide uncertainty).

**Next steps (in order):**
1. **First obtain a valid Qwen × 0009 fairness anchor** (re-attempt; the 2 infra-invalid gateway stalls
   here must not stand in for a capability result). Do not treat 0009 solvability as directly established
   until a clean Qwen × 0009 success is observed.
2. **Then design a 2×2 factor-isolation study** (e.g., 0009c/0009d-style single-factor ablations:
   canonical-labels-but-no-anchors; ambiguous-labels-but-with-anchors) to test which component of the
   clarity bundle drives the effect — so the eventual claim can move from "the clarity bundle affects
   semantic-role binding" toward an isolated factor.
3. **Do not run more DeepSeek × 0009/0010 trials immediately** — the k=3 controlled difference is
   established for this round; further DeepSeek trials add little before the Qwen anchor and the
   factor-isolation design are in place.

---
*Compliance: Qwen3.7-Max + DeepSeek-V4-Pro only (no MiniMax/Kimi/GLM). `.env` symlinked as runtime
config (to be removed in teardown). No secrets printed; no shell tracing; no code modified. Real
PrimeTime grading (b04 shim). **Not committed, not pushed.** Stage-0 gate: golden=1.0 (both tasks),
294→1 uniqueness, no leak; acceptance matrix 12/12 on these bytes.*
