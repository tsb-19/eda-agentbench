# p14 Workflow Generator — Phase-4D Checkpoint

Status: checkpoint summary only (no code, no tasks, no tools, no models run).
Scope: state of the p14 workflow-generator track after Phase-4D commit `99565dc`.

---

## 1. Current branch checkpoint

- **branch:** `synthetic-phase0a`
- **current HEAD:** `99565dc feat: add workflow handoff cross-source conflict variant`
- **working tree status:** clean
- **remote:** local-only; **not pushed** (no upstream configured for `synthetic-phase0a`)
- **p10–p13 retained** as reliability / protocol / evidence-provenance substrates — they are kept, not replaced, because they validate orthogonal properties (constraint drift, single-fault handoff, multi-artifact repair, trajectory/evidence reproduction).
- **p14 is now the workflow-generator candidate** — the first track whose tasks are built by a generator that emits real workflow structure (ordered evidence chains and a hazard-recovery variant), rather than a hand-authored single-edit repair.

---

## 2. Why p14 exists — the negative-results ladder

Each prior track saturated for the top protocol-compliant agents (Qwen3.7-Max, DeepSeek-V4-Pro), which is *why* the next rung was built:

- **p10 constraint-drift** — saturated for Qwen/DeepSeek. Single drifted constraint is trivially localizable.
- **p11 single-fault FlowHandoff** — saturated. One injected fault across a handoff is still single-localization.
- **p12 multi-artifact two-edit repair** — saturated. Two coupled edits did not raise the floor; still a search-free repair.
- **p13 trajectory/evidence repair** — validated that **evidence provenance** (fresh, right-package, not hand-edited, authority-correct) can be made load-bearing, but the underlying repair stayed saturated for Qwen.
- **p14** — introduced because a *generator* track needs genuine **workflow structure**: ordered evidence chains with cross-stage coupling, and recoverable **hazards** (conflicting sources requiring authority diagnosis). The hypothesis is that difficulty comes from *workflow reasoning and authority diagnosis*, not from hiding a single fault more cleverly.

---

## 3. p14 v1 — ordered evidence-chain generator

Two generated tasks establish the ordered-chain contract:

- **workflow_handoff_0001** — `evidence_steps=1`. p13-style trajectory/evidence reproduction baseline; validates the single-stage evidence path end to end.
- **workflow_handoff_0002** — `evidence_steps=2`. Ordered two-stage chain.
- **Coupling:** `stage2_summary.json` depends on stage1 via **`upstream_evidence_digest`** — stage2's deterministic `run_nonce` folds in stage1's fresh `report_digest`.
- **Failure modes that must fail:**
  - stage1-only (chain incomplete) → fails
  - stale stage1 (stage2 built on an outdated stage1 report) → fails
  - wrong order (stage2 before a valid stage1) → fails
- **Pass:** only a full, fresh, correctly-ordered chain passes.
- **Probe result:** the p14 tiny probe (committed) showed **Qwen/DeepSeek still solve v1** — i.e. v1 validates the generator substrate, **not** difficulty.

---

## 4. p14 v2 — workflow hazard recovery

- **workflow_handoff_0003** adds a **cross-source conflict** hazard (`hazard_type=cross_source_conflict`, `evidence_steps=2`, `num_hazards=1`, `hint_level=1`).
- **Authority model:** `spec.md` / `handoff_manifest.json` are the **authority**. Lower sources include **stale or misleading** config / report / evidence / log artifacts (e.g. a lying `evidence_manifest.json` claiming a v2 netlist while its `report_digest` was produced from a v1 run, plus a `prev_signoff.log` decoy).
- **Failure modes that must fail:**
  - **wrong-authority repair** — making files agree with a *lower* source instead of the manifest → fails. The oracle pins `expected_netlist=v2` from `handoff_truth.json`, so wrong-authority repair fails on `evidence_is_authority_pkg=WRONG` independent of anti-cheat.
  - **trust-decoy / consume stale v1** evidence → fails.
- **Pass:** only a full **authority-consistent** recovery (lower sources recovered upward to the authority, fresh evidence regenerated) passes.
- This is the **first p14 task that explicitly tests authority diagnosis**, not just ordered execution.

---

## 5. Generator architecture

- **`generators/p14_workflow_handoff_gen.py`** — `build_task_skeleton(out_dir, task_id, seed, evidence_steps, hazard_type=None, hint_level=1)` is **pure** (no tool); `bake_golden(task_dir, pt_cmd, evidence_steps)` is **tool-backed** (real PrimeTime on b04). Reuses frozen p13 assets via `_REUSED_FROM_P13`. The `hazard_type="cross_source_conflict"` branch is **gated** so 0001/0002 skeletons stay byte-identical.
- **`scripts/generate_workflow_handoff_tasks.py`** — `TASKS = [(0001,0,1,None),(0002,0,2,None),(0003,0,2,"cross_source_conflict")]`; supports `--only` and `--bake`.
- **`eda_agentbench/evaluator/workflow_handoff.py`** — `WorkflowHandoffEvaluator`, strict-gate `_eval_marker` pattern mirroring p13. Components: `signoff`, `evidence_generation` (the **EVIDENCE_OK** master gate), `final_state`, `stage_chain`, `provenance`, plus the gated `authority_consistency` and `hazard_recovery` for 0003. Dispatch parity held in both `cli.py` and `agentic/runner.py::_select_evaluator`.
- **p14 task layout** — `files/` (agent-visible inputs + public runners), `hidden/` (`grade_workflow.py`, `handoff_truth.json`, hidden runners), `solution/` (golden baked chain).
- **Seed/determinism model** — pure skeleton from `seed`; deterministic `run_nonce` over input hashes + clock + scenario + corner + report_digest (+ upstream_evidence_digest); **no wall-clock**.
- **Evidence manifest schema** — per-stage `evidence_manifest.json` records selected netlist/clock, `report_digest`, and `run_nonce`.
- **Stage chain schema** — `stage2_summary.json` carries `upstream_evidence_digest` binding it to stage1's fresh report.
- **Hidden oracle strategy** — `regen_reference.sh` re-runs the **trusted generator** on submitted inputs; `grade_workflow.py` compares submitted vs reference and emits verdict-first markers.

---

## 6. Evidence / provenance model

- **`report_digest`** — sha256 of the canonicalized `report_timing` path-table body (volatile lines stripped); binds real PT output and defeats hand-forgery.
- **`upstream_evidence_digest`** — folds stage1's fresh `report_digest` into stage2's nonce, so partial / stale / wrong-order chains fail.
- **deterministic `run_nonce`** — `sha256(input_hashes ++ clock ++ scenario ++ corner ++ report_digest [++ upstream_evidence_digest])[:16]`; reproducible, no wall-clock.
- **stage1 evidence** — fresh single-stage manifest + report bound by digest.
- **stage2 evidence** — manifest + summary bound to stage1 via the upstream digest.
- **authority-pinned validation** — the oracle pins the expected target (e.g. `expected_netlist=v2`) from `handoff_truth.json`, independent of what any submitted manifest claims.
- **Why stale / hand-edited / wrong-package evidence fails** — any of these breaks the digest/nonce binding or the authority-pin, so `EVIDENCE_OK` (the master gate) does not fire and all gated components score 0.

---

## 7. Acceptance filters (collapse-prevention)

Core filters that keep p14 from collapsing back into p10–p13 triviality:

- golden = 1.0
- mutant below pass
- full recovery = 1.0
- single-edit repair fails
- final-state-only repair fails
- stage1-only fails
- stage2 from stale stage1 fails
- wrong-order fails
- wrong-authority repair fails
- stale evidence fails
- hand-edited evidence fails
- no hidden leaks
- verdict-first public output
- deterministic regeneration
- real b04 PrimeTime validation

---

## 8. Model-probe status

- **p14 v1 probe** completed and committed (`reports/synthetic_p14_tiny_probe.{md,json}`).
- **Qwen / DeepSeek solved `workflow_handoff_0002`** with pass^k = 1.00 (capability read from `total_score`, not protocol_status).
- **MiniMax-M3** continued to expose reliability / protocol failures (not capability).
- **`workflow_handoff_0003` has not yet been probed.**
- **Do not claim p14 v2 difficulty** until `workflow_handoff_0003` is probed.

---

## 9. What is genuinely new after `99565dc`

- p14 is **no longer merely p13 with more stages**.
- p14 v2 introduces **workflow hazard recovery**.
- The agent must **diagnose source authority**.
- Correctness is **not** "make artifacts agree".
- Correctness is **"recover lower sources upward to the authority"**.
- This is closer to **recoverable workflow-hazard benchmarks** than previous p10–p13 tracks.

---

## 10. Open risks

- Qwen / DeepSeek may still solve `workflow_handoff_0003` (single hazard, explicit hierarchy).
- Decoy evidence may be **too weak** to mislead a careful agent.
- The authority hierarchy may be **too explicit** in `spec.md` / manifest.
- Token cost may rise quickly with longer chains and more distractors.
- **FINISH/confidence budget artifacts remain unresolved** (budget_exhausted tagging); blocks trusting k≥5.
- The deterministic tiny PT substrate may still be **forgeable if reports are too simple**.
- **Over-strict oracle** could reject valid alternative workflows (false NO-GO on legitimate recoveries).

---

## 11. Recommended next steps (in order)

A. **Commit this checkpoint summary** after review.
B. Optionally run a **tiny p14 v2 probe on `workflow_handoff_0003` only**.
C. If Qwen/DeepSeek solve 0003, design stronger **p14 v3** hazards:
   - multiple conflicting authorities
   - deeper distractor reports
   - scenario / corner ambiguity
   - tool-output drift
   - dependency-repair planning
D. **Only after that** consider scaling the generator.

> Do **not** recommend immediate large-scale generation.

---

## 12. GO / NO-GO before next probe

**GO** for a `workflow_handoff_0003` tiny probe if:

- `scripts/check` is green
- b04 validation still passes
- working tree is clean
- no hidden leaks
- no local config / secrets tracked
- cost cap is explicit

**NO-GO** if:

- any harness / provisioning issue appears
- the wrong-authority acceptance filter regresses
- `workflow_handoff_0001` / `0002` behavior changes
- p14 evaluator dispatch parity breaks
