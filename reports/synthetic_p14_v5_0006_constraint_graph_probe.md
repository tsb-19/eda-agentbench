# p14 v5 0006 — constraint-graph capability probe (Qwen + DeepSeek, k=3, preserved)

**Status: COMPLETE (6 episodes). Not committed (awaiting review).** HEAD `1057624`.

Preserved capability probe on `workflow_handoff_0006` (constraint-graph multi-source recovery): can
Qwen3.7-Max and DeepSeek-V4-Pro infer the unique globally-consistent package, or does the constraint
graph finally create a stable capability difficulty signal?

## Headline — FIRST REAL CONSTRAINT-GRAPH CAPABILITY DIFFICULTY SIGNAL

**Qwen saturated (3/3 solve). DeepSeek did NOT (2/3 solve + 1 byte-confirmed confident-wrong).** DeepSeek
trial-1 is a clean **wrong-assignment confident-wrong**: it inferred `(scenario=func, corner=typ)` instead
of the unique `(slow, func)` — satisfying C1 (netlist_v2) + C2 (clk_main) but **violating C3**
(scenario/corner signoff pair). It FINISHed at 1307s with **high confidence** on the 0.20 answer. This is
the **first p14 task to elicit a clean wrong-assignment confident-wrong from the frontier** — exactly the
signal 0006 was designed to produce, and the kind of failure 0005's directly-readable authority tuple
could never provoke. Cost ¥62.5 / ¥60 (all 6 episodes completed; see caveats).

## 1. Valid-trial count by model
- Qwen3.7-Max: **3/3**
- DeepSeek-V4-Pro: **3/3**

## 2. Capability metrics
| model | pass@1 | pass@k | pass^k (all-3) | overconfident_wrong |
|---|---|---|---|---|
| Qwen3.7-Max | 1.0 | 1.0 | **1.0** | 0 |
| DeepSeek-V4-Pro | 1.0 | 1.0 | **0.667** | **1** |

## 3–5. Outcome / confidence / protocol counts
solved 5 · non-solved 1 · timeout 0 · budget_exhausted 0 · **confident-wrong 1** · abstain 0 ·
clean-FINISH+confidence **6/6** · **overconfident_wrong 1** · **protocol_clean 6/6**.

Every episode cleanly FINISHed with high confidence. The single failure is a confident-**WRONG**, not a
protocol/budget slip — the opposite of 0005's broken-chain mode.

## 6–8. Per-episode detail

| trial | model | score | inferred assignment | FINISH | conf | oc_wrong | tools | PT runs | wall (s) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Qwen | **1.0** | slow/func ✓ | yes | high | no | 56 | 36 | 1478 |
| 1 | DeepSeek | **0.20** | **func/typ ✗ (C3)** | yes | high | **yes** | 35 | 27 | 1307 |
| 2 | Qwen | **1.0** | slow/func ✓ | yes | high | no | 47 | 40 | 1192 |
| 2 | DeepSeek | **1.0** | slow/func ✓ | yes | high | no | 36 | 23 | 1658 |
| 3 | Qwen | **1.0** | slow/func ✓ | yes | high | no | 49 | 37 | 1588 |
| 3 | DeepSeek | **1.0** | slow/func ✓ | yes | high | no | 38 | 28 | 1549 |

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

Security scan: no forbidden filename, no `HIDDEN_TRUTH`/`API_KEY`/`BASE_URL`/`Bearer` in any preserved tree.

## 10. Byte-confirmed failure classification — trial1/DeepSeek (the only non-pass)

- **Class: CONFIDENT_WRONG — wrong global assignment (constraint-graph inference failure).**
- Submitted `flow_config`: `{netlist: netlist_v2.v, clock: clk_main, scenario: func, corner: typ}`.
- **Violated constraint: C3** (scenario/corner signoff pair). C1 (netlist_v2) and C2 (clk_main) satisfied.
- **Failure mode: a VALUE-SWAP.** DeepSeek bound the *correct corner value* (`func`) to the **scenario**
  axis, and `typ` to the **corner** axis. The correct pair is `(slow, func)`. It mis-inferred which axis
  each value belongs to under the joint constraint.
- **NOT decoy-following:** did not adopt report_A (test/typ), report_B (v1), report_C (clk_old), or
  evidence_D (v1). `(func, typ)` is a **novel** wrong assignment — a genuine inference error.
- **NOT a broken chain:** stage1 and stage2 both consumed `flow_config` hash `297e2790` — the evidence
  chain was internally consistent. This is a *correct chain on a wrong assignment*, the opposite of 0005's
  *wrong chain on a correct assignment*.
- **NOT timeout / NOT protocol:** 1307s < 1800s, FINISH + high confidence, `protocol_status=ok`.
- **Component scores:** only `signoff` + `explanation` = 1.0; `final_state`/`evidence_generation`/
  `stage_chain`/`provenance`/`authority_consistency`/`hazard_recovery` all 0.0.
- **Is pairwise-plausible-but-globally-invalid:** yes (satisfies C1+C2, violates C3).

Other episodes: N/A — 5/6 solved with the correct `[slow/func]` assignment.

## 11. Did each model infer the unique global assignment?
- **Qwen3.7-Max: 3/3** inferred `[netlist_v2, clk_main, slow, func]`.
- **DeepSeek-V4-Pro: 2/3** inferred correct; **1/3** inferred the wrong `[netlist_v2, clk_main, func, typ]`.

## 12. Did each model satisfy all constraints C1–C8?
- **Qwen3.7-Max: 3/3** satisfied all of C1–C8.
- **DeepSeek-V4-Pro: 2/3** satisfied all of C1–C8; **1/3** satisfied only **C1+C2** (violated C3, and
  transitively C4/C5/C6 since its fresh chain was on the wrong package).

## 13. Comparison to workflow_handoff_0005
| | 0005 (multi-conflict decoy) | 0006 (constraint graph) |
|---|---|---|
| DeepSeek pass^k | 1.0 (k=5) | **0.667 (k=3)** |
| correctness | saturated | **NOT saturated** |
| failure mode | broken-chain protocol slip (1/5, didn't recur) | **wrong-assignment confident-wrong (1/3)** |
| authority discoverability | tuple directly readable from spec/manifest | **no single file reveals the tuple** (joint inference) |

0006 is the first p14 task whose difficulty is **joint constraint inference**, not exploration cost.

## 14. Final interpretation
**FIRST REAL CONSTRAINT-GRAPH CAPABILITY DIFFICULTY SIGNAL (for DeepSeek).**

Per the interpretation rule: a model that fails by committing to a pairwise-plausible-but-globally-invalid
assignment is the first real constraint-graph difficulty signal. DeepSeek trial-1 committed to `(func,typ)`
(satisfied C1+C2, violated C3) with high confidence and a clean finish. This is **not** timeout, **not**
protocol, **not** infra, **not** a broken chain, and **not** decoy-following — it is a genuine
joint-inference failure. Qwen saturated (3/3), so the task is solvable; 0006 **discriminates between
frontier models**, a valuable benchmark property.

## Caveats
1. **n=3 per model is small.** DeepSeek's 1/3 confident-wrong is a real signal but the 33% rate is a
   wide-interval point estimate; a larger k would sharpen it. Still the **first clean wrong-assignment
   confident-wrong in the entire p14 ladder.**
2. **Qwen saturated (3/3)**, so 0006 is solvable; the difficulty discriminates *between* frontier models.
3. **Cost ¥62.5 vs ¥60 cap:** all 6 episodes completed before the post-trial cap gate tripped; no episode
   was cut mid-run, so k=3 is fully satisfied. A lower per-trial projection margin would avoid this.
4. **DeepSeek's wrong assignment is a value-swap** (correct corner value `func` bound to the scenario
   axis). The difficulty is specifically **axis-value binding under joint constraints**, not
   netlist/clock selection.
5. **Phase-4I/4J preservation is load-bearing here:** without preserved artifacts this failure could only
   be *inferred* (and might have been mis-guessed as decoy-following or a broken chain, as the 0005
   episode initially was). The preserved `flow_config.json` byte-confirms the exact wrong assignment.

## Future work (optional, not blocking this report)

- **Optionally run DeepSeek k=5** to tighten the confident-wrong rate statistics (current 1/3 is a
  wide-interval point estimate).
- **Optionally run Qwen k=5** as a robustness check on its saturation (3/3 → confirm it holds at k=5).
- **No more evidence is needed before committing this report** — the 1/3 byte-confirmed wrong-assignment
  confident-wrong is already the first clean constraint-graph capability-difficulty signal in p14.

## Process compliance
Qwen3.7-Max + DeepSeek-V4-Pro only (no MiniMax/Kimi/GLM). `.env` symlink provisioned as runtime config
and **removed after**. No secrets printed; no shell tracing. **Not committed, not pushed.** Other
worktrees untouched. `runs/` and `configs/baseline_models.json` gitignored and not staged.
