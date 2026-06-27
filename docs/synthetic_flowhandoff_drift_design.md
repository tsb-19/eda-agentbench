# Synthetic FlowHandoff drift — mechanism design (Phase-0E design only)

**Status:** design proposal. No code, no tasks, no tool runs, no model runs. Awaiting review.
**Predecessor:** `docs/synthetic_phase0a_design.md`, `docs/synthetic_phase0b_generator_design.md`
(constraint-drift, track `p10_synthetic_project`). This document defines the *next* mechanism
family and is deliberately written to avoid repeating constraint-drift's collapse.

---

## 1. Motivation

Phase-0D closed constraint-drift as a standalone **difficulty** mechanism:

- **Qwen3.7-Max and DeepSeek-V4-Pro saturated it** — pass@1 = 1.00, pass^k = 1.00, flip = 0.00,
  trust = 1.00 across all generated p10 tasks and all three trials. A model that reads `spec.md`
  and recomputes one budget (e.g. `t_co + flight`, `t_su + flight`) solves it in a single step.
- **MiniMax-M3 exposed only protocol instability**, not capability difficulty — when it emitted a
  well-formed tool call it scored 1.0; its failures were `nocommit` from a command-formatting
  artifact (`]<]minimax[>[`). Useful reliability signal, not task difficulty.
- **p10 remains valuable** as a clean, real-PrimeTime **reliability/protocol substrate**: it
  already discriminates models by trust without any difficulty pretension. We keep it for that.
- **Therefore the next mechanism must require cross-artifact reasoning**, not deriving a number
  from `spec.md`. The defining property of constraint-drift's weakness was that *all information
  needed to solve it lived in one file and reduced to one arithmetic edit*. FlowHandoff drift is
  designed so that **no single file contains the answer**: the fault is an *inconsistency between
  artifacts*, and the agent must (a) locate which artifact disagrees with which, and (b) restore
  the handoff contract — a diagnosis problem, not an arithmetic problem.

The north-star test still governs: this must measure a *real* capability gap vs human chip
engineers (who routinely chase "the netlist the manifest points at is last week's"), not
contrived difficulty. Cross-artifact handoff reconciliation is a genuine, daily EDA skill.

---

## 2. Mechanism definition

**FlowHandoff drift:** a handoff *package* (the set of artifacts a downstream flow consumes) is
internally inconsistent because exactly one artifact, mapping, or provenance pointer was mutated
away from the golden package, while the rest of the package and the authoritative intent
(`spec.md` + a manifest) still describe the un-mutated state. The downstream DC/PT flow then
either (a) **fails** with a mismatch error, or — the more valuable case — (b) **silently
consumes the wrong artifact** and produces a green-but-meaningless sign-off.

The inconsistency must span **at least two** of:

- RTL source (`design.v`)
- synthesized netlist (`*_netlist.v`), possibly multiple versions
- SDC constraints (`constraints.sdc`, possibly per-scenario)
- library path / library version / corner (`tiny.lib` / `tiny.db`, fast/typ/slow)
- top module name
- clock name
- generated report (timing/area report from the golden flow)
- handoff manifest / config (`handoff_manifest.json`)
- downstream PT/DC script (`pt_signoff.tcl` / `dc_synth.tcl`)

**Hard constraint (anti-collapse):** the fault must **not** be repairable by editing one obvious
numeric constraint, nor be derivable from `spec.md` alone. The repair requires comparing two or
more artifacts and restoring agreement. A correct fix that does not restore *full* cross-artifact
consistency must not pass (the oracle checks the whole contract, §5).

**Distinction from p10 constraint-drift:** p10 asks "is this number right per the spec budget?".
FlowHandoff asks "do these artifacts describe the *same* design/scenario/corner, and does the
flow consume the *intended* one?". The first is local arithmetic; the second is global provenance.

---

## 3. Candidate mini-project concept

One tiny but realistic handoff package — proposed track id `p11_flow_handoff` (new track; reuses
the p10 scalar-Liberty timing substrate so a wrong artifact yields a *real* PrimeTime
consequence, not just a structural diff).

A `pipe_stage` (or reuse `acc_stage`) handoff bundle:

```
files/ (agent-visible)
  spec.md                  # authoritative intent: top name, clock name, scenario, corner, port list
  design.v                 # RTL source (reference)
  netlist_v1.v             # an EARLIER synthesized netlist (stale)
  netlist_v2.v             # the CURRENT synthesized netlist (matches spec/RTL)
  constraints.sdc          # SDC (single- or per-scenario; see variants)
  handoff_manifest.json    # the handoff contract: which netlist/sdc/corner/clock/top to use + provenance hashes
  tiny.lib / tiny.db       # scalar Liberty (typ); plus corner assets where a variant needs them
  reports/golden_timing.rpt# a report emitted by the golden flow (carries a provenance stamp)
  run_public.sh/.tcl       # public feedback runner (manifest-driven, verdict-first)
hidden/ (grading only)
  run_hidden.sh/.tcl       # launder + run signoff in a fresh session from the REPAIRED package
  run_signoff.tcl
  grade_handoff.py         # cross-artifact consistency oracle (stdlib only)
  handoff_truth.json       # the golden handoff contract (top/clock/scenario/corner/hashes/ports)
solution/
  <repaired artifact(s)>   # the golden form of whatever the agent must fix
```

The package must *feel like an EDA handoff*: a manifest naming the design + scenario + corner +
provenance, a downstream script that obeys the manifest, frozen synthesized netlists, and a
report stamped with which netlist produced it. The agent's job is the everyday "this package
doesn't hang together — make it consistent and sign off."

**Substrate reuse:** keep the p10 scalar-Liberty closed-form timing (BUF 0.10, DFF clk→Q 0.08,
setup 0.02) so that consuming the wrong netlist/clock/corner produces a *real* slack change or a
*real* "no paths constrained" outcome. DC is represented by **frozen** synthesized netlists
(no live `dc_shell` needed for the first variant); a later variant may add a frozen `dc_synth.tcl`
+ area report for provenance checks.

---

## 4. Drift variants

For each: golden state → mutant change → public symptom → realism → true fix → rejected shortcuts.

### Variant A — manifest points to stale netlist (RECOMMENDED FIRST)
- **Golden:** `handoff_manifest.json` selects `netlist_v2.v` and records its provenance hash;
  `v2` matches the RTL/spec port list; SDC constrains `v2`'s ports; PT signs off clean.
- **Mutant:** manifest's `netlist` pointer (and/or its declared hash) is changed to
  `netlist_v1.v` (the stale version, e.g. missing a port `en` or an extra legacy port).
- **Public symptom:** PT run via the manifest either errors (`get_ports en` returns empty → SDC
  command fails) **or silently** constrains the stale design (a port the spec requires is absent,
  so a real path goes unconstrained → falsely "clean"). The public verdict shows the mismatch
  (port-count / unconstrained-path hint) without naming the fix.
- **Realism:** the single most common real handoff bug — the manifest/Makefile points at last
  week's netlist after a re-synthesis.
- **True fix:** repoint the manifest to `netlist_v2.v` and update its declared provenance hash to
  `v2`'s, so the flow consumes the design the spec/RTL describe.
- **Rejected shortcuts:** editing the SDC to match the *stale* netlist (suppresses the symptom
  but consumes the wrong design); deleting the port check; `set_false_path` to hide an
  unconstrained path; editing `netlist_v1.v` to look like v2 (forbidden artifact); hand-editing
  the report.

### Variant B — downstream script/manifest selects the wrong SDC for the scenario
- **Golden:** manifest declares `scenario = func` → `constraints_func.sdc`; PT script reads the
  manifest-selected SDC; sign-off clean for the functional scenario.
- **Mutant:** manifest's scenario→SDC mapping (or the selected scenario field) is flipped to
  `constraints_test.sdc` (a different scenario's constraints with a different clock period / IO
  budget).
- **Public symptom:** PT may pass with the *wrong* SDC (silent — green but the functional
  scenario is unverified) or fail if the test SDC references ports/clocks absent in the func setup.
- **Realism:** multi-scenario sign-off where the wrong constraint set gets wired in is a classic
  MMMC/handoff slip.
- **True fix:** correct the manifest's scenario selection / mapping so the func scenario uses
  `constraints_func.sdc`.
- **Rejected shortcuts:** editing `constraints_test.sdc` numbers to "pass" (wrong scenario still
  selected); editing the PT script to bypass scenario selection; hardcoding a clean report.

### Variant C — clock name renamed in netlist but SDC still constrains the old clock
- **Golden:** netlist + manifest + SDC all use clock `clk`; `create_clock` lands on a real port;
  paths constrained; clean.
- **Mutant:** current netlist (`v2`) renames the clock port to `clk_core` (a realistic ECO), and
  the manifest reflects `clk_core`, but `constraints.sdc` still says `create_clock ... clk`.
- **Public symptom:** `create_clock` targets a non-existent/old port → either an error or, worse,
  **no paths constrained** → PT reports "clean" because nothing was checked (silent false pass).
- **Realism:** clock renames during ECO/restructuring routinely strand SDCs.
- **True fix:** update the SDC clock object to `clk_core` to match netlist+manifest (and any
  `get_clocks`/`-clock` references).
- **Rejected shortcuts:** adding a second create_clock without removing the dangling one;
  `set_false_path`; renaming the port back in the netlist (forbidden); editing the manifest to the
  old name (contradicts spec/netlist → oracle rejects).

### Variant D — library corner mismatch (manifest says slow, script/asset loads typ/fast)
- **Golden:** manifest declares `corner = slow`; the package ships `tiny_slow.db`; PT loads the
  slow corner; sign-off reflects worst-case and is clean by the spec's margin.
- **Mutant:** manifest still says `corner = slow`, but the link/asset actually resolves to
  `tiny_typ.db` (or the manifest's corner field is flipped to `typ` while spec demands slow).
- **Public symptom:** sign-off passes optimistically (typ) though the contract requires slow —
  silent under-sign-off; a corner-stamp mismatch is visible if surfaced.
- **Realism:** signing off the wrong corner is a high-stakes real failure.
- **True fix:** make the consumed corner asset agree with the manifest+spec (`slow`), restoring a
  worst-case-honest sign-off.
- **Rejected shortcuts:** loosening the SDC so typ passes; editing the manifest corner to `typ`
  (violates spec); swapping `.db` content (forbidden asset).

### Variant E — report provenance mismatch (stale report vs current artifacts)
- **Golden:** `reports/golden_timing.rpt` carries a provenance stamp (netlist hash + clock +
  corner) matching the current package; manifest references it.
- **Mutant:** the report is the one from `netlist_v1` (old stamp) while the package is now `v2`;
  the manifest still cites the old report as current evidence.
- **Public symptom:** artifact-hash/version disagreement between report stamp and manifest/netlist;
  a flow that trusts the report would sign off on stale evidence.
- **Realism:** accepting a stale report as current sign-off evidence is a real audit failure.
- **True fix:** regenerate/replace the report reference so provenance matches the current netlist
  (in the synthetic setting: repoint the manifest to the correct/current report and/or mark the
  stale one invalid), and re-run sign-off so live evidence agrees.
- **Rejected shortcuts:** hand-editing the report's stamp to match (fabrication); ignoring the
  mismatch; editing hashes in the manifest without fixing the underlying artifact.

**Coverage rationale:** A/C/E are PT-substrate-tractable with frozen netlists and need no live DC;
B adds scenario selection; D adds corner assets. A and C exercise the silent-false-pass failure
mode that is the whole point of the family.

---

## 5. Oracle design

The hidden oracle (`grade_handoff.py`, stdlib only; marker-anchored like p10's `grade_spec.py`)
must check the **cross-artifact contract**, not merely final sign-off. It runs against the
agent-repaired package (laundered through a fresh session, the P9/p10 two-session pattern) and
emits `^`-anchored markers consumed by the evaluator:

1. **Manifest consistency** — manifest's selected `{netlist, sdc, scenario, corner, clock, top}`
   are mutually coherent and match `handoff_truth.json`. → `^HANDOFF_MANIFEST_OK` / `_SCORE`.
2. **Provenance / hash-version consistency** — declared netlist (and report, for E) provenance
   hashes match the actual file the flow consumes. → `^HANDOFF_PROVENANCE_OK`.
3. **Top / module / port / clock consistency** — the consumed netlist's top name, port list, and
   clock name agree with spec + manifest + SDC objects. → `^HANDOFF_IFACE_OK`.
4. **Correct scenario / corner selection** — the consumed SDC and library corner are the ones the
   contract requires (not merely *a* passing set). → `^HANDOFF_SCENARIO_OK`.
5. **Sign-off success after repair** — fresh-session PrimeTime reports no negative-slack path on
   the *correctly-selected* design+constraints+corner. → `^SIGNOFF_OK` / `^SIGNOFF_FAIL`.
6. **Symptom-suppression rejection** — detect masking: clock unconstrained / `set_false_path`
   added to hide a real path / SDC loosened to pass the wrong artifact / corner downgraded. A
   green sign-off that was achieved by suppressing the symptom rather than restoring consistency
   scores 0 on the consistency components. → folded into `_SCORE` + `^HANDOFF_MASKING_DETECTED`.
7. **Forbidden-artifact change rejection** — reuse p10/Phase-2 `detect_forbidden_modifications`
   and `detect_hidden_shadows`; editing a forbidden artifact (netlist, lib, report content,
   scripts when not the editable surface) fails anti-cheat regardless of sign-off.

**Pass predicate (intended):** full credit iff *all* applicable consistency markers are OK **and**
`SIGNOFF_OK` **and** no masking / no forbidden change — i.e. the handoff contract is restored, not
just the tool made green. This generalizes p10's `SIGNOFF_OK ∧ CONSTRAINT_SPEC_OK`.

The oracle must **not** be reachable from the public channel (no leak of `handoff_truth.json`,
hashes, or expected names), and must be order/format tolerant (laundered via read/write).

---

## 6. Visible vs hidden artifacts

Applying the Phase-2 and p10 lessons (verdict-first public runner; public runner runs without
hidden files; public scripts reference no hidden-only artifacts; hidden oracle only at grading;
no literal-answer leak):

- **Public editable** (the repair surface — keep it minimal and *cross-artifact*, not a number):
  - Variant A/E: `handoff_manifest.json`
  - Variant B: `handoff_manifest.json` (scenario mapping)
  - Variant C: `constraints.sdc` (clock object) — and manifest read-only so the fix must reconcile
    SDC↔netlist, not edit the manifest
  - Variant D: `handoff_manifest.json` (corner) and/or the corner-asset selection field
  - (The editable set is per-variant and declared in metadata; never include both sides of a
    consistency pair as editable, or the agent could "fix" by corrupting the reference.)
- **Public read-only:** `spec.md`, `design.v`, `netlist_v1.v`, `netlist_v2.v`, `tiny.lib`,
  `tiny.db` (+ corner `.db`s), `reports/golden_timing.rpt`, `run_public.sh`, `run_public.tcl`,
  and whichever of manifest/SDC is *not* the editable surface for that variant.
- **Hidden (grading only):** `run_hidden.sh`, `run_hidden.tcl`, `run_signoff.tcl`,
  `grade_handoff.py`, `handoff_truth.json`.
- **Forbidden:** every visible file except the per-variant editable one; all hidden files; report
  content; netlists; library assets; scripts.
- **Generated reports:** `reports/golden_timing.rpt` is shipped read-only as *evidence with a
  provenance stamp*; the agent may not edit it (only repoint/repair provenance via the manifest).
- **Public runner behavior:** `run_public.{sh,tcl}` loads the manifest-selected artifacts and
  PrimeTime, then prints a **verdict first** — `HANDOFF_PUBLIC: OK|MISMATCH ...` plus a
  short hint (e.g. "manifest netlist hash ≠ on-disk", "create_clock targets missing port",
  "0 paths constrained") within the first ~1000 bytes, ahead of the PT banner/dump — and never
  references any hidden file. The hint states the *symptom*, never the fix.

---

## 7. Scoring contract

Component weights (proposal; final tuned at calibration). Generalizes p10's
`constraint_spec/signoff/explanation`:

- `signoff` (tool_run) — 0.25 — fresh-session PT clean on the correctly-selected package.
- `handoff_consistency` — 0.35 — cross-artifact agreement (iface/clock/scenario/provenance), the
  core skill; strict gate, no partial for "made it green wrongly".
- `manifest_correctness` — 0.25 — the manifest/selected mapping matches the golden contract.
- `explanation` — 0.05 — low-weight auxiliary (root-cause statement).
- `protocol_compliance` — 0.10 — reuse the reliability layer: well-formed FINISH + confidence;
  `nocommit`/format failures are recorded here (carries the p10 reliability lesson forward).

Pass gate: `total ≥ 0.5` should hold **iff** the handoff contract is restored
(`handoff_consistency` full ∧ `signoff` OK ∧ no masking/forbidden) — so masking cannot pass.

**Partial-credit cases (explicit):**
- Final PT green but **wrong manifest still selected** → `signoff` credit only; `handoff_*` = 0 →
  fail. (The headline anti-collapse case: green ≠ correct.)
- **Edited a forbidden artifact** (e.g. the netlist) → anti-cheat zeroes objective regardless.
- **Changed the script to bypass** the failing/selection step → masking detected → fail.
- **Stale report accepted** without fixing root cause (E) → `provenance` = 0 → fail.
- **Correct root cause but incomplete repair** (e.g. fixed manifest netlist pointer but left the
  provenance hash stale, or fixed clock in SDC but missed a `get_clocks` reference) → partial:
  `signoff` may pass, `handoff_consistency` < full → below gate. Rewards diagnosis but requires
  *complete* restoration for full credit.

---

## 8. Generator plan (design only — do NOT implement yet)

Mirror `SyntheticProjectGenerator(BaseGenerator)` conventions (seed, `generate_one`,
`generate_batch(validate=True)`, thin `scripts/generate_*` driver):

- **Seed** controls variant choice, design parameters (depths, period, ports, clock name,
  scenario set, corner set), and which artifact is mutated.
- **Golden package synthesis or frozen assets:** for the first variants, *freeze* the two netlist
  versions and the corner `.db`s as templated assets generated from the closed-form timing model
  (no live DC); a later increment may invoke real `dc_shell` to emit provenance-stamped netlists
  (`flow_synthetic`).
- **Variant selection:** enum {A,B,C,D,E}; each variant has a templated golden + a single,
  well-defined mutant transform on exactly one artifact/mapping.
- **Artifact hash / provenance:** the generator computes content hashes for netlists/reports and
  writes them into both `handoff_manifest.json` (declared) and `handoff_truth.json` (golden),
  so provenance checks are exact and machine-verifiable.
- **Mutant application:** apply the one-artifact drift; assert (closed-form) that the golden flow
  signs off and the mutant either errors or silently mis-signs-off by the intended margin.
- **Acceptance filters** (extend p10's F-series):
  - F1 golden package fully consistent + signs off (closed-form predicted).
  - F2 mutant breaks exactly one cross-artifact relation; golden−mutant objective margin ≥ 0.15.
  - F3 determinism: same seed → byte-identical package.
  - F4 **no-literal-leak**: the correct value/name/hash does not appear as a copyable token in any
    visible file (the p10 leak lesson — extended to hashes, clock names, scenario/corner names).
  - F5 public runner runnable without hidden files; verdict within first 1000 bytes; no hidden
    refs; symptom-only hint (no fix).
  - F6 editable surface never contains both sides of a consistency pair.
  - F7 single-artifact mutation (exactly one file/mapping differs golden↔mutant) for clean
    attribution.
- **Deterministic regeneration & metadata:** emit full `generator.params` (variant, mutated
  artifact, golden/mutant hashes, predicted sign-off, expected mismatch category), `evaluator =
  flow_handoff.FlowHandoffEvaluator`, per-variant editable/forbidden lists.

---

## 9. Tests / validation plan (before any model run)

Tool-free contract tests (mirror `tests/test_synthetic_project_gen.py`) + b04 gate:

- Public runner prints the handoff verdict within the first 1000 bytes (mock-tool test).
- No hidden leaks: public scripts/files never contain `handoff_truth`, `grade_handoff`,
  `run_hidden`, `run_signoff`, expected hashes/names.
- Agent workspace runnable without hidden files (two-phase workspace).
- Golden package validates: closed-form sign-off OK + all consistency markers OK (and, on b04,
  real PT golden = 1.0).
- Mutant fails or exposes mismatch: golden−mutant objective margin ≥ 0.15; mutant either
  `SIGNOFF_FAIL` or `HANDOFF_*` mismatch.
- True fix scores full; symptom-suppression (mask clock / false_path / wrong-SDC-loosened /
  corner-downgrade) scores partial or fail.
- Forbidden-artifact edit → anti-cheat fail; hidden-shadow detection.
- No-literal-answer-leak test (values, names, hashes).
- Deterministic generation (if/when the generator is added): same seed → byte-identical.
- **Agentic and CLI evaluator dispatch parity** for `flow_handoff.FlowHandoffEvaluator` — add the
  branch to *both* `cli.py` and `agentic/runner.py::_select_evaluator` and pin it with a parity
  test. (Direct carry-over of the Phase-0D misdispatch bug: never add an evaluator to one
  dispatch site only.)

---

## 10. GO / NO-GO criteria

**GO** if a hand-built golden package + one-artifact mutant produces a **fair, reproducible,
cross-artifact failure** where:
- the correct repair requires restoring handoff consistency across ≥2 artifacts (diagnosis, not a
  single number/identifier derivable from `spec.md`),
- the golden signs off and the mutant fails or silently mis-signs-off by margin ≥ 0.15,
- the oracle rejects symptom-suppression and forbidden-artifact edits,
- the public symptom states the problem without revealing the fix,
- dispatch parity + no-leak + verdict-first all hold.

**NO-GO** if:
- the fault collapses into another single-line SDC/number edit (then it is just constraint-drift
  in disguise — retire it), **or**
- the public symptom directly reveals the exact fix (then it is a copy task, not diagnosis), **or**
- the only realizable failures are tool/protocol artifacts rather than genuine cross-artifact
  inconsistency (then it adds nothing over p10 as a reliability substrate).

**Phase-0E discipline (unchanged from prior phases):** prove the contract on ONE hand-authored
golden package + ONE mutant on real b04 PrimeTime *before* writing a generator, and run a cheap
falsification probe *before* scaling — exactly the sequence that caught constraint-drift's
saturation cheaply.
