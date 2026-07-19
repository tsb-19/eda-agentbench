# p14 Phase-4W held-out generalization test — 0011 (ambiguous baseline) vs 0017 (BundleS-heldout), k=3 each — COMPLETE

**Status: COMPLETE.** Report-only commit; wording per the predeclared interpretation table. Code: pre-run
gate `e64facc` (all hard gates PASS: structural equivalence, disclosure ELIGIBLE ×2, real-PT fairness
ALL_PASS). Model: Qwen3.7-Max, SSE streaming, frozen Phase-4V2 config. Cost **¥64.78** (Base ¥33.26 +
Held ¥31.52). FROZEN restricted-randomized order `block1:Held,Base / block2:Base,Held / block3:Held,Base`
(seed `phase4w_heldout_seed=20260719`, balanced restriction predeclared before commit). No 0012, no C6,
no BundleD, no individual-component variants, no DeepSeek, no other tasks, no k=5, no non-streaming.

**Headline (predeclared cell: held-out generalization supported).** On the predeclared primary
typed-binding outcome, the frozen ambiguous held-out baseline **0011 reproduced recurrent
semantic-binding failure (1/3 correct)** while the held-out schema/contract variant **0017 (= frozen
0011 + exactly C1+C2+C4+C7) was stably correct (3/3 typed bindings AND 3/3 artifacts)**. This
**supports held-out generalization of the discovered non-answer-bearing BundleS route** to a new hidden
truth (typ/test) that the bundle wording never states: the same component set that recovered the
development 0009 baseline also recovers the held-out baseline, under a disclosure audit showing all 9
typed tuples remain publicly plausible in 0017. Composition of the two 0011 failures (reported
faithfully, not forced into one label): one **literal wrong-axis** submission (ep6: the shipped swap
`scenario=test/corner=slow` kept with only the netlist fixed — the exact fairness-gate wrong-axis
candidate) and one **typed-valid wrong-value** submission (ep2: `scenario=slow/corner=test` — the agent
corrected the role swap but failed to infer the unique scenario value). Both are signoff-GREEN /
evidence-generation-0 semantic-binding rejections, the hazard family under study.

## 1. Per-episode outcomes (frozen order; full dimension set)
| # | block | cond (task) | tv | gradeable | pc | termination | FINISH | score | submitted | binding | conf | act | rtok | retries | tport | ¥ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ep1 | block1 | Held (0017) | ✓ | ✓ | ✓ | finish | yes | 1.0 | typ/test | correct | HIGH | 48 | 37682 | 0 | 0 | 8.70 |
| ep2 | block1 | Base (0011) | ✓ | ✓ | ✗ | task_wall | no | 0.2 | **slow/test** | **wrong-value** | — | 41 | 83869 | 0 | 0 | 9.04 |
| ep3 | block2 | Base (0011) | ✓ | ✓ | ✓ | finish | yes | 1.0 | typ/test | correct | HIGH | 45 | 63483 | 0 | 0 | 11.19 |
| ep4 | block2 | Held (0017) | ✓ | ✓ | ✓ | finish | yes | 1.0 | typ/test | correct | HIGH | 45 | 54438 | 0 | 0 | 9.53 |
| ep5 | block3 | Held (0017) | ✓ | ✓ | ✗ | action_cap | no | 1.0 | typ/test | correct | — | 60 | 65060 | 0 | 0 | 13.29 |
| ep6 | block3 | Base (0011) | ✓ | ✓ | ✗ | task_wall | no | 0.2 | **test/slow** | **wrong-axis** | — | 56 | 79809 | 0 | 0 | 13.03 |

All 6: anti-cheat clean, 0 transport events, 0 chat retries, netlist correct (v2). Both Base failures:
signoff=1.0 / evidence_generation=0.0 (signoff-green, typed-binding-rejected). ep5 reached the correct
1.0 package, then hit the action cap without FINISH (abstained; not a binding or artifact failure).

## 2. Condition tallies (primary + secondaries)
| condition | k | typed-binding correct | artifact pass (1.0) | FINISH | semantic-binding failures |
|---|---|---|---|---|---|
| **Base** (0011, ambiguous baseline) | 3 | **1/3** | 1/3 (ep3) | 1/3 | 2 (1 wrong-axis test/slow; 1 wrong-value slow/test) |
| **Held** (0017 = 0011 + C1/C2/C4/C7) | 3 | **3/3** | **3/3** | 2/3 | 0 |

## 3. Predeclared interpretation (`reports/evidence/p14_phase4w_heldout/interpretation_table.json`)
Cell applied: **"0011 recurrent wrong-axis + 0017 stable correct → supports held-out generalization of
the non-answer-bearing schema/contract route."** Observed composition: 0011's recurrence is 2/3
semantic-binding failures — one literal wrong-axis and one typed-valid wrong-value (stated explicitly
above; both signoff-green/typed-rejected). Excluded cells: baseline NOT saturated (1/3, so the ceiling
cell does not apply); Held artifacts complete (3/3, so the binding-vs-completion split cell is not
needed); no instability cell (allocation stable under blocked order, both orderings present).

## 4. Separated conclusions
**(a) Transport validity.** All 6 episodes transport-clean (0 socket_timeout / 0 hard_deadline / 0
stream errors / 0 retries). Every episode is a valid measurement.

**(b) Capability — held-out generalization of the schema/contract route.** The Run-2 development
finding (BundleS = C1+C2+C4+C7 locally sufficient on 0009) generalizes to the held-out confirmation
pair with a different hidden truth: 0011 at 1/3 typed-binding vs 0017 at 3/3, with 0017's bundle
non-answer-bearing by the same predeclared disclosure audit (golden typ/test never stated; all 9 typed
tuples publicly plausible; wrong-axis remains plausible + signoff-green on real PT). The baseline
failure recurrence matches the development pattern (dev 0009: 1/3, 2 wrong-axis; held-out 0011: 1/3,
1 wrong-axis + 1 wrong-value). Scope: one model (Qwen3.7-Max), one held-out pair, k=3 per condition —
a confirmatory local result, not a universal main effect.

**(c) The two baseline failure modes are distinct and both are semantic-binding rejections.** ep6 is
the classic role-swap acceptance (type error kept). ep2 is new in this run: the agent REPAIRED the role
swap (both values moved to type-valid slots) but bound the wrong scenario value (slow instead of typ) —
type-system compliance without unique-value inference. The schema/contract bundle removed both failure
modes in this sample (0017: zero binding errors).

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
