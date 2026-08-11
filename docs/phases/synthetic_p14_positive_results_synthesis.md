# p14 positive-results synthesis — from negative ladder to constraint-graph frontier split

**Design-only synthesis.** Summarizes the complete p10→p14 research narrative after the successful
`workflow_handoff_0006` probe. No code, no tasks, no probes — analysis only.

---

## 1. Current checkpoint

- **HEAD:** `fb6aebf` (`docs: report p14 constraint graph deepseek k5 probe`)
- **Branch:** `synthetic-phase0a` — **local-only, not pushed** (no upstream), working tree clean.
- **Latest important commits (newest first):**
  - `fb6aebf` — DeepSeek k=5 preserved 0006 report (the reproducible-signal result)
  - `47d108e` — Qwen+DeepSeek k=3 0006 capability probe report (the first clean signal)
  - `1057624` — `feat: add workflow handoff constraint graph variant` (0006 implementation)
  - `3166c89` — 0006 constraint-graph design doc
  - `326961b` — affirmative-only grader markers fix (Phase-4J)
  - `f4ef140` — opt-in probe-artifact preservation (Phase-4I)
  - (`326961b`-tagged checkpoint `synthetic-p14-v4-positive-signal-checkpoint-326961b`;
    `synthetic-p14-constraint-graph-signal-47d108e` tag + bundle at `47d108e`)

---

## 2. Original objective

Build a **workflow-level synthetic industrial EDA benchmark generator** that:
- uses **real commercial EDA tools** (PrimeTime on b04, via a transparent forwarder shim),
- uses **hidden oracles** with forgery-resistant provenance checks,
- generates **mini multi-artifact handoff projects** (not single-file puzzles),
- evaluates both **capability** (can the agent recover the correct package) and
  **reliability/protocol** (does it finish cleanly, with calibrated confidence),
- and eventually obtains **tasks that are not saturated by frontier agents** — i.e., that produce a
  discriminating, reproducible capability signal rather than mere cost/latency stress.

The north star (per memory `benchmark-hardening-north-star`): measure **real** capability gaps vs human
chip engineers, with a **realism test** gating every task. Contrived difficulty is rejected.

---

## 3. Negative ladder summary

Every prior mechanism was built, validated on real PT, probed on frontier models, and found to
**saturate** (frontier solves it) or to produce only **efficiency/protocol stress** (not capability
failure):

| phase | mechanism | outcome |
|---|---|---|
| p10 | single constraint drift | saturated |
| p11 | flow handoff (single fault) | saturated |
| p12 | multi-artifact repair | saturated |
| p13 | trajectory / evidence handoff (provenance validated) | saturated |
| p14 v1 | ordered evidence-chain | saturated |
| p14 v2 | cross-source conflict | no frontier difficulty |
| p14 v3 | scenario/corner conflict | saturated |
| p14 v4 (`0005`) | multi-conflict partially-truthful decoy | **efficiency/protocol stress only** (DeepSeek pass^5 = 1.0) |

---

## 4. What each negative result taught

- **Single numeric drift (p10) is too local** — a one-axis edit is trivially found.
- **Single handoff fault (p11) is too obvious** — one contradiction is easy to localize.
- **More files alone (p12) are insufficient** — count ≠ coupling; the agent can fix each file independently.
- **Ordered evidence chains (p14 v1) are executable by strong agents** — a deterministic rerun recipe is
  followable.
- **A readable authority tuple (p14 v2–v4) makes recovery too easy** — when spec/manifest *state* the
  answer tuple, a strong agent reads it off and rejects decoys by per-axis cross-checks (0005: DeepSeek
  pass^5 = 1.0).
- **Multiple decoys increase cost but do not necessarily create wrong global inference (p14 v4)** — decoys
  that are each wrong on one axis are rejected once the agent cross-checks; cost goes up, correctness does
  not go down.
- **Preservation is needed *before* claiming wrong-package failures** — without final-workspace
  preservation, the early 0005 "confident-wrong" was misclassified (it was a broken-chain protocol slip,
  not a wrong package). Inference-only labels are not trustworthy.

Each negative sharpened the design constraint: difficulty must come from **joint structure the agent
cannot read off any single file**, not from hiding a readable answer behind more decoys.

---

## 5. Positive result — workflow_handoff_0006

`workflow_handoff_0006` is a **constraint-graph multi-source recovery** task:

- **No single visible artifact gives the full correct tuple.** The manifest declares only the netlist
  *family* + interface (C1); spec gives the joint-validity *table* (C3); the clock is pinned by tool-derived
  coverage (C2). The target is recoverable only by **intersecting** the constraints.
- **36 candidate assignments; exactly one satisfies all constraints** (offline-proven by
  `enumerate_constraint_graph`, stored in hidden truth). The unique assignment is
  `[netlist_v2, clk_main, slow, func]`.
- **Qwen3.7-Max solved 3/3** (saturated; pass^3 = 1.0) — the task is solvable.
- **DeepSeek-V4-Pro failed reproducibly:** across the k=3 + k=5 probes, **6/8 passes with 2 byte-confirmed
  wrong global assignments** (observed rate ≈25%, wide-uncertainty n=8).
- **This creates a frontier-model split:** Qwen saturates, DeepSeek does not. 0006 discriminates between
  frontier models — the first p14 task to do so.

---

## 6. Failure mode analysis (DeepSeek, both wrong assignments)

**Failure 1 (k=3, HIGH confidence, score 0.20):**
- submitted `scenario=func, corner=typ` (expected `slow/func`).
- a **value-swap / axis-binding error**: the correct *corner* value `func` was bound to the *scenario* axis.
- satisfied **C1+C2** (netlist_v2 + clk_main); violated **C3** only. PT still signed off (signoff=1.0).

**Failure 2 (k=5 trial3, MEDIUM confidence, score 0.10):**
- submitted `scenario=func, corner=slow_1.0V_125C, clock=clk` (expected `slow/func/clk_main`).
- **axis-binding + value-invention**: again `func`→scenario slot, plus a **hallucinated PVT corner
  string** (`slow_1.0V_125C`, not in the domain) and a wrong/generic clock name (`clk`).
- satisfied **only C1**; violated C2/C3/C4 **+ signoff** (PT did not pass — the invented corner/wrong
  clock broke the run).

**Shared pattern:** both are **wrong global assignment / constraint-axis binding failures.** Neither is:
- an evidence-chain break (both had internally-consistent stage1+stage2 on the wrong package),
- a protocol/no-FINISH slip (both FINISHed with confidence),
- an infra failure,
- an oracle failure,
- or simple decoy-following (failure 2 invented a value present in no shipped source).

The difficulty is specifically **joint constraint inference / axis-value binding** — exactly the mechanism
0006 was designed to stress.

---

## 7. Role of preservation

- **Without final-workspace preservation, the early 0005 failure was misclassified** (inferred as a
  "report_A wrong-corner" confident-wrong; preservation later showed it was a broken-chain protocol slip).
- **Preservation allows byte-confirmed failure classification** — the exact submitted `flow_config.json` +
  hashes let us decode the precise wrong assignment (e.g., `func/slow_1.0V_125C/clk`), not guess it.
- **Going forward, preserved files + hashes + authoritative `component_scores` are REQUIRED for any
  confident-wrong / wrong-package claim.** Inference-only labels must be marked as such.
- **The Phase-4J affirmative-marker fix** (presence-only → affirmative-only parsing) prevents the grader
  markers from misleadingly flagging failed components as passed. `score.json`/`component_scores` are
  authoritative.
- Net effect: **scientific trustworthiness.** The positive 0006 signal rests on byte-confirmed evidence,
  not inference.

---

## 8. Capability vs efficiency/protocol

These two axes are kept strictly separate:

**Capability (correctness of the recovered package):**
- 0006 **discriminates Qwen vs DeepSeek** — Qwen 3/3, DeepSeek 6/8 with 2 wrong assignments.
- DeepSeek has **reproducible wrong-assignment failures** (a genuine joint-inference gap).

**Efficiency / protocol (cost, latency, clean finish):**
- 0005 is **stress only** (DeepSeek pass^5 = 1.0; the residual signal there is wall-time / PT-runs /
  no-FINISH budget_exhausted).
- 0006 **also** carries efficiency/protocol stress (3/4 DeepSeek k=5 passes hit the 60-action cap without
  a clean FINISH), **but** its key signal is the actual **wrong assignment**, not the cost.
- Protocol/infrastructure failures (timeout, budget_exhausted, no-FINISH) are **excluded** from capability
  metrics; they are reported alongside, never folded in.

---

## 9. External positioning (internal framing, not citation-heavy)

- **pass^k-style reliability** (pass@k any-of vs pass^k all-of, run-to-run variance) motivates the
  multi-trial evaluation used here — a single pass@1 would have missed the DeepSeek failures.
- **Constraint-graph tasks** align with the broader move in agent benchmarks toward **structured
  distractors and interdependent constraints** (the answer is the *intersection*, not a retrieved label).
- **Recoverable tool-environment hazards** (cross-source provenance, stale-vs-fresh evidence) align with
  the cross-source/provenance theme in workflow/agent benchmarks.
- **SLSA/in-toto-style provenance** motivates the evidence-chain validation: digest binding, input-hash
  pinning, and "stage2 must bind the fresh stage1" are the same idea as build-provenance attestation.

---

## 10. What this enables

- p14 now has a **validated path from generator substrate to a real positive signal** — the same
  generator/oracle machinery that saturated on v1–v4 produced a discriminator at v5 by changing the
  *discoverability* structure.
- The benchmark can **distinguish strong frontier models** (Qwen vs DeepSeek on 0006).
- The synthetic generator can **produce tasks with hidden uniqueness proofs** (the 36→1 enumeration lives
  in hidden truth, never in a visible file).
- The **acceptance filters** (golden=1.0; every decoy / single-axis / stage2-only / final-state-only /
  hand-edited / forbidden-edit fails; deterministic regen; no-leak; verdict-first) prevent corrupt success.
- 0006 can be used as a **seed for a broader constraint-graph EDA workflow family** (more axes, tighter
  joint-validity tables, cross-tool confirmation).

---

## 11. Remaining limitations (honest)

- **Sample size is still small:** DeepSeek n=8 (across two separate runs); Qwen n=3 only.
- **Qwen only has k=3, not k=5** — its saturation is not yet robustness-checked at k=5.
- **DeepSeek's failure rate is observed 2/8 (25%), not a population estimate** — wide uncertainty; treat
  as "non-trivial reproducible frequency," not a precise parameter.
- **Task is still PT-only** — no DC/Formality cross-tool confirmation yet.
- **Only one constraint-graph task exists** (0006); a family is needed to show the mechanism generalizes.
- **Command-text trace is still sparse** (the agentlog command fields are not full command text) — a
  driver-level change, deferred.
- **No public release or push yet** — branch is local-only.
- **Cost is nontrivial** — each 0006 episode is ¥5–16; k=5 runs cost ¥50–65.

---

## 12. Recommended next steps

A. **Commit this synthesis after review.**
B. Then choose one of:
   1. **run Qwen k=5** on 0006 as a robustness check on its saturation, or
   2. **implement `workflow_handoff_0007`** based on **axis-binding / value-invention stress** (the
      discriminating axis both DeepSeek failures hit), or
   3. **generalize 0006 into a small generator family** (a handful of constraint-graph tasks with
      different axes/joint-validity tables) to show the mechanism generalizes.
C. **Do not run more DeepSeek 0006 trials immediately** unless tighter confidence intervals are needed.
D. **Do not revert to single-hazard variants** (v1–v4 are saturated; the constraint-graph axis is where
   the signal is).

---

## 13. Suggested paper / research framing

Possible framings (one or a combination):

- *"From negative ladder to constraint-graph positive signal."* — the methodological arc (why each simpler
  mechanism saturated, and what structural change finally produced a discriminator).
- *"Real-tool synthetic EDA workflow benchmark with provenance-backed hidden oracle."* — the substrate
  (real PrimeTime, forgery-resistant consumed-netlist/clock/scenario/corner echecks, offline uniqueness
  proof).
- *"Single-hazard handoff tasks saturate; constraint-graph handoff creates a frontier split."* — the core
  empirical finding.
- *"Evidence preservation is necessary for trustworthy failure classification."* — the infrastructure
  lesson (Phase-4I/4J corrected a misclassification and made the 0006 signal byte-confirmable).

---

## 14. Final conclusion

- **p10–p14 v4 established the substrate and ruled out the weaker mechanisms** (single drift, single
  fault, more files, ordered chains, readable authority tuples, multi-decoy cost stress).
- **p14 v5 `workflow_handoff_0006` produced the first clean capability signal** — a constraint-graph task
  where the correct package is the unique intersection of independent constraints, not a readable tuple.
- **DeepSeek fails through byte-confirmed global-assignment errors** (axis-binding / value-invention),
  reproducibly (~25% observed, n=8); **Qwen solves**, proving task solvability.
- **The next frontier is scaling constraint-graph EDA workflows** — a small family of 0006-style tasks,
  with hidden uniqueness proofs and provenance-backed oracles, measured under pass^k with byte-confirmed
  failure classification.

---

*Compliance: design-only. No code, no tasks, no models, no other-worktree changes. Not committed, not
pushed — awaiting review.*
