# Synthetic p10→p14 saturation summary (design-only, negative-results)

**Status: design-only document. No code, no tasks, no tools, no models, no probe, no push.** This is a
research-style negative-results summary of the synthetic handoff/hazard ladder after the p14 v3
(`workflow_handoff_0004`) capability probe concluded that the current single-hazard variants are
**saturated for top protocol-compliant agents**. It restates what was built, what works, what saturated,
why the current hazards are not hard enough, and recommends a structurally-harder p14 v4 direction.

## 1. Current checkpoint

- **Branch:** `synthetic-phase0a` (worktree `/data1/tongsb/eda-agentbench-synthetic-phase0a`).
- **HEAD:** `38d659a` — `docs: report p14 v3 workflow hazard capability probe`.
- **Branch is local-only / not pushed** (no upstream configured; nothing has been pushed this entire
  ladder).
- **Working tree:** clean (this document is the only new, unreviewed file until committed).
- **Latest major checkpoints (annotated tags + bundles, all local):**
  - **p14 architecture checkpoint** — `a7c9267` (`docs: summarize p14 workflow generator checkpoint`),
    tag `synthetic-p14-workflow-checkpoint-a7c9267`, bundle `synthetic-phase0a-p14-checkpoint-a7c9267.bundle`.
  - **p14 v2 smoke checkpoint** — `4a31fb3` (`docs: report p14 v2 workflow hazard smoke probe`),
    tag `synthetic-p14-v2-smoke-checkpoint-4a31fb3`, bundle `synthetic-phase0a-p14-v2-smoke-4a31fb3.bundle`
    (`workflow_handoff_0003` k=1 smoke; stopped at ¥30 cap).
  - **p14 v3 scenario/corner checkpoint** — `d8f37da`
    (`feat: add workflow handoff scenario corner conflict variant`), tag
    `synthetic-p14-v3-scenario-corner-checkpoint-d8f37da`, bundle
    `synthetic-phase0a-p14-v3-scenario-corner-d8f37da.bundle` (`workflow_handoff_0004` generator +
    b04-validated acceptance matrix; no model run yet at that point).
  - **p14 v3 capability probe report** — `38d659a` (this run's report:
    `reports/synthetic_p14_v3_0004_capability_probe.{md,json}`): Qwen3.7-Max and DeepSeek-V4-Pro both
    capability pass^k = 1.00 over valid trials.

Other worktrees remain untouched (`eda-agentbench` `c225cf1`, `eda-agentbench-synthetic` `fec9adc`).

## 2. Original goal

The synthetic-project-generator line was started to build a **complex, multi-task, workflow-level
synthetic industrial EDA benchmark generator**:

- use **real EDA tools** (PrimeTime on b04, via the transparent forwarder shim) and **hidden oracles**,
  not toy parsers;
- generate **mini handoff *projects*** (multi-artifact, cross-stage evidence chains) rather than
  isolated one-file tasks;
- measure **both capability** (can the agent diagnose + recover + produce a globally consistent
  evidence chain) **and reliability/protocol** (does it finish cleanly, declare calibrated confidence,
  avoid infra/anti-cheat traps).

The north star (see [[benchmark-hardening-north-star]]) is to measure *real* capability gaps versus
human chip engineers, with realism gating every task — not contrived difficulty.

## 3. What was built

A progressive ladder of substrates, each reusing the previous one's machinery and raising one axis of
difficulty:

- **p10 — constraint-drift substrate.** A mini project whose `flow_config`/constraints drift from the
  authoritative spec; the agent must repair the lower source upward and rerun.
- **p11 — flow handoff.** Single-artifact handoff with an authority/manifest the agent must obey.
- **p12 — multi-artifact handoff.** Two-edit recovery across coordinated artifacts.
- **p13 — trajectory / evidence handoff.** Single rerun of an evidence chain; the trajectory (fresh
  ordered evidence bound to repaired inputs) is the gate, not just the final files.
- **p14 — `workflow_handoff` generator.** Multi-stage evidence-chain handoff with a real PrimeTime
  sign-off, a hidden re-run of the trusted chain, and a `grade_workflow.py` oracle comparing submitted
  vs reference evidence. Four committed tasks:
  - `workflow_handoff_0001` — `evidence_steps=1` (p13-style baseline).
  - `workflow_handoff_0002` — `evidence_steps=2` (cross-stage `upstream_evidence_digest` chain).
  - `workflow_handoff_0003` — p14 v2 **cross-source conflict / authority diagnosis** (netlist/clock
    authority: netlist_v2/clk_main correct vs stale v1/clk_old, with a lying decoy manifest).
  - `workflow_handoff_0004` — p14 v3 **scenario/corner provenance conflict** (netlist/clock already
    correct; `flow_config` selects wrong scenario/corner test/typ; lying `evidence_manifest` and a
    `prev_corner_signoff.log` decoy reinforce the wrong corner; authority pinned to the hidden re-run).

All four are real-PT-backed, deterministic, seedable, and share one uniform `grade_workflow.py`.

## 4. What works

The infrastructure is validated and load-bearing — this is the retained engineering value:

- **Real PrimeTime-backed acceptance matrices** run end-to-end through the b04 forwarder; golden = 1.0,
  every adversarial shortcut below the 0.5 pass gate, on every p14 task.
- **Hidden oracle checks** (`run_hidden.sh` → launder → coverage → fresh sign-off → `regen_reference.sh`
  → `grade_workflow.py`) execute in an evaluator-private workspace the agent never sees.
- **Evidence chain / `upstream_evidence_digest`** binds later stages to fresh earlier-stage digests, so
  a stale or hand-forged chain is detected.
- **Stale evidence, hand-edited evidence, and wrong-package evidence are all rejected** (EVIDENCE_OK
  master gate denied).
- **Wrong-authority repair is rejected** (authority_consistency gate).
- **Wrong-corner evidence is rejected** — including the "wrong-corner green PT" case: the design signs
  off (`SIGNOFF_OK=True`) yet still totals 0.20 because the scenario/corner authority echeck denies
  `EVIDENCE_OK`.
- **Anti-cheat catches forbidden authority edits** — editing `handoff_manifest.json` (or netlist/lib)
  downward is zeroed (`edit_manifest_down` → 0.0); this is "live-evaluator fail via forbidden authority
  edit," not a grader-only failure.
- **The generator is deterministic and seedable** (deterministic `run_nonce` from input hashes; fresh
  re-run nonces match committed solution nonces — verified on b04).
- **Public verdict-first discipline** works (the public runner hoists the verdict line; no answer leak;
  no hidden leak in committed tasks).
- **p13/p14 reliability/protocol signals are real** — `protocol_status`, `overconfident_wrong`,
  abstention, and infra-exclusion are captured and separable from `capability_pass`.

## 5. What saturated

The single-hazard ladder is capability-saturated for top protocol-compliant agents:

- **p10** — saturated for Qwen/DeepSeek.
- **p11** — saturated for Qwen/DeepSeek.
- **p12** — saturated for Qwen/DeepSeek.
- **p13** — saturated for Qwen; mostly-saturated DeepSeek capability.
- **p14 v1 (`workflow_handoff_0002`)** — saturated for Qwen/DeepSeek, pass^k = 1.00 (k=3 probe).
- **p14 v2 (`workflow_handoff_0003`)** — k=1 capability success for Qwen/DeepSeek with no obvious
  capability wall (full k=3 deferred at the ¥30 cap; no wrong-authority shortcut passed).
- **p14 v3 (`workflow_handoff_0004`)** — saturated for Qwen/DeepSeek, **capability pass^k = 1.00** over
  valid trials (Qwen 3/3, DeepSeek 3/3 after a top-up). Both perform slow/func authority diagnosis →
  upward repair → ordered stage1→stage2 rerun → decoy avoidance on every valid trial.

This is consistent with the broader finding ([[single-localization-saturation]],
[[reliability-calibration-pivot]]): small, single-axis localization/recovery is frontier-saturated.

## 6. Capability vs reliability/protocol

The two findings must be kept separate (Phase-4F metrics contract):

**Capability (the frontier solves it):**
- Qwen3.7-Max and DeepSeek-V4-Pro solve the current generated p14 hazards on essentially every valid
  trial. There is no hazard-recovery capability wall at p14 v1/v2/v3.

**Reliability/protocol (the real discriminator):**
- **MiniMax-M3** exposes nocommit / malformed-command / partial-chain behavior (the p14 v2 smoke and
  earlier reliability runs); it is a reliability/protocol signal, not an authority-diagnosis capability
  signal.
- **DeepSeek-V4-Pro** sometimes shows no-FINISH / budget-exhausted / late-infra artifacts (solves the
  hazard, then over-explores or is grazed by a transient gateway error before FINISH). These are
  protocol artifacts — when `total_score=1.0` with a solved workspace, they are **not** capability
  failures.
- **Gateway/infra failures** (e.g. the transient HTTP-400 "Invalid model name" outage during the 0004
  probe) **must be excluded from capability metrics**; they are tracked as infra, never counted as
  capability.
- **`protocol_clean` and `capability_pass` are reported separately**; `pass@1/pass@k/pass^k` are
  computed over valid (non-infra) capability trials only.

## 7. Why current p14 hazards are not hard enough

The single-hazard design is too legible once an agent has seen the pattern:

- **Single authority hierarchy is too clear** — one `handoff_manifest.json`/`spec.md` is the obvious
  authority; the agent just reads it.
- **Single hazard dimension is too local** — exactly one drift axis (netlist/clock in v2;
  scenario/corner in v3), so there is one thing to fix.
- **Decoys are too easy to discard** — the lying manifest / `prev_corner_signoff.log` decoy contradicts
  the single authority, so cross-checking one source disposes of it.
- **Public spec/manifest make the target too explicit** — the recovery target (slow/func, netlist_v2,
  clk_main) is stated outright.
- **The recovery path is mostly "repair lower sources upward and rerun"** — a fixed, shallow procedure.
- **The tiny PT substrate may be too semantically shallow** — one `tiny.db`, corner-independent report
  body, no real multi-corner/multi-mode semantic depth for the agent to reconcile.
- **Once agents identify the pattern, they execute it reliably** — Qwen solves 0004 in as little as 37s
  / 5 actions; the cost floor shows the task is essentially recognized, not solved from scratch.

## 8. Retained value

The negative result is informative, and the substrate is reusable:

- **p14 is the first real workflow-generator track** in the benchmark (multi-artifact, cross-stage,
  real-tool) — a structural step beyond one-file tasks.
- It **validates the evidence/provenance/hazard-recovery infrastructure** (fresh ordered chain,
  upstream digest binding, authority echecks, forbidden-authority anti-cheat) that harder hazards will
  reuse.
- **Acceptance filters prevent corrupt success** — every local shortcut (final-state-only, stage1-only,
  stale/hand-edited/wrong-corner evidence, wrong-authority) is provably below pass on real PT.
- **Real-tool validation is integrated** (b04 forwarder + deterministic nonces + hash-cached golden).
- **Generated tasks are reproducible** (seedable generator; uniform grader; byte-stable across tasks).
- **Reliability/protocol metrics are meaningful** and already discriminate models (DeepSeek vs MiniMax).
- **The negative result narrows the search**: *more single-hazard variants are unlikely to create
  frontier difficulty* — the gap must come from structural complexity, not renaming.

## 9. Next direction — stronger hazards

To pursue a real frontier signal on this substrate, raise **structural/diagnostic** difficulty (no
search shortcut), reusing the validated oracle/anti-cheat:

- **Multi-conflict workflows** — several independent handoff faults (netlist + clock + scenario/corner +
  SDC) simultaneously; the agent localizes a *set*, not one drift.
- **Partially truthful decoys** — evidence files that are *mostly* correct but wrong in one field,
  defeating the "find the one lie" heuristic.
- **Multiple plausible evidence sources** — several sign-offs of comparable apparent authority; the
  agent must reason about which dominates rather than grep one manifest.
- **Scenario/corner + netlist/clock coupled conflict** — combine the v2 and v3 conflict axes so
  authority is split across sources and must be reconciled.
- **Report A correct on netlist but wrong on corner; report B correct on corner but stale netlist** —
  cross-source consistency, not per-report freshness.
- **Dependency-repair planning** — a hazard whose repair has an ordered dependency; wrong order fails;
  tests planning over diagnosis.
- **Multi-stage invalidation where the agent must decide what to rerun** — not "rerun everything," but
  "which subset of stages is invalidated by this conflict."
- **Public evidence that is locally consistent but globally inconsistent** — passes a within-report
  check but contradicts the cross-source authority graph.
- **Procedure-aware scoring that rejects corrupt success** — score the *procedure* (which stages rerun,
  in what order, against which authority), not just the final files.

## 10. What not to do next

- **Do not keep probing `workflow_handoff_0004`** — it is saturated; more trials will not change the
  capability answer.
- **Do not generate more single-hazard p14 variants expecting difficulty** — v1/v2/v3 establish that
  the single-axis design is saturated.
- **Do not merely increase `evidence_steps`** — a longer single-authority chain is still a fixed
  procedure, not harder diagnosis.
- **Do not run MiniMax in expensive frontier capability probes** — its signal is reliability/protocol;
  run it separately (Mode B) at low k.
- **Do not mix infra/protocol failures into capability pass rates** — keep `capability_pass` (valid
  trials only) and `protocol_clean` separate; exclude infra.
- **Do not push yet** unless branch policy changes (the ladder remains local-only by design).

## 11. Suggested next implementation — p14 v4

**Design target: multi-conflict partially-truthful decoy.**

Concrete sketch (authority = `netlist_v2 / clk_main / slow / func`):

- **report A** uses `netlist_v2` and `clk_main` but the **wrong corner** (locally fresh, internally
  consistent, wrong on corner).
- **report B** uses the **correct corner** but a **stale netlist** (locally consistent on corner, wrong
  on netlist).
- **evidence C** is freshly generated but from the **wrong scenario** (fresh chain, wrong authority).
- `prev_signoff.log` is **recent but non-authoritative** (a plausible decoy that matches no global
  truth).
- `stage2_summary` links to a **valid upstream digest that is semantically wrong** (chain integrity OK,
  semantics wrong).
- The agent must identify the **only globally consistent recovery target** and **rerun the right
  subset of stages** (not all, not one).

Acceptance filters must include:

- each **decoy-alone** recovery fails (A-alone, B-alone, C-alone each below pass);
- each **locally consistent but globally wrong** repair fails;
- **final-state-only** (no chain rerun) fails;
- **wrong-authority** repair fails;
- **full global recovery** (correct subset of stages rerun against the true authority) passes (golden
  1.0);
- anti-cheat still zeroes forbidden authority edits;
- determinism holds (fresh re-run nonces match).

## 12. Recommendation

- **Commit this summary after review.**
- Then choose one of:
  - **A.** Pause p14 and prepare a **research narrative / appendix** (the p10→p14 negative-results
    story + retained infrastructure value), or
  - **B.** **Design p14 v4 multi-conflict hazard** (the Section 11 target) as a design doc, before any
    code.
- **Preferred: design p14 v4 before writing more code.** The saturation evidence is strong enough that
  the next useful spend is a structurally-harder design, gated by a fresh acceptance matrix.
- **Do not run more probes until a v4 acceptance matrix exists** (cheap-probe-before-build: validate
  the oracle on real PT before spending model budget).

This summary exists to make the saturation finding durable, so future work does not re-probe
single-hazard p14 variants expecting a frontier signal that the evidence says is not there.
