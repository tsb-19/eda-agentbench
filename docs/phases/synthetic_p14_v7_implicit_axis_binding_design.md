# p14 v7 design — workflow_handoff_0008 implicit typed-axis constraint graph

**Design-only (Phase-4P).** Specifies `workflow_handoff_0008`, `hazard_type =
implicit_typed_axis_binding`, as the synthesis of `0006` (implicit/hidden constraint graph → real frontier
split) and `0007` (typed-binding oracle → ablation: saturated because the schema was published). No code, no
tasks, no models — this is a reviewable design. Builds on the accepted ablation synthesis (HEAD `7a9477a`).

Goal: **keep the `0007` typed-binding oracle** (signoff-green-but-mis-typed rejection; type-membership
checks) **but make axis membership implicit** — recoverable only by cross-referencing evidence, provenance,
and domain knowledge, never by reading a schema. This is the design lesson from the ablation.

---

## 1. Motivation

- `workflow_handoff_0006` produced the **real positive frontier split** — the only p14 task whose
  difficulty is capability: Qwen 8/8, DeepSeek 6/8 with **2 byte-confirmed axis-binding / value-invention
  errors**. Its mechanism was an **implicit constraint graph**: no single visible file stated the target
  tuple; it was the intersection of netlist-family × clock-coverage × scenario/corner-signoff-pair.
- `workflow_handoff_0007` was built to **target those exact axis-binding failures** (value-swap mutant,
  typed-axis oracle, PVT-substitution rejection). The **oracle contract is valid** (294→1 typed uniqueness;
  signoff-green-but-mis-typed scores 0.20 on real PT). **But the k=3 probe saturated** (Qwen 3/3, DeepSeek
  3/3, 0 axis-binding errors). DeepSeek went 6/8 → 3/3.
- The likely reason: **`axis_schema.json` made binding a vocabulary-LOOKUP task, not an INFERENCE task.**
  Once `scenario_axis {slow,typ,fast}` and `corner_axis {func,test,lowpower}` were published as readable
  JSON, the model no longer had to *infer* axis membership — it could look it up — so the value-swap /
  PVT-invention errors that DeepSeek made on `0006` (where membership had to be inferred) became trivially
  avoidable.
- `0008` should **preserve the typed-binding checks** (they are the reusable `0007` asset) **while making
  axis membership implicit**, exactly as in `0006`. The controlled variable vs `0007` is **schema
  visibility**; the expected effect (from the ablation) is that difficulty returns.

---

## 2. Design principle

**Typed constraints enforced by the oracle; type membership inferred by the agent.**

- The **typed axes** (netlist / clock / scenario / corner / pvt_label) and their closed vocabularies are
  defined in **hidden truth** and enforced by the hidden `grade_workflow.py` — never in a visible schema.
- The agent must **infer type membership from artifacts** — from *how* and *where* each value appears
  (report headers with non-canonical labels, coverage facts, signoff-mode naming, PVT notation, decoy
  cross-checks) — **not** by reading a complete `axis_schema.json`.
- The task requires all four load-bearing steps simultaneously:
  1. **global constraint inference** — intersect independent constraints to find the unique tuple;
  2. **typed axis inference** — decide which axis each candidate value belongs to, from usage/context;
  3. **provenance consistency** — the evidence chain's typed fields must match the consumed package;
  4. **evidence-chain repair** — regenerate stage1→stage2 from the repaired typed package.
- A package that satisfies global constraints but mis-binds an axis (e.g., a corner value in a scenario
  field, a PVT label as a corner) must fail **even if PT signoff is green**, exactly as in `0007`.

---

## 3. Public information policy

**Visible (partial clues only):**
- partial naming conventions in `spec.md` (e.g., "the design has a slow operating point and a functional
  signoff mode"; "PVT descriptors such as `slow_1.0V_125C` characterize, not select");
- **non-canonical field labels** in reports (e.g., `op_point`, `mode`, `cond`) — *not* `scenario`/`corner`;
- examples of valid report fields and a PVT-descriptor example (so PVT notation is recognizable);
- ambiguous report/provenance labels the agent must disambiguate;
- `public_check_summary.json` reporting **typed/provenance inconsistencies** symptom-level (verdict-first);
- decoy reports + an evidence summary.

**Must NOT be visible:**
- a complete `axis_schema.json` (the `0007` collapse mode);
- any full `value → axis` mapping table;
- the final tuple (`netlist_v2/clk_main/slow/func`);
- hidden truth / `handoff_truth.json`;
- any direct "answer table."

---

## 4. Typed axis model (hidden; public artifacts expose only partial clues)

The hidden typed axes are unchanged from `0007` (so the `0007` oracle logic is reusable):
`netlist_axis {netlist_v1.v, netlist_v2.v}`, `clock_axis {clk_old, clk_main}`, `scenario_axis {slow,typ,fast}`,
`corner_axis {func,test,lowpower}`, `pvt_label_axis {slow_1.0V_125C, typ_1.0V_25C, fast_0.8V_0C}`.

But **public artifacts only expose partial clues** — the axis membership is recoverable only by reasoning:
- `slow` appears in report context as an **operating-point** value (e.g. `op_point=slow`) and in the spec's
  design intent as "the slow operating point"; the agent must infer `op_point ≡ scenario_axis`.
- `func` appears as a **mode** (`mode=func`) and in the signoff naming; the agent must infer `mode ≡ corner_axis`.
- `slow_1.0V_125C` appears as a **PVT descriptor** string (recognizable by notation: `<scenario>_<V>_<T>`),
  never as an `op_point`/`mode` value in any consistent report; the agent must classify it as PVT metadata.
- `clk_main` is the only clock that yields **non-zero intended-clock coverage** on netlist_v2 (a tool-derived
  fact from `coverage.txt`); `clk_old`/`clk` produce zero coverage → infer `clk_main` is the clock.
- `netlist_v2` is the only netlist in the manifest's allowed family with the `{clk_main,din,en,dout}`
  interface → infer the netlist.

The agent must **infer type membership from usage, not schema.** A model that pattern-matches a single
field without cross-checking will mis-bind (the `0006` failure mode).

---

## 5. Artifact graph (public, agent-visible + editable/forbidden as marked)

| artifact | role | reveals | withholds |
|---|---|---|---|
| `spec.md` | design intent + **partial** terminology | interface; "slow operating point + functional mode"; PVT-descriptor example | the canonical axis names; the tuple; any value→axis table |
| `handoff_manifest.json` | **partial** authority | netlist family + interface | concrete clock/scenario/corner |
| `glossary.md` *(optional)* | **incomplete** examples | 1–2 examples per concept (a PVT descriptor; "op_point is an operating-point field") | NOT a full schema; NOT a complete vocabulary |
| `flow_config.json` *(editable)* | mutant candidate | a starting package using the **non-canonical labels** (`op_point`/`mode`) | correctness; ships a mis-bind (value-swap on the inferred axes) |
| `constraints.sdc` *(editable)* | clock binding | candidate clock | whether it matches coverage |
| `report_A` | decoy | right netlist/clock; **swapped semantic context** (`op_point=func`, `mode=slow` — labels vs values inconsistent across reports) | the correct axis binding |
| `report_B` | decoy | correct semantic mode (`op_point=slow`, `mode=func`); **stale netlist** | netlist correctness |
| `report_C` | decoy | a **PVT label used in `mode`** (looks plausible, semantically wrong) | that PVT is metadata-only |
| `evidence_D` | decoy | valid digest/upstream chain; **typed-field mismatch** (fields bound to wrong axes) | semantic correctness |
| `public_check_summary.json` | fair feedback | **typed/provenance inconsistency symptoms** (pairwise; verdict-first) | the schema; the tuple |
| `prev_signoff.log` | non-authoritative | a recent-looking summary | no authority |

Editable submitted set stays the `0006/0007` shape (`flow_config.json`, `constraints.sdc`,
`timing_report.rpt`, `evidence_manifest.json`, `stage2_summary.json`). Netlists, library, `axis_schema`
(**not shipped**), `grade_workflow.py`, `handoff_truth.json`, decoys remain **forbidden** (anti-cheat).

**Key vs `0007`: there is NO `axis_schema.json` shipped.** `glossary.md` (if present) is deliberately
incomplete — examples, not a vocabulary list.

---

## 6. Constraint graph (generator + hidden oracle enforce)

Same shape as `0006/0007` (`over`/`allowed` tuples), with typed-binding constraints **inferred from
evidence fields**, not from a published schema:

- **C1 netlist/interface** — consumed netlist ∈ manifest family + matches the spec interface.
- **C2 clock path coverage** — the consumed clock is the one with non-zero intended-clock coverage on the
  chosen netlist (tool-derived; rejects `clk_old`/`clk`).
- **C3 scenario inferred from report provenance** — the `op_point` value recovered from the
  globally-consistent report is a `scenario_axis` member.
- **C4 corner/mode inferred from report semantics** — the `mode` value is a `corner_axis` member.
- **C5 PVT label maps to (scenario,corner) metadata, not an axis value** — a `pvt_label` present in metadata
  must map to the chosen `(scenario, corner)`; it is rejected in any `op_point`/`mode` slot.
- **C6 typed evidence fields match provenance** — the evidence_manifest's typed fields equal the consumed
  flow_config's typed fields (fielded, not set-based).
- **C7 upstream digest binds typed fields** — stage2 `upstream_evidence_digest` = digest of the fresh stage1
  produced under the **typed** assignment.
- **C8 global uniqueness (master)** — C1–C7 hold under exactly one typed assignment.
- **C9 signoff-green does not override typed mismatch** — a package with `SIGNOFF_OK` but a typed-binding
  violation still scores below pass (the `0007` hardening, retained).

`enumerate_constraint_graph` (reused) proves uniqueness over the typed product (including trap values, as
in `0007`, so swapped/PVT/wrong-clock assignments are machine-provable failures).

---

## 7. Decoys and invalid recoveries (each must score below pass)

- **value-swap across inferred axes** — `op_point=func, mode=slow` (a corner value in the scenario field and
  vice versa) → fails C3+C4 (the `0006` DeepSeek failure mode).
- **PVT-label substitution** — `mode=slow_1.0V_125C` (PVT in a corner field) → fails C4+C5 (the `0006`
  DeepSeek k=5 failure mode).
- **wrong clock alias** — `clock=clk` (generic alias) → fails C2.
- **locally consistent report but typed mismatch** — adopt `report_A` (internally consistent, but
  `op_point`/`mode` swapped vs the global authority) → fails C3+C4+C8.
- **digest-valid but typed-wrong evidence** — adopt `evidence_D` (valid digest, fields bound to wrong axes)
  → fails C6+C7.
- **report-correct but provenance-wrong** — right labels but the evidence chain doesn't re-derive from the
  consumed package → fails C6.
- **final-state-only** — fix `flow_config` but ship no fresh chain → fails C6/C7.
- **stage2-only** — rerun stage2 from a stale/typed-wrong stage1 → fails C7.
- **hand-edited evidence** — forged digests/fields → fails C6/C7 re-run + anti-cheat.
- **edit-manifest-down / forbidden edits** — weaken the manifest/spec/glossary to legitimize a mis-bind, or
  edit netlists/library/grader → anti-cheat zeroes.

Each lands at the same far-below-pass floor as `0006` decoys (≈0.20 — `signoff`+`explanation` only).

---

## 8. Valid recovery (the only pass path)

1. **Infer typed membership** from artifact usage (coverage → clock; manifest+interface → netlist;
   `op_point` context → scenario; `mode` context → corner; PVT notation → metadata).
2. **Infer the unique global assignment** by intersecting C1–C7 (no single file states the tuple).
3. **Repair** `flow_config.json` (canonical binding: netlist_v2 + slow + func) and `constraints.sdc`
   (`clk_main`), mapping the non-canonical labels to the correct axes.
4. **Regenerate stage1 then stage2** with the typed/provenance fields consistent (fresh ordered chain).
5. **Pass the hidden typed oracle** (C8 = `GLOBAL_CONSTRAINT_OK` + the typed-binding markers).

---

## 9. Oracle / scoring

**Reuse `WorkflowHandoffEvaluator` unchanged** (the `0006/0007` evaluator). All new logic lives in the
hidden shared `grade_workflow.py`, **gated on a new truth key** so `0001–0007` stay byte-identical (the
gated-additive pattern). Hidden markers (affirmative-only, Phase-4J format):

- `IMPLICIT_AXIS_INFERENCE_OK` — the agent bound the inferred axes correctly (membership recovered from
  evidence, not a schema).
- `TYPED_BINDING_OK` — every value sits in its correct typed slot (no scenario↔corner swap; correct clock
  identity).
- `PVT_METADATA_OK` — a present PVT label occupies only metadata and maps to the chosen `(scenario,corner)`.
- `PROVENANCE_TYPED_OK` — evidence typed fields match the consumed package (C6).
- `GLOBAL_CONSTRAINT_OK` — the assignment is the unique global intersection (C8).
- `UNIQUE_ASSIGNMENT_OK` — matches the single satisfying typed assignment.
- `EVIDENCE_CHAIN_TYPED_OK` — fresh ordered chain re-derivable with typed fields (C7).
- `HAZARD_RECOVERY_OK` — the master gate; folds the above.

Fold the new typed checks into the existing `EVIDENCE_OK` / `HAZARD_RECOVERY_OK` master gates so a
mis-typed package lands at ≈0.20 (signoff + explanation only). **A wrong typed assignment must stay far
below pass even if PT signoff is green** (the `0007` C9 hardening, retained). Preserved `component_scores`
remain authoritative.

---

## 10. Uniqueness and ambiguity gate (the make-or-break for 0008)

- **Enumerate the typed assignment space** (with trap values, as in `0007`) and assert **exactly one** typed
  global assignment satisfies C1–C9, equal to the expected tuple.
- **Partial public clues are sufficient** for a human chip engineer (or a strong agent applying domain
  knowledge: PVT notation, signoff-mode terminology, coverage facts) to infer the answer.
- **No single visible artifact reveals the full schema or the full tuple.**

**GO:** exactly one typed assignment passes; clues are inferable for a domain expert; every decoy/mis-bind
fails; signoff-green-but-mis-typed fails below pass.

**NO-GO if:**
- zero valid assignments (constraints over-constrained),
- multiple valid assignments (under-constrained → guessing),
- the answer is directly readable from one file,
- axis membership is directly listed anywhere (collapses to `0007`),
- the ambiguity requires **guessing** rather than domain-knowledge inference (unfair).

The hardest design balance is the GO/NO-GO line on *ambiguity*: enough context for a domain expert to
infer, not enough for a schema lookup. The glossary + spec terminology must be piloted (e.g., have the
golden-author re-derive the tuple from the visible artifacts alone) before any model probe.

---

## 11. Acceptance filters (prove before accepting the generated task)

- golden (full typed recovery) = **1.0**
- mutant (shipped mis-bind) **below pass**
- **signoff-green-but-mis-typed below pass** (the `0007` C9 hardening, on real PT)
- value-swap across inferred axes **below pass**
- PVT-substitution **below pass**
- wrong-clock alias **below pass**
- digest-valid typed-wrong evidence **below pass**
- report-correct provenance-wrong **below pass**
- final-state-only **below pass**
- stage2-only **below pass**
- hand-edited evidence **below pass**
- edit-manifest-down / forbidden edits → anti-cheat zeroes
- **deterministic regeneration** (same seed → byte-identical tree)
- **no hidden leak** (no truth/secret/`axis_schema` in the public tree)
- **public verdict-first** (public output never states the hidden verdict)
- **`workflow_handoff_0001–0007` behavior unchanged** (byte-identical golden + grader hash for `0001–0006`;
  `0007` keeps its published-schema variant — `0008` is a *new* hazard_type, not a modification of `0007`)
- **human-inferrability check:** the golden-author (or a scripted domain-aware solver) can recover the
  tuple from the **visible artifacts alone** — proving the task is fair, not a guess.

---

## 12. Probe plan (after implementation + acceptance matrix only)

1. **Validate the acceptance matrix only** (no models) on b04, **including the human-inferrability check**.
2. Then **Qwen + DeepSeek only**, **`workflow_handoff_0008` only**, **k=3**, **1800s**, max 60 actions,
   temp 0.7, `--elicit-confidence`, concurrency 1, **preservation on**, **explicit cost cap** (≈¥60–62;
   expect `0006`-like ¥4–16/episode).
3. **MiniMax later**, only as a protocol/reliability comparison — not part of the capability read.
4. Classify with preserved artifacts (byte-confirm every non-pass: value-swap vs PVT-invention vs
   wrong-clock vs provenance-mismatch); keep protocol_clean separate from capability_pass.

**Interpretation up-front:** if `0008` reproduces the DeepSeek axis-binding failures (≥1 wrong assignment
at k=3), it is the targeted stronger signal; if both models saturate, the implicit-membership difficulty is
also insufficient and the result is logged as another saturation (no over-claiming).

---

## 13. Relationship to previous tasks

| task | axis membership | constraint graph | result |
|---|---|---|---|
| `0006` | readable from report **field labels** (`scenario=`/`corner=`) | **implicit** (intersect family × coverage × signoff pair) | **positive frontier split** (Qwen 8/8, DeepSeek 6/8) |
| `0007` | **fully published** (`axis_schema.json`) | explicit typed schema | **saturated** (Qwen 3/3, DeepSeek 3/3) — vocabulary lookup |
| `0008` | **implicit** (inferred from non-canonical labels + context + domain knowledge) | **implicit typed** constraint graph | **expected harder than `0007`, more targeted than `0006`** (TBD) |

`0008` is the controlled combination: `0006`'s implicit-graph difficulty + `0007`'s typed-binding oracle,
with the schema-visibility variable set back to "hidden."

---

## 14. Risks

- **Hiding too much → unfair ambiguity.** If the non-canonical labels + glossary are too sparse, even a
  domain expert cannot infer membership → the task becomes a guess (NO-GO). *Mitigation:* the
  human-inferrability acceptance check (§11); pilot the visible artifacts with a golden-author solve.
- **Exposing too much → collapses to `0007`.** If `glossary.md` or `spec.md` effectively lists the value→axis
  mapping, binding reverts to lookup and the task saturates again. *Mitigation:* examples-only glossary;
  no complete vocabulary; verify no visible file resolves the binding.
- **Typed inference may still be too easy.** A strong model with PVT-notation domain knowledge may bind
  correctly without the schema (as it did on `0006`'s harder implicit graph... partially). If so, `0008`
  saturates like `0007` and the lesson is that axis-binding per se is frontier-easy when labels are
  inferable. That is still an informative result (do not over-claim).
- **Oracle brittleness.** If typed-binding checks rely only on label strings, an agent that renames fields
  could evade them. *Mitigation:* pin checks to the **consumed** flow_config + trusted-laundered
  `applied_hidden.sdc` + the hidden re-run (forgery-resistant, as in `0006/0007`), not to agent-authored
  labels.
- **Cost may rise.** Implicit membership may take more tool calls (more report reads, more coverage runs)
  → higher per-episode cost; budget the cap accordingly and watch the 60-action limit (4/6 episodes hit it
  on `0007`).

---

## 15. Recommendation

- **Write this design first** (this document); review before any code.
- **Do not implement `0008`** until the design is reviewed **and** the human-inferrability gate is judged
  fair.
- **Do not run more `0007` probes** — its saturation is established.
- **Do not push.**
- Preferred path if pursuing stronger capability: **implement `0008` per §5–§9, validate §10–§11 (including
  the human-inferrability check), then §12 probe** — the implicit-typed-axis combination is the
  principled next step predicted by the ablation.

---

*Compliance: design-only. No code, no tasks, no models, no other-worktree changes. Not committed, not
pushed — awaiting review.*
