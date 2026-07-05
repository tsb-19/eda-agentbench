# p14 v5 0006 — Qwen k=5 preserved robustness probe

**Status: COMPLETE (k=5, all valid). Not committed (awaiting review).** HEAD `4243807`.

Robustness check: verify Qwen3.7-Max robustly saturates `workflow_handoff_0006`, strengthening the
Qwen-vs-DeepSeek frontier split (Qwen robustly solves; DeepSeek reproducibly fails).

## Headline — QWEN ROBUSTLY SATURATES 0006; FRONTIER-MODEL SPLIT STRENGTHENED

Qwen solved **5/5 (pass^5 = 1.0)**; combined with the original k=3 (3/3), Qwen is **8/8 on 0006 with ZERO
wrong assignments**. This contrasts sharply with **DeepSeek 6/8 (2 byte-confirmed wrong assignments)**.
The constraint-graph task **discriminates between frontier models**: Qwen robustly solves it, DeepSeek
reproducibly fails. Cost ¥49.71 / ¥60.

## 1. Valid-trial count
**5/5** (no infra exclusions).

## 2. Capability metrics (Qwen3.7-Max)
- **pass@1 = 1.0**, **pass@k = 1.0**, **pass^5 = 1.0**.
- Combined with k=3: **8/8 = 100%**, 0 wrong assignments.

## 3–5. Outcome / confidence / protocol counts

| metric | value |
|---|---|
| solved | 5 |
| non-solved | 0 |
| timeout | 0 |
| budget_exhausted (protocol) | 2 (t2, t5 — both still scored 1.0) |
| confident-wrong | 0 |
| abstain / protocol-incomplete | 2 |
| clean FINISH + confidence | 3 |
| **overconfident_wrong** | **0** |
| **protocol_clean rate** | **3/5** |

## 6–8. Per-trial detail

| trial | score | inferred assignment | FINISH | conf | tools | PT runs | wall (s) | cost ¥ |
|---|---|---|---|---|---|---|---|---|
| 1 | **1.0** | slow/func ✓ | yes | high | 55 | 37 | 1209 | 10.18 |
| 2 | **1.0** | slow/func ✓ | no | — | 60 | 39 | 1474 | 12.17 |
| 3 | **1.0** | slow/func ✓ | yes | high | 29 | 22 | 711 | 4.00 |
| 4 | **1.0** | slow/func ✓ | yes | high | 49 | 40 | 1015 | 10.31 |
| 5 | **1.0** | slow/func ✓ | no | — | 59 | 37 | 1786 | 13.05 |

## 9. Preserved-artifact status (all 5 trials)
| check | all 5 |
|---|---|
| `preserved_artifacts.json` present | ✓ |
| editable files preserved (5) | ✓ |
| hashes recorded | ✓ |
| `component_scores` (authoritative) | ✓ |
| `affirmative_grader_markers` | ✓ |
| `secrets_excluded: true` | ✓ |
| hidden truth / forbidden / secrets excluded | ✓ |

Security scan: no forbidden filename, no `HIDDEN_TRUTH`/`API_KEY`/`BASE_URL`/`Bearer` in any preserved tree.

## 10. Byte-confirmed failure classification
**N/A — there were NO non-passes.** All 5 trials solved with the correct `[netlist_v2, clk_main, slow, func]`
assignment. No wrong-assignment, decoy-following, broken-chain, final-state-only, stage-only, hand-edited,
forbidden-edit, timeout, or infra failure occurred.

## 11. Did Qwen infer the unique global assignment?
**5/5** inferred `[netlist_v2, clk_main, slow, func]`. Combined with k=3: **8/8 correct.**

## 12. Did Qwen satisfy all constraints C1–C8?
**5/5** satisfied all of C1–C8. Combined with k=3: **8/8 all-satisfied.**

## 13. Comparison

| model | 0006 result | wrong assignments |
|---|---|---|
| Qwen k=3 (original) | 3/3 pass | 0 |
| **Qwen k=5 (this)** | **5/5 pass** | **0** |
| **Qwen combined** | **8/8 = 100%** | **0 — robust saturation** |
| DeepSeek combined (k=3 + k=5) | 6/8 = 75% | **2 byte-confirmed axis-binding errors** |

**The frontier-model split holds and is strengthened:** Qwen robustly solves 0006 (8/8); DeepSeek
reproducibly fails (6/8, 2 wrong assignments). The constraint-graph task discriminates between frontier
models.

## 14. Final interpretation
**QWEN ROBUSTLY SATURATES 0006; FRONTIER-MODEL SPLIT STRENGTHENED.**

Per the interpretation rule: if Qwen solves all 5 valid trials, classify Qwen as robustly saturated and
strengthen the Qwen-vs-DeepSeek split. Qwen solved 5/5 (pass^5 = 1.0), all with the correct unique
assignment; combined 8/8 with 0 wrong assignments — vs DeepSeek 6/8 with 2 wrong assignments. 0006
discriminates between frontier models.

**Secondary signal (separate from capability):** 0006 carries mild efficiency/protocol stress for Qwen too
— 2/5 passes (t2, t5) hit the 60-action cap without a clean FINISH (`budget_exhausted`), but both still
scored 1.0. Unlike DeepSeek, Qwen's residual signal is **protocol-only, never capability** (0 wrong
assignments across 8 trials).

## Caveats
1. **Qwen n=8 combined** (k=3 + k=5, two separate runs). 8/8 is strong but finite; a wrong-assignment tail
   cannot be fully excluded, though none was observed.
2. **Qwen's 2/5 budget_exhausted** episodes show 0006 is also a mild efficiency/protocol stress task for
   Qwen (like 0005), but unlike DeepSeek, Qwen never produced a wrong assignment — its residual signal is
   protocol-only, never capability.
3. **Only one constraint-graph task (0006) exists**; the Qwen-saturates / DeepSeek-fails split is for this
   single task. A small 0006-style family would test whether the split generalizes.
4. **Scope limitation (do not over-claim):** the result shows Qwen > DeepSeek **on this task/family only**.
   It does **not** mean Qwen is universally stronger than DeepSeek — DeepSeek outperforms Qwen on other
   tracks in this benchmark's history. The claim is specifically: on `workflow_handoff_0006` (constraint-
   graph multi-source recovery), Qwen robustly saturates and DeepSeek reproducibly fails.
5. Cost ¥49.71 / ¥60, all 5 completed under cap.

## Next direction

- **Write an updated positive-results synthesis** that folds in the Qwen k=5 result (Qwen 8/8 robust
  saturation) alongside the DeepSeek k=5 result (6/8, 2 wrong assignments), restating the strengthened
  frontier-model split.
- **Then decide whether to design `workflow_handoff_0007`** — the natural successor is an
  axis-binding / value-invention stress task (the discriminating axis both DeepSeek failures hit), or a
  small 0006-style family to test whether the split generalizes. Do **not** start 0007 until the synthesis
  is updated and reviewed.

## Process compliance
Qwen3.7-Max only (no DeepSeek/MiniMax/Kimi/GLM). `.env` symlink provisioned as runtime config and
**removed after**. No secrets printed; no shell tracing. **Not committed, not pushed.** Other worktrees
untouched. `runs/` and `configs/baseline_models.json` gitignored and not staged.
