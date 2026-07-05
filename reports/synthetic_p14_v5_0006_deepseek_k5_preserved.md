# p14 v5 0006 — DeepSeek k=5 preserved reliability probe

**Status: COMPLETE (k=5, all valid). Not committed (awaiting review).** HEAD `47d108e`.

Statistical strengthening of the first clean p14 constraint-graph signal: DeepSeek-only k=5 on
`workflow_handoff_0006` to tighten the wrong-assignment failure-rate estimate.

## Headline — REPRODUCIBLE CONSTRAINT-GRAPH CAPABILITY DIFFICULTY SIGNAL

DeepSeek solved **4/5 (pass^5 = 0.80)** with **1 byte-confirmed wrong-global-assignment** (trial3).
Combined with the k=3 probe (2/3, 1 wrong-assignment), DeepSeek is now **6/8 on 0006 with TWO
byte-confirmed wrong-assignment failures (~25% observed failure rate)** — both axis-binding errors.
This is a **stable, reproducible constraint-graph difficulty signal** for DeepSeek (Qwen saturated 3/3).
Cost ¥55.63 / ¥60.

## 1. Valid-trial count
**5/5** (no infra exclusions).

## 2. Capability metrics (DeepSeek-V4-Pro)
- **pass@1 = 0.80**, **pass@k = 1.0**, **pass^5 = 0.80**.
- Combined with k=3: **6/8 = 75%**, 2 wrong-assignment failures.

## 3–5. Outcome / confidence / protocol counts

| metric | value |
|---|---|
| solved | 4 |
| non-solved | 1 |
| timeout | 0 |
| budget_exhausted (protocol) | 3 (t1, t4, t5 — all still scored 1.0) |
| confident-wrong | 1 |
| abstain / protocol-incomplete | 3 |
| clean FINISH + confidence | 2 |
| **overconfident_wrong** | **1** |
| **protocol_clean rate** | **2/5** |

## 6–8. Per-trial detail

| trial | score | inferred assignment | FINISH | conf | oc_wrong | tools | PT runs | wall (s) | cost ¥ |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **1.0** | slow/func ✓ | no | — | no | 54 | 37 | 1755 | 15.82 |
| 2 | **1.0** | slow/func ✓ | yes | high | no | 29 | 22 | 1058 | 4.66 |
| 3 | **0.10** | **func/slow_1.0V_125C ✗ (invented)** | yes | medium | **yes** | 21 | 16 | 979 | 5.87 |
| 4 | **1.0** | slow/func ✓ | no | — | no | 46 | 35 | 1669 | 14.16 |
| 5 | **1.0** | slow/func ✓ | no | — | no | 46 | 38 | 1771 | 15.12 |

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

## 10. Byte-confirmed failure classification — trial3 (the only non-pass)

- **Class: CONFIDENT_WRONG — wrong global assignment (axis-binding + value-invention).**
- Submitted `flow_config`: `{netlist: netlist_v2.v, clock: clk, scenario: func, corner: slow_1.0V_125C}`.
- Expected: `{netlist: netlist_v2.v, clock: clk_main, scenario: slow, corner: func}`.
- **Failure mode (three compounded errors):**
  1. **Axis-swap** — put the correct *corner* value `func` in the *scenario* slot (same pattern as the k=3 failure).
  2. **Value-invention** — `corner: slow_1.0V_125C` is a **hallucinated PVT-style string not in the constraint domain**.
  3. **Wrong clock name** — `clock: clk` (generic) instead of `clk_main`.
- PT did **not** sign off (`signoff` component = 0.0) — the invented corner/wrong clock broke the run.
- **Satisfied:** C1 (netlist_v2 family) only. **Violated:** C2 (clock), C3 (scenario/corner pair), C4 (provenance re-run), + signoff.
- **NOT decoy-following:** `slow_1.0V_125C` is invented, not any shipped decoy.
- **NOT broken chain:** stage1 + stage2 both consumed flow_config `990dbc60` (internally consistent on the wrong package).
- **NOT timeout/protocol:** 979s < 1800s, FINISH + medium confidence, `protocol_status=ok`.
- **Component scores:** only `explanation` = 1.0; everything else 0.0 (incl. `signoff`).
- confidence = **medium** (lower than the k=3 failure's *high*).

Other episodes: N/A — 4/5 solved with the correct `[slow/func]` assignment.

## 11. Did DeepSeek infer the unique global assignment?
**4/5** inferred `[netlist_v2, clk_main, slow, func]`; **1/5** (trial3) inferred the wrong
`[netlist_v2, clk, func, slow_1.0V_125C]`.

## 12. Did DeepSeek satisfy all constraints C1–C8?
**4/5** satisfied all of C1–C8; **1/5** (trial3) satisfied only C1 (netlist family) and violated C2/C3/C4 + signoff.

## 13. Comparison to the original Qwen+DeepSeek k=3

| | k=3 probe | k=5 probe | combined |
|---|---|---|---|
| DeepSeek pass | 2/3 | 4/5 | **6/8 (75%)** |
| DeepSeek wrong-assignments | 1 (func/typ clean swap, HIGH conf, 0.20) | 1 (func/slow_1.0V_125C invented, MEDIUM conf, 0.10) | **2 (~25%)** |
| Qwen pass | 3/3 | (not run) | 3/3 saturated |

Both DeepSeek failures are **axis-binding / constraint-inference errors** — neither is timeout/budget/infra/protocol/broken-chain/forbidden/oracle. The Qwen-vs-DeepSeek split holds: **0006 discriminates between frontier models.**

## 14. Final interpretation
**REPRODUCIBLE CONSTRAINT-GRAPH CAPABILITY DIFFICULTY SIGNAL (for DeepSeek).**

Per the interpretation rule: one or more byte-confirmed wrong global assignments ⇒ classify 0006 as a
**reproducible constraint-graph difficulty signal** and report the observed failure rate. DeepSeek now has
**two** byte-confirmed wrong-assignment failures on 0006 (k=3 + k=5), both axis-binding errors. Observed
wrong-assignment rate: **k=5 = 20% (1/5); k=3+k=5 combined = 25% (2/8)**. This is **not** saturated for
DeepSeek (pass^5 = 0.80); Qwen saturated (3/3).

**Secondary signal (separate from capability):** 0006 is ALSO an efficiency/protocol-stress task for
DeepSeek — 3/4 passes hit the 60-action cap without a clean FINISH (`budget_exhausted`, no confidence),
like 0005. But unlike 0005, the residual signal here is **not only protocol** — it includes a real,
reproducible **capability** failure (wrong assignment).

## Caveats
1. The two wrong-assignment failures differ in severity: k=3 was a clean `func/typ` value-swap (only C3
   violated, signoff passed → 0.20, HIGH confidence); k=5 trial3 was a more confused state (invented
   corner + wrong clock + axis-swap, signoff failed → 0.10, MEDIUM confidence). Both are axis-binding /
   constraint-inference failures, but the k=5 one shows DeepSeek can also **hallucinate** corner values
   outside the domain.
2. Combined n=8 (k=3 + k=5) gives a 25% wrong-assignment rate; the two runs were separate, so this is a
   rate estimate, not a single controlled k=8.
3. **Qwen k=5 was NOT run** in this phase (DeepSeek-only). A Qwen k=5 robustness check remains optional.
4. Confidence calibration varies: the k=3 wrong assignment was HIGH confidence; the k=5 wrong assignment
   was MEDIUM. DeepSeek is sometimes (not always) miscalibrated on its wrong assignments.
5. Phase-4I/4J preservation is load-bearing: both wrong assignments are **byte-confirmed**, not inferred.

## Next direction

- **No need for more DeepSeek `workflow_handoff_0006` trials immediately** — the reproducible signal
  (2/8 wrong-assignments) is established; further DeepSeek trials would only tighten the rate estimate,
  not change the qualitative conclusion.
- **Optionally run Qwen k=5 later** as a robustness check on its saturation (3/3 → confirm at k=5).
- **Or design `workflow_handoff_0007` based on axis-binding / value-invention stress** — both DeepSeek
  failures were axis-binding errors (one a clean value-swap, one an invented out-of-domain corner string),
  so the discriminating axis appears to be **joint constraint inference / axis-value binding**. A 0007
  that stresses this specifically (more axes, tighter joint-validity table, decoys that are valid under
  axis-confusion) is the natural successor.

## Statistical precision caveat (do not over-claim)

- The **25% figure is an OBSERVED failure rate (2/8), not a population-level confidence estimate.** With
  n=8 (across two separate runs), the uncertainty is wide; treat it as "DeepSeek fails on 0006 with
  non-trivial, reproducible frequency," not as a precise population parameter. A single controlled k=8 (or
  larger) would be needed for a tighter interval.

## Process compliance
DeepSeek-V4-Pro only (no Qwen/MiniMax/Kimi/GLM). `.env` symlink provisioned as runtime config and
**removed after**. No secrets printed; no shell tracing. **Not committed, not pushed.** Other worktrees
untouched. `runs/` and `configs/baseline_models.json` gitignored and not staged.
