# p14 v6 0007 — axis-binding capability probe (preserved, k=3)

**Status: COMPLETE (k=3, all 6 valid). Not committed (awaiting review).** HEAD `5a014cd`.

Preserved capability probe on `workflow_handoff_0007` (axis_binding_value_invention): can Qwen3.7-Max and
DeepSeek-V4-Pro solve the typed-axis binding task, or does 0007 produce stronger axis-binding /
value-invention failures than 0006?

## Headline — 0007 SATURATED AT k=3 FOR BOTH MODELS

**Qwen 3/3** and **DeepSeek 3/3**, every episode byte-confirmed the **correct** typed assignment
`[netlist_v2, clk_main, slow, func]`, **0 wrong assignments**, **0 value-swaps, 0 PVT substitutions, 0
wrong-clock aliases, 0 typed-field mismatches**. **DeepSeek did NOT reproduce its 0006 axis-binding
failures.** Per the interpretation rule (both models solve all valid trials → saturated), **0007 is
classified SATURATED.**

**k=3 was completed only after the cost cap was explicitly raised ¥60 → ¥62** (the chained driver had
correctly skipped trial3 when the projected 6-episode total hit ¥60.67 > ¥60; the actual total came in at
**¥56.17, under BOTH the original ¥60 and the revised ¥62** caps). **Do NOT treat 0007 as a new positive
difficulty result** — it is a useful **oracle-contract validation** (the typed-binding oracle is real:
294→1 typed uniqueness; on real PT golden=1.0 and a signoff-green-but-mis-typed package scores 0.20) **and
a design ablation**, not a capability-difficulty signal.

## 1. Valid-trial count
**6/6** (Qwen 3, DeepSeek 3; no infra exclusions).

## 2. Capability pass@1 / pass@k / pass^k
| model | pass@1 | pass@k (any-of-k) | pass^k (all-of-k) | wrong assignments |
|---|---|---|---|---|
| Qwen3.7-Max | 1.00 | 1.00 | 1.00 | 0 |
| DeepSeek-V4-Pro | 1.00 | 1.00 | 1.00 | 0 |

## 3–5. Outcome / confidence / protocol counts
| metric | value |
|---|---|
| solved | 6 |
| non-solved | 0 |
| timeout | 0 |
| budget_exhausted (protocol) | 4 (t1 DeepSeek, t2 Qwen, t2 DeepSeek, t3 Qwen — all still scored 1.0) |
| confident-wrong | 0 |
| abstain / protocol-incomplete | 4 |
| clean FINISH + confidence | 2 (t1 Qwen high; t3 DeepSeek high) |
| **overconfident_wrong** | **0** |
| **protocol_clean rate** | **2/6** |

## 6–8. Per-trial detail
| trial | model | score | submitted assignment | FINISH | conf | tools | wall (s) | cost ¥ |
|---|---|---|---|---|---|---|---|---|
| 1 | Qwen3.7-Max | 1.0 | slow/func/clk_main ✓ | yes | high | 47 | 1256 | 10.31 |
| 1 | DeepSeek-V4-Pro | 1.0 | slow/func/clk_main ✓ | no | — | 37 | 1800 | 9.91 |
| 2 | Qwen3.7-Max | 1.0 | slow/func/clk_main ✓ | no | — | 59 | 1450 | 11.40 |
| 2 | DeepSeek-V4-Pro | 1.0 | slow/func/clk_main ✓ | no | — | 40 | 1800 | 8.83 |
| 3 | Qwen3.7-Max | 1.0 | slow/func/clk_main ✓ | no | — | 60 | 1391 | 11.53 |
| 3 | DeepSeek-V4-Pro | 1.0 | slow/func/clk_main ✓ | yes | high | 33 | 864 | 4.20 |

## 9. Preserved-artifact status (all 6 episodes)
| check | all 6 |
|---|---|
| `preserved_artifacts.json` present | ✓ |
| editable files preserved (5) | ✓ |
| hashes recorded | ✓ |
| `component_scores` (authoritative) | ✓ |
| `affirmative_grader_markers` | ✓ |
| `secrets_excluded: true` | ✓ |
| hidden truth / forbidden / secrets excluded | ✓ |

Preservation note: the runner writes preservation to its **temp** runs_root (`/tmp/agentic_eval_*`); artifacts
were collected post-trial into `runs/.../trialN/preserved_capture/<model>/`. `runs/` is gitignored. Security
scan: no forbidden filename, no `handoff_truth.json`/`grade_workflow.py`/`axis_schema.json`/netlists/library/
`.env`/API_KEY/BASE_URL in any of the 6 preserved trees.

## 10. Byte-confirmed failure classification
**N/A — there were NO non-passes.** All 6 episodes solved with the correct typed assignment. No value-swap,
PVT-substitution, wrong-clock-alias, typed-field-mismatch, decoy-following, broken-chain, final-state-only,
stage-only, hand-edited, forbidden-edit, timeout, or infra failure occurred in any episode.

## 11–12. Inferred assignment / typed constraints
**6/6** inferred the unique typed assignment `[netlist_v2, clk_main, slow, func]`. **6/6** satisfied all of
C1–C5 + the typed-binding constraints (`AXIS_SCHEMA_OK`, `TYPED_BINDING_OK`, `PVT_LABEL_OK` affirmative;
`evidence_generation` component = 1.0 in all 6).

## 13. Comparison to workflow_handoff_0006
| model | 0006 | 0007 |
|---|---|---|
| Qwen3.7-Max | 8/8 (k=3+k=5), 0 wrong | **3/3**, 0 wrong |
| DeepSeek-V4-Pro | **6/8**, 2 byte-confirmed axis-binding failures (k=3 func/typ value-swap; k=5 invented `slow_1.0V_125C` + `clk` alias) | **3/3, 0 wrong** |

**Verdict: 0007 is NOT stronger than 0006.** DeepSeek went from 6/8 (2 axis-binding failures) on 0006 to
3/3 (0 failures) on 0007. 0007 directly targeted the DeepSeek 0006 failure modes, yet DeepSeek made **none**
of those errors in 3 trials.

## 14. Final interpretation — SATURATED
Per the interpretation rule: *if both Qwen and DeepSeek solve all valid trials, classify 0007 as saturated
despite the stronger typed-axis oracle.* **Qwen 3/3, DeepSeek 3/3, 0 wrong assignments across 6 episodes.**
The decisive pre-model gates held (no oracle shortcut, no signoff-green-but-mis-typed pass — verified on
real PT: golden=1.0, signoff-green-but-mis-typed=0.20); the runs are valid; this is a genuine capability
result, not infra/harness noise.

**Why 0007 is not stronger (most likely mechanism):** PUBLISHING the typed vocabulary in `axis_schema.json`
(scenario_axis / corner_axis / clock_axis / pvt_label_axis + the type rules) tells DeepSeek exactly which
values are valid on each axis, so it binds correctly and never makes the `func`-in-scenario / `typ`-in-corner
swap or the PVT-as-corner invention it made on 0006. The 0006 axis-binding difficulty came from the correct
tuple being **implicit** (intersecting hidden constraints); 0007 made the vocabulary **explicit**, which
paradoxically **removes** the binding difficulty. This mirrors the recurring p14 lesson — when the answer
(or here, the valid value vocabulary) is directly discoverable, a strong agent reads it off.

**Small-sample caveat:** DeepSeek's 0006 failure rate was ~25% (2/8). At k=3, P(0 failures | 25% rate) =
0.75³ ≈ 0.42, so 0/3 is statistically consistent with a residual 25% rate. k=3 cannot distinguish "true
saturation" from "small-sample luck"; a larger k would sharpen it. But the qualitative conclusion — no
axis-binding failure observed; 0007 saturates DeepSeek where 0006 did not — holds at k=3.

**Secondary signal:** 0007 carries protocol/efficiency stress for both models (4/6 hit the 60-action cap
without a clean FINISH, all still scored 1.0) — separate from capability, matches the 0006 pattern.

**Design lesson for a future stronger task (do NOT build 0008 without review):**
- **KEEP the typed-binding oracle.** It correctly rejects signoff-green-but-mis-typed, value-swap,
  PVT-substitution, and wrong-clock-alias packages (proven: 0.20 below pass on real PT).
- **DO NOT publish a complete `axis_schema.json`** that makes axis membership and valid values directly
  readable — that publication is what removed the difficulty here.
- **REQUIRE axis membership / final axis binding to be inferred from evidence + provenance** (reports,
  digests, cross-source cross-checks) rather than read directly from a schema — preserving the typed-binding
  oracle while making binding non-trivial.
- **Beware the tension:** hiding the vocabulary risks collapsing back into 0006-style hidden-tuple
  difficulty; the design must keep *binding* (not *hiding*) as the load-bearing step.

## Cost / cap note
- Per-trial: trial1 ¥20.22, trial2 ¥20.23, trial3 ¥15.73. **Total ¥56.17.**
- Original cap ¥60; the chained driver **skipped trial3** because projected 6-ep was ¥60.67 > ¥60. The user
  explicitly authorized raising the cap to **¥62** for this probe; trial3 then ran. **Actual total ¥56.17 is
  under BOTH the original ¥60 and the revised ¥62** (trial3 came in cheaper than projected).

## Process compliance
Qwen3.7-Max + DeepSeek-V4-Pro only (no MiniMax/Kimi/GLM). `.env` symlinked to the gateway as runtime config
and **removed after**. No secrets printed; no shell tracing; no code modified. **Not committed, not pushed.**
Other worktrees untouched. `runs/` and `configs/baseline_models.json` gitignored and not staged.

## Next direction
- **No more 0007 probes immediately** — 0/6 axis-binding failures across k=3 establishes the qualitative
  result. A larger k would only tighten the rate estimate.
- **Do NOT treat 0007 as a new positive difficulty result.** It is an oracle-contract validation + a design
  ablation showing that publishing the typed vocabulary removes the axis-binding difficulty.
- **Do not start 0008 without review** (see the design-lesson block above).
