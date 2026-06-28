# Phase-4C — Workflow Hazard & Recovery Generator (p14 v2)

**Status:** design-only. No code, tasks, tools, or models are produced by this document.
**Worktree / branch:** `eda-agentbench-synthetic-phase0a` @ `synthetic-phase0a`, from clean `15c326e`.
**Builds on:** `docs/synthetic_workflow_generator_spec.md` (p14 v1) and
`docs/synthetic_negative_results_summary.md` (the p10→p14 ladder).
**One-line goal:** shift the difficulty source from *"run the ordered evidence stages"* to *"diagnose
which workflow evidence is stale/drifted/misleading, decide which source is authoritative, choose the
correct recovery path, then repair and regenerate the chain"* — so that a capable agent that merely
follows the obvious steps fails, and only correct **hazard diagnosis + recovery** passes.

---

## 1. Motivation

The synthetic ladder has validated mechanisms but not produced top-model capability difficulty:

- **p10** constraint-drift — saturated (Qwen/DeepSeek).
- **p11** single-fault FlowHandoff (provenance + clock-binding) — saturated.
- **p12** multi-artifact, two coordinated edits — saturated.
- **p13** trajectory/evidence handoff — saturated for Qwen, **but validated the forgery-resistant
  evidence/provenance oracle** (deterministic `run_nonce`, digest binds real PT output).
- **p14 v1** workflow generator — validated `evidence_steps=1` and `evidence_steps=2` with real
  cross-stage `upstream_evidence_digest` coupling; the oracle correctly rejects stage1-only, stale
  stage1, stage2-from-stale-stage1, wrong-order, wrong-package. **Yet Qwen and DeepSeek both reach
  pass^k=1.00 on the depth-2 chain**, performing the ordered stage1→stage2 flow every trial.

**Conclusion:** the difficulty lever is **not** `evidence_steps=3`. Adding one more *ordered* stage
just adds steps a capable planner already executes. The next lever is **hazard diagnosis and recovery**:
make the public evidence *partially inconsistent*, force the agent to reason about *which source to
trust*, and require it to *choose and execute a recovery path* — a reasoning load, not a sequencing
load. p14 v1 gives us the substrate (chain + oracle + PT binding); p14 v2 adds the *epistemic* layer.

---

## 2. Definition of "workflow hazard recovery"

A **recoverable workflow hazard** in this EDA handoff setting is a structured inconsistency or
recoverable failure that:

- **is observable** through public artifacts or tool outputs (the agent can detect it by cross-checking
  spec/manifest/config/report/evidence, or by running `run_public.sh`);
- **has at least one valid recovery path** that restores an authority-consistent, freshly-evidenced
  package;
- **is not solved by one local edit** — recovery requires deciding *which* artifact is wrong and
  regenerating downstream evidence, not patching a single value;
- **requires choosing the authoritative source** among conflicting ones (the agent must apply the
  authority hierarchy, §4, not just match two files);
- **is checkable by a deterministic hidden oracle** (the fresh hidden re-run + hash/digest comparison
  decides correctness with no wall-clock or fragile tool nondeterminism).

A hazard is **not** valid for this generator if it can be repaired by blindly copying one value, if the
public output names the fix, or if more than one authority-consistent recovery exists (that would be
ambiguous — a NO-GO, §14).

---

## 3. Hazard taxonomy (≥5 families)

Each family below specifies golden, mutant, public symptom, valid recovery, invalid shortcuts, hidden
checks. All reuse the p13/p14 `acc_stage` substrate (v2/clk_main/func/typ authority).

### A. Specification drift
- **Golden:** spec/manifest = v2/clk_main/func/typ; configs + evidence all agree.
- **Mutant:** `handoff_manifest.json` (authority) says func/typ, but `scenario_config.json` /
  `corner_config.json` (lower authority) follow an *older* spec (e.g. `test`/`slow`), and the shipped
  report claims the old scenario.
- **Public symptom:** `scenario/corner mismatch: manifest=func/typ config=test/slow`.
- **Valid recovery:** repair the **lower-authority** configs to match the manifest, then regenerate the
  evidence chain so provenance is honest.
- **Invalid shortcuts:** edit the manifest down to the configs (wrong-authority repair); hand-edit the
  report's claimed scenario.
- **Hidden checks:** `selected_scenario/corner == manifest`; fresh re-run reproduces the report digest
  under the *manifest's* corner library.

### B. Invocation error
- **Golden:** the public stage runner invokes the tool with the authority scenario/config.
- **Mutant:** `flow_config.json` carries a **wrong scenario/config argument** (e.g. `scenario:"test"`)
  that the stage runner faithfully passes to PT, so the tool runs the *wrong* analysis; the netlist
  selection itself may be correct.
- **Public symptom:** `signoff ran but consumed scenario != authority` / `evidence=STALE`.
- **Valid recovery:** repair the `flow_config.json` invocation argument, rerun the chain.
- **Invalid shortcuts:** edit the report; leave the wrong-argument evidence; rerun before fixing the
  argument.
- **Hidden checks:** `selected_*` in fresh evidence == authority; the laundered invocation constrains
  paths under the right scenario.

### C. Execution failure (dependency/order)
- **Golden:** stage 2 consumes a fresh stage-1 product.
- **Mutant:** stage 1's derived artifact is **missing or from the wrong order**, so stage 2 fails or
  binds a stale upstream digest (this is the p14 v1 chain hazard, retained as a *recovery* family:
  the agent must recognize stage 2 can't be trusted and **rerun the prerequisite stage 1 first**).
- **Public symptom:** `stage2 upstream digest mismatch` / `stage2 MISSING`.
- **Valid recovery:** repair inputs, rerun stage 1, **then** stage 2 (ordered).
- **Invalid shortcuts:** rerun only stage 2; reuse the stale stage-1 product.
- **Hidden checks:** `REQUIRED_STAGE_CHAIN_OK` (stage2.upstream == fresh stage1 digest), as in v1.

### D. Output drift
- **Golden:** report content matches the current package; manifest digest == report body digest.
- **Mutant:** a report has **valid format but stale/altered content** — its body is from an old run (or
  a benign-looking edit), so its digest conflicts with the current inputs; a `stale_log.txt` distractor
  *agrees* with the drifted report (plausible but non-authoritative).
- **Public symptom:** `report provenance conflict: report body != current inputs`.
- **Valid recovery:** discard the drifted report, regenerate fresh evidence from the repaired inputs.
- **Invalid shortcuts:** trust the drifted report; hand-edit the manifest to claim the current package
  over a stale body.
- **Hidden checks:** submitted report digest == fresh hidden re-run; manifest↔report binding holds.

### E. Cross-source conflict
- **Golden:** spec, manifest, configs, report, evidence manifest all coherent.
- **Mutant:** **three sources disagree** — e.g. `handoff_manifest.json` says v2/clk_main,
  `flow_config.json` says v1, and `evidence_manifest.json` claims v2 while the `timing_report.rpt` body
  is a v1/clk_old run. A distractor `prev_signoff.log` agrees with the v1 story (plausible decoy).
- **Public symptom:** `cross-source conflict: manifest=v2 flow=v1 evidence_claims=v2 report=v1`.
- **Valid recovery:** apply the authority hierarchy (§4) → the **manifest** wins → repair `flow_config`
  (and SDC) to v2/clk_main, regenerate the chain so report+manifest+evidence all become v2-consistent.
- **Invalid shortcuts:** "make them agree" by editing the manifest to v1 (wrong authority); trust the
  distractor log; hand-edit the report.
- **Hidden checks:** consumed == manifest authority; fresh evidence describes the manifest package;
  `AUTHORITY_CONSISTENCY_OK` (the chosen target equals the highest-authority source).

**This is the recommended first family (§13)** — it is the purest test of "decide which source is
authoritative" and reuses the exact v1 stale-package mechanism with one added decoy source.

---

## 4. Authority model

A **strict, total order** so there is exactly one authority-consistent repair target (no ambiguity):

1. `spec.md` / `design_intent.md` — human intent (narrative ground truth; never mutated).
2. `handoff_manifest.json` — **the machine authority** (read-only, frozen): netlist/clock/scenario/corner.
3. `flow_config.json` / `scenario_config.json` / `corner_config.json` — **selection inputs** the agent
   repairs (lower than the manifest; when they disagree with the manifest, the manifest wins).
4. **freshly generated** evidence manifests (`evidence_manifest.json`, `stage2_summary.json`) — trusted
   only when their `input_hashes`/digests match the repaired inputs (freshness gates their authority).
5. reports (`timing_report.rpt`) — products, authoritative only as the body the fresh manifest binds.
6. stale logs / distractor artifacts (`prev_signoff.log`, `stale_log.txt`) — **non-authoritative
   diagnostics**; never a valid repair target or evidence source.

**Invariant (anti-ambiguity):** the generator guarantees a *single coherent authority-consistent
package* — the manifest names exactly one (netlist, clock, scenario, corner), and the only valid repair
makes levels 3–5 consistent with level 2. Editing level 2 (the manifest) is a forbidden edit; "agreeing
with" a lower level instead of the manifest is the canonical wrong-authority shortcut the oracle rejects.

---

## 5. Workflow DAG and recovery paths

The generated task is a DAG with a **normal path**, a **failing/hazard path**, a **recovery path**, and
a **revalidation path**. Nodes (PT-only first):

| Node | inputs | outputs | command | expected evidence | hazard injection | recovery action |
|---|---|---|---|---|---|---|
| N0 authority | — | manifest (RO) | — | — | (never) | — |
| N1 select | manifest, configs | flow/scenario/corner config | (edit) | — | spec-drift / cross-source | choose manifest-consistent selection |
| N2 constrain | N1 | constraints.sdc | (edit) | — | invocation / clock drift | bind authority clock |
| N3 stage1 evidence | N1,N2 | timing_report.rpt + evidence_manifest.json | `run_evidence_stage1.sh` | stage1 digest/nonce | output-drift (stale report shipped) | regenerate fresh stage1 |
| N4 stage2 evidence | N3 | stage2_summary.json | `run_evidence_stage2.sh` | stage2 digest + upstream binding | execution-failure (stale upstream) | rerun stage1 then stage2 |
| N5 public check | N1–N4 | `WORKFLOW_PUBLIC:` verdict + hazard symptoms | `run_public.sh` | — | — | read to diagnose |
| N6 hidden oracle | submitted | markers | `run_hidden.sh` | fresh re-run | — | — |

**Recovery edges:** the mutant ships with hazards on N1/N2/N3 (and a stale upstream on N4). The agent's
**diagnosis** = run N5, cross-check the conflicting sources against N0/manifest, decide the authoritative
target. The **recovery path** = repair N1+N2 to the authority, rerun N3 then N4 (ordered), then **N5
revalidation** to confirm `evidence=FRESH stage2=FRESH` and no residual conflict. The generator can emit
graphs where *which nodes must be rerun* depends on which hazard family is active — so the agent must
decide the rerun set, not follow a fixed recipe.

---

## 6. Artifact and evidence schema (extends p14 v1)

Per-stage `evidence_manifest.json` / `stage2_summary.json` keep all v1 fields (`input_hashes`,
`selected_*`, `report_digest`, `upstream_evidence_digest`, deterministic `run_nonce`, no wall-clock) and
add hazard/recovery metadata. New fields (set by the generator; the **hidden** truth file holds the
authoritative copy, the visible artifacts only carry what's fair to see):

| Field | Where | Meaning |
|---|---|---|
| `authority_source` | hidden truth | the highest-authority source id (`"handoff_manifest.json"`) |
| `hazard_type` | hidden truth | active family code (`spec_drift`/`invocation`/`execution`/`output_drift`/`cross_source`) |
| `stale_source_id` | hidden truth | which artifact(s) carry the stale/drifted story (e.g. `flow_config.json`, `prev_signoff.log`) |
| `invalidated_by` | hidden truth + fresh manifest | what makes a source non-authoritative (e.g. `input_hashes_mismatch`, `lower_than_manifest`) |
| `recovery_step_expected` | hidden truth | the ordered rerun set required (e.g. `["fix_flow","fix_sdc","stage1","stage2"]`) |
| `recovery_hint_level` | metadata/public | 0 (no hint) / 1 (symptom only) / 2 (symptom + which source conflicts) — a difficulty knob |
| `report_provenance` | report header (non-digest) | the package the report *claims* (for conflict detection; not trusted by the oracle) |
| `scenario`/`corner`/`clock` binding | manifest + evidence | the authority triple, echoed in fresh evidence |

The agent **never** edits the hidden truth or the manifest; it edits selection inputs and *regenerates*
evidence. Distractor artifacts (`prev_signoff.log`, `stale_log.txt`) are visible read-only and forbidden
to cite as evidence.

---

## 7. Public feedback design

`run_public.sh` / `run_public.tcl` must be **fair but not revealing**:

- **Verdict-first** within the first 1000 bytes (`WORKFLOW_PUBLIC: ...`), before any long PT dump.
- **Concise hazard symptoms** only: e.g. `cross-source conflict: manifest=v2 flow=v1 evidence_claims=v2
  report=v1`, `scenario/corner mismatch`, `stage2 upstream digest mismatch`, `report provenance
  conflict`. These describe *what disagrees*, enabling diagnosis by cross-checking.
- **No hidden oracle markers** (`EVIDENCE_OK`, `AUTHORITY_CONSISTENCY_OK`, `HAZARD_RECOVERY_OK`, the
  truth file) and **no exact fix literal** (never "set flow_config.netlist=netlist_v2.v").
- **Stale/conflict indicators allowed** (FRESH/STALE/MISSING, which sources disagree) but **not the
  resolution** (never names which source is authoritative — the agent must apply §4 itself).
- **No full report dump before the verdict.** The report tail may follow the verdict for context, as in
  p13/p14.
- `recovery_hint_level` (§6) scales how much the public symptom reveals — level 0 emits only
  `MISMATCH`/`CONFLICT` with the disagreeing values; higher levels are reserved for easier calibration
  samples, never for the difficulty samples.

---

## 8. Hidden oracle design

Layered, deterministic where possible; real PT only for the fresh re-run (as in v1). Checks:

| Check | Nature |
|---|---|
| structural validity, required files | deterministic |
| anti-cheat / forbidden edits (manifest, netlists, generators, runners, truth, distractors-as-evidence) | deterministic |
| public/hidden split, no leak, verdict-first | deterministic |
| **final state**: consumed == manifest authority (netlist/clock/scenario/corner) | deterministic + hash |
| **tool/signoff**: fresh PT sign-off of the consumed design | real PT |
| **evidence chain**: each required stage's submitted evidence == fresh hidden re-run (digest/hashes/nonce); stage2.upstream == fresh stage1 | real PT + hash |
| **authority consistency**: the repaired target equals the highest-authority source; lower sources made consistent *to* it, not vice-versa | deterministic |
| **hazard recovered**: the active `hazard_type` no longer holds (the specific inconsistency is gone) and `recovery_step_expected` was performed (fresh evidence reflects the required reruns) | deterministic + hash |
| **stale invalidated / wrong-source rejected**: no stale/distractor digest survives in the submitted evidence | deterministic |
| masking / symptom suppression (set_false_path / loosened period) | deterministic |

**Failure classification** (the oracle emits a `RECOVERY_CLASS:` diagnostic, not scored but reported):
`final_state_only`, `wrong_authority_chosen`, `stale_evidence_reuse`, `partial_recovery`, `wrong_order`,
`symptom_suppression`, `report_forgery`, `protocol_nocommit`.

`EVIDENCE_CHAIN_OK` and `HAZARD_RECOVERY_OK` remain **hard preconditions** (as EVIDENCE_OK was in
p13/p14): final/authority axes score 0 unless the fresh chain exists *and* the hazard is recovered, so a
"looks fixed but wrong source / stale" submission cannot reach pass.

---

## 9. Scoring contract (p14 v2)

**Hard gates (all required to pass):**

```
PASS  ⟺  NO_FORBIDDEN_EDIT
       ∧ SIGNOFF_OK
       ∧ FINAL_STATE_OK
       ∧ EVIDENCE_CHAIN_OK
       ∧ HAZARD_RECOVERY_OK
       ∧ AUTHORITY_CONSISTENCY_OK
```

**Pass requires correct recovery, not merely green signoff or generated evidence** — green PT on the
wrong/stale package, or fresh evidence from the wrong-authority target, both fail (¬HAZARD_RECOVERY_OK /
¬AUTHORITY_CONSISTENCY_OK).

**Partial axes (diagnostic, below the 0.5 gate):**
`signoff 0.10 / diagnosis 0.10 / partial_evidence 0.15 / final_state 0.15 / evidence_chain 0.20 /
hazard_recovery 0.15 / authority_consistency 0.10 / explanation 0.05` (starting proposal; sum 1.0). As in
p13/p14, because the harness pass is a fixed additive `total ≥ 0.5`, **HAZARD_RECOVERY_OK +
AUTHORITY_CONSISTENCY_OK are folded into the EVIDENCE master gate** so partial/wrong-authority states
stay ≤0.30. `diagnosis` is a small partial axis: the agent's stated root-cause (parsed, low weight) —
never enough alone to pass, mirroring the explanation-weight rule.

Indicative failure totals: final-state-only ~0.25; wrong-authority repair ~0.25; stale reuse ~0.25;
partial recovery (one stage) ~0.25–0.35; nocommit ≤0.25.

---

## 10. Acceptance filters

Before a generated p14 v2 task is accepted (tool-gated checks on real b04 PT):

1. golden = **1.0**; 2. mutant **< pass**; 3. full recovery (correct authority + ordered chain) = **1.0**;
4. final-state-only repair **fails**; 5. **wrong-authority repair fails** (e.g. editing the manifest down
to a lower source); 6. stale-evidence reuse **fails**; 7. partial chain **fails**; 8. wrong-order
**fails**; 9. symptom suppression (set_false_path/loosened period) **fails**; 10. hand-edited evidence
**fails**; 11. public verdict within first 1000 bytes; 12. no hidden artifact / answer-literal leak;
13. **deterministic regeneration** (nonce/digest bit-identical ×3); 14. CLI⇄agentic dispatch parity;
15. real-tool validation green.

Filter **5 (wrong-authority repair fails)** is the new anti-collapse keystone: it is what makes the task
a *diagnosis* task rather than a *make-two-files-agree* task. A sample where "agree with any source"
passes is **rejected**.

---

## 11. Difficulty controls

| Knob | Shallow → Deep | Anti-ambiguity guardrail |
|---|---|---|
| `num_hazards` | 1 → 3 | each hazard independently recoverable; combined recovery still unique |
| `hazard_type` | output_drift → cross_source → mixed | every family resolves to the *same* manifest authority |
| `conflicting_sources` | 2 → 4 | the manifest must out-rank all; lowers never tie |
| `recovery_steps` | 2 → 4 | each required rerun must be *necessary* (removing it breaks a filter) |
| `evidence_stages` | 1 → 2 (→3 later) | each stage genuinely upstream-coupled |
| `distractor_reports/logs` | 0 → 2 | distractors self-consistent but **non-authoritative**; never a 2nd valid answer |
| `recovery_hint_level` | 2 → 0 | weaker hints raise diagnosis load; never make the target ambiguous |
| `stale_source_plausibility` | low → high | a more plausible decoy is harder to reject, but still wrong by authority |
| `scenario/corner/clock complexity` | 1 axis → 3 axes | each axis authority-unique |
| `required_reruns` | 1 → 3 | each necessary |
| `action_budget_target` | from measured golden length × safety | avoid budget-as-difficulty (the p13/p14 lesson) |

**Rule:** difficulty comes from **diagnosis + recovery-planning load**, never from ambiguity. Two equally
valid recoveries = NO-GO (§14).

---

## 12. Generator pipeline

```
generate_hazard_task(seed, params):
    cfg   = sample_hazard_config(seed, params)         # families, #sources, #reruns, hints, distractors
    golden = build_golden_dag(cfg)                     # manifest authority + coherent v2 package
    g_ev   = run_evidence_chain(golden)                # deterministic stage1(+2)
    assert deterministic(g_ev, repeats=3)
    mutant = inject_hazards(golden, cfg)               # spec-drift / invocation / exec / output-drift / cross-source
    mutant = add_distractors(mutant, cfg)              # stale logs / decoy reports, self-consistent but non-authoritative
    assert structural_valid(task) and verdict_first(run_public) and no_leak(public)
    assert oracle(full_recovery(mutant)) == 1.0        # correct authority + ordered chain
    for s in single_edit/each_source:                  assert oracle(s) < PASS
    for s in {final_state_only, wrong_authority, stale_reuse, partial_chain, wrong_order,
              symptom_suppress, hand_edit, trust_distractor}:  assert oracle(s) < PASS
    assert oracle(golden) == oracle(golden)            # determinism
    write_task_dir(...); update_inventory(...)
    return task
```

Steps that assert (the acceptance filters, §10) run inline; a sample failing any is **discarded** under a
per-batch attempt cap.

---

## 13. First implementation milestone (after design approval)

Deliberately tiny — **do not build a full generator**:

1. **Extend the existing p14 generator with ONE hazard family** — recommended **cross-source conflict**
   (family E): reuse the v1 stale-package mechanism + add one decoy source (`prev_signoff.log`) and an
   `evidence_manifest.json` that *claims* v2 while the report body is v1. Authority = manifest.
2. **Generate exactly ONE p14 v2 task** (`workflow_handoff_0003` or a new id), `evidence_steps=2`,
   `num_hazards=1`, `recovery_hint_level=1`.
3. **Validate on b04:** full recovery = 1.0; **wrong-authority repair fails** (filter 5); stale/distractor
   reuse fails; partial/wrong-order fails; determinism; verdict-first; no leak; dispatch parity.
4. **No model probe** until the generator *contract* (all acceptance filters green) is proven.

Gate to proceed: the one task passes the full acceptance matrix on real PT; `scripts/check` green; tests
green.

---

## 14. GO / NO-GO criteria

**GO** if the generated task, verifiably via acceptance filters:
- requires **hazard diagnosis** (the agent must detect the inconsistency);
- has **≥2 plausible evidence sources that conflict**;
- has **exactly one** authority-consistent recovery;
- **wrong-source / wrong-authority recovery fails**;
- **full recovery passes**;
- the hidden oracle is **deterministic**;
- public feedback is **fair** (verdict-first, no fix literal, no oracle markers);
- the task is **reproducible** (bit-identical evidence).

**NO-GO** if:
- the task reduces to following obvious public instructions;
- public output reveals the fix;
- any single local edit passes;
- stale evidence can be accepted;
- **multiple equally valid recovery paths exist** (ambiguity);
- the oracle depends on fragile timing / nondeterministic tool output;
- token/tool cost becomes unreasonable.

---

## 15. Relationship to p14 v1

**Reuses (no change):**
- `WorkflowHandoffEvaluator` — the marker-gated evaluator; v2 adds `HAZARD_RECOVERY`/`AUTHORITY_CONSISTENCY`
  axes but keeps the same strict-gate `_eval_marker` pattern (likely a thin subclass or a few extra
  component branches — decide at milestone time; prefer reuse over a new evaluator).
- the **stage evidence chain** + `upstream_evidence_digest` coupling + deterministic `run_nonce`.
- the **generator skeleton** (`build_task_skeleton` / `bake_golden`), frozen p13/p14 PT substrate
  (netlists, libs, signoff TCL, launder/coverage/signoff phases), and the SDC-laundering forge-resistant
  grading.

**Must change / add:**
- **hazard metadata** (`hazard_type`, `stale_source_id`, `invalidated_by`, `recovery_step_expected`,
  `recovery_hint_level`) in the hidden truth + fair subsets in public/metadata.
- **authority hierarchy** encoded in `handoff_truth.json` + enforced by the oracle (`AUTHORITY_CONSISTENCY`).
- **recovery classification** (`RECOVERY_CLASS:` diagnostic) in the grader.
- **conflict / distractor evidence generation** (decoy logs, claim-vs-body mismatched manifests).
- **shortcut matrix** for wrong-authority repairs (the new acceptance filter 5) in the generator's
  validation pass.

**Track decision:** see open question 1 — leaning **same `p14_workflow_handoff` track, new task ids**
(v2 is the hazard preset of the same generator), but a `p15_*` track is the alternative if the schema/
evaluator diverge enough.

---

## 16. Open questions

1. **Same track (`p14_workflow_handoff`) or new `p15`?** Leaning same track + new ids (v2 = hazard
   preset), to keep the validated evaluator/oracle; promote to `p15` only if the evaluator must diverge.
2. **First hazard: output-drift or cross-source conflict?** Recommended **cross-source conflict** —
   purest "decide the authority" test, smallest delta from the validated v1 stale-package mechanism.
3. **How many distractor sources are enough?** Hypothesis: **1 decoy** (a `prev_signoff.log` agreeing
   with the stale story) is enough to force authority reasoning; 2+ risks ambiguity/brittleness.
4. **How to make recovery difficult without ambiguity?** Keep a single manifest authority; vary
   *plausibility* of decoys and *hint level*, not the number of valid answers.
5. **How to cap token cost?** The p14 v1 probe hit ¥49.71 at depth-2/60-actions; v2 adds reading more
   sources. Keep `evidence_steps=2`, design tasks solvable in ≲30 actions, and consider lowering
   `max_tool_calls` once the FINISH/confidence artifact is fixed (see #6).
6. **Fix FINISH/confidence before larger probes?** **Yes, recommended** — the pervasive
   `budget_exhausted`/empty-confidence artifact masked correct agents in p14 v1; fix it (a
   FINISH+confidence prompt that fires before the action budget is consumed) before any k≥5 v2 probe so
   trust/format metrics are meaningful.
7. **Should `max_tool_calls` scale with `evidence_steps` × hazard count?** Likely yes — budget should
   track measured golden recovery length; but only after the FINISH fix, so budget headroom isn't spent
   on un-emitted confidence.

---

*Prepared at the Phase-4C boundary. Implementation is deferred until this design is reviewed and
approved; the first milestone (§13) is one hazard family, one task, contract-only — no model probe.*
