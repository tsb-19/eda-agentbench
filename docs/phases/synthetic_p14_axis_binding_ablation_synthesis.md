# p14 axis-binding ablation synthesis — workflow_handoff_0007

**Design-only synthesis.** Distills the lesson from `workflow_handoff_0007`: the typed-axis oracle works
(signoff-green-but-mis-typed is correctly rejected), but **publishing the complete axis schema makes the
task saturate**. Future stronger variants should keep typed-binding checks *hidden in the oracle* while
requiring axis membership to be **inferred from evidence/provenance**. No code, no tasks, no models —
analysis only.

---

## 1. Current checkpoint

- **HEAD:** `4e74111` (`docs: report p14 axis binding probe`)
- **Branch:** `synthetic-phase0a` — **local-only, not pushed** (no upstream), working tree clean.
- **Latest relevant commits (newest first):**
  - `4e74111` — `0007` axis-binding probe report (k=3, both models saturated)
  - `5a014cd` — `feat: add workflow handoff axis binding variant` (`0007` implementation)
  - `4d5fb5e` — `0007` axis-binding *design* doc
  - `e4cf58e` — final positive-results synthesis (the `0006` frontier split)
  - `660bf85` — `0006` Qwen k=5 preserved report (robust-saturation result)
  - `fb6aebf` — `0006` DeepSeek k=5 preserved report (reproducible-signal result)
  - `47d108e` — `0006` Qwen+DeepSeek k=3 capability probe (first clean signal)
  - `1057624` — `feat: add workflow handoff constraint graph variant` (`0006` implementation)

---

## 2. Background: why 0007 existed

- `workflow_handoff_0006` produced the **first robust p14 frontier-model split** — the first p14 task
  whose difficulty is capability, not protocol:
  - **Qwen3.7-Max:** 8/8 (k=3 + k=5), **0 wrong assignments** — robust saturation.
  - **DeepSeek-V4-Pro:** 6/8, **2 byte-confirmed wrong global assignments** — both **axis-binding /
    value-invention errors**:
    1. k=3: `scenario=func, corner=typ` — a value-swap (corner value in the scenario slot).
    2. k=5: `scenario=func, corner=slow_1.0V_125C, clock=clk` — axis-swap + invented PVT corner + wrong
       clock alias.
- `workflow_handoff_0007` was designed to **target those exact failure modes directly**: axis-value
  binding, value swaps across axes, out-of-domain value invention, typed evidence/provenance consistency.
- The goal was **not more decoys** (p14 v4 already proved decoy count only raises cost). The goal was
  **stricter typed-axis binding** — a closed typed vocabulary, type-membership checks in the oracle, and a
  mutant that ships the DeepSeek value-swap as its starting state.

---

## 3. 0007 contract validation (the positive part)

`0007` is a **valid oracle contract**. The decisive pre-model gates held on real PrimeTime (b04) and in
unit tests:

- **Typed uniqueness:** the typed constraint graph enumerates **294 candidate typed assignments → exactly
  1** satisfying all constraints, equal to the expected `[netlist_v2, clk_main, slow, func]`. Swapped-axis,
  PVT-substitution, and wrong-clock-alias assignments are *proven* to violate typed constraints.
- **Signoff-green-but-mis-typed is correctly rejected:** because the report body is corner-independent on
  the single `tiny.db`, a package with the correct netlist+clock PrimeTime-**signs-off green** even when
  scenario/corner are swapped. On real PT, that package returns `SIGNOFF_OK=1` but `EVIDENCE_OK=0` and
  `MISTYPED_BINDING_REJECTED`, scoring **0.20 — below pass**. (The `0.783` echeck-fraction is a diagnostic;
  the evaluator's gate is on `EVIDENCE_OK`, which is absent.)
- **Typed-binding checks work:** `AXIS_SCHEMA_OK`, `TYPED_BINDING_OK`, `PVT_LABEL_OK`,
  `EVIDENCE_CHAIN_TYPED_OK` are emitted on the golden and withheld on mis-typed packages.
- **Evaluator unchanged.** All new logic is gated in the hidden `grade_workflow.py` on `truth["axis_schema"]`.
- **`0001–0006` behavior preserved** byte-for-byte (the new grader block is inert for them; output is
  identical; the shared grader was re-synced uniformly across all 7 tasks).

So `0007` is a **successful oracle-contract validation**: the typed-axis mechanism is real and
forge-resistant. What it is *not* is a capability-difficulty signal.

---

## 4. 0007 probe result (the negative part)

Preserved k=3 probe, Qwen3.7-Max + DeepSeek-V4-Pro only, 1800s / 60 actions / temp 0.7 / confidence
elicited / preservation on. 6 episodes, ¥56.17 (cap raised ¥60→¥62 mid-probe; actual total under both).

- **Qwen3.7-Max:** **3/3 pass**, 0 wrong assignments.
- **DeepSeek-V4-Pro:** **3/3 pass**, 0 wrong assignments.
- **All 6 byte-confirmed** the **correct typed assignment** `[netlist_v2, clk_main, slow, func]`
  (decoded from preserved `flow_config.json` + `constraints.sdc`).
- **0 value-swaps, 0 PVT substitutions, 0 wrong-clock aliases, 0 typed-field mismatches.**
- **protocol_clean 2/6** (t1 Qwen, t3 DeepSeek — both FINISH+high confidence); **4/6 budget_exhausted**
  (hit the 60-action cap, no FINISH) but **all 4 still scored 1.0** on final-state grading.
- **Conclusion: capability SATURATED; residual signal is efficiency/protocol stress only** (matches the
  `0006` pattern). Per the interpretation rule (both models solve all valid trials → saturated).

---

## 5. Comparison with 0006

| model | `0006` (constraint-graph, hidden tuple) | `0007` (axis-binding, published schema) |
|---|---|---|
| Qwen3.7-Max | 8/8, 0 wrong | **3/3, 0 wrong** |
| DeepSeek-V4-Pro | **6/8, 2 wrong global assignments** (axis-binding / value-invention) | **3/3, 0 wrong** |

**The typed-axis target did not reproduce the DeepSeek `0006` failure mode.** `0007` was built to provoke
exactly the value-swap and PVT-invention errors DeepSeek made on `0006`, yet DeepSeek made **none** of
them in 3 trials — and even improved relative to `0006` (6/8 → 3/3). `0007` is **not stronger** than
`0006`; on this task/family it is **easier** for DeepSeek.

---

## 6. Likely cause

- **`axis_schema.json` exposed the allowed vocabulary and type membership directly.** The file published
  `scenario_axis {slow,typ,fast}`, `corner_axis {func,test,lowpower}`, `clock_axis {clk_old,clk_main}`,
  `pvt_label_axis`, the PVT→(scenario,corner) mapping, and the type rules — all as readable JSON.
- **Once `scenario_axis` and `corner_axis` were explicit, the model no longer had to *infer* axis
  membership** — it could look up which slot each value belongs to. The `func`-in-scenario /
  `typ`-in-corner swap and the PVT-as-corner invention that DeepSeek made on `0006` (where axis membership
  had to be *inferred from implicit constraints*) became trivially avoidable.
- **The challenge became rule-following with a visible schema**, which strong agents handle.
- **The design principle *"the challenge is binding, not vocabulary hiding"* was too generous for this
  benchmark goal.** Publishing the vocabulary is correct for *software-engineering clarity* but defeats
  *capability measurement*: it converts a typed-inference problem into a vocabulary-lookup problem.

This is the same discoverability lesson that recurred across p14: when the answer (or here, the valid
value vocabulary) is directly readable, a strong agent reads it off. `0006` kept the tuple *implicit*
(intersect hidden constraints) and produced the split; `0007` made the vocabulary *explicit* and saturated.

---

## 7. Design lesson

- **Keep the typed-binding oracle.** It correctly rejects signoff-green-but-mis-typed / value-swap /
  PVT-substitution / wrong-clock-alias packages (0.20 below pass on real PT).
- **Keep signoff-green-but-mis-typed rejection.** It is the load-bearing innovation of `0007` — the thing
  `0006`'s oracle could only partially enforce.
- **But do NOT publish a complete schema that directly resolves the binding.** A full `axis_schema.json`
  with direct membership lists is what removed the difficulty.
- **Future tasks should require axis membership / type semantics to be INFERRED from evidence, provenance,
  and consistency checks** — e.g. axis membership recoverable only by cross-checking reports, digests, and
  consumed-input fields, never by reading a schema file.
- **The goal is typed *inference*, not vocabulary *lookup*.** Binding must be the load-bearing step, and
  binding is only load-bearing when the type domains are not handed to the agent.

---

## 8. Implication for workflow_handoff_0008

A hypothetical `0008` that seeks genuine axis-binding difficulty should **combine**:

- **`0006`-style hidden constraint graph** — no single visible file reveals the target tuple.
- **`0007`-style typed-binding oracle** — type-membership + signoff-green-but-mis-typed rejection stay in
  the hidden grader.
- **Partial or indirect schema exposure** — at most *partial* type information (e.g. "scenario and corner
  are disjoint typed axes"), never a complete membership list.
- **Evidence-derived axis membership** — the agent must recover which value belongs to which axis by
  cross-checking evidence (a value that appears as a signoff mode in one report, as a coverage condition in
  another, etc.), not by reading a schema.
- **PVT metadata that can be interpreted only through report/provenance consistency** — a PVT label is
  accepted only if it maps to a `(scenario, corner)` pair that is *jointly attested* by the evidence chain,
  not because a published mapping table says so.

**Avoid:**
- a full `axis_schema.json` with direct membership lists (the `0007` failure mode),
- any direct tuple leak,
- simple "read the schema, then fix the fields" workflows.

`0008` is the natural successor **only if** the binding-difficulty is restored by hiding the type
vocabulary. Do **not** build `0008` without that change — it would just reproduce `0007`'s saturation.

---

## 9. What not to do

- **Do not run more `0007` trials expecting capability failure.** k=3 = 0/6 axis-binding failures; the
  qualitative result (saturation) is established. More trials only tighten an already-zero observed rate.
- **Do not claim `0007` is stronger than `0006`.** It is not — DeepSeek went 6/8 → 3/3.
- **Do not remove the typed-binding oracle just because `0007` saturated.** The oracle is valid and is the
  reusable asset; the saturation came from the *published schema*, not from the oracle.
- **Do not revert to single-hazard variants** (p14 v1–v4 are saturated; the constraint-graph axis is where
  any residual difficulty lives).
- **Do not publish complete schemas in future hard variants.**

---

## 10. Research framing

Frame `0007` as three things, honestly:

1. **An ablation** showing that an *explicit* type schema **removes** the axis-binding difficulty that
   `0006`'s *implicit* constraint graph produced. (The controlled variable is schema visibility; the
   observed effect is DeepSeek 6/8 → 3/3.)
2. **An oracle validation** showing that signoff-green-but-mis-typed packages can be rejected on real PT
   via typed-binding checks folded into the master evidence gate — independent of signoff status.
3. **A design lesson** for future constraint-graph tasks: keep the typed-binding oracle; make axis
   membership *inferred*, not *published*.

It is **not** a new positive capability result, and the reports say so explicitly.

---

## 11. Recommendation

- **Commit this synthesis after review.**
- Then choose one of:
  - **A. Design `workflow_handoff_0008`** with hidden/implicit typed-axis inference (the `0006` hidden
    graph + the `0007` typed oracle + evidence-derived axis membership + provenance-only PVT
    interpretation). **Preferred if pursuing stronger capability** — and **design first, no more `0007`
    probes.**
  - **B. Stop p14 task generation** and prepare a broader results narrative (the `0006` frontier split is
    the positive result; `0007` is the ablation that explains *why* discoverability must be controlled).

**Preferred if pursuing stronger capability:** design `0008` first (a hidden-vocabulary typed-binding
task), and run **no more `0007` probes**.

---

*Compliance: design-only. No code, no tasks, no models, no other-worktree changes. Not committed, not
pushed — awaiting review.*
