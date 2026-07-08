# p14 0006/0007/0008 ablation synthesis — what produces (and what doesn't) an axis-binding frontier split

**Design-only synthesis.** Compares `workflow_handoff_0006` (the durable positive frontier split), `0007`
(explicit typed-axis schema → saturated), and `0008` (schema hidden → also saturated) to isolate what
actually caused the 0006 difficulty. No code, no tasks, no models — analysis only. The central finding:
**schema visibility alone does not explain 0006; the difficulty depends on the specific implicit-tuple /
report-label interaction in 0006.**

---

## 1. Current checkpoint

- **HEAD:** `073927e` (`docs: report p14 implicit axis binding probe`)
- **Branch:** `synthetic-phase0a` — **local-only, not pushed** (no upstream), working tree clean.
- **Relevant commits (newest first):**
  - `073927e` — `0008` implicit-axis probe report (k=3, both models)
  - `565f9c2` — `feat: bake workflow handoff implicit axis binding task` (`0008` full build)
  - `3f386eb` — `feat: add implicit axis binding inferability gate` (`0008` gate + solver)
  - `f56b7fb` — `0008` implicit-axis *design* doc
  - `7a9477a` — `0007` axis-binding *ablation* synthesis
  - `4e74111` — `0007` axis-binding probe report (k=3, saturated)
  - `5a014cd` — `feat: add workflow handoff axis binding variant` (`0007` implementation)
  - `e4cf58e` — `0006` final positive-results synthesis
  - `660bf85` — `0006` Qwen k=5 preserved report (robust saturation)
  - `fb6aebf` — `0006` DeepSeek k=5 preserved report (reproducible-signal result)
  - `47d108e` — `0006` Qwen+DeepSeek k=3 capability probe (first clean signal)
  - `1057624` — `feat: add workflow handoff constraint graph variant` (`0006` implementation)

---

## 2. Executive summary

- **`0006` is the positive capability result** — the only p14 task that produced a robust frontier-model
  split (Qwen 8/8; DeepSeek 6/8 with 2 byte-confirmed axis-binding failures).
- **`0007` and `0008` are ablations** built to explain *why* 0006 was hard, by varying one design axis at
  a time:
  - **`0007`** added an explicit typed-axis oracle **and published the full `axis_schema.json`** →
    **saturated** (Qwen 3/3, DeepSeek 3/3, 0 wrong assignments). Publishing the vocabulary converted
    binding into vocabulary *lookup*.
  - **`0008`** kept the typed-binding oracle **but hid the schema** (implicit membership, inferred from
    non-canonical report labels / PVT notation / coverage) → **still saturated on axis-binding inference**
    (Qwen 3/3; DeepSeek 3/3 correct typed assignment, 2/3 by score only because of one stale-input-hash
    evidence-chain failure; **0 axis-binding failures**).
- **The durable lesson: schema visibility alone does not explain 0006.** Hiding the schema is necessary-but-
  not-sufficient; publishing it removes difficulty, but hiding it does **not** automatically restore it.
- **The exact form of implicit constraint presentation matters** — specifically the 0006-style
  implicit-tuple / report-label interaction. That interaction, not typed-binding per se, is what produced
  the DeepSeek failures.

---

## 3. Recap: workflow_handoff_0006 (the positive result)

- **Mechanism:** a hidden/implicit **constraint graph** — no single visible file states the target tuple;
  it is the intersection of C1 (netlist family) × C2 (clock coverage) × C3 (scenario/corner signoff pair).
- **Uniqueness:** **36 candidate assignments → exactly one** satisfying assignment
  `[netlist_v2, clk_main, slow, func]` (proven by `enumerate_constraint_graph`).
- **Qwen3.7-Max:** combined **8/8** pass (3/3 k=3 + 5/5 k=5), 0 wrong assignments — robust saturation.
- **DeepSeek-V4-Pro:** combined **6/8** pass with **2 byte-confirmed wrong global assignments** (~25%
  observed failure rate, n=8):
  1. k=3: `scenario=func, corner=typ` — a **value-swap** (corner value in scenario slot; signoff green,
     scored 0.20).
  2. k=5: `scenario=func, corner=slow_1.0V_125C, clock=clk` — **value-invention** (hallucinated PVT
     corner) + axis-swap + wrong clock alias (signoff failed, scored 0.10).
- **Conclusion:** a genuine **frontier-model split** on a real capability axis (joint constraint inference
  / axis-value binding), not protocol/efficiency stress. This is the durable positive result.

---

## 4. Recap: workflow_handoff_0007 (ablation 1 — schema published)

- **Mechanism:** added the **typed-axis oracle** (type-membership checks folded into `EVIDENCE_OK`;
  signoff-green-but-mis-typed rejected) **and published the full `axis_schema.json`** (closed vocabularies
  + PVT mapping + type rules as readable JSON).
- **Uniqueness:** **294 candidate typed assignments → exactly one** (the axis domains include trap values
  so swapped/PVT/wrong-clock assignments are machine-provably rejected).
- **Oracle validated:** on real PT, golden = 1.0; a signoff-green-but-mis-typed package scores **0.20**
  below pass (`EVIDENCE_OK` absent, `MISTYPED_BINDING_REJECTED`).
- **Probe (k=3):** Qwen 3/3, DeepSeek 3/3, **0 wrong assignments** across 6 episodes.
- **Conclusion:** the typed oracle is a valid, reusable asset — but the task **saturated**. Publishing the
  complete schema **converted typed inference into vocabulary lookup**: once `scenario_axis {slow,typ,fast}`
  and `corner_axis {func,test,lowpower}` were readable, DeepSeek no longer had to *infer* axis membership,
  so the value-swap / PVT-invention errors it made on 0006 became trivially avoidable.

---

## 5. Recap: workflow_handoff_0008 (ablation 2 — schema hidden)

- **Mechanism:** kept the typed-binding oracle **but shipped NO `axis_schema.json`**. Axis membership is
  **implicit** — recoverable only from non-canonical report labels (`op_point`/`mode`), spec terminology,
  PVT notation, and a coverage fact. (A domain-aware scripted solver recovers the tuple from visible
  artifacts only — the human-inferrability gate; no leak, no full tuple in any single file.)
- **Uniqueness:** **294 → exactly one** (identical oracle to 0007).
- **Real-PT validated (Phase-4R):** golden = 1.0; signoff-green-but-mis-typed = 0.20 below pass.
- **Probe (k=3):** Qwen **3/3**; DeepSeek **2/3 by score but 3/3 correct typed assignment**. The single
  DeepSeek non-pass (trial2, 0.20) is byte-confirmed as a **stale-input-hash evidence-chain failure**
  (DeepSeek edited `flow_config.json` after generating evidence): `input_hashes_match_ref=WRONG`,
  `run_nonce_matches_ref=WRONG`, **every typed-binding echeck passed**, PT report digest matched golden.
  It is a **reliability/protocol** failure (overconfident, high confidence), **not** an axis-binding error.
- **Conclusion:** **no restored axis-binding difficulty.** Hiding the schema alone is **insufficient** —
  both models still infer the implicit typed assignment correctly (6/6 correct assignments, 0 axis-binding
  failures).

---

## 6. What 0007 and 0008 ruled out

- The 0006 difficulty is **not** simply due to the **absence of a typed-axis oracle** — 0008 had the oracle
  and still saturated on the *capability* axis (the oracle hardened rejection, but didn't create difficulty).
- The 0006 difficulty is **not** simply due to **full schema visibility** — 0008 hid the schema and still
  saturated on axis-binding inference.
- **Publishing the schema removes difficulty (0007), but hiding the schema does not automatically restore
  it (0008).** So schema visibility is a real but **insufficient** causal variable.
- **Typed-binding checks are useful for oracle hardening** (signoff-green-but-mis-typed rejection is a
  genuine, reusable mechanism), but **not by themselves sufficient to create capability difficulty.**

The controlled variable across 0007→0008 was schema visibility; the observed effect was null on
axis-binding capability. The 0006 difficulty must therefore come from a different variable.

---

## 7. What remains special about 0006

The 0006 difficulty most likely resides in its **specific implicit-tuple / report-label interaction** — the
*way* the scenario/corner/clock values were presented and cross-checked, which is materially different from
both 0007 and 0008:

- **Report-label interaction:** in 0006, reports carried `scenario=`/`corner=` field labels *with wrong
  values* in locally-plausible decoys (report_A: right netlist/clock, wrong scenario/corner; report_B: right
  scenario/corner, stale netlist; report_C: wrong clock). The agent had to **cross-check conflicting
  contexts** and intersect — and DeepSeek mis-resolved the conflict into a value-swap.
- **Implicit tuple presentation:** 0006 gave **no glossary, no public_check_summary, no coverage-fact
  shortcut** — only the abstract spec ("exactly one signoff pair") + the decoys. There was no clean
  domain-aware solver path; the agent had to reason under genuine ambiguity.
- **Absence of a fairness scaffold:** unlike 0008 (which added a glossary + a public pairwise summary + a
  coverage fact to *prove* human-inferrability), 0006 was leaner — which left more room for the model to
  mis-bind. (0006 was still fair — it had a unique answer — but it did not hand the model the inference
  structure.)
- **Decoy-induced errors:** 0006's three decoys each agreed on a *different* wrong axis, so no majority
  vote worked; the agent had to *intersect*, and DeepSeek's intersection sometimes produced an
  axis-binding error (the value-swap) rather than the unique assignment.
- **0006 forced global consistency without making type semantics explicit or easily inferred** — exactly
  the regime where DeepSeek slipped. 0007 made them explicit (saturated); 0008 made them *inferable* via a
  clean scaffold (also saturated). 0006 sat in a narrower band where they were neither explicit nor cleanly
  inferable.

In short: 0006's difficulty is an **interaction effect** (implicit tuple × ambiguous report labels × no
inference scaffold), not a main effect of schema visibility or typed-binding alone.

---

## 8. Reliability / protocol findings (kept separate from capability)

- **0005** was pure **efficiency/protocol stress** (DeepSeek pass^5 = 1.0; residual signal was wall-time /
  PT-runs / no-FINISH budget_exhausted) — no capability failure.
- **0007 and 0008 also show budget_exhausted / no-FINISH** despite correct scores (0007: 4/6; 0008: 2/6
  budget_exhausted, all scoring 1.0). This is a **protocol** signal, separate from capability.
- **DeepSeek 0008 trial2 is the clearest reliability/protocol data point:** a byte-confirmed
  **stale-input-hash evidence-chain failure** — correct assignment, genuine fresh PT evidence, but a
  post-generation `flow_config` edit broke the input-hash binding. **overconfident** (high confidence on a
  broken chain). This is *not* a capability failure.
- **Preservation was essential** to classify it correctly: without the preserved `flow_config` +
  `evidence_manifest` + the re-run `EVIDENCE_DETAIL`, the 0.20 could have been misread as an axis-binding
  failure. **Always require preserved artifacts (or mark inference-only) for any wrong/failure claim.**
- **Keep capability vs reliability/protocol strictly separate** in every probe report.

---

## 9. Design implications for workflow_handoff_0009

- **Do not merely hide the schema** (0008 proved that's insufficient).
- **Do not publish a full schema** (0007 proved that removes difficulty).
- **Reconstruct the 0006-style implicit report-label ambiguity** *while* adding the typed-binding oracle
  checks (the oracle is reusable; the 0006 ambiguity is the difficulty source).
- **Use multiple report labels whose semantic roles must be inferred from conflict resolution, not from
  examples** — i.e., the agent must resolve *which* value goes on *which* axis by cross-checking
  conflicting reports, not by reading a glossary.
- **Avoid a domain-aware solver that is too direct** — unless it is intentionally the *fairness proof*
  (as in 0008's gate). If a scripted solver trivially recovers the tuple, a strong model will too.
- **Consider preserving the exact confusing structure of 0006** (no clean glossary/public-summary/coverage
  shortcut; decoys that agree on different wrong axes) **while scaling it to more instances** — so the
  difficulty generalizes beyond one hand-built task.

The guiding principle: difficulty should come from **resolving ambiguity across conflicting evidence under
global-consistency pressure**, not from vocabulary hiding or lookup.

---

## 10. What not to do

- **Do not claim 0007 or 0008 are new positive difficulty results.** They are ablations (0007 saturated by
  publishing; 0008 saturated by hiding).
- **Do not run more 0008 trials expecting axis-binding failure** without a design change — 0 axis-binding
  failures across k=3 establishes that hiding the schema alone doesn't restore difficulty.
- **Do not discard the typed-binding oracle** just because 0007/0008 saturated — it is a valid, reusable
  hardening mechanism (signoff-green-but-mis-typed rejection).
- **Do not assume schema visibility is the only causal variable** — the 0007/0008 null result proves it
  isn't.
- **Do not return to single-hazard variants** (p14 v1–v4 are saturated; the constraint-graph axis is where
  any residual difficulty lives).

---

## 11. Recommended next step

Either:

**A. If continuing task design:**
- Design `workflow_handoff_0009` around the **specific 0006 implicit-tuple / report-label interaction**
  (§7), keeping the typed-binding oracle, avoiding a full schema or overly-helpful public summaries, and
  preserving human-inferrability without making a direct solver trivial. **Study the 0006 interaction
  first** (what exactly made DeepSeek mis-bind there) before generalizing.

**B. If consolidating:**
- Stop p14 task generation and prepare a research write-up: the negative ladder (p10–p14 v4), the **0006
  positive split**, and the **0007/0008 ablation** explaining why the difficulty is fragile.

**Preferred recommendation:** **write this synthesis now** (this document), **then decide** whether to
design 0009 (option A) or consolidate the paper narrative (option B). Do not run more probes before that
decision.

---

## 12. Final conclusion

- **`0006` remains the central positive result** — the one robust p14 frontier-model split, with byte-
  confirmed DeepSeek axis-binding failures.
- **`0007` and `0008` explain why that difficulty is fragile:** publishing the schema saturates (lookup),
  and hiding it is insufficient (the 0008 reports/glossary still give enough structure to infer binding).
- **The next frontier is not just typed binding, but controlling how implicit constraints are presented** —
  specifically the 0006-style interaction of ambiguous report labels, conflicting decoys, and global-
  consistency pressure, *without* an inference scaffold that collapses it into a lookup or a clean solver
  path. That interaction, not schema visibility, is the variable to study and generalize.

---

*Compliance: design-only. No code, no tasks, no models, no other-worktree changes. Not committed, not
pushed — awaiting review.*
