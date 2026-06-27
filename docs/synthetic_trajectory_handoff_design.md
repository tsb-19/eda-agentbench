# Synthetic trajectory / evidence-generation handoff — mechanism design (Phase-3A, design only)

**Status:** design proposal. No code, no tasks, no tool runs, no model runs. Awaiting review.
**Predecessors:** `docs/synthetic_phase0a_design.md` + `docs/synthetic_phase0b_generator_design.md`
(p10 constraint-drift), `docs/synthetic_flowhandoff_drift_design.md` (p11 single-fault FlowHandoff),
`docs/synthetic_multifact_handoff_escalation_design.md` (p12 multi-artifact escalation). This
document defines the **next difficulty lever**: a handoff whose repair cannot be completed by editing
files at all — the agent must *rerun the correct flow and regenerate fresh evidence* whose provenance
matches the repaired package. Proposed track id `p13_trajectory_handoff` (new track; reuses the
p10–p12 scalar-Liberty PrimeTime substrate).

---

## 1. Motivation and prior negative results

Three consecutive mechanisms saturated for protocol-compliant frontier agents:

- **p10 single constraint-drift — saturated.** Qwen3.7-Max and DeepSeek-V4-Pro pass@1 = pass^k = 1.00.
  Read `spec.md`, recompute one budget, edit one value.
- **p11 single-fault FlowHandoff (Variants A, C) — saturated.** Both top models 6/6 by capability
  score; one inconsistency, one-step-diagnosable, one-edit-fixable.
- **p12 two-edit multi-artifact escalation (stale-package triangle) — saturated.** Probe 2026-06-26,
  9 episodes: Qwen 3/3 and DeepSeek 3/3 full coordinated repairs (`flow_config→v2 ∧ SDC→clk_main`,
  plus the optional provenance reconcile). No single-edit partial, no PT-green symptom suppression, no
  forbidden edit. The coupling filter held *technically*, but two coordinated edits are within easy
  reach. MiniMax-M3 again produced only a `nocommit` reliability signature, not capability difficulty.

**The common weakness:** p10/p11/p12 are all **final-state repair** tasks. The grade is a pure
function of the *final bytes* of a small set of files. A strong agent can inspect the package, infer
the intended contract from the authority, and **directly edit the required files** to that contract —
no execution, no evidence, no trajectory required. The hidden oracle then re-derives the verdict by
running the tool itself, so the agent never has to run anything.

**What the next mechanism must verify:** not only *what the final artifacts say*, but *that the agent
actually executed the correct flow on the repaired package and produced fresh evidence whose
provenance is bound to those repaired inputs*. The difficulty moves from "know the answer" to
"perform the procedure and prove you performed it on the right inputs" — a property that cannot be
satisfied by editing a value, because the evidence must be *generated*, and generation is only correct
if the inputs were already correct. This couples a **procedure** to the repair, not just a second edit.

Retention note: p10/p11/p12 stay as clean real-tool **reliability/protocol substrates** (MiniMax
nocommit, run-to-run variance, calibration). p13 is the *difficulty* successor, not a replacement.

---

## 2. Mechanism definition

**Trajectory / evidence-generation handoff repair:** a handoff package is broken such that a valid
submission requires the agent to (a) repair the inconsistent inputs, (b) **rerun a specified public
evidence-generation flow** on the repaired inputs, (c) thereby **produce a fresh evidence artifact**
(`timing_report.rpt` + `evidence_manifest.json`) whose recorded provenance is bound by **content
hashes** to the repaired inputs, and (d) submit the repaired package *plus* the freshly generated
evidence. The grade is a function of the final artifacts **and** of whether the evidence was
demonstrably generated from the repaired package.

The defining property: **the evidence artifact is no longer a file to edit — it is an output to
produce.** Editing it by hand cannot succeed, because its correctness is defined by a relation
(hashes + digest) to the *other* repaired files plus the *actual tool result*, and that relation is
re-checked by the hidden oracle against a fresh hidden re-run. The only way to make the relation hold
is to have actually run the public generator on the correct inputs.

The oracle must distinguish, each to a distinct score outcome (§8, validated in §12):

| trajectory state | what happened | verdict |
|---|---|---|
| **true rerun-generated evidence** | inputs repaired, public generator rerun, evidence binds to repaired inputs | full credit |
| **hand-edited report** | `timing_report.rpt`/`evidence_manifest.json` edited to look right, never regenerated | reject (digest/hash mismatch vs hidden re-run) |
| **stale report reuse** | inputs repaired but old evidence left in place | reject (evidence hashes ≠ repaired-input hashes) |
| **fix-without-rerun** | inputs repaired, evidence never regenerated/absent | below pass (no fresh evidence) |
| **rerun-from-wrong-package** | generator run *before* repair, or on a still-stale input | reject (evidence binds to stale inputs) |
| **PT-green on wrong package** | stale island self-signs-off green, evidence binds to stale inputs | below pass (provenance ≠ authority) |
| **partial consistency** | one input repaired, evidence regenerated on a half-fixed package | below pass (coverage/consistency fail) |

---

## 3. Candidate mini project

Reuse the p12 scalar-Liberty / PrimeTime substrate (BUFX1 0.10, DFFX1 clk→Q 0.08, setup 0.02;
`acc_stage`; golden worst slack 0.13 at period 3.0; the `-nworst 1` binary-coverage quirk). One tiny
package:

```
files/ (agent-visible)
  spec.md                  authority: intent = v2 / clk_main / func / typ
  handoff_manifest.json    authority contract (read-only): netlist=v2, clock=clk_main, ...
  flow_config.json         EDITABLE: which netlist the flow consumes (mutant: v1)
  constraints.sdc          EDITABLE: clock binding (mutant: clk_old)
  netlist_v2.v             current (clk_main, en-qualified)   [read-only]
  netlist_v1.v             stale  (clk_old, no en)            [read-only]
  pt_signoff.tcl           reference doc of the consumed flow [read-only]
  run_evidence.sh          PUBLIC generator: reruns the flow + WRITES fresh evidence  [read-only]
  timing_report.rpt        GENERATED artifact (mutant ships a stale v1/clk_old report)
  evidence_manifest.json   GENERATED artifact (mutant ships a stale-run manifest)
  tiny.lib / tiny.db       library                            [read-only]
  run_public.sh/.tcl       verdict-first public feedback      [read-only]
hidden/
  run_hidden.sh            orchestrator (launder + fresh re-run + grade)
  run_hidden.tcl           launder agent SDC + coverage facts
  run_signoff.tcl          fresh-session sign-off of consumed netlist
  regen_reference.sh/.tcl  hidden RE-RUN of the generator on the SUBMITTED package
  grade_trajectory.py      stdlib grader (hashes, digests, provenance, coverage)
  handoff_truth.json       golden contract + expected hashes
solution/
  flow_config.json, constraints.sdc   golden inputs
  timing_report.rpt, evidence_manifest.json   golden GENERATED evidence (for reference/tests)
```

**The key difference from p12:** `timing_report.rpt` and `evidence_manifest.json` are **products of
`run_evidence.sh`**, not static files to edit. The agent's editable surface is exactly the two
*inputs* (`flow_config.json`, `constraints.sdc`); the evidence is *generated* by running the public
command. (Provenance-as-editable from p12 is dropped — provenance now lives inside generated
evidence, so it cannot be hand-set.)

---

## 4. Golden state

- `handoff_manifest.json` (authority, read-only): netlist=`netlist_v2.v`, clock=`clk_main`,
  scenario=`func`, corner=`typ`, declared v2 provenance hash.
- `flow_config.json`: `netlist = netlist_v2.v` (+ top/constraints/library/scenario/corner).
- `constraints.sdc`: `create_clock -name clk_main ... [get_ports clk_main]`, I/O budget per spec.
- `timing_report.rpt`: produced by `run_evidence.sh` from the v2/clk_main package — worst slack 0.13,
  ≥1 constrained path, stamped with the consumed netlist + clock + corner.
- `evidence_manifest.json` (produced by `run_evidence.sh`): records, for the run that produced the
  report —
  - `input_hashes`: sha256 of `flow_config.json`, `constraints.sdc`, and the **consumed netlist**;
  - `selected_netlist = netlist_v2.v`, `selected_sdc = constraints.sdc`, `selected_clock = clk_main`,
    `scenario = func`, `corner = typ`;
  - `tool = pt_shell`, `tool_exit = 0`, `signoff = OK`, `constrained_paths ≥ 1`;
  - `report_digest`: sha256 of the canonicalized `timing_report.rpt` body;
  - `run_nonce`: a **deterministic** generation stamp derived from the input hashes (see §7) — NOT a
    wall-clock timestamp.
- Sign-off passes; oracle passes (all components OK → 1.0).

## 5. Mutant state

A realistic "the flow signed off last week's netlist and nobody re-ran it" package:

- `flow_config.json` selects the stale `netlist_v1.v`.
- `constraints.sdc` constrains `clk_old`.
- `timing_report.rpt` is the **stale v1/clk_old report** (a clean historical run).
- `evidence_manifest.json` claims an **old run**: input hashes of the *stale* inputs, selected
  netlist v1, clock clk_old, an old `run_nonce` consistent with the stale inputs.
- `handoff_manifest.json` + `spec.md` (authority) expect **v2 / clk_main / func / typ**.

The {flow_config, SDC, report, evidence} island is **locally self-consistent** (the stale evidence
correctly describes the stale inputs!) but **inconsistent with the authority**. This is the trap that
makes hand-editing tempting and rerun-less "fixes" plausible — and it is exactly what the trajectory
oracle is built to reject.

## 6. Required repair trajectory

Minimal valid sequence (the oracle checks the *resulting evidence*, not a command transcript — see the
observability note):

1. repair `flow_config.json` → `netlist = netlist_v2.v`;
2. repair `constraints.sdc` → bind `clk_main`;
3. run the public command `bash run_evidence.sh` (reruns sign-off on the repaired inputs);
4. → fresh `timing_report.rpt` generated from the repaired package;
5. → fresh `evidence_manifest.json` whose `input_hashes` equal the **repaired** files' hashes and
   whose `report_digest` equals the freshly generated report;
6. final sign-off passes (≥1 constrained path, worst slack ≥ 0).

**Observability stance (load-bearing).** The harness cannot reliably observe the agent's *command
history* (the agentic runner records tool calls, but submission-mode grading and the forwarder do
not guarantee an ordered, tamper-proof transcript). Therefore the oracle must **not** require an exact
command sequence. Instead it verifies the **fresh evidence/provenance** the public generator produces:
correct evidence is *only obtainable* by running `run_evidence.sh` on already-repaired inputs, so
"valid evidence exists and binds to the repaired inputs" is a sound proxy for "the agent ran the
correct flow after repairing." Step 3 is thus checked by its *effect* (steps 4–5), re-verified by a
hidden re-run (§8), not by trajectory logging.

Order independence within reason: repairing both inputs then running once is the canonical path;
running, then repairing, then running again is also fine (the *last* evidence is what's graded).
Running before repairing and never re-running is the `rerun-from-wrong-package` reject case.

## 7. Evidence / provenance design

Make regenerated evidence **machine-checkable without leaking the hidden answer**, and
**reproducible without wall-clock**.

`evidence_manifest.json` fields (all produced by the public `run_evidence.sh`):

- `input_hashes`: `{flow_config.json: <sha256>, constraints.sdc: <sha256>, consumed_netlist: <sha256>}`
  — the consumed netlist is whatever `flow_config.json.netlist` names, hashed from disk.
- `selected_netlist`, `selected_sdc`, `selected_clock`, `scenario`, `corner` — parsed from the inputs.
- `tool`: `"pt_shell"`; `tool_exit`: integer; `signoff`: `OK|FAIL`; `constrained_paths`: integer.
- `report_digest`: sha256 of the **canonicalized** report body (strip the provenance header + any
  numeric-format noise; hash the structural timing content) so the digest is stable across benign
  formatting but changes if the design/clock/coverage changes.
- `run_nonce`: **deterministic generation stamp** =
  `sha256(input_hashes ++ selected_clock ++ scenario ++ corner ++ report_digest)[:16]`.
  This ties the evidence to *exactly* this input set and result, with **no wall-clock dependency** —
  re-running on identical repaired inputs yields the identical nonce (reproducible, determinism-safe),
  while any input change flips it. It also defeats stale-evidence reuse: a stale manifest's nonce was
  computed over stale hashes and cannot match the repaired-input recomputation.

No hidden secret (golden hash, expected nonce, expected digest) appears in any visible file. The
golden v2 hash legitimately appears only in the authority `handoff_manifest.json` (it is the contract,
not the answer-to-the-evidence); the *expected evidence relation* is computed, never published.

## 8. Oracle design

Hidden, stdlib, marker-anchored (the p11/p12 pattern, extended with a **hidden re-run**). Phases in
`run_hidden.sh`, all `[apply]`-prefixed laundering kept off the `^`-anchored markers:

- **Phase 0 — select:** parse the **submitted** `flow_config.json` (consumed selection) + the
  read-only authority clock → `selected.tcl` (workspace file; never env — the forwarder boundary).
- **Phase 1 — launder + coverage:** `run_hidden.tcl` applies the submitted SDC via
  `read_sdc`/`write_sdc` → `applied_hidden.sdc`; records trusted PT coverage facts
  (`intended_clock_present`, `constrained_paths` via `-nworst 1`) → `coverage.txt`.
- **Phase 2 — fresh sign-off:** `run_signoff.tcl` signs off the consumed netlist from the laundered
  SDC → `^SIGNOFF_OK/FAIL` (zero constrained paths = FAIL, never a clean empty run).
- **Phase 3 — hidden evidence RE-RUN:** `regen_reference.sh` runs the **same generation logic** the
  public `run_evidence.sh` runs, on the **submitted repaired inputs**, in an evaluator-private scratch
  dir, producing a *reference* report + reference manifest. This is the anti-forgery keystone: the
  oracle does not trust the submitted evidence, it **recomputes** what correct evidence must be.
- **Phase 4 — grade (`grade_trajectory.py`, stdlib, all inputs as data):** emit `^`-anchored markers:

  1. **`FINAL_CONSISTENCY_OK/_SCORE/_DETAIL`** — submitted `flow_config` consumes the authority
     netlist; consumed netlist content hash matches the authority provenance; corner matches.
  2. **`SCENARIO_CLOCK_OK/_SCORE`** — laundered SDC binds the authority clock (`clk_main`, not stale)
     **and** `constrained_paths ≥ min` (coverage).
  3. **`EVIDENCE_OK/_SCORE/_DETAIL`** — the submitted `evidence_manifest.json` **and**
     `timing_report.rpt` exist, are well-formed, and **equal the hidden re-run's reference**:
     submitted `report_digest` == reference digest; submitted `input_hashes` == hashes of the
     *submitted repaired inputs*; submitted `run_nonce` == recomputed nonce; `tool_exit==0`,
     `signoff==OK`, `constrained_paths≥min`. (This single check folds in "fresh", "from the right
     package", and "not hand-edited" — any of them failing breaks the digest/nonce equality.)
  4. **`PROVENANCE_OK/_SCORE`** — `selected_*` in the manifest equal the authority
     (netlist/clock/scenario/corner), i.e. the evidence describes the *intended* run, not a stale one.
  5. **`HANDOFF_MASKING_DETECTED`** — timing weakening/exceptions in the laundered SDC → zeroes the
     consistency + evidence components.
  6. **anti-cheat** — `detect_forbidden_modifications` / `detect_hidden_shadows` over the forbidden
     set (netlists, libs, manifest authority, `run_evidence.sh`, the runners, the oracle).

**Distinguishing the seven trajectory states** (each → a distinct outcome, all tested §12):
true rerun (all OK → full); hand-edited report (EVIDENCE fail: digest/nonce ≠ re-run); stale reuse
(EVIDENCE fail: input_hashes ≠ repaired-input hashes, nonce mismatch); fix-without-rerun (EVIDENCE
fail/absent); rerun-from-wrong-package (EVIDENCE fail: binds to stale inputs + PROVENANCE fail);
PT-green-on-wrong-package (SIGNOFF maybe OK but FINAL_CONSISTENCY + PROVENANCE fail); partial repair
(SIGNOFF/SCENARIO fail — zero constrained paths from the half-fixed clock/port mismatch, exactly as
p12).

## 9. Scoring contract

Components (sum 1.0), per the approved proposal:

| component | weight | meaning |
|---|---|---|
| `signoff` (tool_run) | 0.15 | clean, non-empty sign-off of the consumed design |
| `final_artifact_consistency` | 0.25 | flow_config↔authority↔netlist (+corner) agreement |
| `scenario_clock_consistency` | 0.15 | clock binding + coverage (the p11-C axis) |
| `evidence_generation` | 0.25 | fresh evidence equals the hidden re-run (digest+hashes+nonce) |
| `provenance_consistency` | 0.10 | evidence `selected_*` match the authority |
| `explanation` | 0.10 | root-cause + repair narrative |

**Pass gate:** `total ≥ 0.5` **iff** SIGNOFF_OK ∧ FINAL_CONSISTENCY_OK ∧ EVIDENCE_OK ∧
PROVENANCE_OK ∧ no forbidden edit.

Gate math (the load-bearing inequalities):
- **Final state without fresh evidence** (inputs fixed, evidence stale/absent): signoff 0.15 +
  final 0.25 + scenario 0.15 + explanation 0.10 = **0.65**… which would *pass*. **This is unacceptable
  per the spec** ("final state without fresh evidence must fail below pass"). → **Make EVIDENCE_OK a
  hard precondition for `final_artifact_consistency` and `scenario_clock_consistency` too**, OR raise
  `evidence_generation` so the gate cannot be met without it. **Chosen design:** EVIDENCE_OK is a
  **precondition** gating `final_artifact_consistency`, `scenario_clock_consistency`, and
  `provenance_consistency` (mirroring p12's sign-off precondition). Then "inputs fixed but no fresh
  evidence" scores signoff 0.15 + explanation 0.10 = **0.25 < 0.5** ✓. (Sign-off itself is computed by
  the hidden re-run on the repaired inputs, so it can read OK even without submitted evidence; that is
  why signoff alone must not approach the gate — 0.15 keeps it far below.)
- **Fresh evidence from the wrong package:** EVIDENCE binds to stale inputs → the hidden re-run on
  *those submitted inputs* may even reproduce the submitted evidence, but PROVENANCE fails
  (`selected_*` ≠ authority) and FINAL_CONSISTENCY fails (consumed ≠ authority) → below pass ✓.
- **Hand-edited report:** submitted digest/nonce ≠ hidden re-run → EVIDENCE fail → precondition zeroes
  the consistency axes → ≤ 0.25 ✓.
- **Full repair + rerun:** all OK → 1.0 ✓.

(The EVIDENCE-as-precondition choice is a documented refinement of the bare additive proposal; flagged
for review in §13/closing. It is the cleanest way to honor "final state without fresh evidence must
fail.")

## 10. Public feedback design

All prior harness lessons:

- **Verdict first, within the first ~1000 bytes** of `run_public.sh` stdout (the Phase-0D truncation
  lesson). Form: `TRAJECTORY_PUBLIC: OK|MISMATCH consumed=<net>/<clk> manifest=<net>/<clk>
  constrained_paths=N signoff=<...> evidence=<FRESH|STALE|MISSING>` + one `PUBLIC_HINT:` line.
- **`run_evidence.sh` is the public, agent-runnable generator** (no hidden files); it reruns the flow
  and writes `timing_report.rpt` + `evidence_manifest.json` from the *current* inputs. The agent is
  *expected* to run it; making it public is the whole point (the difficulty is doing the procedure,
  not discovering a secret).
- **`run_public.sh` evidence-staleness check:** recompute the input hashes of the current package and
  compare to those recorded in `evidence_manifest.json`; report `evidence=FRESH|STALE|MISSING` — a
  *symptom*, not the oracle answer (it never reveals expected hashes/nonce/digest).
- **No hidden references / no hidden-oracle markers** (`EVIDENCE_OK`, `PROVENANCE_OK`, etc.) in public
  stdout; **no exact-answer literal leak** — extend the p11/p12 no-leak scan to hashes, nonces,
  digests, clock/corner names.
- **No long report dump before the verdict**; any dump follows the marker lines and is `-nworst 1`.

## 11. Anti-cheat and report-forgery resistance

Forgery is the central threat for an evidence task. Defenses:

- **Hidden re-run is the source of truth.** The oracle recomputes the reference report + manifest from
  the submitted inputs (Phase 3) and compares; the submitted evidence is never trusted on its face.
- **`report_digest` must match the generated report** (recomputed by the oracle from the submitted
  report body) — a hand-typed digest that doesn't match its own report fails immediately.
- **`input_hashes` must equal the submitted repaired inputs' hashes** (recomputed) — a copied stale
  manifest fails.
- **`run_nonce` is a pure function of the inputs+result** (§7) — recomputed by the oracle; cannot be
  guessed or carried over from a stale run.
- **Forbidden edits fail:** `run_evidence.sh` (the generator), netlists, libs, manifest authority, the
  runners, the oracle — all in the forbidden set; editing any → anti-cheat fail regardless of evidence.
- **Stale evidence fails** (hash/nonce mismatch); **missing evidence fails** (EVIDENCE precondition).

**Honest limits (must be stated in the doc, not hidden):**
- *A determined agent could, in principle, reproduce the exact evidence format and recompute the
  hashes/nonce by hand without running the tool* — because the nonce/digest are deterministic
  functions of file contents the agent can read. **File-only oracles cannot fully prevent this.**
  Mitigation: the `report_digest` is over the **actual PrimeTime report body**, which encodes the
  *timing result* (worst slack, constrained-path structure). To hand-forge it, the agent would have to
  *correctly predict PrimeTime's output for the repaired design* — i.e. simulate the tool. For the
  tiny scalar-Liberty design this is *possible* (slack 0.13 is computable), so for this substrate the
  forgery resistance is **"must reproduce the tool's exact report text", not "impossible"**. We accept
  this for the *prototype* because (a) it still defeats the cheap cheats (hand-edit, stale reuse,
  fix-without-rerun, wrong-package), and (b) the realistic agent behavior is to *just run the public
  generator* (it's free and public). The probe will reveal whether agents forge or run.
- **Preferred hardening (for later, not the prototype):** have the hidden oracle compare the submitted
  report to a **fresh hidden re-run** (already in Phase 3) and require **byte/structural equality of
  the report body**, so the agent must produce the tool's *actual* output, not a plausible one. Push
  forgery cost toward "run the tool" by making the report body large/idiosyncratic enough that exact
  hand-reproduction is impractical on a non-trivial design — a reason the *generator* track matters
  more here than for p10–p12.
- Prefer the **public generator script** producing deterministic evidence from real tool outputs over
  any scheme that asks the agent to author evidence by hand.

## 12. Required tests and validation (before any model probe)

Tool-free contract tests (mirror `test_multifact_handoff.py`) + a b04 real-PT gate:

- golden validates (all markers OK; real-PT golden = 1.0).
- mutant fails below pass; golden−mutant objective margin ≥ 0.15.
- **correct repair + rerun → 1.0.**
- **correct repair WITHOUT rerun (stale/absent evidence) → below pass** (the defining test).
- **rerun BEFORE repair (evidence binds to stale inputs) → below pass.**
- **stale report reuse → below pass** (input_hashes/nonce mismatch).
- **hand-edited report (digest/nonce ≠ hidden re-run) → below pass.**
- **wrong-package evidence → below pass** (PROVENANCE + FINAL_CONSISTENCY fail).
- **missing evidence → below pass.**
- **PT-green on wrong package → below pass.**
- partial repair (one input only) → below pass (zero constrained paths).
- forbidden edit (netlist / `run_evidence.sh` / manifest authority) → anti-cheat fail; hidden-shadow.
- masking (weaken SDC) → consistency+evidence credit 0.
- public verdict within first 1000 bytes (mock-PT); no hidden-oracle markers / no hash-nonce-digest
  leak in public stdout; public scripts reference no hidden-only artifacts.
- agent workspace runnable without hidden files; `run_evidence.sh` runnable by the agent.
- **CLI + agentic dispatch parity** for `trajectory_handoff.TrajectoryHandoffEvaluator` (BOTH sites,
  parity test — the Phase-0D lesson).
- **real PrimeTime validation on b04** (golden=1.0, mutant + each cheat-state below pass, full
  repair+rerun=1.0); **determinism** — the deterministic `run_nonce` must be byte-stable across
  repeated golden re-runs (no wall-clock).
- forwarder-boundary check: selection to fresh PT sessions via workspace file, never env.

## 13. GO / NO-GO criteria

**GO** if a hand-authored golden + mutant on real b04 PrimeTime yields a fair, reproducible task where:
- final-state-only repair (no rerun) **fails below pass**;
- a valid pass **requires regenerated evidence** bound to the repaired inputs;
- stale evidence and wrong-package evidence are **rejected**;
- hand-edited evidence is **rejected** (digest/nonce mismatch vs the hidden re-run);
- full repair + rerun **passes (1.0)**;
- the oracle is **unambiguous** (exactly one coherent restored contract + one canonical evidence);
- public feedback is verdict-first, leak-free, and the public generator is agent-runnable.

**NO-GO** if: final file edits alone pass; the report can be **trivially** hand-edited to pass; the
oracle depends on **wall-clock timestamps** (fragile/non-deterministic); **multiple equally valid
repair trajectories** make scoring ambiguous; public files **leak** the hidden hashes/nonce/digest; or
the task **collapses into another two-edit final-state repair** (i.e. the rerun adds no real
requirement because the agent can forge evidence cheaply — the central risk, see §11).

---

## 14. Recommended implementation path

**Hand-author one prototype first. No generator. No model probe until the hand-authored prototype
passes the full validation matrix.** Split, each gated by review:

- **A. design doc commit** (this document) — `docs: design trajectory handoff` (after your review).
- **B. prototype task + evaluator** — one `traj_handoff_0001` + `TrajectoryHandoffEvaluator`, dispatch
  parity in both sites, schema id+track, the public `run_evidence.sh`, the hidden re-run oracle.
- **C. validation matrix** — the §12 tests tool-free + the b04 real-PT gate (golden=1.0, every cheat
  state below pass, full repair+rerun=1.0, determinism on the nonce).
- **D. tiny smoke probe** — only after C is green: same shape as the p12 probe (Qwen / DeepSeek /
  MiniMax, k=3, 9 episodes, cost-capped), to answer the real question: *do top agents run the public
  generator (good — procedure verified), or do they forge the evidence by hand (collapse — §11 risk)?*

The single biggest open risk to settle in B/C before any probe: **forgery cheapness on the tiny
design** (§11). If hand-forged evidence passes the hidden re-run, the mechanism is just p12 again with
extra steps; the hidden-re-run byte/structural-equality hardening (and, later, a larger generated
report) is the lever to keep difficulty real.
