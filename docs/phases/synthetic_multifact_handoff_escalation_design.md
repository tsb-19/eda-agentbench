# Synthetic multi-artifact FlowHandoff escalation — mechanism design (Phase-2A, design only)

**Status:** design proposal. No code, no tasks, no tool runs, no model runs. Awaiting review.
**Predecessors:** `docs/synthetic_phase0a_design.md`, `docs/synthetic_phase0b_generator_design.md`
(p10 constraint-drift), `docs/synthetic_flowhandoff_drift_design.md` (p11 single-fault FlowHandoff
A–E). This document defines the **escalation** mechanism: a handoff package whose repair cannot be
reduced to one local edit. Proposed track id `p12_multifact_handoff` (new track; reuses the p10/p11
scalar-Liberty PrimeTime substrate).

---

## 1. Motivation and negative results

The probes closed the single-fault families as *difficulty* mechanisms:

- **p10 constraint-drift: saturated.** Qwen3.7-Max and DeepSeek-V4-Pro pass@1 = pass^k = 1.00,
  flip 0, trust ~1.0. A model that reads `spec.md` and recomputes one budget solves it in one step.
- **p11 FlowHandoff Variant A (manifest→stale netlist) and Variant C (clock-name/unconstrained
  false-clean): also saturated** for Qwen and DeepSeek (both 6/6 by capability score across the
  tiny probe; pass^k=1.0, flip 0, zero overconfident-wrong). Variant C is a *distinct* mechanism but
  **not harder** than A for the top two models — each fault is one-step-diagnosable and one-edit-fixable.
- **MiniMax-M3 continues to expose reliability/protocol signal only** (nocommit/format), not
  capability difficulty — it solves both mechanisms whenever it commits a clean edit.
- **Conclusion that matters:** small single-fault EDA tasks do not produce difficulty for
  protocol-compliant frontier agents. p10 and p11 remain valuable as clean real-tool
  **reliability/protocol substrates** and should be retained as such — not expanded as difficulty
  mechanisms. The next difficulty lever must require **multi-artifact reasoning and multi-step
  restoration**: a task where any single correct-looking local edit still leaves the package broken,
  so the agent must hold and restore a *contract spanning several artifacts at once*.

The escalation hypothesis: difficulty for these agents comes not from hiding one value harder, but
from **coupling** — interdependent inconsistencies where fixing one surfaces or depends on another,
and where "make PrimeTime green" is reachable on a still-wrong package (the silent-false-pass made
worse by the agent's own partial repair).

---

## 2. Mechanism definition

**Multi-artifact handoff escalation:** a handoff *package* contains **≥3 coupled artifacts** and is
mutated with **≥2 mutually-related inconsistencies** such that:

1. no single local edit restores the package — fixing inconsistency X either leaves inconsistency Y,
   or *exposes* Y (e.g. correcting the consumed netlist makes a previously-dormant clock/SDC
   mismatch start to bite);
2. a green PrimeTime sign-off is reachable on a still-incorrect package (by stale-but-self-consistent
   artifacts, or by the agent's own partial fix), so "PT green" is far below pass;
3. the correct repair is a **coordinated set of edits** across the manifest, the downstream script,
   and the SDC (and possibly the report/provenance pointer) that together restore one coherent
   contract: the same netlist revision, clock, scenario, and corner consumed end-to-end, with
   matching provenance, signing off a non-empty, spec-correct timing graph.

Artifacts in scope (any ≥3, with ≥2 coupled mutations):
`handoff_manifest.json`, `netlist_v1.v` / `netlist_v2.v`, `constraints.sdc` (or per-scenario SDCs),
`pt_signoff.tcl` (the downstream script that actually selects what PT reads), `timing_report.rpt`
(provenance-stamped golden report), a scenario/corner config, the library selection, and
`spec.md` / `design_intent.md` as the authority.

**Anti-collapse invariant (load-bearing):** the editable surface and the mutation set must be chosen
so that *every* single-file edit leaves at least one hidden-oracle check failing. This is the
property the whole design must defend (see §6, §7, §12).

---

## 3. Candidate first scenario

**Scenario "stale-package triangle" — manifest vs script vs SDC, with a stale report.**

The manifest declares the intended contract:
- `netlist = netlist_v2.v` (current, `clk_main`, has the `en` qualifier)
- `corner = slow`, `scenario = func`, `clock = clk_main`
- `script = pt_signoff.tcl`, `constraints = constraints.sdc`, `report = timing_report.rpt`

The mutant package drifts **three coupled artifacts**:
- **`pt_signoff.tcl` reads `netlist_v1.v`** (the stale pre-ECO netlist, `clk_old`, no `en`) instead
  of the manifest-named `netlist_v2.v` — the script ignores the manifest.
- **`constraints.sdc` constrains `clk_old`** — consistent with the *stale* netlist the script reads,
  inconsistent with the manifest/spec intent (`clk_main`).
- **`timing_report.rpt` is the v1/clk_old report** (old provenance stamp) — it "agrees" with the
  drifted script+SDC, so a flow that trusts the report looks internally consistent on the wrong design.

The manifest itself is *correct* (names v2 / clk_main / slow / func). So the package has two
self-consistent islands: {manifest, spec} say v2/clk_main; {script, SDC, report} say v1/clk_old. PT
run through the **script** signs off green on the stale v1 design — a silent-false-pass.

Why this resists single edits:
- Fix the **SDC** to `clk_main` alone → the script still reads v1 (which has no `clk_main` port) →
  zero constrained paths / link error → not fixed.
- Fix the **script** to read v2 alone → the SDC still says `clk_old` (absent on v2) → zero
  constrained paths → false-clean persists.
- Fix the **manifest** alone → it was already correct; nothing changes.
- The correct repair is **script→v2 AND SDC→clk_main** (two coordinated edits), plus reconciling the
  **report provenance** to the v2 run (re-point/regenerate), so all three consumers agree with the
  manifest/spec.

---

## 4. Golden package

- `handoff_manifest.json`: netlist=`netlist_v2.v`, clock=`clk_main`, scenario=`func`, corner=`slow`,
  script=`pt_signoff.tcl`, constraints=`constraints.sdc`, report=`timing_report.rpt`, with the v2
  provenance hash and the report stamped to the v2/clk_main/slow run.
- `pt_signoff.tcl`: reads the **manifest-named** netlist + SDC + corner library, runs setup sign-off,
  emits `^SIGNOFF_OK`.
- `constraints.sdc`: `create_clock -name clk_main ... [get_ports clk_main]`, I/O budget per spec;
  constrains the sequential paths.
- `netlist_v2.v` (current), `netlist_v1.v` (stale, provenance history only), library corner assets
  (`tiny_slow.db` / `tiny_typ.db`), `tiny.lib`.
- `timing_report.rpt`: provenance stamp = {netlist=v2 hash, clock=clk_main, corner=slow}.
- Expected **public runner** output: `HANDOFF_PUBLIC: OK` with consumed=v2/clk_main/slow,
  constrained_paths≥1, signoff=OK — verdict on line 1.
- Expected **hidden oracle** output: `SIGNOFF_OK`, `ARTIFACT_CONSISTENCY_OK`,
  `SCENARIO_CLOCK_OK`, `PROVENANCE_OK`, all `*_SCORE: 1.000` → full credit.

## 5. Mutant package

Exactly three artifacts inconsistent (script, SDC, report), manifest + spec correct:
- **Visible-through-public:** the public runner (which obeys the manifest) flags that the
  **script** consumes a netlist different from the manifest's, and/or that the consumed clock isn't
  the intended one — a cross-artifact mismatch verdict (symptom, not fix).
- **Silent unless cross-checked:** the **report provenance** is stale (v1 stamp). A flow that reads
  the report as evidence sees a "clean" historical run; only hashing the report stamp against the
  current netlist reveals it. This inconsistency does not surface in a naive PT run at all.
- **Realism:** a re-synthesis (v1→v2) and a clock rename (clk_old→clk_main) landed in the manifest
  and spec, but the downstream sign-off script, the SDC, and the archived report were never updated —
  the single most common real "the flow is signing off last week's netlist" failure, escalated to
  the realistic case where *several* downstream artifacts lag together and mutually corroborate.
- **Why local repair is insufficient:** the {script, SDC} pair is jointly stale; fixing either alone
  yields zero constrained paths (clock/port mismatch) — the false-clean simply changes shape. The
  report stays wrong regardless until explicitly reconciled. Full sign-off of the *intended* design
  is only reachable after the coordinated set.

## 6. Repair surface

- **Editable (the coordinated repair surface, ≥2 files):**
  - `pt_signoff.tcl` — repoint the consumed netlist (and corner/SDC selection) to the manifest's.
  - `constraints.sdc` — bind `clk_main` (and the func/slow scenario budget).
  - `handoff_manifest.json`'s **report pointer** (or a small `provenance.json`) — reconcile the
    report provenance to the current run. (Manifest's netlist/clock/corner fields are golden and
    read-only — see below — so the agent cannot "fix" by corrupting the authority.)
- **Read-only (visible):** `spec.md` / `design_intent.md`, `netlist_v1.v`, `netlist_v2.v`,
  `tiny.lib`, the corner `.db`s, `timing_report.rpt`, the manifest's design/netlist/clock/corner/
  scenario fields, `run_public.{sh,tcl}`.
- **Forbidden (anti-cheat enforced):** every netlist and library/corner asset, the report *content*
  (only the pointer/provenance may be reconciled, not hand-edited), the public/hidden runners, the
  hidden oracle + truth. Editing any of these → anti-cheat fail regardless of sign-off.
- **Explicitly disallowed shortcuts** (rejected by the oracle, §7): editing a netlist to match the
  stale SDC/script; deleting/over-riding a consistency check; weakening timing (period/uncertainty/
  exceptions); fabricating or hand-stamping the report; bypassing the manifest in the script (e.g.
  hardcoding a green echo); editing manifest authority fields to legalize the stale island.

**Surface-design rule (load-bearing):** the editable set must never contain *both* sides of any
single consistency pair such that one edit can satisfy a check by corrupting its reference; and the
mutation must be placed so that no single editable file, alone, clears all of `SIGNOFF`,
`ARTIFACT_CONSISTENCY`, and `SCENARIO_CLOCK`.

## 7. Oracle design

Hidden, stdlib, marker-anchored (the p11 pattern, extended), run over the agent-repaired package
laundered through fresh PT sessions. New/extended `^`-anchored markers:

1. **Sign-off** — fresh-session PT setup sign-off of the **manifest-+-script-consumed** design is
   clean and **non-empty** (zero constrained paths = FAIL, as in Variant C). → `^SIGNOFF_OK/FAIL`.
2. **Artifact consistency** — the script consumes the manifest's netlist; the consumed netlist's
   content hash matches the manifest's declared provenance; the consumed library corner matches the
   manifest. → `^ARTIFACT_CONSISTENCY_OK / _SCORE / _DETAIL`.
3. **Scenario/clock consistency** — the laundered SDC binds the manifest/spec clock (`clk_main`, not
   a stale name) and the intended sequential endpoints are actually constrained (coverage ≥ min),
   for the manifest's scenario. → `^SCENARIO_CLOCK_OK / _SCORE`.
4. **Provenance/report consistency** — the report referenced as current evidence carries a stamp
   matching the consumed netlist/clock/corner (no stale report accepted; no fabricated stamp). →
   `^PROVENANCE_OK / _SCORE`.
5. **Masking** — timing weakening / exceptions / manifest-bypass in the script → `^HANDOFF_MASKING_DETECTED`,
   which zeroes the consistency components.
6. **Anti-cheat** — forbidden-artifact modification / hidden-shadow via the existing
   `detect_forbidden_modifications` / `detect_hidden_shadows`.

The oracle must **distinguish** (each maps to a distinct score outcome, all verified by tests, §10):
true full repair (all OK → 1.0); PT green on the wrong package (SIGNOFF maybe OK but
ARTIFACT/SCENARIO/PROVENANCE fail → far below pass); correct netlist but wrong SDC (SCENARIO_CLOCK
fail → below pass); correct SDC but wrong script/manifest-consumed netlist (ARTIFACT fail → below
pass); stale report accepted (PROVENANCE fail → below pass); fabricated report (PROVENANCE fail +
possibly anti-cheat); forbidden edit (anti-cheat fail).

**Partial-consistency rule (the escalation's core):** the gate requires **all** of SIGNOFF ∧
ARTIFACT_CONSISTENCY ∧ SCENARIO_CLOCK to be OK (PROVENANCE refines toward full credit). Any *single*
restored axis with another still broken stays **below the pass gate** — partial consistency is never
a pass.

## 8. Scoring contract

Proposed components (sum 1.0):

- `signoff` (tool_run): **0.15** — clean, non-empty sign-off of the consumed design.
- `artifact_consistency`: **0.35** — script↔manifest↔netlist (+ corner) agreement; the core coupling.
- `scenario_clock_consistency`: **0.20** — clock binding + scenario coverage (the Variant-C axis).
- `provenance_report_consistency`: **0.15** — report stamp matches the consumed run; no stale/fake.
- `explanation`: **0.10**.
- `protocol_compliance`: **0.05** — reliability layer (nocommit/format), as in p10/p11.

**Pass gate:** `total ≥ 0.5` **iff** SIGNOFF_OK ∧ ARTIFACT_CONSISTENCY_OK ∧ SCENARIO_CLOCK_OK ∧ no
forbidden edit. With these weights, signoff+explanation+protocol alone = 0.30 (far below 0.5), so
**final PT green on a wrong package cannot pass**; and any single objective axis missing
(artifact 0.35 or scenario 0.20) drops total below 0.5 — enforcing that *partial* restoration fails.
PROVENANCE (0.15) separates full (1.0) from "correct design signed off but report not reconciled"
(0.85, still a pass — provenance is the refinement axis, optionally promotable into the gate if we
want report reconciliation mandatory; flagged as a tuning decision for review).

## 9. Public feedback design

All prior harness lessons apply:
- **Verdict first, within the first ~1000 bytes** of `run_public.sh` stdout (offset 0), ahead of the
  PT banner / any report dump. Form: `HANDOFF_PUBLIC: OK|MISMATCH consumed=<netlist>/<clock>/<corner>
  manifest=<...> constrained_paths=N signoff=<...>` + one `PUBLIC_HINT:` line.
- **Public runner is manifest-driven and executable without hidden files**; references **no**
  hidden artifact and emits **no** hidden-oracle markers (`ARTIFACT_CONSISTENCY`, `PROVENANCE`, etc.).
- **Concise symptoms, no fix:** the hint states *what disagrees* ("script consumes a netlist the
  manifest does not name"; "consumed clock not bound / 0 constrained paths"; "report stamp ≠ consumed
  netlist") but never the target names/hashes. It must give a human/agent enough to diagnose by
  cross-checking the visible artifacts, and no more.
- **No exact-answer literal leak:** the correct netlist name is discoverable (it's the manifest's),
  but no hidden secret (golden provenance hash, expected stamp) appears in any visible file — extend
  the p11 no-leak scan to hashes, clock names, corner names, and report stamps.
- **No long report dump before the verdict** (the Phase-0D truncation lesson); the dump, if any,
  follows the marker lines and is `-nworst 1`.

## 10. Tests and validation plan (before any model probe)

Tool-free contract tests (mirror `test_flow_handoff*.py`) + a b04 real-PT gate:
- golden package validates: all oracle markers OK; real-PT golden = 1.0.
- mutant fails below pass; golden−mutant objective margin ≥ 0.15.
- **true full repair (coordinated: script→v2 ∧ SDC→clk_main ∧ report reconciled) scores 1.0.**
- **each single-edit partial repair fails below pass** — script-only, SDC-only, manifest-pointer-only,
  report-only — one explicit test per single edit (this is the escalation's defining test).
- PT-green-but-wrong-package fails (consumed stale island, SIGNOFF maybe OK, ARTIFACT/SCENARIO fail).
- stale report accepted → PROVENANCE fail; fabricated report → PROVENANCE/anti-cheat fail.
- forbidden netlist/lib/report-content edit → anti-cheat fail; hidden-shadow detection.
- masking (weaken timing / bypass manifest in script) → handoff credit 0.
- public verdict within first 1000 bytes (mock-PT); no hidden-oracle markers in public stdout;
  public scripts reference no hidden-only artifacts; no literal/hash/stamp leak.
- agent workspace runnable without hidden files.
- **CLI and agentic evaluator dispatch parity** for `multifact_handoff.MultiFactHandoffEvaluator`
  (add to BOTH `cli.py` and `agentic/runner.py`; pin with a parity test — the Phase-0D lesson).
- real PrimeTime golden/mutant validation on b04; deterministic task layout (byte-stable).
- forwarder-boundary check: any selection passed to a fresh PT session goes via a workspace file
  (e.g. `selected.tcl`), never an env var (the Variant-A lesson).

## 11. Generator implications

**Hand-author first.** The escalation's correctness hinges on the *coupling* between mutations
(every single edit must leave a check failing) and on the oracle distinguishing 6+ partial states —
properties that must be proven on one concrete package on real PT before any parameterization. A
generator that emits subtly *decoupled* mutations (where one edit happens to satisfy two checks)
would silently reintroduce the single-edit collapse the whole mechanism exists to avoid.

Later generator outline (only after a hand-authored GO):
- **seed** chooses which artifact pair/triple drifts (script+SDC, script+SDC+report, manifest-island
  vs consumer-island split) and the design params (revisions, clock names, scenarios, corners).
- **provenance hashes** generated deterministically from the templated netlists/reports and written
  into both manifest (declared) and hidden truth (golden).
- **scripts and reports generated from the golden package** so provenance is exact and machine-checkable.
- **mutant application** records the full parameter vector (which artifacts drifted, each mutation,
  the predicted partial-repair scores) in `generator.params`.
- **acceptance filters** (extend the p10/p11 F-series) must include a **coupling filter**: simulate
  every single-file edit and assert each leaves ≥1 oracle check failing (reject any task solvable by
  one edit), plus the no-decoupling, no-literal/hash/stamp-leak, determinism, verdict-first, and
  no-both-sides-of-a-pair-editable filters.
- generated tasks must require **≥2 coordinated repairs** by construction (assert in the filter).

## 12. GO / NO-GO criteria

**GO** if a hand-authored golden + multi-inconsistency mutant on real b04 PrimeTime yields a fair,
reproducible task where:
- the true fix requires **coordinated multi-artifact restoration** (≥2 editable files), proven by
  the single-edit-each-fails tests;
- a single local edit is insufficient (each leaves an oracle check failing);
- final sign-off green alone is far below pass (≤0.30);
- the oracle cleanly distinguishes true repair from symptom suppression and from each partial state;
- public feedback is fair, verdict-first, leak-free, and diagnosable by cross-checking visible artifacts.

**NO-GO** if it collapses into: a one-line SDC edit; a one manifest-pointer edit; a one script edit;
an answer leaked by spec/report; local symptom suppression accepted as pass; or an **ambiguous oracle
with multiple equally-valid repairs** (the new failure mode for multi-artifact tasks — there must be
exactly one coherent restored contract, or the grade is unfair). The single greatest risk is
**accidental decoupling** (the mutations don't actually interlock, so one edit clears the gate);
the design must treat the coupling filter as the central correctness property.

---

### Phase-2A discipline
Prove the contract on ONE hand-authored golden + ONE coupled-mutant on real b04 PrimeTime, with the
single-edit-each-fails tests passing, **before** writing a generator; then a cheap falsification
probe before scaling — the same sequence that cheaply caught p10/p11 saturation.
