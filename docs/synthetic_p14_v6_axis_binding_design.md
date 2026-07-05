# p14 v6 design — workflow_handoff_0007 axis-binding / value-invention stress

**Design-only (Phase-4M).** Specifies `workflow_handoff_0007`, `hazard_type =
axis_binding_value_invention`, as a stricter successor to `0006`. No code, no task, no models — this is a
reviewable design. Builds on the accepted final positive-results synthesis (`e4cf58e` / `660bf85`).

Target: the **exact** DeepSeek failure modes byte-confirmed on `0006`, generalized into a benchmark that
requires *type-correct axis binding* on top of *global constraint satisfaction*.

---

## 1. Motivation

- `workflow_handoff_0006` produced the **first robust p14 frontier-model split** — the first p14 task whose
  difficulty is capability, not protocol.
  - **Qwen3.7-Max:** 3/3 (k=3) + 5/5 (k=5) = **8/8**, **0 wrong global assignments** — robust saturation.
  - **DeepSeek-V4-Pro:** 2/3 (k=3) + 4/5 (k=5) = **6/8**, **2 byte-confirmed wrong global assignments**.
- **DeepSeek's two failures are both axis-binding / value-invention errors** (not decoy-following, not
  broken-chain, not protocol, not infra — byte-confirmed from preserved `flow_config.json` + hashes):
  1. **Value swap across axes** (k=3, HIGH conf, 0.20): submitted `scenario=func, corner=typ`; the correct
     *corner* value `func` was bound to the *scenario* slot. Satisfied C1+C2, violated C3 only; PT still
     signed off — a *plausible, signoff-green wrong answer*.
  2. **Value invention / out-of-domain binding** (k=5 t3, MEDIUM conf, 0.10): submitted `scenario=func,
     corner=slow_1.0V_125C, clock=clk`; `func`→scenario slot again, **plus a hallucinated PVT corner string**
     (`slow_1.0V_125C`, not in the domain) and a generic/wrong clock name (`clk` instead of `clk_main`).
     PT did **not** sign off.
- `0007` should **target those two failure modes directly** and generalize them. The point is not more
  files or more decoys — `0006` already proved that decoy count only raises cost. The point is to make the
  task demand **stricter axis-value typing and cross-axis binding**, so that:
  - a value that is legal on one axis is **illegal** on another (kills the value-swap);
  - a plausible-looking PVT string is **rejected** unless it is a mapped descriptor, never an axis
    substitution (kills the value-invention);
  - a signoff-green package with a mis-typed axis still scores **far below pass**.
- **Why this is the right successor:** the discriminating axis both DeepSeek failures hit is *joint
  constraint inference / axis-value binding*. `0006` measured it as a side effect; `0007` measures it as
  the *primary, deliberate* difficulty, with an oracle that can distinguish "right values, wrong slots"
  from "right values, right slots" — which `0006`'s signoff-tolerant grader could only partially catch.

---

## 2. Design principle

**Typed axes with binding as a first-class constraint — global satisfaction is necessary but not
sufficient.**

- **Values belong to typed axes.** Each axis has a closed vocabulary; a token is meaningful only *in the
  context of its axis*.
- **A value valid on one axis must not be accepted on another.** `func` is a legal *corner*; it is an
  *illegal scenario*. Placing `func` in the scenario field is a **type error**, independent of whether the
  global tuple is otherwise "close."
- **In-domain labels must be axis-bound, not freely swappable.** Two axes may even share a surface token in
  a naive reading; the oracle checks the *slot*, not just the *presence* of the string somewhere in the
  package.
- **Out-of-domain labels must be rejected even if they look like plausible PVT strings.**
  `slow_1.0V_125C` is a descriptive PVT label; it is **not** a corner value. It may appear only as *mapped
  metadata* pointing at a `(scenario, corner)` pair — never as a substitute for either axis.
- **The correct solution requires BOTH:**
  1. **global constraint satisfaction** (the unique intersection, inherited from `0006`), **and**
  2. **type-correct axis binding** (each value sits in its own typed slot; no PVT substitution; correct
     clock identity, not a generic alias).
- A package that satisfies (1) but violates (2) — e.g. the exact DeepSeek value-swap — must score **below
  pass even if PT signoff is green.** This is the core hardening over `0006`.

---

## 3. Axis schema

Explicit typed axes (closed vocabularies; the *vocabulary* is public, the *correct assignment* is not):

| axis | typed values | role |
|---|---|---|
| `netlist_axis` | `netlist_v1.v`, `netlist_v2.v` | design version / interface family |
| `clock_axis` | `clk_old`, `clk_main`, *(optional)* `clk_alias` | clock identity (not a generic name) |
| `scenario_axis` | `slow`, `typ`, `fast` | operating-mode selector |
| `corner_axis` | `func`, `test`, `lowpower` | signoff-corner selector |
| *(optional)* `pvt_label_axis` | `slow_1.0V_125C`, `typ_1.0V_25C`, `fast_0.8V_0C` | **descriptive metadata only** |

**Hard typing rules (these are the mechanism, not decoration):**

- **`scenario_axis` values and `corner_axis` values are NOT interchangeable.** `slow`/`typ`/`fast` may
  appear *only* in the scenario field; `func`/`test`/`lowpower` may appear *only* in the corner field. A
  cross-placement is a type violation regardless of global closeness. *(This directly kills the DeepSeek
  value-swap `scenario=func`.)*
- **PVT labels are descriptive metadata, not valid scenario/corner substitutions unless explicitly
  mapped.** A `pvt_label_axis` token is accepted **only** in a dedicated `pvt_label` metadata field **and
  only if** it maps to the chosen `(scenario, corner)` pair via the public schema. It can never occupy the
  scenario or corner slot. *(This directly kills the DeepSeek value-invention `corner=slow_1.0V_125C`.)*
- **`clock_axis` requires exact identity.** A generic/aliased name (`clk`) is not a member of the
  vocabulary and fails clock binding even if it "looks right." *(This kills DeepSeek's `clock=clk`.)*
- `clk_alias` (optional) is included deliberately as a **binding trap**: it is a real vocabulary member but
  is only correct when the constraint graph pins it; otherwise choosing it over `clk_main` is a
  binding error, not an out-of-domain error — a second, subtler axis-binding failure surface.

**Design note on shared surface tokens:** to make the type rule *load-bearing* (not trivially satisfiable
by string uniqueness), at least one scenario value and one corner value should be chosen so a naive agent
is tempted to reuse a token across slots. `func` (corner) vs `slow` (scenario) already gave DeepSeek
trouble; `0007` keeps that trap and the oracle judges *slot occupancy*, never mere presence.

---

## 4. Constraint graph

Constraints are expressed in the existing generator form — each constraint is `(over: [axes...], allowed:
{tuples})` and the hidden `enumerate_constraint_graph` proves uniqueness over the full typed product.
`0007` adds **typed-binding constraints** on top of `0006`'s global-consistency constraints.

- **C1 netlist family / interface** — chosen netlist ∈ manifest-allowed family and matches the spec
  interface. *(inherited from 0006; kills wrong-family / stale-version.)*
- **C2 clock-path coverage** — chosen clock matches the netlist clock port *and* the fresh report
  coverage, by **exact identity** (`clk_main`, not `clk`). *(hardened: identity, not substring.)*
- **C3 scenario token must be in `scenario_axis`** — the scenario field value ∈ {`slow`,`typ`,`fast`}. A
  corner token in the scenario slot fails C3. **(new typed-binding constraint.)**
- **C4 corner token must be in `corner_axis`** — the corner field value ∈ {`func`,`test`,`lowpower`}. A
  scenario token, or a PVT label, in the corner slot fails C4. **(new typed-binding constraint.)**
- **C5 scenario/corner pair must be jointly valid** — `(scenario, corner)` ∈ the joint-validity table for
  the chosen netlist. *(inherited from 0006's C3; the joint table.)*
- **C6 PVT-label mapping** — if a `pvt_label` is present, it must **map to** the chosen `(scenario, corner)`
  pair via the public schema, and must occupy the `pvt_label` field **only**. A PVT label in an axis slot,
  or one that maps to a different pair, fails C6. **(new typed-binding constraint.)**
- **C7 evidence report provenance uses typed fields** — the submitted report must be re-derivable from the
  chosen typed assignment (byte re-run) with each value in its own typed field; a report whose fields are
  internally swapped fails C7 even if the *set* of values is correct. *(hardened provenance: fielded, not
  set-based.)*
- **C8 upstream evidence digest binds typed fields** — stage2's `upstream_evidence_digest` equals the
  digest of the **fresh** stage1 produced under the **typed** assignment; a digest computed over a
  swapped-field stage1 fails C8. *(hardened from 0006's C5/C6.)*
- **C9 global consistency across all typed axes (master)** — C1–C8 hold **simultaneously** under **one**
  typed assignment. This is the master gate; any subset-satisfying or type-violating assignment fails C9.

**Relationship to 0006:** `0006` had C1–C8 with a *single* scenario/corner joint check. `0007` splits the
scenario/corner handling into **type membership (C3/C4)** + **joint validity (C5)** + **PVT mapping (C6)**,
and upgrades provenance/digest to be **field-typed (C7/C8)**. The added constraints are what make a
signoff-green value-swap fail.

---

## 5. Public artifacts

Visible (agent-readable) files; the correct tuple is never written in any single one:

| artifact | role | reveals | withholds |
|---|---|---|---|
| `spec.md` | design intent + naming conventions | which typed axes exist, the typing rules, that PVT labels are metadata | the concrete correct values / final tuple |
| `handoff_manifest.json` | **partial** authority | netlist *family* + interface | full scenario/corner/clock, exact netlist version |
| `axis_schema.json` | **visible typed-value vocabulary** | the allowed members of every axis + the PVT→(scenario,corner) mapping table | *nothing about which member is correct* — vocabulary, not answer |
| `flow_config.json` *(editable)* | mutant candidate | a starting assignment | correctness; ships with a **swapped or invented** axis value |
| `report_A` | decoy | correct values | **swapped between scenario/corner fields** (right set, wrong slots) |
| `report_B` | decoy | a valid **PVT label** used **as if it were a corner** | that PVT labels are metadata-only |
| `report_C` | decoy | correct scenario/corner | **wrong clock binding** (`clk` / wrong alias) |
| `evidence_D` | decoy | syntactically valid chain | **typed-field mismatch** (fields swapped inside a well-formed chain) |
| `public_check_summary.json` | fair feedback | **type** + **pairwise** consistency failures (symptom-level) | the full recovery / final tuple |

**On publishing `axis_schema.json` (deliberate):** the challenge is *binding*, not *hiding the
vocabulary*. Publishing the closed vocabularies (and the PVT mapping table) makes the task **cleaner and
harder**: the agent cannot excuse a value-invention as "I didn't know the domain" — every legal value is
on the table, so an out-of-domain string or a mis-slotted value is an unambiguous binding error. This also
sharpens the oracle: "in-domain but wrong-slot" and "out-of-domain" become distinct, checkable classes.

**Editable submitted set:** keep the `0006` shape (`flow_config.json`, `constraints.sdc`,
`timing_report.rpt`, `evidence_manifest.json`, `stage2_summary.json`) — the scenario/corner/pvt fields live
*inside* `flow_config.json` as typed keys (`scenario`, `corner`, optional `pvt_label`), so binding is
exercised without adding new editable files. `axis_schema.json`, netlists, library, `grade_workflow.py`,
`handoff_truth.json`, and all decoy reports remain **forbidden** (anti-cheat checked).

---

## 6. Decoys and invalid recoveries

Each is **locally plausible** and must score **below pass**:

- **value-swap** — `scenario=func` / `corner=typ` (correct set, wrong slots) → fails C3 (and C4). *(the
  exact k=3 DeepSeek failure.)*
- **PVT substitution** — `scenario=slow` / `corner=slow_1.0V_125C` (PVT label in the corner slot) → fails
  C4 + C6. *(the exact k=5 DeepSeek failure family.)*
- **wrong clock alias** — `clock=clk` instead of `clk_main` (or `clk_alias` where `clk_main` is required)
  → fails C2. *(the exact k=5 DeepSeek clock error.)*
- **accepting `report_A`** — right labels, wrong typed fields → fails C3/C4/C7 (fielded provenance).
- **stage2 from typed-mismatched stage1** — regenerate downstream from a swapped-field stage1 → fails
  C7/C8 (typed digest).
- **corrected values, wrong type metadata** — right scenario/corner but a `pvt_label` that maps to a
  different pair, or a leftover mis-typed field → fails C6/C9.
- **editing `axis_schema.json` / `handoff_manifest.json` down** — widen the vocabulary or the mapping to
  legitimize a swap → anti-cheat forbidden-edit zeroes.
- **hand-editing evidence** — fake digests / rewritten report fields to *look* typed-consistent → fails
  C7/C8 re-run + anti-cheat.
- **final-state-only repair** — fix `flow_config.json` typed fields but ship no fresh chain → fails C7/C8
  (no re-derivation).

The A/B/C/D decoys each stress a **different** binding failure (slot-swap / PVT-substitution / clock-alias
/ typed-chain-mismatch), so an agent cannot majority-vote or pattern-match one decoy into a pass.

---

## 7. Valid recovery (the only pass path)

1. **Infer** the unique global assignment from the intersection of C1–C8 (no single file gives it).
2. **Bind each value to its correct typed axis:** scenario-axis value → scenario field, corner-axis value →
   corner field, clock identity → clock field.
3. **Use `scenario_axis` value only in the scenario field**; a corner token there is a type error.
4. **Use `corner_axis` value only in the corner field**; a scenario token or PVT label there is a type
   error.
5. **Use a PVT label only as mapped metadata** (`pvt_label` field), and only if it maps to the chosen
   `(scenario, corner)` pair; otherwise omit it.
6. **Repair the lower configs** (`flow_config.json` typed fields, `constraints.sdc` clock identity).
7. **Rerun stage1 then stage2** with typed fields consistent (fresh, minimal correct subset — not more,
   not less).
8. **Produce a fresh, typed-consistent evidence chain** (C7/C8 satisfied under the typed assignment).
9. Pass the hidden oracle (C9 = master typed-global gate).

---

## 8. Oracle / scoring

**Prefer no evaluator change.** Reuse `WorkflowHandoffEvaluator`; all new logic lives in the hidden shared
`grade_workflow.py`, **gated on a new truth key** so `0001–0006` stay byte-identical (the established
gated-additive pattern — mirrors how `constraint_graph` gates the `0006` echecks).

Hidden grader marker set (affirmative-only, Phase-4J format — `MARKER` bare on pass + `MARKER_SCORE:
<float>`):

- `AXIS_SCHEMA_OK` — every submitted axis value is an in-domain member of its axis (no out-of-domain
  strings anywhere).
- `TYPED_BINDING_OK` — every value sits in its correct typed slot (no scenario↔corner swap; correct clock
  identity).
- `PVT_LABEL_OK` — a present `pvt_label` occupies only the metadata field and maps to the chosen
  `(scenario, corner)` pair; absence is also OK.
- `GLOBAL_CONSTRAINT_OK` — the assignment is the unique global intersection (inherited from `0006`).
- `EVIDENCE_CHAIN_TYPED_OK` — the fresh stage1→stage2 chain is re-derivable with typed fields (C7/C8).
- `UNIQUE_ASSIGNMENT_OK` — matches the single satisfying typed assignment (inherited).
- `HAZARD_RECOVERY_OK` — the master gate; folds the above.

**Folding rule (keep weights summing to 1.0, additive integration):** where a standalone weight would be
awkward, fold `AXIS_SCHEMA_OK` / `TYPED_BINDING_OK` / `PVT_LABEL_OK` into the existing `EVIDENCE_OK` and
`HAZARD_RECOVERY_OK` master gates, exactly as `0006` folded its global-constraint checks. A type-violating
package then lands at the same *far-below-pass* floor a `0006` decoy hits (≈0.20 — `signoff` +
`explanation` partial credit only).

**Critical requirement:** a **wrong typed assignment must stay far below pass even if PT signoff is
green.** This is the explicit hardening over `0006`, where the k=3 value-swap scored 0.20 *because* it
still signed off — `0007`'s `TYPED_BINDING_OK` must fail that package on binding grounds, independent of
signoff, so it cannot climb on signoff credit.

Preserved `component_scores` remain authoritative; `affirmative_grader_markers` stay non-misleading.

---

## 9. Acceptance filters (prove before accepting the generated task)

- golden (full typed recovery) = **1.0**
- mutant (shipped swapped/invented config) **below pass**
- **value-swap** recovery (`scenario=func`/`corner=typ`) **fails**
- **PVT-substitution** recovery (`corner=slow_1.0V_125C`) **fails**
- **wrong-clock** recovery (`clock=clk`) **fails**
- **typed-field mismatch** (right set, wrong slots) **fails**
- `report_A`-only **fails**
- `report_B`-only **fails**
- `report_C`-only **fails**
- `evidence_D`-only **fails**
- **stage2-from-typed-wrong-stage1** **fails**
- **final-state-only** **fails**
- **hand-edited evidence** **fails**
- **edit-`axis_schema`/`manifest`-down** **fails or anti-cheat zeroes**
- forbidden netlist/lib/authority edit **fails**
- **deterministic regeneration** (same seed → byte-identical tree)
- **no hidden leak** (no truth/secret in public tree; `axis_schema.json` carries vocabulary only, never the
  correct assignment)
- **public verdict-first** (public output never states the hidden pass/fail)
- **`workflow_handoff_0001–0006` behavior unchanged** (byte-identical golden + grader hash)
- **key check — signoff-green-but-mis-typed fails:** a package that PT-signs-off but has a scenario↔corner
  swap **scores below pass** (this is the `0006`→`0007` hardening; prove it explicitly).

---

## 10. Uniqueness gate

Extend `enumerate_constraint_graph` to enumerate over the **typed** axis product (netlist × clock ×
scenario × corner × optional pvt_label) with the typed-binding constraints (C3/C4/C6) as first-class
allowed-set constraints. The offline proof must assert:

- **exactly one** assignment satisfies all constraints **and** all type rules, and equals the expected
  unique typed assignment;
- **swapped-axis** assignments (scenario-value in corner slot or vice-versa) **fail** C3/C4 typed-binding;
- **PVT-as-axis** assignments (a `pvt_label_axis` token in the scenario or corner slot) **fail** C4/C6
  typed-binding;
- **clock-alias-misuse** assignments (`clk` / wrong `clk_alias`) **fail** C2 clock-binding;
- **decoys** satisfy some local checks (a subset of C1–C8) but **fail** global typed consistency (C9).

The enumeration count grows vs `0006` (adds the pvt_label dimension + type membership as explicit
constraints); the proof must still resolve to **exactly one** satisfying typed assignment. If it resolves
to zero or more than one, the design is **NO-GO** until the joint-validity + mapping tables are retuned.

---

## 11. Generator sketch (do NOT implement yet)

Extend `generators/p14_workflow_handoff_gen.py` following the existing gated-preset pattern:

- Add `hazard_type = "axis_binding_value_invention"` to the allowed set + a `TASKS` entry
  `("workflow_handoff_0007", 0, 2, "axis_binding_value_invention")`.
- `_handoff_truth`: new `_is_ab` branch adding an `axis_schema` metadata block (typed vocabularies + PVT
  mapping table) and a **typed** `constraint_graph` (C1–C8 as `over`/`allowed` tuples incl. type-membership
  constraints). Gate every new echeck on `truth.get("axis_schema") is not None` so `0001–0006` are
  untouched.
- `_metadata`: `ab` branch — visible `axis_schema.json` + forbidden decoys (`report_A/B/C`, `evidence_D`,
  `public_check_summary.json`), editable set unchanged, re-balanced weights summing to 1.0.
- `build_task_skeleton`: `ab` branch — mutant `flow_config.json` with a **swapped or invented** typed
  field; the 3 typed decoys (slot-swap / PVT-substitution / clock-alias) + `evidence_D` (typed-field
  mismatch); the public type/pairwise conflict summary.
- `bake_golden`: bake each decoy report from a **real b04 PT run** of its (typed-wrong) assignment so
  reports are numerically genuine; bake the golden fresh chain from the unique correct typed assignment.
- `enumerate_constraint_graph`: extend to the typed product + type-membership constraints (§10); store the
  uniqueness result in hidden truth.
- Grader echecks + markers: `AXIS_SCHEMA_OK`, `TYPED_BINDING_OK`, `PVT_LABEL_OK`, `EVIDENCE_CHAIN_TYPED_OK`
  (plus inherited `GLOBAL_CONSTRAINT_OK` / `UNIQUE_ASSIGNMENT_OK` / `HAZARD_RECOVERY_OK`), synced
  byte-identical across all p14 tasks.
- Validate the full acceptance matrix (§9) on b04 before any model probe.

**Do not implement yet.**

---

## 12. Cost control

- **PT-only first.** Do **not** add DC/Formality unless `0007` *also* saturates on PT alone.
- **Reuse the existing tiny substrate** (`0006`'s `tiny.db` / tiny netlists) to keep PT runs cheap.
- **Compact public feedback** (type + pairwise symptoms, small JSON).
- Minimal decoys: A/B/C + one `evidence_D` — no more.
- **Preservation stays enabled for probes** (Phase-4I opt-in, default-off) — byte-confirmation of any typed
  failure is the whole point of `0007`.

---

## 13. Probe plan (after implementation + acceptance matrix only)

1. **Validate the acceptance matrix only** (no models) on b04.
2. Then **Qwen + DeepSeek only**, **`workflow_handoff_0007` only**, **k=3**, **1800s**, max 60 actions,
   temp 0.7, `--elicit-confidence`, concurrency 1, **preservation on**, **explicit cost cap** (≈¥40–60).
3. **MiniMax optional later**, only as a protocol/reliability comparison — never part of the capability
   read. (No Kimi, no GLM.)
4. Classify with preserved artifacts (byte-confirm every non-pass; distinguish value-swap vs PVT-invention
   vs clock-alias); keep protocol_clean separate from capability_pass.

---

## 14. GO / NO-GO

**GO if:**
- the typed axis schema is **visible** but the final tuple is **not** directly revealed by any single file;
- **exactly one** typed global assignment passes (uniqueness proven over the typed product);
- **value swaps fail** (scenario↔corner);
- **PVT substitutions fail** (label in an axis slot);
- **wrong clock alias fails** (`clk` / wrong `clk_alias`);
- **decoy-only recoveries fail** (A/B/C/D each below pass);
- a **signoff-green but mis-typed** package scores below pass;
- the full acceptance matrix passes.

**NO-GO if:**
- the final tuple is obvious from one file;
- the **type schema itself gives the answer** (vocabulary leaks the correct member);
- **multiple** typed assignments pass;
- **out-of-domain labels accidentally pass**;
- the oracle depends on **brittle string labels only** (presence, not slot/re-derivation);
- the task **collapses into `0006` with renamed fields** (no genuine type-binding pressure beyond global
  consistency).

---

## 15. Recommendation

- **Write this design first** (this document); review before any code.
- **Do not implement `0007`** until the design is reviewed.
- **Do not run more `0006` probes now** — the split (Qwen 8/8 vs DeepSeek 6/8, both failures axis-binding)
  is established; more trials would only tighten the rate, not change the conclusion.
- **Do not push.**
- Preferred path if pursuing the stronger signal: **implement `0007` per §11, validate §9/§10, then §13
  probe** — turning the byte-confirmed DeepSeek failure modes into a deliberate, typed benchmark axis.

---

*Compliance: design-only. No code, no tasks, no models, no other-worktree changes. Not committed, not
pushed — awaiting review.*
