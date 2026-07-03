# p14 v5 design — workflow_handoff_0006 constraint-graph multi-source recovery

**Design-only (Phase-4K).** Specifies `workflow_handoff_0006`, `hazard_type =
constraint_graph_multi_source_recovery`, as a stronger successor to `0005`. No code, no task, no models
— this is a reviewable design. Builds on the accepted post-k5 synthesis (`326961b`…`7216329`).

---

## 1. Motivation

- The p10→p14 v3 ladder **saturated** (single-fault localization + earlier handoff hazards frontier-easy).
- `0005` (multi-conflict partially-truthful decoy) added real **operational cost** but **saturated in
  correctness**: DeepSeek pass^5 = 1.00 at 1800s; the earlier "confident-wrong" was a protocol slip.
- Root cause of `0005`'s saturation: the **global authority tuple is directly recoverable** — `spec.md` /
  `handoff_manifest.json` effectively let a strong agent read off `[netlist, clock, scenario, corner]`,
  then reject decoys by simple per-axis cross-checks.
- **`0006` must remove that shortcut.** The agent must solve a **coupled constraint graph** where **no
  single artifact reveals the full recovery target**, and the target is pinned only by the **intersection**
  of several independent constraints. Difficulty comes from *joint* inference + minimal-rerun repair, not
  from hiding a readable answer.

---

## 2. Design principle

Central principle — **joint-constraint uniqueness, not single-source authority:**

- **No single file reveals the full target tuple.** Each source gives a *partial* or *axis-local* view.
- The correct recovery is inferred **only** by satisfying **multiple independent constraints
  simultaneously**.
- Each decoy is **locally plausible**: it **satisfies at least one check** and **fails at least one
  other**.
- **Exactly one** global assignment satisfies **all** constraints. Any assignment that passes a *subset*
  of checks but not the full graph must score **below pass**.
- Public feedback exposes **pairwise** inconsistencies only — never the global solution.

---

## 3. Global variables / axes

The constraint graph is defined over these axes (the correct target is the **unique** joint assignment,
never written as one tuple in one file):

| axis | domain | notes |
|---|---|---|
| netlist version | `v1` / `v2` / (optional `v3`) | interface/family constrained by manifest, exact version by provenance |
| clock | `clk_old` / `clk_main` / (optional generated alias `clk_gen`) | binding pinned by constraints.sdc + coverage |
| scenario | `slow` / `typ` / `fast` | pinned by scenario/corner constraint + report cross-check |
| corner | `func` / `test` / `lowpower` | coupled to scenario via a joint validity table |
| stage1 evidence package | (derived) | must be fresh vs the chosen netlist+clock |
| stage2 upstream digest | (derived) | must bind the *fresh* stage1, not a stale/invalidated one |
| optional scenario report | present/absent | one decoy axis |
| optional equivalence/report artifact | present/absent | reserved for a future cross-tool variant |

**Uniqueness requirement:** the joint-validity relation over (netlist × clock × scenario × corner ×
stage-freshness) must have **exactly one** satisfying assignment. This is an acceptance filter (§10), not
a runtime hint.

---

## 4. Artifact graph (public, agent-visible + editable/forbidden as marked)

| artifact | role | reveals | withholds |
|---|---|---|---|
| `spec.md` | design intent | interface + which axes matter | concrete netlist/clock/scenario/corner values |
| `handoff_manifest.json` | **partial** authority | allowed netlist *family* + required interface | full scenario/corner, exact netlist version |
| `flow_config.json` *(editable)* | one candidate assignment | a starting guess | correctness |
| `scenario_config.json` / `corner_config.json` *(editable)* | another candidate axis-assignment | scenario/corner guess | netlist/clock coupling |
| `constraints.sdc` *(editable)* | clock binding | candidate clock | whether it matches netlist/coverage |
| `report_A` | decoy | correct **netlist + clock** | **wrong scenario/corner** |
| `report_B` | decoy | correct **scenario/corner** | **stale netlist** |
| `report_C` | decoy | correct **netlist + scenario** | **wrong clock binding** |
| `evidence_D` | decoy | **valid upstream digest** (syntactically) | **depends on an invalidated prerequisite stage** (semantically wrong) |
| `prev_signoff.log` | non-authoritative | recent-looking summary | no authority |
| `public_check_summary.json` *(optional)* | fair feedback | **pairwise** inconsistencies | the full fix / global tuple |

Editable submitted set stays the `0005` shape (`flow_config.json`, `constraints.sdc`,
`timing_report.rpt`, `evidence_manifest.json`, `stage2_summary.json`) **plus** `scenario_config.json` /
`corner_config.json` so scenario/corner become independently-repairable axes. Netlists, library,
`grade_workflow.py`, `handoff_truth.json`, decoy reports remain **forbidden** (anti-cheat checked).

**Design tension resolved:** the three decoys A/B/C each cover a *different* pair of correct axes, so no
two decoys agree on the same wrong axis — the agent cannot "majority-vote" the answer; it must intersect.

---

## 5. Constraint model (generator + hidden oracle enforce)

- **C1 netlist/interface:** chosen netlist ∈ manifest-allowed family **and** matches the interface in
  spec. (kills wrong-family / stale-version.)
- **C2 clock binding:** `constraints.sdc` clock matches the netlist's clock port **and** the coverage in
  the fresh report. (kills report_C's wrong clock.)
- **C3 scenario/corner joint validity:** (scenario, corner) ∈ the joint-validity table for the chosen
  netlist. (kills report_A's wrong scenario/corner and illegal scenario×corner pairs.)
- **C4 report provenance:** the submitted `timing_report.rpt` must be **re-derivable** from the chosen
  netlist+clock+scenario+corner (byte re-run), not copied from any decoy. (kills "adopt a decoy report".)
- **C5 upstream digest:** stage2 `upstream_evidence_digest` must equal the digest of the **fresh** stage1
  under the chosen assignment. (kills evidence_D's valid-but-stale digest.)
- **C6 stage dependency:** the stage1 that stage2 binds must itself be fresh (not an invalidated
  prerequisite). (kills "valid digest of an invalidated stage".)
- **C7 pairwise consistency:** every emitted artifact pair must agree on shared axes. (what public
  feedback surfaces.)
- **C8 global consistency (master):** all of C1–C6 hold **simultaneously** under **one** assignment.

**Solvable only when C8 holds.** Any subset-satisfying assignment (a decoy, a single-axis fix) violates
≥1 constraint and scores below pass.

---

## 6. Public feedback (fair, `public_check_summary.json` / `run_public.sh` stdout)

May report:
- "conflict detected between `report_A` and `evidence_D`" (pairwise)
- "upstream digest valid but prerequisite package inconsistent" (C6 symptom, not the fix)
- "scenario label mismatch" (C3 symptom)
- "clock path coverage mismatch" (C2 symptom)
- generic **pairwise** consistency failures (C7)

Must **not** report:
- the full correct tuple
- exact file edits to make
- hidden truth / `handoff_truth.json` contents
- oracle internals / the joint-validity table

Feedback is **symptom-level and pairwise** — enough to guide honest debugging, never enough to skip the
joint inference. (Verdict-first: public output never states pass/fail of the hidden oracle.)

---

## 7. Failure modes / decoys (each must score **below pass**)

- follow `report_A` (right netlist+clock, wrong scenario/corner) → fails C3.
- follow `report_B` (right scenario/corner, stale netlist) → fails C1/C4.
- follow `report_C` (right netlist+scenario, wrong clock) → fails C2.
- follow `evidence_D` because its digest is valid → fails C6 (invalidated prerequisite).
- repair only scenario/corner → fails C1/C2.
- repair only netlist/clock → fails C3.
- make all reports agree with a decoy → fails C4 (provenance re-run) + C8.
- rerun only stage2 → fails C5/C6 (stale stage1).
- final-state-only (fix configs, no fresh chain) → fails C4/C5 (no re-derivation).
- edit `manifest`/`spec` downward to legitimize a decoy → anti-cheat forbidden-edit zeroes.
- hand-edit evidence (fake digests/report) → fails C4/C5 (re-run mismatch) + anti-cheat.

---

## 8. Valid recovery (the only pass path)

1. **Infer** the globally-consistent assignment from the intersection of C1–C6 (no single file gives it).
2. **Repair** lower-level configs: `flow_config.json`, `scenario_config.json`/`corner_config.json`.
3. **Repair** clock/scenario/corner selection (`constraints.sdc` + configs).
4. **Invalidate** the wrong stage outputs (stale stage1, evidence_D's prerequisite).
5. **Rerun the minimal correct subset** of stages (fresh stage1 → fresh stage2) — not more, not less.
6. Produce a **fresh, globally-consistent evidence chain** (C4/C5/C6 all satisfied).
7. Pass the hidden oracle (C8 = `GLOBAL_CONSTRAINT_OK`).

---

## 9. Oracle / scoring

- **Reuse `WorkflowHandoffEvaluator`.** New logic lives in the hidden shared `grade_workflow.py` (synced
  byte-identical across all p14 tasks, as `0005` does).
- **Gate hierarchy (all hard gates, folded into a master gate):**
  - `SIGNOFF_OK`
  - `FINAL_STATE_OK`
  - `GLOBAL_CONSTRAINT_OK` (C8)
  - `EVIDENCE_CHAIN_OK` (C4/C5/C6 fresh ordered chain)
  - `PROVENANCE_OK`
  - `MULTI_CONFLICT_RECOVERY_OK`
  - `NO_FORBIDDEN_EDIT` (anti-cheat)
- **Additive-scoring integration:** to keep `0001–0005` byte-identical, the new constraint checks are
  **gated on a new `constraint_graph` truth key** (mirroring how `global_authority_tuple` gates the
  `0005` echecks). Where a standalone weight would be awkward, **fold** the global-constraint checks into
  the existing `EVIDENCE_OK` master gate and `HAZARD_RECOVERY_OK`, so every locally-plausible decoy lands
  **far below pass** (only `signoff` + `explanation` partial credit, ≈0.20 like `0005`'s broken-chain
  case). Weights re-balance to sum 1.0, as the generator already does per hazard preset.
- Emit affirmative markers in the Phase-4J format (`MARKER` bare on pass + `MARKER_SCORE: <float>`), so
  preserved `component_scores` remain authoritative and `affirmative_grader_markers` stay non-misleading.

---

## 10. Acceptance filters (prove before accepting the generated task)

- golden (full global recovery) = **1.0**
- mutant (shipped broken handoff) **below pass**
- every **single-axis** repair **fails**
- `report_A`-only / `report_B`-only / `report_C`-only **fail**
- `evidence_D`-only **fails**
- stage2-only rerun **fails**
- final-state-only **fails**
- hand-edited evidence **fails**
- edit-manifest-down **fails or anti-cheat zeroes**
- forbidden netlist/lib/authority edit **fails**
- **deterministic regeneration** (same seed → byte-identical tree)
- **no hidden leak** (no truth/secret in public tree)
- **public verdict-first** (public output never states the hidden verdict)
- **`workflow_handoff_0001–0005` behavior unchanged** (byte-identical golden + grader hash)
- **uniqueness:** exactly one joint assignment passes (enumerate the axis product, assert single pass)

---

## 11. Generator implementation sketch (do NOT implement yet)

Extend `generators/p14_workflow_handoff_gen.py` following the existing gated-preset pattern:

- Add `hazard_type = "constraint_graph_multi_source_recovery"` to the allowed set + `TASKS` entry
  `("workflow_handoff_0006", 0, 2, "constraint_graph_multi_source_recovery")`.
- `_handoff_truth`: new `_is_cg` branch adding a `constraint_graph` key (axes, joint-validity table,
  decoy→violated-constraint map). Gate all new echecks on `truth.get("constraint_graph") is not None` so
  `0001–0005` are untouched.
- `_metadata`: `cg` branch — visible+forbidden decoy files (`report_A/B/C`, `evidence_D`,
  `public_check_summary.json`), editable set + `scenario_config.json`/`corner_config.json`, re-balanced
  weights summing to 1.0.
- `build_task_skeleton`: `cg` branch — mutant `flow_config` (wrong assignment), the 3 decoys + evidence_D,
  optional public conflict summary.
- `bake_golden`: bake each decoy report from a **real b04 PT run** of its (partly-wrong) assignment so
  reports are numerically genuine (not hand-faked); bake the golden fresh chain from the unique correct
  assignment.
- Grader echecks: `constraint_graph_global_consistent`, `evidence_chain_fresh`,
  `report_provenance_rederivable`, `upstream_prerequisite_valid` + markers `GLOBAL_CONSTRAINT_OK` /
  `MULTI_CONFLICT_RECOVERY_OK`.
- Validate the acceptance matrix (§10) on b04 before any model probe.

---

## 12. Cost control

- **PT-only first.** No DC/Formality unless `0006` *also* saturates on PT alone.
- **Minimal decoys:** 3 reports (A/B/C) + one `evidence_D` — no more.
- **Compact public feedback** (pairwise symptoms, small JSON).
- **Preserve final workspaces only for probes** (Phase-4I, opt-in, default-off).
- Reuse `0005`'s `tiny.db`/tiny netlists to keep PT runs cheap.
- Model probes: **Qwen + DeepSeek only, k=3** first (no MiniMax/Kimi/GLM at capability stage).

---

## 13. Probe plan (after implementation + acceptance)

1. **Validate the acceptance matrix only** (no models) on b04.
2. Then **Qwen + DeepSeek only**, **`workflow_handoff_0006` only**, **k=3**, **1800s**, max 60 actions,
   temp 0.7, `--elicit-confidence`, concurrency 1, **preservation on**, **explicit cost cap** (≈¥40–60).
3. **MiniMax later**, only as a reliability/protocol comparison — not part of the capability read.
4. Classify with preserved artifacts (byte-confirm every non-pass); keep protocol_clean separate from
   capability_pass.

---

## 14. GO / NO-GO

**GO if:**
- no single artifact reveals the full tuple
- exactly one global assignment passes (uniqueness proven)
- every decoy-only / single-axis recovery fails
- the valid recovery is unambiguous (one minimal rerun subset)
- the full acceptance matrix passes
- cost stays manageable (PT-only, few decoys)

**NO-GO if:**
- the correct answer is explicit in one file
- multiple valid recoveries exist
- any wrong decoy recovery can pass
- the oracle relies on brittle textual labels only (not re-derivation)
- the task collapses to "`0005` with more files" (still per-axis solvable)
- cost explodes before model probing

---

## 15. Recommendation

- **Write this design first** (this document); review before any code.
- **Do not implement `0006`** until the design is reviewed.
- **Do not run more `0005` probes.**
- **Do not run models** until the `0006` acceptance matrix exists and passes.
- Preferred path if pursuing positive capability: **implement `0006` per §11, validate §10, then §13
  probe** — rather than any further `0005` work.

---

*Compliance: design-only. No code, no tasks, no models, no other-worktree changes. Not committed, not
pushed — awaiting review.*
