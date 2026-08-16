# Phase-4A — Trajectory / Evidence Workflow Generator Spec

**Status:** design-only. No code, tasks, tools, or models are produced by this document.
**Worktree / branch:** `eda-agentbench-synthetic-phase0a` @ `synthetic-phase0a`, from clean checkpoint `ee60a82`.
**Builds on:** the p10→p13 probe ladder and the p13 evidence/provenance substrate. Both source
documents were part of the research chronology and are not on this branch; see
`docs/REMOVED.md`. The substrate itself is retained at
`tasks/p13_trajectory_handoff/traj_handoff_0001/`, because this generator reads it.
**One-line goal:** specify a generator that emits *mini EDA workflow projects* whose pass requires repairing a
broken handoff **and** executing an ordered, evidence-producing tool workflow whose provenance binds across
stages — so that local single-file repair is provably insufficient.

---

## 1. Motivation

The synthetic line has climbed a four-rung ladder and each rung was solved by the top protocol-compliant agents:

- **p10** (single numeric constraint-drift repair) — saturated for Qwen / DeepSeek.
- **p11** (single-fault FlowHandoff: provenance + clock-binding) — saturated.
- **p12** (multi-artifact, two coordinated edits, final-state) — saturated.
- **p13** (trajectory: repair **+ rerun generator + bind fresh evidence**) — substrate validated on real
  PrimeTime, but **still saturated for Qwen** (3/3, pass^k=1.00); DeepSeek solved whenever the action budget
  wasn't the limiter; MiniMax exposed only reliability/protocol failures (nocommit, wrong-package evidence).

Three conclusions drive this spec:

1. **Adding files/artifacts alone was not enough.** p12's multi-artifact triangle did not move top models. Static
   breadth is cosmetic, not load-bearing.
2. **Final-state repair is too shallow.** When the win condition is "make the files consistent," a capable agent
   diffs the authority against the package and edits — one or two edits, done. No planning load.
3. **p13's evidence/provenance substrate is the right seed.** The one place difficulty *flickered* was when the
   task forced a tool-grounded **trajectory** that produces evidence bound to a hidden fresh re-run. p13 proved the
   mechanism works (wrong-package/stale/hand-edited evidence all fail; forgery NO-GO cleared) but used only a
   **single** rerun step — not enough depth to load planning.

Therefore the generator must produce **longer, deeper, evidence-producing workflows**: multiple *ordered* stages,
evidence from more than one tool step, cross-stage provenance, and a hidden oracle that checks the **chain**, not
just the endpoint. The generator's job is to make *planning and sequencing* load-bearing, so that a capable agent
that does not plan fails for a **capability** reason, not a protocol one — while a generator-side acceptance gate
prevents regression to p10–p13 triviality.

---

## 2. Generator objective

**Target output:** a self-contained benchmark task that *reads like a small project handoff*, not a single-file
edit. Each generated task directory contains:

- a **design source** — frozen RTL or a frozen gate netlist set (`netlist_v1.v`, `netlist_v2.v`, optional `_v3`);
- **constraints** (`constraints.sdc`) and **flow/scenario/corner config** (`flow_config.json`,
  `scenario_config.json`, `corner_config.json`);
- **authority** (`handoff_manifest.json` / `design_intent.md`, read-only) defining the correct package;
- **scripts**: a public ordered runner (`run_workflow.sh` / per-stage `run_evidence.sh`), signoff TCL
  (`pt_signoff.tcl`), shared deterministic evidence generator;
- **stale** and (after repair) **fresh** reports (`timing_report.rpt`, `stage2_summary.rpt`, `stale_report.rpt`);
- an **evidence manifest** (`evidence_manifest.json`) carrying per-stage provenance;
- a **public runner** (verdict-first, no leak) for agent feedback;
- a **hidden oracle** (re-run + hash checks, anti-cheat, chain-order check);
- **`metadata.json`** + **`prompt.md`**;
- **`solution/`** (golden package + golden evidence chain) and an implicit **mutant** starting state.

The generated artifact is still a standard task dir (schema-valid, `scripts/check`-passing), but its *content*
is a multi-stage workflow with a required trajectory.

---

## 3. Workflow DAG model

A generated task is a **DAG of stages**, not a flat edit target. The canonical chain (PT-only first generator):

| Stage | Name | Inputs | Outputs | Editable/RO/Hidden | Expected command | Provenance fields | Failure mode it gates |
|---|---|---|---|---|---|---|---|
| S0 | authority / design intent | — | `handoff_manifest.json` | **read-only** | — | authority: netlist=v2, clk=clk_main, scenario=func, corner=typ | wrong target package |
| S1 | select netlist / scenario / corner | S0, configs | `flow_config.json`, `scenario_config.json`, `corner_config.json` | **editable** | — | selected_netlist/scenario/corner | consumes stale island |
| S2 | repair constraints / flow | S1 | `constraints.sdc` | **editable** | — | selected_clock | wrong/loosened clock binding |
| S3 | run public signoff / stage-1 evidence | S1,S2 | (PT session) | RO script, hidden re-run | `bash run_evidence.sh` (or `run_workflow.sh stage1`) | tool_exit, signoff, constrained_paths | no rerun / rerun-before-repair |
| S4 | produce `timing_report.rpt` | S3 | `timing_report.rpt` | **generated** (not hand-edited) | (emitted by S3) | report_digest (binds real PT body) | hand-edited report |
| S5 | produce stage-2 summary evidence | S4 | `stage2_summary.rpt` + `evidence_manifest.json` | **generated** | `bash run_evidence.sh stage2` | upstream_evidence_digest = digest(S4) | partial chain / wrong order |
| S6 | hidden oracle re-run / verify | S1–S5 submitted | reference evidence + markers | **hidden** | trusted re-gen on submitted inputs | all of the above, recomputed | forged / stale / wrong-package |
| S7 | final scoring | S6 markers | score JSON | **hidden** | evaluator | — | gate composition |

**Key DAG property (the depth that p13 lacked):** S5 consumes **S4's output digest** as an input
(`upstream_evidence_digest`). The agent cannot produce a valid `evidence_manifest.json` (S5) unless S4's
`timing_report.rpt` was itself freshly regenerated from the *repaired* S1/S2 inputs. This creates a **dependency
edge** (S2→S3→S4→S5) that a single rerun cannot satisfy out of order. Wrong order (run S5 before fixing S2, or
reuse an old S4) breaks the chain digest → no `EVIDENCE_OK`.

The DAG is intentionally small (≤3 evidence stages) but **ordered and digest-coupled**, so correctness depends on
*sequence*, not just *final file contents*.

---

## 4. Artifact schema

Artifact types the generator may emit, with **authority (stable)** vs **mutable** designation:

| Artifact | Role | Authority (stable) fields | Mutable-by-generator (drift target) |
|---|---|---|---|
| `design_intent.md` / `spec.md` | human-readable intent | the prose intent | — (never mutated; it is ground truth narrative) |
| `handoff_manifest.json` | **authority** | netlist, clock, scenario, corner, netlist sha | — (read-only authority; mutating it would move the target) |
| `flow_config.json` | flow selection | — | `netlist`, `constraints`, `scenario`, `corner` (the stale-island drift) |
| `constraints.sdc` | timing constraints | port/period structure | clock name (`clk_old` vs `clk_main`), exceptions |
| `scenario_config.json` | scenario binding | scenario id space | selected scenario (func/test) |
| `corner_config.json` | corner binding | corner id space, lib map | selected corner (typ/slow) |
| `netlist_v1.v` / `_v2.v` / `_v3.v` | frozen design | gate structure, port sets, sha | — (frozen; never edited; selection drifts, not content) |
| `pt_signoff.tcl` | signoff script | the signoff body | — (forbidden edit) |
| `run_workflow.sh` / `run_evidence.sh` | public ordered runner / generator | — | — (forbidden edit) |
| `timing_report.rpt` | **generated** stage-1 evidence | — | produced by tool; **never hand-written** |
| `stage2_summary.rpt` | **generated** stage-2 evidence | — | produced by tool; **never hand-written** |
| `evidence_manifest.json` | provenance | schema | produced by generator; **never hand-written** |
| `stale_report.rpt` | distractor | — | a plausible old report for the stale island (decoy) |
| `tiny.lib` / `tiny.db` / `slow.db` | library assets | cell models | — (frozen) |
| `metadata.json` | task metadata | schema | weights, editable/forbidden lists, budgets |
| `prompt.md` | task prompt | — | the workflow narrative |
| `handoff_truth.json` (hidden) | hidden truth | authority truth + per-stage expected digests | — |
| hidden grader scripts | oracle | — | — |

**Rule:** the agent edits only **selection/config** artifacts (`flow_config.json`, `constraints.sdc`,
`scenario_config.json`, `corner_config.json`); it **runs** scripts to *produce* evidence artifacts; it **never**
hand-writes reports or manifests, and never edits frozen design/library/authority/scripts. Editability is the
contract that forces the trajectory.

---

## 5. Failure-mechanism families

Each family ships with: golden state, mutant state, required coordinated repair, invalid shortcuts, public
symptom, hidden checks, and why it is harder than p10–p13.

### A. Stale-package triangle
- **Golden:** `flow_config.netlist=v2`, SDC binds `clk_main`, fresh report on v2.
- **Mutant:** script consumes stale `netlist_v1`, SDC constrains `clk_old`, a `stale_report.rpt` *agrees* with the
  old package (internally consistent decoy).
- **Required repair:** `flow_config→v2` **and** `constraints.sdc→clk_main`, then rerun evidence.
- **Invalid shortcuts:** fix only one of the two; reuse the agreeing stale report.
- **Public symptom:** `consumed=v1/clk_old … evidence=STALE`.
- **Hidden checks:** consumed==authority; fresh report digest matches re-run; no stale-clock.
- **Harder than p10–p13:** the stale report is *self-consistent*, so a final-state diff alone looks plausible; only
  a fresh rerun bound to the repaired package distinguishes it. (p12 had this but no rerun requirement.)

### B. Wrong evidence trajectory
- **Golden:** evidence regenerated *after* both repairs.
- **Mutant:** final files already look fixed, but evidence is stale **or** was generated before repair.
- **Required repair:** regenerate evidence after the repair (S3→S4→S5 in order).
- **Invalid shortcuts:** leave the stale evidence; rerun once but before fixing S2.
- **Public symptom:** `evidence=STALE` despite `consumed=OK`.
- **Hidden checks:** `report_digest`/`run_nonce`/`input_hashes` equal the fresh re-run on submitted inputs.
- **Harder:** this is p13's core, retained as a *baseline* family; the generator layers the chain (family E) on top.

### C. Wrong scenario / corner chain
- **Golden:** manifest says `func/slow`; configs select `func/slow`; report provenance claims `func/slow`.
- **Mutant:** manifest says `func/slow`, but `scenario_config`/`corner_config` load `test/typ`, and the report
  provenance *claims* `func/slow` (provenance lie).
- **Required repair:** fix scenario **and** corner selection to the authority, then rerun so provenance is honest.
- **Invalid shortcuts:** fix scenario but not corner (or vice-versa); edit the report's claimed corner by hand.
- **Public symptom:** `scenario/corner mismatch` or `evidence=STALE`.
- **Hidden checks:** `selected_scenario==authority`, `selected_corner==authority`, AND the re-run with that
  corner's library reproduces the report digest.
- **Harder:** introduces a **second coupled axis** (scenario×corner) plus a provenance-lie that hand-edits can't
  fix, because the digest must match a re-run under the *correct corner's* `.db`.

### D. Report-provenance drift
- **Golden:** report belongs to the current (netlist, SDC) pair; manifest agrees.
- **Mutant:** report is from an *old* (netlist, SDC) pair; `evidence_manifest` claims the *current* package
  (manifest/report disagree).
- **Required repair:** regenerate so report and manifest describe the same, authority-correct pair.
- **Invalid shortcuts:** hand-edit the manifest to claim the current package over an old report.
- **Public symptom:** `manifest≠report provenance`.
- **Hidden checks:** `submitted_report_matches_its_manifest` (digest) **and** both equal the fresh re-run.
- **Harder:** isolates the manifest↔report binding; tests that the oracle catches a *claim* that doesn't match the
  *content* — a pure-forgery vector p13 already resists; here it's a first-class family with a decoy.

### E. Multi-stage rerun dependency (the new depth)
- **Golden:** S4 `timing_report.rpt` regenerated from repaired inputs; S5 `stage2_summary.rpt` +
  `evidence_manifest.json` regenerated *from S4's fresh digest* (`upstream_evidence_digest`).
- **Mutant:** both stage reports stale; S5 summary references an old S4 digest.
- **Required repair:** repair inputs → regenerate S4 → **then** regenerate S5 (ordered); S5's
  `upstream_evidence_digest` must equal the fresh S4 digest.
- **Invalid shortcuts:** regenerate only S4 (missing S5); regenerate S5 against a stale S4; run S5 first.
- **Public symptom:** `stage2 evidence missing` or `upstream digest mismatch`.
- **Hidden checks:** `REQUIRED_STAGE_CHAIN_OK` = S4 fresh ∧ S5 fresh ∧ `S5.upstream_evidence_digest == digest(S4_fresh)`.
- **Harder than all of p10–p13:** correctness now depends on **stage order and cross-stage digest coupling**. No
  single edit, no single rerun, and no final-state snapshot satisfies it — the agent must *plan a sequence*. This
  is the family that justifies the generator.

---

## 6. Parameterization

Generator parameters (seedable, deterministic):

| Param | Range | Effect |
|---|---|---|
| `stages` | 2–4 | DAG depth (S3..S5 count) |
| `inconsistent_artifacts` | 1–4 | how many config/constraint files drift |
| `required_edits` | 1–4 | coordinated edits needed |
| `evidence_steps` | 1–3 | number of ordered evidence-generation reruns |
| `stale_distractor_reports` | 0–2 | decoy `stale_report.rpt` count |
| `stale_islands` | 1–2 | number of self-consistent stale packages |
| `scenario_choices` | {func,test} | scenario axis |
| `corner_choices` | {typ,slow} | corner axis (needs the corner's `.db`) |
| `scenario_corner_coupling` | on/off | whether C-family coupling is active |
| `provenance_coupling` | on/off | whether D-family report↔manifest binding is active |
| `clock_names` | {clk_main, clk_old, …} | clock-binding drift |
| `netlist_versions` | {v1,v2,(v3)} | which islands exist |
| `report_provenance_hashes` | derived | per-package expected digests |
| `action_budget_target` | derived from depth | recommended `max_tool_calls` |
| `runtime_budget_sec` | derived | per-episode wall budget |
| `seed` | int | full determinism |

**Calibration vs difficulty:** a *shallow* sample (`stages=2, required_edits=2, evidence_steps=1, coupling off`)
reproduces p13 for calibration/fairness; a *deep* sample (`stages=4, required_edits=3, evidence_steps=2–3,
coupling on, distractors=2`) targets capability difficulty. Same generator, different knobs.

---

## 7. Provenance and evidence model

Deterministic, no wall-clock. Each `evidence_manifest.json` records **per stage**:

```
{
  "stage": "stage1" | "stage2",
  "selected_netlist": "...", "selected_sdc": "...", "selected_clock": "...",
  "selected_scenario": "...", "selected_corner": "...",
  "input_hashes": { "flow_config.json": "...", "constraints.sdc": "...",
                    "scenario_config.json": "...", "corner_config.json": "...",
                    "consumed_netlist": "..." },
  "tool": "pt_shell", "tool_exit": 0,
  "constrained_paths": <int>, "signoff": "OK"|"FAIL",
  "report_digest": "<sha256 of canonical real-PT report body>",
  "upstream_evidence_digest": "<digest of the previous stage's report, or null for stage1>",
  "run_nonce": "<sha256(input_hashes ++ clock ++ scenario ++ corner ++ report_digest ++ upstream_evidence_digest)[:16]>"
}
```

- **`report_digest`** binds to the *actual* `report_timing` path-table body (canonicalized: volatile banner/blank
  lines stripped), so a hand-written report cannot reproduce it.
- **`upstream_evidence_digest`** is the cross-stage coupling: stage2's nonce folds in stage1's digest, so the chain
  cannot be assembled out of order or from stale parts.
- **`run_nonce`** is fully deterministic (the p13 formula, extended with `upstream_evidence_digest`).

The hidden oracle **re-runs the trusted generator on the submitted inputs** and rejects: hand-edited reports
(digest≠re-run), stale reuse (input_hashes/nonce≠re-run), wrong-package evidence (`selected_*`≠authority),
evidence-before-repair (input_hashes reflect stale inputs), missing evidence (absent files), **partial chain**
(stage2 missing or `upstream_evidence_digest`≠fresh stage1), and any forgery that does not match the fresh hidden
reference.

---

## 8. Hidden-oracle architecture

Layered, with each layer's nature (deterministic file/hash vs real-tool) marked:

| Layer | Check | Nature |
|---|---|---|
| L0 structural | schema valid, required files present, golden present | deterministic |
| L1 anti-cheat | no forbidden edits; no hidden-artifact shadow; no `set_false_path`/loosened-period masking | deterministic (diff/parse) |
| L2 public/hidden split | no hidden ref or answer literal in visible files; verdict-first | deterministic |
| L3 final-state | consumed package == authority (netlist/clock/scenario/corner), provenance integrity on disk | deterministic |
| L4 signoff / tool | fresh PT signoff of the consumed netlist from laundered SDC → `SIGNOFF_OK` | **real PT re-run** |
| L5 evidence freshness | submitted stageN report/manifest == hidden fresh re-run (digest, input_hashes, nonce) | **real PT re-run** + hash |
| L6 provenance consistency | manifest↔report binding; `selected_*`==authority; corner lib matches | deterministic (hash) on top of L5 |
| L7 workflow-order / dependency | `REQUIRED_STAGE_CHAIN_OK`: each stage fresh ∧ `upstream_evidence_digest` chains correctly | deterministic (hash) on top of L5 |
| L8 explanation / protocol | brief root-cause; confidence parse; protocol_status | deterministic (parse) |

**`EVIDENCE_OK` remains the hard precondition** (the p13 keystone): emitted only when L5 passes for *all required
stages* **and** the evidence describes the authority-correct package. L6/L7 are gated behind `EVIDENCE_OK`. The
real-tool layers (L4/L5) are the forgery-resistance core; everything else is deterministic and cheap.

---

## 9. Scoring contract

Generic, gate-composed. **Hard gates (all required to pass):**

```
PASS  ⟺  NO_FORBIDDEN_EDIT
       ∧ SIGNOFF_OK
       ∧ FINAL_STATE_OK
       ∧ EVIDENCE_OK              (all required stages fresh & authority-correct)
       ∧ PROVENANCE_OK
       ∧ REQUIRED_STAGE_CHAIN_OK  (when evidence_steps ≥ 2)
```

Explicit non-passes (by construction):
- **final state alone** must not pass (no fresh evidence → ¬EVIDENCE_OK);
- **PT green alone** must not pass (signoff on stale island → ¬FINAL_STATE_OK / ¬EVIDENCE_OK);
- **fresh evidence from wrong package** must not pass (`selected_*`≠authority → ¬EVIDENCE_OK);
- **partial evidence chain** must not pass (missing stage2 / bad upstream digest → ¬REQUIRED_STAGE_CHAIN_OK).

**Partial scores (diagnostic, below the 0.5 pass gate):**

| State | Components credited | Indicative total |
|---|---|---|
| correct diagnosis, incomplete repair (signoff fail) | explanation only | ~0.10 |
| final files fixed, no evidence rerun | signoff + explanation | ~0.25 |
| evidence rerun but wrong package | signoff + explanation | ~0.25 |
| one required stage missing (chain broken) | signoff + (stage1 evidence partial?) + explanation | ~0.25–0.35 |
| protocol / nocommit failure | whatever completed + explanation | ≤0.25 |

Weights (starting proposal, mirrors p13 with a chain axis added):
`signoff 0.15 / final_state 0.20 / evidence_generation 0.25 / stage_chain 0.15 / provenance 0.15 / explanation 0.10`.
(Because the harness pass is a fixed additive `total ≥ 0.5`, `EVIDENCE_OK` must encode authority-correctness — the
documented p13 deviation — so wrong-package cannot reach 0.5 via free axes.)

---

## 10. Acceptance filters

Before a generated task is accepted into the dataset, the generator **must** verify (on real b04 PT for the
tool-gated checks):

1. golden package scores **1.0**;
2. mutant scores **below the pass gate**;
3. full coordinated repair (+ ordered reruns) scores **1.0**;
4. **every single-edit repair fails** below pass (one-edit-fails matrix over all `required_edits`);
5. final-state-only repair (no evidence rerun) **fails**;
6. wrong-package evidence **fails**;
7. stale-evidence reuse **fails**;
8. hand-edited report **and** hand-edited manifest **fail**;
9. **partial chain** (stage2 missing / wrong upstream digest) **fails** (when `evidence_steps ≥ 2`);
10. public runner verdict appears **within the first 1000 bytes**;
11. **no hidden artifact leaks** into public files;
12. **no exact answer literal** leak (authority values not echoed as a fix recipe);
13. **CLI ⇄ agentic evaluator dispatch parity**;
14. **deterministic regeneration** (nonce/digest bit-identical across ≥3 regenerations);
15. tool runtime within the per-sample budget.

**This section is the anti-collapse gate.** A sample that any capable single-edit / final-state / single-rerun
strategy can pass is **rejected** by filters 4/5/9 — that is precisely what prevents the generator from emitting
p10/p11/p12/p13-trivial tasks. Filters are mandatory, not advisory.

---

## 11. Difficulty controls

Explicit knobs and how to calibrate them *without* introducing ambiguity:

| Knob | Shallow → Deep | Calibration guardrail |
|---|---|---|
| `required_edits` | 2 → 3 → 4 | every edit must be *uniquely determined* by the authority (no two valid fixes) |
| `evidence_steps` | 1 → 2 → 3 | each added stage must have a real upstream-digest dependency, not a cosmetic rerun |
| `distractor_reports` | 0 → 2 | distractors must be *self-consistent but wrong-package* (never a second valid answer) |
| `stale_islands` | 1 → 2 | each island fully self-consistent; authority picks exactly one |
| `scenario_corner_coupling` | off → on | the correct (scenario,corner) pair must be authority-unique |
| `provenance_coupling` | off → on | report↔manifest binding deterministic and singular |
| `manifest/script mismatch depth` | 1 → N | mismatches must all point to the *same* authority package |
| `action_budget_target` | generous | set from measured golden trajectory length × safety factor (avoid the p13 budget artifact) |
| `public_hint_strength` | strong → weak | weaker hints raise planning load but must never make the target *ambiguous* |
| `required_tool_reruns` | 1 → 3 | each rerun must be *necessary* (removing it must break an acceptance filter) |

**Fairness rule:** difficulty comes from **depth and sequencing**, never from ambiguity. A task with two equally
valid repairs is a NO-GO (§17). Action budget is **calibrated to measured task depth and reported**, so capability
is never confounded by the cap.

---

## 12. Reliability / protocol metrics

Generated tasks are evaluated with the existing reliability layer plus workflow-specific failure tags:

- **Capability/reliability:** pass@1, pass@k, pass^k, flip-rate, trust score, overconfident-wrong, abstention.
- **Protocol:** nocommit, budget_exhausted, empty_response, parse_fail, format compliance.
- **Workflow failure taxonomy (new, per episode):** wrong-package evidence, stale-evidence reuse,
  final-state-only-no-rerun, partial-chain (stageN missing / upstream-digest mismatch), wrong-order,
  forbidden-edit, masking.
- **Cost:** tokens, tool-calls, wall-time, est cost.

The generator is explicitly intended to produce **both**: (a) *reliability/protocol substrate* tasks (shallow, for
calibrating format/nocommit/overconfidence) and (b) *candidate capability-difficulty* tasks (deep, chain-coupled).
Which one a sample is depends on the difficulty knobs (§11) — and is recorded in `metadata.json`.

---

## 13. Generator pipeline

Pseudocode-level (no implementation here):

```
generate_workflow_task(seed, params):
    rng = seeded(seed)
    # 1. sample structure
    cfg = sample_difficulty(rng, params)        # stages, edits, evidence_steps, coupling, distractors
    # 2. build golden package
    golden = build_golden(cfg)                   # authority manifest + v2 selection + clk_main + scenario/corner
    # 3. generate golden evidence chain (real tool or frozen, see §15)
    golden_ev = run_evidence_chain(golden, stages=cfg.stages)   # S3..S5, deterministic nonces/digests
    assert deterministic(golden_ev, repeats=3)
    # 4. create mutant by applying COUPLED drifts
    mutant = apply_coupled_drift(golden, cfg)    # stale island(s), clock, scenario/corner, stale reports, distractors
    # 5. public + hidden validation
    assert structural_valid(task_dir)
    assert no_leak(public_files) and verdict_first(run_workflow.sh)
    # 6. full-repair oracle  -> must be 1.0
    assert oracle(full_repair(mutant)) == 1.0
    # 7. single-edit-fails matrix -> all < pass
    for e in each_single_edit(cfg): assert oracle(apply(mutant, e)) < PASS
    # 8. evidence-forgery + chain matrix -> all < pass
    for s in {stale_reuse, hand_report, hand_manifest, wrong_pkg, no_rerun, partial_chain, wrong_order}:
        assert oracle(s) < PASS
    # 9. deterministic regeneration check
    assert oracle(golden) == oracle(golden)      # bit-identical evidence
    # 10. emit task directory (files/, hidden/, solution/, metadata.json, prompt.md)
    write_task_dir(...)
    # 11. update inventory + report metadata
    update_inventory(track, task_id, cfg)
    return task_dir
```

Steps 6–9 are the **acceptance filters (§10)** executed inline; a sample failing any is **discarded** (logged,
not emitted) — runaway generation is bounded by a per-batch attempt cap.

---

## 14. Directory layout

Proposed layout, with the **as-built** paths beside each entry — three of
the names below were renamed during implementation, and this document is preserved as written
rather than retro-edited:

```
generators/p14_workflow_project_gen.py        # AS BUILT: generators/p14_workflow_handoff_gen.py
scripts/generate_workflow_tasks.py            # AS BUILT: scripts/generate_workflow_handoff_tasks.py
eda_agentbench/evaluator/workflow_handoff.py  # as built
tasks/p14_workflow_handoff/workflow_handoff_0001/   # as built (0001-0027)
tests/test_workflow_generator.py              # AS BUILT: tests/test_workflow_handoff_gen.py
docs/synthetic_workflow_generator_spec.md     # this document
```

**Recommendation: new `p14_workflow_handoff` track, not an extension of p13.** Rationale:
- p13 (`p13_trajectory_handoff`) is **accepted, committed (`aa6d64a`), tagged, and bundled** as a stable
  single-rerun substrate; mutating its schema/evaluator would disturb a frozen checkpoint and its retained
  reliability value.
- The chain-coupling (S5 `upstream_evidence_digest`, `REQUIRED_STAGE_CHAIN_OK`) is a **genuinely new mechanism**
  with a new scoring axis — a clean track boundary keeps p13 as the calibration baseline and p14 as the
  capability-difficulty candidate.
- Dispatch parity and tests are per-track anyway; a new track is the low-risk path.

p13 can later be re-expressed as the `evidence_steps=1` shallow preset of the same generator, but the **track id
stays p14** for generated multi-stage tasks.

---

## 15. Cost / runtime plan

- **Tool runs per generated sample (validation):** golden (1 chain) + full-repair (1) + single-edit matrix
  (`required_edits` runs) + forgery/chain matrix (~6–8 runs) + determinism (≥3) ≈ **12–16 PT re-runs/sample**.
- **b04 runtime:** each PT signoff/report on the tiny `acc_stage` substrate ≈ a few seconds via the forwarder;
  ~1–2 min wall per sample validation (forwarder-bound, not compute-bound).
- **Model probe cost:** at p13 rates (~¥0.5/episode), a 9-episode smoke ≈ ¥4–5; budget per probe ≤¥20.
- **Runaway caps:** per-batch attempt cap (discarded samples counted); hard ceiling on samples/run; a generated
  sample that fails acceptance ≥N times for a seed is skipped, not retried indefinitely.
- **Caching:** golden evidence is deterministic → **hash-cache** generated reports keyed by (inputs, stage); the
  validation matrix reuses the cached reference instead of re-running PT where a hash check suffices.
- **Frozen vs real-tool:** **frozen** the design/library assets (netlists, `.lib`/`.db`) and the *golden report
  bodies* used as references; use **real PT** only where forgery-resistance requires it (the hidden re-run in L4/L5
  during validation and grading). First generator stays **PT-only** (no DC) to bound cost and reuse the validated
  p13 substrate.

---

## 16. First implementation milestone (after spec approval)

Deliberately tiny; does **not** jump to a full generator:

1. **Parameterize `traj_handoff_0001` into a template** — extract the p13 task into a generator function with the
   `evidence_steps=1` shallow preset; prove it reproduces the committed p13 task byte-for-byte (or scores
   identically) as a self-test.
2. **Generate 2 workflow tasks** with **different evidence-chain structures**: one `evidence_steps=2` (family E,
   S4→S5 digest coupling) and one with `scenario_corner_coupling=on` (family C).
3. **Run the acceptance-filter matrix (§10) on b04** for both — golden=1.0, mutant<pass, single-edit-fails,
   forgery/chain-fails, determinism, verdict-first, no-leak, dispatch parity.
4. **Do not run a model probe** until the generator *contract* (acceptance filters all green on the 2 generated
   tasks) is proven. Capability measurement comes only after the substrate is provably fair and non-trivial.

Gate to proceed past milestone: both generated tasks pass all acceptance filters on real PT; `scripts/check` green;
tests green.

---

## 17. GO / NO-GO criteria

**GO** if the spec defines a generator that can produce tasks where, *verifiably via acceptance filters*:
- local single edits fail;
- final-state-only repair fails;
- an **evidence chain** is required (≥2 coupled stages for deep samples);
- wrong-package evidence fails;
- the hidden oracle is **deterministic and fair** (recomputes/re-runs; no ambiguity);
- generated tasks are **reproducible** (bit-identical evidence);
- **action budget is calibrated** to measured depth (no budget-as-difficulty confound).

**NO-GO** if the generator merely emits:
- p10-style numeric edits;
- p11-style single-artifact inconsistencies;
- p12-style two-edit final-state repairs;
- p13-style one-shot rerun tasks *without* a deeper evidence chain;
- **ambiguous** tasks with multiple equally valid repairs;
- tasks **too expensive** to validate.

The §10 acceptance filters are the operational GO/NO-GO test executed per sample.

---

## 18. Open questions

1. **Extend p13 or new p14?** Recommendation: **new p14** (§14). Confirm before implementation.
2. **How many evidence stages are enough?** Hypothesis: **2 coupled stages** is the minimum that loads planning;
   3 may be over-constraining/brittle. Needs a depth-vs-discrimination probe (after the contract is proven).
3. **How much command-history/trajectory can be observed reliably?** The harness logs `actions` (tool calls). Is
   that sufficient to assert *order*, or must order be inferred purely from evidence digests? (Leaning:
   **digest-only**, so the oracle never depends on log scraping.)
4. **Preventing deterministic forgery on tiny designs.** A 13-buffer path is simple; a sufficiently clever agent
   might reconstruct the report body. Mitigations: bind to more of the real PT output, add benign per-seed
   structural variation to the design, or keep the hidden re-run authoritative. Needs explicit study.
5. **Action-budget fairness vs difficulty.** Where to set `max_tool_calls` so depth loads planning without
   `budget_exhausted` masquerading as failure (the DeepSeek p13 lesson). Calibrate from measured golden length.
6. **Real-tool vs frozen split.** Confirm the §15 split (frozen assets + golden bodies; real PT only in the hidden
   re-run) is forgery-safe at depth 2–3.
7. **DC in the loop?** Whether to introduce Design Compiler as a second tool stage before generatorization, or keep
   **PT-only** for the first generator. Recommendation: **PT-only first** (reuse validated substrate; defer DC).

---

*Prepared at the Phase-4A boundary. Implementation is deferred until this spec is reviewed and approved.*
