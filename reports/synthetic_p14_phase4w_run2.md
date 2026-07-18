# p14 Phase-4W Run-2 — non-C6 grouped screening (BundleS=0015, BundleD=0016), k=3 each — COMPLETE

**Status: COMPLETE.** Report-only commit `b2d2c1a`; wording amended per review (this commit). Code:
variants `5abb5c5` (pre-run gate, all hard gates PASS). Model: Qwen3.7-Max, SSE streaming. Cost **¥76.79** (BundleS ¥38.08 + BundleD ¥38.71).
Frozen blocked-randomized order `block1:D,S / block2:S,D / block3:D,S` (seed `phase4w_run2_seed=20260718`).
No C6, no k=5, no DeepSeek, no held-out/other-variant/non-streaming calls.

**Headline (supported conclusion, review-refined wording).** "On the predeclared primary
typed-binding outcome, Run-2 **localizes the stable non-C6 improvement on this development task pair
to the schema/contract bundle (C1+C2+C4+C7) rather than the decoy-disambiguation bundle (C3+C5)**.
BundleS achieved 3/3 correct typed bindings; BundleD achieved 1/3 and reproduced two wrong-axis
failures." BundleD is **not** thereby proven to have no effect or to be categorically insufficient —
it **did not establish stable local sufficiency under the predeclared k=3 criterion**. Semantic
binding and end-to-end completion are kept separate: BundleS typed-binding **3/3**, artifact
completion **2/3**; BundleD typed-binding **1/3**, artifact completion **1/3**. The BundleS
incomplete-artifact episode is an **evidence-regeneration/task-wall failure after the correct binding
was already selected**, not a semantic-binding failure.

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
| typed-binding (primary) | **3/3 (stable correct binding)** | **1/3 (did not establish stable local sufficiency under the predeclared k=3 criterion; 2 wrong-axis reproduced)** | **localizes the stable non-C6 improvement to the schema/contract bundle → prioritize semantic schema/contract decomposition** |
| artifact (secondary here) | 2/3 (intermediate) | 1/3 | schema-leaning, with an artifact-completion caveat (see §4) |

## 4. Separated conclusions
**(a) Transport validity.** All 6 episodes transport-clean (0 socket_timeout / 0 hard_deadline / 0 stream
errors; 1 recovered chat retry on ep3).

**(b) Capability — Run-2 localizes the non-C6 route to schema/contract.** Run-1 established two
sufficient routes (answer-bearing C6 + the non-C6 bundle); Run-2 decomposes the non-C6 bundle. On the
**typed-binding** measure, the schema/contract bundle (C1 canonical labels + disjoint-typed-axes
declaration, C2 PVT-def, C4 glossary, C7 contract-wording) achieved stable correct binding on 0009
(3/3), whereas the decoy-disambiguation bundle (C3 coverage-fact, C5 pairwise-conflict) **did not
establish stable local sufficiency under the predeclared k=3 criterion** (1/3 binding; two wrong-axis
failures reproduced, clustering with the ambiguous 0009 baseline). This localizes the stable non-C6
improvement **on this development task pair** to the schema/contract bundle; it does NOT prove BundleD
has no effect. This is a **local** finding at one endpoint of one pair — not a general main effect and
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
