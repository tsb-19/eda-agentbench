# Synthetic Failure-Mechanism Taxonomy

Status: **DESIGN DRAFT (planning only).** Companion to `synthetic_eda_project_generator_plan.md`.

This document defines a taxonomy of **failure mechanisms**, not task types. A task type ("debug an SDC")
is what we already saturated. A *mechanism* is a way a real chip project breaks where the **root cause and
the symptom live in different artifacts or different flow stages**, so resolving it requires cross-artifact
reconciliation — the work that does not reduce to "grep for the broken line".

For each mechanism the entry states, uniformly:

- **Golden** — what is in the correct, passing project.
- **Mutant** — how the mutator injects the mechanism automatically from the golden.
- **Symptom (tool-visible)** — how a commercial tool surfaces it to the agent.
- **Oracle (auto-judge)** — how we decide *mechanism resolved* vs *symptom merely suppressed*,
  machine-checkably, reusing the anchored-marker evaluator pattern.
- **Why harder than single-point debug** — the cross-artifact / cross-stage property.
- **Frontier-shortcut risk** — the honest way a capable agent might collapse it; what the Phase-0 probe
  must falsify before we invest.

The MVP (`synthetic_phase0_mvp.md`) implements only the first two mechanisms (constraint drift, flow
handoff drift) on VCS+DC+PrimeTime. The rest are designed here so the schema and oracle conventions are
general, but are **deferred** until the MVP proves the loop.

---

## A. Constraint drift  *(MVP mechanism #1)*

- **Golden:** `spec.md` states the timing contract (clock period, IO budget, false/multicycle exceptions);
  `constraints.sdc` encodes *exactly* that contract; DC synthesis and PrimeTime sign-off both pass against it.
- **Mutant:** mutate the SDC so it silently *diverges from the spec* — period tightened/loosened, an IO
  delay dropped, an exception added/removed — while staying syntactically valid and tool-accepted. The
  spec is unchanged; only the encoding drifts.
- **Symptom:** PrimeTime reports a violation (or a *suspiciously clean* slack that contradicts the spec
  budget), or DC optimizes to the wrong target. The error is real but its cause is "the constraint no
  longer means what the spec says".
- **Oracle:** the hidden run script re-derives the intended constraint set from a machine-readable spec
  fixture and checks the agent's SDC against *spec-equivalence* (clocks, IO budgets, exceptions match the
  spec), then runs PT sign-off. Emits `^CONSTRAINT_SPEC_SCORE: <frac>` (fraction of spec properties the
  SDC satisfies) **and** `^SIGNOFF_OK`. Over-constraining to mask the symptom fails spec-equivalence even
  if PT goes green — the key discriminator.
- **Why harder:** the broken artifact (SDC) and the authority (spec) are different documents; the symptom
  appears in a third (PT report). The agent must reconcile three sources, not patch one.
- **Frontier-shortcut risk:** if the spec is terse and the SDC is short, a strong model may just diff
  "SDC vs the obvious reading of the spec" and win. **Mitigation / probe:** spec must contain real budget
  arithmetic (IO delay = launch + margin) so the correct constraint is *derived*, not copied; the Phase-0
  probe checks whether models that pass actually reconstructed the budget vs guessed.

## B. Flow handoff drift  *(MVP mechanism #2)*

- **Golden:** the flow is staged — elaborate/synthesize (DC) produces a netlist + an SDC/SDF handoff that
  PrimeTime consumes for sign-off; the handoff artifacts are mutually consistent.
- **Mutant:** break the *handoff*, not either stage internally — e.g. DC writes the netlist with one
  module/clock naming, the PT script reads constraints that assume the pre-synthesis name; or the
  generated-clock definition is correct in DC but the SDC handed to PT references the source pin that
  synthesis renamed. Each stage *in isolation* looks fine.
- **Symptom:** PrimeTime errors on unresolved references / unconstrained clocks, or silently sign-offs an
  *under-constrained* netlist (paths fall out of the analysis). VCS elaboration of the netlist may also
  expose the rename.
- **Oracle:** hidden script runs the *full* DC→PT chain and checks the handoff invariants: every clock in
  the netlist is constrained in PT, no unresolved references, sign-off path count matches the golden's.
  Emits `^HANDOFF_OK` / `^HANDOFF_SCORE: <frac>` plus `^SIGNOFF_OK`. Fixing only the consumer (PT script)
  to paper over a producer (DC) rename is detectable because the golden invariant set won't all hold.
- **Why harder:** the root cause is *between* stages; neither stage's local checker fires. This is the
  canonical "works on my stage, breaks at integration" failure that single-file tasks structurally cannot
  express.
- **Frontier-shortcut risk:** if only one name is renamed, search collapses to "find the one mismatched
  identifier". **Mitigation / probe:** require the agent to choose the *correct side* to fix (producer vs
  consumer) and grade that choice; multiple consistent-but-wrong patches must score lower than the
  producer-side fix.

## C. Generated-clock / multicycle / false-path semantic drift

- **Golden:** a `create_generated_clock` (divider/MUX), multicycle, or false-path exception that is
  *semantically correct* for the RTL's actual timing relationship.
- **Mutant:** keep it syntactically valid but semantically wrong — divide-by factor off, multicycle set on
  a path that is actually single-cycle, false-path on a path that must meet. (This is the P9 mechanism, but
  embedded in a project where the RTL + spec jointly define the *true* relationship, not a lone constraint.)
- **Symptom:** PT either reports a violation (too-tight) or a deceptively-clean report (too-loose / falsely
  cut path) that contradicts what the RTL can actually do.
- **Oracle:** hidden script cross-checks the exception against an RTL-derived timing-relationship fixture
  (golden generated-clock ratio, golden multicycle multiplier) and re-runs PT; emits
  `^EXCEPTION_SEMANTIC_SCORE: <frac>` + `^SIGNOFF_OK`. Loosening to hide the symptom fails the semantic
  check.
- **Why harder:** correctness is defined by RTL behavior, not by syntax or by the constraint alone.
- **Frontier-shortcut risk:** **high** — this is exactly where P9 collapsed once. Only include in a project
  if the project context (multiple interacting clocks, real divider RTL) demonstrably re-hardens it; the
  taxonomy keeps it but flags it for a mandatory falsification probe.

## D. Library / scenario / corner drift

- **Golden:** sign-off uses the intended Liberty corner(s) / operating scenario consistent with the spec.
- **Mutant:** swap or drop a corner / scenario — sign off at the wrong PVT, or omit a corner the spec
  requires — so the *reported* timing is real but answers the wrong question.
- **Symptom:** PT passes at the wrong corner or a required scenario is missing from the analysis; numbers
  look fine but don't cover the spec.
- **Oracle:** hidden script checks the active scenario/corner set against the spec's required set and
  re-runs sign-off across all required corners; emits `^CORNER_COVERAGE_SCORE` + `^SIGNOFF_OK`.
- **Why harder:** the symptom is an *absence* (a corner not analyzed), not a present error line.
- **Frontier-shortcut risk:** medium — listing required corners from a spec is enumerable; difficulty
  depends on the spec encoding coverage as a derived requirement. Deferred past MVP (needs multi-corner
  Liberty assets).

## E. Checkpoint / version drift

- **Golden:** scripts, netlist, SDC, and reports all correspond to the same design revision / checkpoint.
- **Mutant:** advance one artifact and not the others — an SDC updated for a new port that the netlist
  checkpoint predates, or a report regenerated against a stale netlist.
- **Symptom:** unresolved references, count mismatches, or a report whose totals can't be reproduced from
  the netlist.
- **Oracle:** hidden script regenerates the report/sign-off from the *current* artifacts and checks
  internal consistency (every spec'd object present, report reproducible); emits `^CONSISTENCY_SCORE`.
- **Why harder:** the fault is a *relationship* (mutual staleness) across ≥2 artifacts; no single file is
  "wrong" in isolation.
- **Frontier-shortcut risk:** medium. Deferred past MVP.

## F. CDC / waiver drift

- **Golden:** clock-domain-crossings are correctly synchronized; lint/CDC waivers apply only to genuinely
  safe crossings.
- **Mutant:** add an over-broad waiver that masks a real unsynchronized crossing, or remove a legitimate
  waiver so noise drowns the real issue.
- **Symptom:** SpyGlass CDC reports clean (because waived) despite a real hazard, or floods with false
  violations.
- **Oracle:** hidden script diffs the *effective* (post-waiver) violation set against the golden hazard
  set; emits `^CDC_HAZARD_SCORE`. Waiving the symptom away is the failure mode it catches.
- **Why harder:** the waiver file and the RTL jointly determine correctness; a clean report can be *worse*
  than a noisy one.
- **Frontier-shortcut risk:** medium–high (waiver reasoning is subtle but enumerable). Deferred — needs
  SpyGlass, out of MVP tool scope.

## G. ECO / Formality drift

- **Golden:** a functional ECO is applied to both RTL and netlist; Formality proves pre/post equivalence
  under the intended don't-cares.
- **Mutant:** apply the ECO to one representation only, or under the wrong key-point mapping, so
  equivalence silently breaks (or is falsely asserted).
- **Symptom:** Formality reports non-equivalence, or passes only because the mapping hides a real diff.
- **Oracle:** hidden `fm_shell` run with the golden key-point map; emits `^LEC_EQUIV` / `^LEC_SCORE`.
- **Why harder:** correctness spans two representations + a mapping; this is the LEC-attribution idea but
  embedded in a project with a real ECO intent.
- **Frontier-shortcut risk:** **high** — combinational single-fault LEC already saturated (#118). Keep only
  if the ECO is multi-point and the project context re-hardens it. Deferred — needs Formality.

## H. Timing / PPA drift

- **Golden:** synthesis meets the spec's timing *and* area/power budget.
- **Mutant:** a constraint or directive change that meets timing but blows area/power, or vice-versa — a
  *trade-off* regression, not a hard failure.
- **Symptom:** sign-off "passes" timing but the PPA report violates the spec budget; or timing fails while
  area is comfortably under.
- **Oracle:** hidden script checks the full spec budget vector (WNS/TNS *and* area/power) from real reports;
  emits per-metric `^PPA_SCORE`.
- **Why harder:** there is no single pass/fail; the agent must balance a vector against a multi-objective
  spec — the realistic version of "fix it".
- **Frontier-shortcut risk:** medium; risk of search-collapse if the trade-off has one obvious knob.
  Deferred past MVP.

## I. DRC / physical drift

- **Golden:** placed/routed block is DRC-clean and matches floorplan intent.
- **Mutant:** a constraint/floorplan edit that introduces localized DRC or a spec-violating placement.
- **Symptom:** ICC2/Innovus DRC report shows violations tied to the edit.
- **Oracle:** hidden P&R + DRC run; emits `^DRC_SCORE` against the golden-clean baseline.
- **Why harder:** couples logical constraints to physical outcome across the synthesis→P&R handoff.
- **Frontier-shortcut risk:** unknown; **expensive** (full P&R). Deferred — out of MVP tool scope (needs
  ICC2/Innovus), and cost makes it a late candidate at best.

## J. Analog / post-layout parasitic drift

- **Golden:** schematic sizing meets spec; post-layout (parasitic-annotated) simulation still meets spec.
- **Mutant:** a sizing/layout-parasitic change that passes schematic-level but fails post-layout (or a
  corner/temperature the spec requires).
- **Symptom:** Spectre post-layout sim misses a spec metric (gain/BW/phase-margin/settling) that the
  schematic-level sim met.
- **Oracle:** hidden Spectre run with extracted parasitics; emits per-metric `^ANALOG_SPEC_SCORE` (reusing
  the P4 measure-window discipline).
- **Why harder:** schematic-vs-post-layout is a cross-representation gap; the symptom only appears with
  parasitics.
- **Frontier-shortcut risk:** medium; P4 sizing already showed simulator-in-the-loop sizing can collapse
  (memory `damping-track-frontier-collapse`), so this must be a *diagnosis* (why does post-layout miss),
  not a *search*. Deferred — needs Spectre + extraction.

---

## Cross-cutting oracle conventions (apply to every mechanism)

1. **Execution-based, marker-anchored.** The hidden run script is the authority and emits `^MARKER`
   (or `^NAME_SCORE: <frac>`) lines; the evaluator only parses anchored markers from the combined log —
   identical to `dc_constraint_debug.py`. No exact-diff grading.
2. **Mechanism-fixed vs symptom-suppressed.** Every oracle must score the *mechanism* (spec-equivalence,
   handoff invariants, semantic relationship) independently of whether the headline tool went green, so
   over-constraining / masking / consumer-only patches score below the true producer-side fix.
3. **Golden ground truth.** Because every project is generated, the golden artifacts and the injected
   mechanism are known; the oracle compares against generated fixtures, never against an LLM answer.
4. **Reliability-layer first.** Every score flows through `reliability.py` so "solvable but unreliable /
   overconfident" remains visible and infra (429/empty) never counts as capability.
5. **Falsify before scaling.** Each mechanism carries a shortcut-risk note; none is built at scale until a
   cheap multi-model probe shows the gap is real and survives the reliability layer (the lesson from the
   six retired directions).
