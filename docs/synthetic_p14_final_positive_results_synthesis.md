# p14 final positive-results synthesis — robust frontier-model split on a constraint-graph EDA workflow

**Design-only synthesis (updated).** Supersedes `docs/synthetic_p14_positive_results_synthesis.md` by
folding in the **Qwen k=5** result alongside DeepSeek k=5. The headline strengthens: `workflow_handoff_0006`
now shows a **robust** frontier-model split (Qwen 8/8; DeepSeek 6/8 with 2 wrong assignments). No code, no
tasks, no probes — analysis only.

---

## 1. Current checkpoint

- **HEAD:** `660bf85` (`docs: report p14 constraint graph qwen k5 probe`)
- **Branch:** `synthetic-phase0a` — **local-only, not pushed** (no upstream), working tree clean.
- **Latest relevant commits (newest first):**
  - `660bf85` — Qwen k=5 preserved 0006 report (robust-saturation result)
  - `4243807` — prior positive-results synthesis (superseded by this doc)
  - `fb6aebf` — DeepSeek k=5 preserved 0006 report (reproducible-signal result)
  - `47d108e` — Qwen+DeepSeek k=3 0006 capability probe report (first clean signal)
  - `1057624` — `feat: add workflow handoff constraint graph variant` (0006 implementation)
  - `326961b` — affirmative-only grader markers fix (Phase-4J)
  - `f4ef140` — opt-in probe-artifact preservation (Phase-4I)
  - (checkpoints: `synthetic-p14-positive-results-synthesis-4243807` tag + bundle at `4243807`)

---

## 2. Executive summary

- p10–p14 v4 **saturated or produced only efficiency/protocol stress** — no frontier capability wall.
- `workflow_handoff_0006` introduced a **true constraint-graph** task (no single visible artifact reveals
  the full target; the answer is the unique intersection of independent constraints).
- **Qwen3.7-Max solved 8/8** (3/3 k=3 + 5/5 k=5), 0 wrong assignments — robust saturation.
- **DeepSeek-V4-Pro solved 6/8** (2/3 k=3 + 4/5 k=5) with **2 byte-confirmed wrong global assignments**.
- Therefore p14 now has a **clean positive capability result: a frontier-model split** on this
  constraint-graph EDA workflow family. (Task/family-specific — not a universal model ranking.)

---

## 3. Negative ladder recap

| phase | mechanism | outcome |
|---|---|---|
| p10 | single constraint drift | saturated |
| p11 | flow handoff (single fault) | saturated |
| p12 | multi-artifact repair | saturated |
| p13 | trajectory / evidence handoff (provenance validated) | saturated |
| p14 v1 | ordered evidence-chain | saturated |
| p14 v2 | cross-source conflict | no stable difficulty |
| p14 v3 | scenario/corner conflict | saturated |
| p14 v4 (`0005`) | multi-conflict partially-truthful decoy | **efficiency/protocol stress, not a capability wall** (DeepSeek pass^5 = 1.0) |

Every weaker mechanism was built, validated on real PT, probed on frontier models, and found solvable.

---

## 4. Transition to constraint graph

- The failure of weaker mechanisms motivated `0006`. The recurring lesson: when a task's correct answer is
  **directly readable** from a single file (spec/manifest authority tuple), a strong agent reads it off and
  rejects decoys by per-axis cross-checks — cost rises, correctness does not fall.
- `0006` **removed the directly-readable full authority tuple.** The manifest declares only the netlist
  *family* + interface (C1); spec gives the joint-validity *table* (C3); the clock is pinned by tool-derived
  coverage (C2). The target is recoverable only by **intersecting** the constraints.
- `0006` introduced a **hidden uniqueness gate**, offline-proven and stored in hidden truth:
  - **36 candidate assignments; exactly one satisfies all constraints** = `[netlist_v2, clk_main, slow, func]`.
- Decoys are **locally plausible but globally invalid** (each satisfies a subset of constraints).
- The task requires **joint constraint inference, not single-file authority lookup**.

---

## 5. Final workflow_handoff_0006 results

| model | k=3 | k=5 | combined | wrong global assignments |
|---|---|---|---|---|
| **Qwen3.7-Max** | 3/3 pass | 5/5 pass | **8/8 (100%)** | **0** |
| **DeepSeek-V4-Pro** | 2/3 pass | 4/5 pass | **6/8 (75%)** | **2 (byte-confirmed)** |

- **Capability pass rates:** Qwen pass^k = 1.0 (8/8); DeepSeek pass^k = 0.75 (6/8).
- **Protocol notes:** both models show mild efficiency/protocol stress (some trials hit the 60-action cap
  without a clean FINISH but still score 1.0): Qwen 2/5 budget_exhausted at k=5; DeepSeek 3/5 at k=5.
  These are **separate from capability** — every such episode still scored 1.0 on final-state grading.
- **Preservation status:** all trials preserved (5 editable files + manifest + hashes + component_scores);
  no hidden truth / secrets / forbidden files in any preserved tree.

---

## 6. DeepSeek failure analysis (both wrong assignments)

**Failure 1 (k=3, HIGH confidence, score 0.20):**
- submitted `scenario=func, corner=typ` (expected `slow/func`).
- a **value-swap / axis-binding error**: the correct *corner* value `func` was bound to the *scenario* axis.
- satisfied **C1+C2** (netlist_v2 + clk_main); violated **C3** only. PT still signed off (signoff=1.0).

**Failure 2 (k=5 trial3, MEDIUM confidence, score 0.10):**
- submitted `scenario=func, corner=slow_1.0V_125C, clock=clk` (expected `slow/func/clk_main`).
- **axis-binding + value-invention + wrong clock**: again `func`→scenario slot, plus a **hallucinated PVT
  corner string** (`slow_1.0V_125C`, not in the domain) and a wrong/generic clock name (`clk`).
- satisfied **only C1**; violated C2/C3/C4 **+ signoff** (PT did not pass — the invented corner/wrong clock
  broke the run).

**Shared pattern:** both are **wrong global assignment / axis-value binding failures.** Neither is:
- an evidence-chain break (both had internally-consistent stage1+stage2 on the wrong package),
- a protocol/no-FINISH slip (both FINISHed with confidence),
- an infra failure,
- an oracle failure,
- or simple decoy-following (failure 2 invented a value present in no shipped source).

The difficulty is specifically **joint constraint inference / axis-value binding**.

---

## 7. Qwen robustness analysis

- Qwen **inferred the unique global assignment `[netlist_v2, clk_main, slow, func]` in all 8 trials**
  (3/3 k=3 + 5/5 k=5).
- Qwen **satisfied C1–C8 in all 8 preserved trials** (0 wrong assignments, 0 overconfident_wrong).
- Some Qwen runs still had **protocol/efficiency stress**: 2/5 k=5 trials hit the 60-action cap
  (`budget_exhausted`, no FINISH) **despite total_score=1.0** — i.e., Qwen reached the correct final state
  but did not always close the protocol within budget. This is a separate, non-capability signal.
- **Qwen showed no capability failures on this task family instance.**
- **Do not claim universal superiority:** the claim is **task-specific robustness** — on
  `workflow_handoff_0006`, Qwen robustly saturates and DeepSeek reproducibly fails. DeepSeek outperforms
  Qwen on other tracks in this benchmark's history; this is not a universal model ranking.

---

## 8. Role of preservation and scoring audit

- **Final-workspace preservation enabled byte-confirmed failure classification.** Both DeepSeek wrong
  assignments were decoded from the preserved `flow_config.json` + hashes — not inferred.
- **Earlier unpreserved inferences could be wrong** (the 0005 "confident-wrong" was initially misguessed;
  preservation later showed it was a broken-chain protocol slip). Going forward, wrong-package /
  confident-wrong claims require preserved artifacts or must be marked inference-only.
- **`component_scores` (mirroring score.json) are authoritative** for component pass/fail.
- **`affirmative_grader_markers` are diagnostic only** (Phase-4J made them affirmative-only — no presence-
  only false positives; they agree with component_scores).
- **No hidden truth / secrets / forbidden files were preserved** in any of the 13 preserved trees across
  the 0006 probes (verified by filename + content scan).
- Net effect: **the benchmark evidence is auditable and trustworthy.**

---

## 9. Why this is a positive result

- This is **no longer only a negative ladder.** p14 now demonstrates a mechanism that creates a measurable
  frontier split, not just a cost increase.
- It shows that **constraint-graph EDA workflow tasks are more discriminative than single-hazard tasks** —
  the structural change (hide the tuple behind joint constraints, not behind more decoys) is what produced
  the signal.
- It **validates the generator/oracle/acceptance-filter approach**: hidden uniqueness proof (36→1),
  forgery-resistant consumed-netlist/clock/scenario/corner echecks, and an acceptance matrix that every
  decoy / single-axis / stage-only / hand-edited / forbidden-edit recovery fails.
- It **provides a seed for a broader family** of constraint-graph EDA workflows (more axes, tighter
  joint-validity tables, optional cross-tool confirmation).

---

## 10. Limitations (honest)

- **Only one `0006` instance exists** — the Qwen-saturates / DeepSeek-fails split is for this single task.
- **Sample sizes are still small:** Qwen n=8, DeepSeek n=8 (each across two separate k=3+k=5 runs).
- **Results are task/family-specific, not a universal model ranking.**
- **PT-only** — no DC/Formality cross-tool confirmation yet.
- **Cost is nontrivial** — each 0006 episode is ¥4–16; a k=5 run is ~¥50.
- **Command trace remains sparse** (agentlog command fields are not full command text) — a deferred
  driver-level change.
- **Qwen k=5 helps but is still not huge n** (8/8 is strong but finite; a wrong-assignment tail cannot be
  fully excluded, though none was observed).
- **No public release / no push yet** — branch is local-only.

---

## 11. Recommended next steps

A. **Commit this updated synthesis after review.**
B. Then choose one of:
   1. **tag/bundle** the new synthesis checkpoint, or
   2. **design `workflow_handoff_0007`** focused on **axis-binding / value-invention stress** (the
      discriminating axis both DeepSeek failures hit), or
   3. **generalize `0006` into a small generated family** (a handful of constraint-graph tasks with
      different axes/joint-validity tables) to test whether the split generalizes.
C. **Do not run more `0006` probes immediately** unless tighter confidence intervals on the DeepSeek
   failure rate are needed.
D. **Do not return to single-hazard variants** (v1–v4 are saturated).

---

## 12. Suggested research framing

Possible framings (one or a combination):

- *"Negative ladder to positive constraint-graph signal."* — the methodological arc.
- *"Real-tool synthetic EDA workflow benchmark with provenance-backed hidden oracle."* — the substrate.
- *"Single-hazard handoff saturates; constraint-graph recovery produces a frontier split."* — the core
  empirical finding.
- *"Preserved artifacts make agent failure classification auditable."* — the infrastructure lesson.

---

## 13. Final conclusion

- p14 now has **both**:
  - a **validated synthetic workflow-generator substrate** (real PT, hidden oracle, acceptance filters,
    offline uniqueness proof), and
  - a **positive constraint-graph capability signal** (a robust frontier-model split).
- `workflow_handoff_0006` **separates Qwen and DeepSeek on this task family** — Qwen 8/8 robust
  saturation; DeepSeek 6/8 with 2 byte-confirmed axis-binding failures. This is task/family-specific, not a
  universal ranking.
- **The next frontier is scaling from one constraint-graph instance to a generated family** — to test
  whether the split generalizes and to turn a single positive signal into a discriminative benchmark axis.

---

*Compliance: design-only. No code, no tasks, no models, no other-worktree changes. Not committed, not
pushed — awaiting review.*
