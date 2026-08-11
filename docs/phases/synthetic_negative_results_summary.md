# Synthetic EDA Exploration — Negative-Results Summary

**Scope:** worktree `eda-agentbench-synthetic-phase0a`, branch `synthetic-phase0a`, through commit `866abbd`.
**Status:** design/measurement phase summary. No code, tasks, tools, or models are produced by this document.
**Thesis in one line:** small hand-authored EDA tasks — even with real commercial tools and forgery-resistant
hidden oracles — are rapidly saturated by protocol-compliant frontier agents (Qwen3.7-Max, DeepSeek-V4-Pro);
the durable signal they surface is **reliability/protocol** and **benchmark-integrity**, not top-model capability
difficulty.

---

## 1. Timeline / commit chain

The synthetic line pivoted from "hunt a single-shot task the frontier can't solve" (retired earlier this program
after four Phase-0 collapses) to "build small multi-artifact EDA *projects* and escalate the handoff mechanism."
Each rung was: **design doc → hand-authored prototype (real-PT-backed) → falsification smoke probe → accept/retire.**

| Stage | Commit | What it added |
|---|---|---|
| Synthetic planning docs | (docs-only, pre-`72bea1d`) | plan / taxonomy / phase-0 MVP under `docs/synthetic_*.md`; pivot to mini multi-artifact projects |
| p10 constraint-drift generator | `72bea1d` | `feat: generate synthetic phase0b constraint-drift tasks` — first synthetic family + generator |
| p10 Phase-0D probe | `ac08632` | `docs: report synthetic phase0d probe` — first agentic measurement on the synthetic substrate |
| p11 FlowHandoff Variant A | `c27e2a9` | `feat: add synthetic flow handoff prototype` — single-fault handoff/provenance |
| p11 FlowHandoff Variant C | `1e3b1eb` | `feat: add flow handoff clock binding variant` — clock-binding variant |
| p11 tiny probe | `7615d04` | `docs: report synthetic p11 tiny probe` |
| p12 multi-artifact prototype | `96bd79a` | `feat: add multi-artifact handoff escalation prototype` — stale-package triangle, ≥2 coordinated edits |
| p12 smoke probe | `f4e8cfe` | `docs: report synthetic p12 smoke probe` |
| p13 trajectory/evidence prototype | `aa6d64a` | `feat: add trajectory evidence handoff prototype` — repair **and** rerun generator **and** bind fresh evidence |
| p13 smoke probe | `866abbd` | `docs: report synthetic p13 smoke probe` |

(Intervening commits — designs, the Phase-0D dispatch fix `821b954`, p10 generator scaling, p12/p13 designs
`7c89b5a`/`7f9bdfb`/`572c65b` — are part of the same chain; the table lists the load-bearing rungs.)

---

## 2. Negative-result ladder

Each rung added structure on top of the last; each was *still* solved by the top protocol-compliant agents.

| Rung | Mechanism added | Result for top agents |
|---|---|---|
| **p10** | single numeric **constraint-drift** repair (one value to restore) | **saturated** for Qwen / DeepSeek |
| **p11** | single-fault **handoff/provenance** + **clock-binding** variants (A/C) | **saturated** for Qwen / DeepSeek |
| **p12** | **multi-artifact, two-edit** final-state repair (stale-package triangle; ≥2 coordinated edits, any single edit stays below pass) | **saturated** for Qwen / DeepSeek |
| **p13** | **trajectory / evidence-generation** handoff: repair inputs **+ rerun the public generator + produce fresh report & manifest bound to the repaired package**, validated against a hidden fresh re-run | **still saturated for Qwen** (3/3, pass^k=1.00); **DeepSeek** solves when not action-budget-limited (2/3, 1× budget_exhausted mid-trajectory); **MiniMax** exposed protocol/wrong-package-evidence reliability failures |

The ladder's shape is the finding: **adding artifacts and edits did not create capability difficulty.** Difficulty
only began to *flicker* at p13, and even there only as a budget-depth sensitivity (DeepSeek) and a reliability
failure (MiniMax) — not as a capability wall for the strongest agent.

---

## 3. What was learned

**Separate two axes that look alike in a pass-rate table:**

- **Capability difficulty** — can a competent agent, given enough budget, solve the task at all?
- **Reliability / protocol signal** — does the agent reliably *complete and commit* a valid trajectory every run?

Findings:

- **Qwen3.7-Max and DeepSeek-V4-Pro are strong enough** to solve these hand-authored small EDA tasks. Across
  p10–p13 they perform the intended repair (and, at p13, the rerun-and-bind trajectory) correctly. They are not
  the discriminating axis for tasks at this size.
- **MiniMax-M3 repeatedly exposes reliability issues** — `nocommit`, missing/garbled FINISH, format/stop-token
  artifacts. At p13 this manifested as running the evidence generator on an **uncommitted (wrong) package** and
  producing *authentic-but-wrong-package* evidence.
- **p13 is the first mechanism to produce a live evidence/provenance failure mode**: the hidden oracle correctly
  **rejected EVIDENCE_OK** for MiniMax's wrong-package evidence. This is a genuinely new, useful signal — but it is
  a *mechanism* signal, **not top-model difficulty** (Qwen never triggered it).
- **Increasing static artifact count alone is insufficient.** p12's multi-artifact triangle did not move top
  models. More files ≠ more difficulty.
- **Final-state-only or shallow-trajectory tasks are not enough.** The only place difficulty even flickered was
  when the task forced a *multi-step trajectory that produces evidence* (p13) — and even that needs more depth.

---

## 4. Benchmark-integrity fixes discovered

These were found while building/validating the substrate. **None is a model-capability finding** — each is a
property of the harness, provisioning, or the validation tooling that, left unfixed, would have *mis-scored*
models (either inflating cheats or penalizing correct work). Surfacing them is a primary value of the exploration.

| Finding | Nature | Why it is an integrity issue, not capability |
|---|---|---|
| **Public verdict truncated after long PT report** | harness output | the agent-visible `TRAJECTORY_PUBLIC:` verdict could scroll past a long `report_timing`; fixed to **verdict-first**. A truncated verdict would make a *capable* agent look lost. |
| **Agentic evaluator misdispatch for `synthetic_project`** (`821b954`) | dispatch bug | the agentic runner selected the wrong evaluator → wrong scores independent of the model. |
| **Dispatch-parity requirement (p10/p11/p12/p13)** | invariant | the evaluator branch must exist in **both** `cli.py` and `agentic/runner.py::_select_evaluator`; a mismatch scores agentic runs differently from single-shot. Enforced by tests on every track. |
| **`max-actions=12` too tight for p13 trajectory** | budget setting | DeepSeek hit the action cap mid-trajectory → `budget_exhausted` abstain counted as a non-pass. The model was *succeeding*; the budget cut it off. Fix: `max-actions ≥ 18–20` for trajectory/evidence tasks. |
| **Forwarder boundary with env vars** | provisioning | the b04 forwarder pipes stdin from `/dev/null` and does not inherit arbitrary env; heredocs (`pt_shell -f -`) and PATH-bare `pt_shell` fail remotely. Required passing **real workspace `.tcl` files** and resolving the **absolute** `pt_shell` path. A naive setup yields a false `SKIP/SIGNOFF_FAIL`, not a model signal. |
| **Validation-driver flat-vs-nested hidden workspace** | validation tooling | my gate-3 driver kept `hidden/` nested, but the harness `create_evaluator_workspace` **flattens** `hidden/` + editable files into one dir; the grader's bare relative filenames then resolved to `None`, showing a spurious **golden=0.1**. After matching the flat layout: golden=1.0, full matrix correct. The "0.1" was a *driver* artifact, never task or model. |

**Why this matters:** every one of these, undetected, would have masqueraded as a model result. The discipline of
"grade the known-correct solution through the same path first" (fairness gate) is what caught them.

---

## 5. Retained value of p10 / p11 / p12 / p13

These tracks are **not retired** — they are saturated as *difficulty* benchmarks but remain valuable as
instruments:

- **Real-tool reliability / protocol substrates.** They run real PrimeTime end-to-end and reliably expose
  `nocommit`, format/stop-token, abstention, and budget-exhaustion behaviors (MiniMax's signature is visible every
  time).
- **Anti-cheat / provisioning regression tests.** They encode dispatch-parity, forbidden-edit detection,
  hidden-shadow detection, verdict-first public output, and the forwarder/workspace contract — cheap guards that
  catch the integrity bugs above if they regress.
- **Evidence / provenance oracle substrates.** p13's deterministic `run_nonce` + report-digest-binds-to-real-PT
  mechanism is a working, forgery-resistant evidence oracle proven on b04. It is the seed for any deeper
  evidence-chain task.
- **Cheap calibration tasks.** Low cost (the whole p13 probe was ¥4.18 for 9 episodes) makes them ideal for
  format/nocommit/overconfidence/failure-mode calibration of the reliability layer.

**They are not yet strong difficulty benchmarks** for Qwen/DeepSeek-class agents.

---

## 6. Methodological conclusion

> **Small hand-authored EDA tasks — even with real tools and forgery-resistant hidden oracles — are rapidly
> saturated by protocol-compliant frontier agents.** Difficulty does not come from more artifacts, more edits, or
> a cleverer single-fault hiding place. It begins to appear only when the task imposes a **long-horizon,
> multi-stage, evidence-producing workflow** with enough **depth, ambiguity control, and action-planning load**
> that local repair is insufficient and the agent must plan, sequence, and *regenerate evidence that binds to a
> hidden fresh reference.* p13 is the first step in that direction and is necessary but not sufficient.

Corollary: at this task size the productive measurement is **reliability/calibration over a capable population**
(which agents complete and commit a valid trajectory *every* run, know when they are uncertain, and avoid
confident-wrong), plus **benchmark integrity**. Capability difficulty requires the depth described next.

---

## 7. Next research direction (design-only)

Recommend **Phase-3C / Phase-4 as design-only** (no implementation yet). Explore tasks where difficulty is
structural, not cosmetic:

- **Longer evidence chains across multiple ordered tool stages** (e.g. synth → STA → a second downstream stage),
  not a single rerun.
- **Required rerun sequence with dependency constraints** — stage *N* consumes stage *N−1*'s fresh output; wrong
  order or partial evidence fails.
- **Cross-stage report provenance** — the later stage's evidence must bind to the *earlier* stage's regenerated
  artifact (provenance chain, not a single nonce).
- **Action budget calibrated to task depth** — set generously and *measured*, so capability is not confounded by
  the cap (the p13 lesson).
- **Trajectory-aware oracle** — validates both final state **and** the evidence chain order/consistency.
- **Multi-scenario / multi-corner consistency** — evidence must be coherent across scenarios/corners.
- **Generated distractor artifacts and stale logs** — plausible wrong evidence the agent must not reuse.
- **Task families where local repair is insufficient** and fresh rerun evidence must match a hidden fresh
  reference — extending p13's core mechanism to a chain.

The goal of the design is to make **planning and sequencing** load-bearing, so that a capable-but-unplanning agent
fails for a *capability* reason, not a protocol one.

---

## 8. Open risks

- **Forgeable-if-too-simple evidence.** If a stage's tool output is too deterministic/simple, an agent could
  reconstruct it without running the tool. The oracle must bind to genuinely tool-derived content (p13 binds to the
  real `report_timing` path table; a chain must keep that property at every stage).
- **Over-constraining valid workflows.** A trajectory-aware oracle must accept *equivalent* valid orderings and
  not reject a correct-but-different sequence; otherwise it measures conformance to one blessed path, not ability.
- **Brittleness from too much trajectory checking.** Excessive step-by-step assertions make tasks fragile and
  noisy; check outcomes and provenance, not incidental form.
- **Action-budget confounding capability.** Budgets too tight turn capability into `budget_exhausted`; too loose
  removes planning load. Must be *calibrated to measured task depth* and reported.
- **Cost.** Multi-stage real-tool chains cost more per episode and per k-run; design must keep substrates tiny and
  budget-aware.
- **Real-EDA nondeterminism.** Forwarder drops and license/version quirks (observed: transient forwarder drops,
  PT-version path-count quirks) can inject run-to-run noise; the design must isolate evidence binding from volatile
  banner/timestamp lines and re-confirm determinism.

---

## 9. Recommendations before push

- **Move `configs/baseline_models_phase0d.json` outside the repo** (or otherwise ensure it is never committed). It
  is currently untracked and contains only env-var *names* (no secret values), but it should not live in the tree
  at push time.
- **Keep `synthetic-phase0a` local** until this summary is reviewed. **Do not push yet.**
- **Optionally squash / reorganize the chain only after** a publication/release plan is decided — not before; the
  per-rung commits are currently useful as an audit trail.
- **Preserve the invalid probe reports / the golden=0.1 episode as integrity case studies, not capability data.**
  They document how a validation-tooling bug can masquerade as a result and how the fairness gate caught it.
- Continue the standing constraints: `.env` symlink-only and removed after runs; never commit `runs/`; do not
  modify or delete the `synthetic-project-generator` worktree/branch.

---

*Prepared as a phase boundary before opening any new task family or generator. Phase-3C/Phase-4 remains
**design-only** until reviewed.*
