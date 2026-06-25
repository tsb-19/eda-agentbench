# Synthetic EDA Project Generator — Phase-0 MVP

Status: **DESIGN DRAFT (planning only).** Companion to `synthetic_eda_project_generator_plan.md` and
`synthetic_failure_taxonomy.md`. No generator code, no commercial-tool runs, no b04-heavy tasks in this
document — this defines the *minimal verifiable closed loop* to build next, and the GO/NO-GO that gates
any scale-up.

## Goal

Prove a single closed loop end-to-end, on the smallest possible footprint:

> A generated mini EDA **project** can produce a **golden flow that passes**, a **mutant flow that fails
> with a tool-visible symptom**, an **agent-visible workspace** (visible+editable only, no oracle leak),
> a **hidden machine-checkable oracle** that distinguishes *mechanism-fixed* from *symptom-suppressed*,
> and a **score routed through the reliability/calibration layer** — for **2 mechanisms** on a
> **3-tool** flow.

If that loop holds and a cheap probe shows a real gap, we scale. If not, we retire it cheaply — the same
discipline that killed the six earlier directions.

## Hard scope limits (MVP only)

- **5–10 mini projects total** (not hundreds). Enough to stratify trivially and run a cheap probe.
- **Exactly 2 mechanisms**, both cross-artifact, both already tractable on our toolchain:
  1. **Constraint drift** (taxonomy §A) — SDC diverges from spec; PT sign-off + spec-equivalence oracle.
  2. **Flow handoff drift** (taxonomy §B) — DC→PT handoff broken; handoff-invariant oracle.
- **Tools limited to VCS + DC + PrimeTime.** No ICC2 / Spectre / Formality / SpyGlass / StarRC in MVP —
  those mechanisms are designed in the taxonomy but deferred. This keeps the flow inside tools we have
  already validated on b04 and keeps per-episode cost low.
- **Scoring reuses the reliability/calibration layer** verbatim (`reliability.py`,
  `scripts/reliability_report.py`, `--elicit-confidence`); no new metrics.
- **No new core-harness rewrites.** Reuse schema, workspace builder, tool detector/env-shim, evaluator
  base, anti-cheat. At most ONE additive, backward-compatible schema field (below).

## What each mini project contains

Every project is a small but *real* design that flows through synth + sign-off:

- **RTL** — a compact synthesizable module (e.g. an FSM controller or small datapath) that VCS elaborates
  and DC synthesizes. Reuse the existing `fsm_ctrl`-class RTL templates already used by P6 generation.
- **SDC** — constraints for the design (the editable artifact for constraint-drift; part of the handoff
  for handoff-drift).
- **Scripts** — `run_public.*` (agent-visible: elaborate + synth + a sign-off the agent can run to see the
  symptom) and `run_hidden.*` (evaluator-only: the authoritative oracle that emits anchored markers).
  Same split as P6/P7 today.
- **README / spec** — `spec.md`: a machine-referenced timing/IO contract (real budget arithmetic, not
  prose) that is the *authority* the drifted SDC must be reconciled against. This is the new artifact that
  makes the task cross-document.
- **Golden reports** — the DC/PT reports from the passing golden flow, used by the oracle as ground-truth
  fixtures (path counts, constrained-clock set, slack budget).
- **Mutant reports** — the reports from the failing mutant flow (for inspection / dataset provenance; not
  shown to the agent if they would leak the fix).
- **Hidden oracle metadata** — a machine-readable fixture (`oracle/spec_truth.json`) holding the
  spec-derived intended constraint set / handoff invariants the hidden script checks against.

## Reuse map (concrete)

| Need | Reused component | Note |
|---|---|---|
| Task metadata + validation | `eda_agentbench/schema.py`, `task/validator.py` | project = superset of file-task; `data_type: flow_synthetic` |
| Agent vs evaluator isolation | `agentic/workspace.py` (`create_agent_workspace` / `create_evaluator_workspace`) | hidden/oracle never seeded to agent |
| Reward-hack guard | `workspace.detect_hidden_shadows` + `anti_cheat/guard.py` | more forbidden files (every script + golden report) = stronger guard |
| Real tools on PATH | `tools/detector.py`, `tools/env_shim.py` | `EDA_TOOL_ROOT` rewrite; b04 only |
| Execution-based grading | `evaluator/base.py` + new `synthetic_project` evaluator (parses `^MARKER` / `^*_SCORE`) | mirrors `dc_constraint_debug.py` |
| k-trials + confidence + protocol | `reliability.py`, `scripts/reliability_report.py`, driver `--elicit-confidence`/`--temperature` | scoring routes through here |
| Orchestration | `scripts/run_agentic_baseline.py`, CLI `run-agent` / `run-agent-dataset` | new track name only |
| Inventory / report | `scripts/benchmark_report.py` dynamic counts (`01b0356`) | new track tolerated by gate |

### Schema note (the one possibly-needed additive field)

A file-task today lists flat `files.visible/editable/...`. A project has a small directory of artifacts;
the existing lists already support multiple files, so the MVP can likely proceed **with no schema change**
by listing `spec.md`, `design.v`, `constraints.sdc`, `run_public.*` as visible and `run_hidden.*`,
golden reports, `oracle/spec_truth.json` as hidden. If a project needs subdirectories, add **one**
optional `project_manifest` field (additive, ignored by existing tracks) rather than changing any required
field — documented in the commit per CLAUDE.md's "minimal + documented" rule for `schema.py`.

## Recommended directory structure (describe only — do NOT create code dirs this round)

A project task directory, consistent with the existing standard layout, would look like:

```text
tasks/p10_synthetic_project/<project_id>/
  prompt.md
  metadata.json
  spec.md                      # visible: the authoritative contract (budget arithmetic)
  files/                       # agent workspace (visible + editable)
    design.v                   # visible, forbidden-to-edit
    constraints.sdc            # editable (constraint-drift) / part of handoff
    run_public.sh|.tcl         # visible, forbidden-to-edit (lets agent see the symptom)
  hidden/                      # evaluator-only (never seeded to the agent)
    run_hidden.sh|.tcl         # authoritative oracle; emits ^MARKER / ^*_SCORE
    golden/                    # golden DC/PT reports used as ground-truth fixtures
  oracle/
    spec_truth.json            # machine-readable spec-derived intended constraints / handoff invariants
  solution/                    # the correct fixed artifact(s) for the golden-pass gate
```

Generators would live under the repo's existing `generators/` convention (the project generator is a new
module there, *not* under `datagen/`, which is P5-only per CLAUDE.md). **No directories are created in this
planning round** — this is the target shape only.

`p10_synthetic_project` is a placeholder track name; final naming decided at build time and registered in
`schema.py`'s track enum (one additive enum entry).

## Verification loop the MVP must demonstrate

1. **Golden pass** — golden project flows VCS→DC→PT; hidden oracle emits `^SIGNOFF_OK` and
   `^*_SCORE: 1.0`; overall golden score ≈ 1.0 through the *same* path the agent will use (the standing
   fairness gate).
2. **Mutant fail** — injected mechanism makes the flow fail with a tool-visible symptom; golden − mutant
   objective margin ≥ 0.15 (the CLAUDE.md margin rule).
3. **Agent-visible symptom** — the agent, running only `run_public.*`, can *observe* the symptom (PT
   violation / unresolved reference) without seeing the oracle or the fix.
4. **Hidden oracle** — `run_hidden.*` + `oracle/spec_truth.json` are absent from the agent workspace
   (`create_agent_workspace` guarantees this); `detect_hidden_shadows` flags any attempt to fabricate
   them.
5. **Anti-cheat safe** — forbidden files (RTL, scripts, golden reports, oracle) SHA-guarded; a
   symptom-suppressing edit (over-constrain / consumer-only patch / hardcoded marker) scores **below** the
   true fix.
6. **Reliability-routed** — k≥3 trials at temperature>0 with `--elicit-confidence`; the report shows
   pass@1/@k/^k, trust, overconfident-wrong, protocol tally — proving the layer ingests the new track
   unchanged.

## Implementation phasing (next round, after this design is accepted)

- **Phase 0A — hand-authored mini golden project.** Build ONE project by hand (RTL+SDC+scripts+spec+golden
  reports), flow it on b04, confirm golden-pass oracle ≈ 1.0. *Deliverable:* one task dir + a b04 golden
  log. *Cost:* minimal (one design, a few tool runs).
- **Phase 0B — one synthetic mutation mechanism.** Implement the constraint-drift mutator as an automated
  transform on the golden; generate 5–10 mutant variants; confirm each fails with a tool-visible symptom
  and golden−mutant margin ≥ 0.15. *Deliverable:* generator module (constraint-drift only) + variants.
- **Phase 0C — oracle validation.** Implement the `synthetic_project` evaluator (marker parsing) +
  `spec_truth.json` checks; validate on: golden→1.0, mutant→fail, and ≥2 hand-written *wrong fixes*
  (over-constrain, consumer-only) → scored below the true fix. *Deliverable:* evaluator + a validation
  record (golden/buggy/wrong-fix matrix), mirroring `validate_dataset.py` discipline.
- **Phase 0D — 3-model cheap probe.** Run 3 models (cheapest/most-instructive from the gateway set), k=3,
  `--elicit-confidence`, on the 5–10 projects via the existing agentic harness on b04. Small spend
  (target ≪ ¥30; estimate per the Phase-2 anchor ≈ ¥0.5/episode → ~¥15 for 3×10×k=1 baseline, scale with
  k). *Deliverable:* a reliability report on the new track.

## GO / NO-GO criteria (gate before any scale-up)

**GO** (proceed to add the second mechanism + scale to more projects) requires **all**:

1. **Loop integrity:** golden ≈ 1.0, mutant fails with margin ≥ 0.15, oracle distinguishes mechanism-fixed
   from symptom-suppressed on the hand-written wrong fixes, workspace leaks nothing, anti-cheat holds.
2. **Real gap:** on Phase-0D, the projects are *not* frontier-saturated — at least one strong model fails
   or is unreliable (pass^k materially below pass@1, or non-trivial overconfident-wrong), and the gap is
   **not** explained by infra (429/empty) or pure protocol failure.
3. **Cross-artifact difficulty is the cause:** spot-checked transcripts show failures come from
   *reconciling spec↔SDC↔report* (or producer↔consumer), not from a single-line lookup the project shape
   accidentally still permits.
4. **Reliability layer ingests it cleanly:** the new track renders in `reliability_report.py` with no
   special-casing.

**NO-GO / retire cheaply** if any of:

- The mutant is trivially localizable (frontier solves it like the retired single-fault tracks) →
  the project shape didn't add real cross-artifact difficulty; retire, like P9/LEC/MCMM.
- The gap is noise (within run-to-run variance) or is actually infra/protocol, not capability.
- Building a *valid* oracle that resists symptom-suppression proves intractable for these mechanisms.

Record the verdict the same way the prior six directions were recorded (a memory entry + a one-line
status), GO or NO-GO, so the next cycle inherits the evidence rather than re-deriving it.

## Guardrails (unchanged, restated)

Cheap-probe-before-build; reuse don't fork; EDA tools only on b04 (`/tmp` or `~/Desktop/tsb`, clean up, no
internet/pip); shim stays outside the repo; never commit credentials or raw tool outputs; never modify
hidden/oracle/forbidden/scoring to manufacture a score; grade the golden through the same path before
trusting any number; ¥1000 total budget — Phase 0 is deliberately tiny; do not touch the running Phase-2
reliability directory; no commit/push without explicit instruction.
