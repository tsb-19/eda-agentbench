# p14 Phase-4W Run-2 — non-C6 grouped screening (BundleS=0015, BundleD=0016), k=3 each — COMPLETE

**Status: COMPLETE.** Report-only commit. HEAD `[SHA-TBD]`. Code: variants `5abb5c5` (pre-run gate, all hard
gates PASS). Model: Qwen3.7-Max, SSE streaming. Cost **¥76.79** (BundleS ¥38.08 + BundleD ¥38.71).
Frozen blocked-randomized order `block1:D,S / block2:S,D / block3:D,S` (seed `phase4w_run2_seed=20260718`).
No C6, no k=5, no DeepSeek, no held-out/other-variant/non-streaming calls.

**Headline (primary = typed-binding + artifact, both reported).** On the **typed-binding** measure, the
schema/contract bundle **BundleS (0009+C1/C2/C4/C7) succeeds (3/3 correct slow/func binding)** while the
decoy-disambiguation bundle **BundleD (0009+C3/C5) does not (1/3 binding; 2/3 wrong-axis)**. This indicates
the non-C6 clarity-bundle's sufficiency on the ambiguous baseline is carried by the **schema/contract
components (C1 labels+type-decls, C2 PVT-def, C4 glossary, C7 wording)**, not the decoy-disambiguation
components (C3 coverage-fact, C5 pairwise-conflict). On the **artifact** measure BundleS is **2/3** (one
episode bound correctly but did not finish evidence regeneration before the wall) and BundleD is 1/3 — so
the schema-succeeds verdict is clean on binding but carries an artifact-completion caveat.

## 1. Per-episode outcomes (frozen order; full dimension set)
| # | block | bundle (task) | tv | gradeable | pc | termination | FINISH | score | submitted | binding | conf | act | rtok | retries | tport | ¥ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ep1 | block1 | BundleD (0016) | ✓ | ✓ | ✗ | action_cap | no | 1.0 | slow/func | correct | — | 60 | 47826 | 0 | 0 | 12.93 |
| ep2 | block1 | BundleS (0015) | ✓ | ✓ | ✗ | task_wall | no | 0.2 | slow/func | correct* | — | 57 | 71467 | 0 | 0 | 12.63 |
| ep3 | block2 | BundleS (0015) | ✓ | ✓ | ✓ | finish | yes | 1.0 | slow/func | correct | HIGH | 53 | 62858 | 1 | 0 | 11.48 |
| ep4 | block2 | BundleD (0016) | ✓ | ✓ | ✗ | task_wall | no | 0.2 | **func/slow** | **wrong-axis** | — | 51 | 80212 | 0 | 0 | 13.36 |
| ep5 | block3 | BundleD (0016) | ✓ | ✓ | ✗ | task_wall | no | 0.2 | **func/typ** | **wrong-axis** | — | 57 | 74860 | 0 | 0 | 12.42 |
| ep6 | block3 | BundleS (0015) | ✓ | ✓ | ✗ | task_wall | no | 1.0 | slow/func | correct | — | 56 | 71847 | 0 | 0 | 13.97 |

`*` ep2 submitted the **correct** slow/func binding but hit the task wall before completing evidence
regeneration → artifact score 0.20 (evidence-generation incomplete), NOT a binding error.
All 6: anti-cheat clean, 0 transport events, netlist correct (v2).

## 2. Condition tallies (both primary outcomes)
| condition | k | typed-binding correct | artifact/grader pass (score 1.0) | protocol-complete FINISH | wrong-axis bindings |
|---|---|---|---|---|---|
| **BundleS** (0009+C1/C2/C4/C7) — schema/contract | 3 | **3/3** | 2/3 (ep3, ep6) | 1/3 (ep3) | 0 |
| **BundleD** (0009+C3/C5) — decoy-disambiguation | 3 | **1/3** | 1/3 (ep1) | 0/3 | 2 (func/slow, func/typ) |

## 3. Interpretation (predeclared table; `reports/evidence/p14_phase4w_run2/interpretation_table.json`)
| measure | BundleS | BundleD | cell |
|---|---|---|---|
| typed-binding (primary) | **3/3 (succeeds)** | **1/3 (does not)** | **schema succeeds, decoy does not → prioritize semantic schema/contract decomposition** |
| artifact (primary) | 2/3 (intermediate) | 1/3 (does not) | schema-leaning, with an artifact-completion caveat (see §4) |

## 4. Separated conclusions
**(a) Transport validity.** All 6 episodes transport-clean (0 socket_timeout / 0 hard_deadline / 0 stream
errors; 1 recovered chat retry on ep3).

**(b) Capability — the non-C6 route is the schema/contract route.** Run-1 established two sufficient routes
(answer-bearing C6 + the non-C6 bundle); Run-2 decomposes the non-C6 bundle. On the **typed-binding**
measure, the schema/contract bundle (C1 canonical labels + disjoint-typed-axes declaration, C2 PVT-def,
C4 glossary, C7 contract-wording) alone recovers correct binding on 0009 (3/3), whereas the
decoy-disambiguation bundle (C3 coverage-fact, C5 pairwise-conflict) alone does not (1/3; 2/3 wrong-axis,
clustering with the ambiguous 0009 baseline). This is a **local sufficiency** finding (schema/contract
sufficient; decoy-disambiguation insufficient) at one endpoint of one pair — not a general main effect and
not a generalization claim (held-out 0011/0012 not yet run).

**(c) Artifact-completion caveat (do not overclaim a clean 3/3).** On the **artifact** measure BundleS is
2/3: ep2 committed the correct binding but did not complete evidence regeneration before the task wall
(0.20, evidence-incomplete). So the schema route's binding success is 3/3 but its artifact completion is
2/3. If the schema-succeeds threshold is applied strictly on artifact (3/3), BundleS is intermediate; the
clean signal is on the typed-binding measure (3/3 vs 1/3). Per the predeclared table, this is reported
faithfully rather than forced into a single cell.

**(d) Negative controls are DISTINCT hazards.** BundleD's 2/3 failures are **wrong-axis** (the primary
semantic-role failure: signoff-green but typed-binding rejected, 0.20). Stale-decoy is a **separate
netlist-family hazard** (signoff-RED in source+held-out; netlist_v1 under pinned `clk_main`), not a
semantic-binding failure — not observed as an agent submission here, but distinct by construction.

**(e) Calibration — illustrative anecdote.** Only 1/6 episodes protocol-completed with a confidence label
(ep3, BundleS, HIGH, correct). No calibration claim.

## 5. Sample-size + scope
k=3 per condition. Local sufficiency finding at the ambiguous endpoint of one pair. Not a main effect; not
a generalization claim (held-out pair frozen, not model-run). The 2/3-vs-1/3 artifact split and 3/3-vs-1/3
binding split are point observations with wide uncertainty at k=3.

## 6. Frozen execution order + provenance
Order `BundleD,BundleS,BundleS,BundleD,BundleD,BundleS` (blocks 1–3), seed `phase4w_run2_seed=20260718`,
FROZEN at `5abb5c5` before any result. All 6 ran at HEAD `5abb5c5` over task bytes committed there.

## 7. Artifacts + SHA-256
Evidence root: `reports/evidence/p14_phase4w_run2_episodes/` — 6 dirs × 8 sanitized files + MANIFEST +
SHA256SUMS. Per-episode evidence-chain copies byte-match grader `submitted_file_hashes`. Run-2 pre-run
gate (disclosure audit + fairness vectors + randomization + interpretation table) at
`reports/evidence/p14_phase4w_run2/`.

---
*Compliance: Qwen3.7-Max only; 0015/0016 only (no C6/DeepSeek/held-out/other-variant/non-streaming); no
k=5; frozen blocked-randomized order; `.env` removed after runs; sanitized evidence + hashes (chain of
custody byte-verified); `scripts/check` PASSED. Real PrimeTime grading (b04 shim). Not pushed.*
