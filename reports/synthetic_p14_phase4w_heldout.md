# p14 Phase-4W held-out generalization test — 0011 (ambiguous baseline) vs 0017 (BundleS-heldout), k=3 each — COMPLETE

**Status: COMPLETE.** Report-only commit; wording per the predeclared interpretation table. Code: pre-run
gate `e64facc` (all hard gates PASS: structural equivalence, disclosure ELIGIBLE ×2, real-PT fairness
ALL_PASS). Model: Qwen3.7-Max, SSE streaming, frozen Phase-4V2 config. Cost **¥64.78** (Base ¥33.26 +
Held ¥31.52). FROZEN restricted-randomized order `block1:Held,Base / block2:Base,Held / block3:Held,Base`
(seed `phase4w_heldout_seed=20260719`, balanced restriction predeclared before commit). No 0012, no C6,
no BundleD, no individual-component variants, no DeepSeek, no other tasks, no k=5, no non-streaming.

**Headline (accepted conclusion, review wording).** "Within Qwen3.7-Max, the non-answer-bearing
schema/contract bundle C1+C2+C4+C7 generalizes across two distinct hidden truths in the controlled
workflow-handoff task family. On the development family, the ambiguous baseline produced recurrent
binding failures while BundleS achieved 3/3 typed-binding correctness. On the pre-frozen held-out
family with a different golden binding, the baseline achieved 1/3 while the held-out BundleS condition
achieved 3/3 typed-binding and 3/3 artifact correctness." **Scope: this conclusion is explicitly
limited to Qwen3.7-Max and this controlled task family — BundleS is NOT yet claimed as a general
cross-model harness mechanism** (cross-model confirmation is the next phase).

**Failure taxonomy (review-defined; do not collapse the subtypes).** Parent category
**`semantic_binding_failure`** (signoff-GREEN / typed-binding-rejected), with at least two subtypes:
1. **`axis_binding_failure`** — a literal semantic-axis binding failure: a value occupies the wrong
   typed axis (ep6: `scenario=test / corner=slow`, the shipped swap kept with only the netlist fixed).
2. **`role_conditioned_value_selection_failure`** — axis/type-valid but the wrong value is selected
   for the role (ep2: `scenario=slow / corner=test`, role swap repaired into type-valid slots but the
   unique scenario value not inferred).
Both held-out baseline failures are semantic binding failures; they are NOT identical and are never
collapsed into "wrong-axis."

## 1. Per-episode outcomes (frozen order; full dimension set)
| # | block | cond (task) | tv | gradeable | pc | termination | FINISH | score | submitted | binding | conf | act | rtok | retries | tport | ¥ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ep1 | block1 | Held (0017) | ✓ | ✓ | ✓ | finish | yes | 1.0 | typ/test | correct | HIGH | 48 | 37682 | 0 | 0 | 8.70 |
| ep2 | block1 | Base (0011) | ✓ | ✓ | ✗ | task_wall | no | 0.2 | **slow/test** | **role_conditioned_value_selection_failure** | — | 41 | 83869 | 0 | 0 | 9.04 |
| ep3 | block2 | Base (0011) | ✓ | ✓ | ✓ | finish | yes | 1.0 | typ/test | correct | HIGH | 45 | 63483 | 0 | 0 | 11.19 |
| ep4 | block2 | Held (0017) | ✓ | ✓ | ✓ | finish | yes | 1.0 | typ/test | correct | HIGH | 45 | 54438 | 0 | 0 | 9.53 |
| ep5 | block3 | Held (0017) | ✓ | ✓ | ✗ | action_cap | no | 1.0 | typ/test | correct | — | 60 | 65060 | 0 | 0 | 13.29 |
| ep6 | block3 | Base (0011) | ✓ | ✓ | ✗ | task_wall | no | 0.2 | **test/slow** | **axis_binding_failure** | — | 56 | 79809 | 0 | 0 | 13.03 |

All 6: anti-cheat clean, 0 transport events, 0 chat retries, netlist correct (v2). Both Base failures:
signoff=1.0 / evidence_generation=0.0 (signoff-green, typed-binding-rejected). ep5 reached the correct
1.0 package, then hit the action cap without FINISH (abstained; not a binding or artifact failure).

## 2. Condition tallies (primary + secondaries)
| condition | k | typed-binding correct | artifact pass (1.0) | FINISH | semantic-binding failures |
|---|---|---|---|---|---|
| **Base** (0011, ambiguous baseline) | 3 | **1/3** | 1/3 (ep3) | 1/3 | 2 semantic_binding_failure (1 axis_binding_failure test/slow; 1 role_conditioned_value_selection_failure slow/test) |
| **Held** (0017 = 0011 + C1/C2/C4/C7) | 3 | **3/3** | **3/3** | 2/3 | 0 |

## 3. Predeclared interpretation (`reports/evidence/p14_phase4w_heldout/interpretation_table.json`)
Cell applied: **"0011 recurrent wrong-axis + 0017 stable correct → supports held-out generalization of
the non-answer-bearing schema/contract route."** Observed composition: 0011's recurrence is 2/3
**semantic_binding_failure** episodes — one `axis_binding_failure` and one
`role_conditioned_value_selection_failure` (taxonomy above; both signoff-green/typed-rejected).
Excluded cells: baseline NOT saturated (1/3, so the ceiling cell does not apply); Held artifacts
complete (3/3, so the binding-vs-completion split cell is not needed); no instability cell (allocation
stable under blocked order, both orderings present).

## 4. Separated conclusions
**(a) Transport validity.** All 6 episodes transport-clean (0 socket_timeout / 0 hard_deadline / 0
stream errors / 0 retries). Every episode is a valid measurement.

**(b) Capability — held-out generalization within Qwen3.7-Max.** The accepted conclusion (headline,
verbatim) is explicitly scoped to Qwen3.7-Max and this controlled workflow-handoff task family: the
Run-2 development finding (BundleS = C1+C2+C4+C7 locally sufficient on 0009) generalizes to the
held-out confirmation pair with a different hidden truth — 0011 at 1/3 typed-binding vs 0017 at 3/3,
with 0017's bundle non-answer-bearing by the same predeclared disclosure audit (golden typ/test never
stated; all 9 typed tuples publicly plausible; wrong-axis remains plausible + signoff-green on real
PT). The baseline failure recurrence matches the development pattern (dev 0009: 1/3; held-out 0011:
1/3). **BundleS is not yet claimed as a general cross-model harness mechanism**; cross-model
confirmation (DeepSeek, transport-homogeneous streaming) is the prioritized next phase, before any
further decomposition of C1/C2/C4/C7.

**(c) The two baseline failures are distinct subtypes of `semantic_binding_failure`.** ep6 =
`axis_binding_failure`: the classic role-swap acceptance (type error kept — a corner value in the
scenario slot and vice versa). ep2 = `role_conditioned_value_selection_failure`, new in this run: the
agent REPAIRED the role swap (both values moved to type-valid slots) but selected the wrong scenario
value (slow instead of typ) — type-system compliance without unique-value inference. The
schema/contract bundle removed both subtypes in this sample (0017: zero binding errors). Future
analyses tally the subtypes separately under the parent category.

**(d) Calibration.** All 3 protocol-completed episodes (ep1/ep3/ep4) elicited HIGH confidence and all
3 were correct — no overconfident-wrong. The 3 non-FINISH episodes abstained (no confidence emitted);
two of them (ep2/ep6) were the failures, one (ep5) was correct-but-capped. Anecdote at k=3; no
calibration claim.

**(e) Confirmatory freeze honored.** After ep1 (the first held-out result), 0011, 0017, the BundleS
definition, the grader, and the stopping rule were not modified (frozen at `e64facc`; hashes in
`prerun_freeze_manifest.json`). Exactly six authorized episodes were run.

## 5. Sample-size + scope
k=3 per condition; one held-out pair; one model. The 3/3-vs-1/3 split is a point observation with wide
uncertainty at k=3; the generalization claim is the predeclared cell verdict, not an effect-size claim.
Family split: development = 0009/0010/0013–0016; held-out confirmation = 0011/0017.

## 6. Frozen execution order + provenance
Order `Held,Base / Base,Held / Held,Base` (blocks 1–3), seed `phase4w_heldout_seed=20260719` with the
predeclared balanced restriction (first RNG triple was all-Base-first and was rejected by the declared
rule BEFORE commit and before any paid call; second triple accepted — recorded in
`randomization_manifest.json`). All 6 episodes ran at HEAD `e64facc` over task bytes committed there.

## 7. Artifacts + SHA-256
Evidence root: `reports/evidence/p14_phase4w_heldout_episodes/` — 6 trials × 8 sanitized files +
MANIFEST.json + SHA256SUMS; per-episode evidence-chain copies byte-match the grader-submitted files
(chain-of-custody in MANIFEST.json). Pre-run gate (structural equivalence + disclosure audit + fairness
vectors + pt_evidence + randomization + interpretation table + freeze manifest) at
`reports/evidence/p14_phase4w_heldout/` (committed `e64facc`).

---
*Compliance: Qwen3.7-Max only; workflow_handoff_0011 + workflow_handoff_0017 only (no 0012 / C6 /
BundleD / individual-component variants / DeepSeek / other tasks / k=5 / non-streaming); frozen
restricted-randomized order; `.env` symlinked for the run and removed by the chain on completion;
sanitized evidence + hashes; `scripts/check` PASSED. Real PrimeTime grading (b04 shim). Not pushed.*
