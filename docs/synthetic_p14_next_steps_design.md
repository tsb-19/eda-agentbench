# Phase-4E — Next Steps After the p14 v2 Workflow-Hazard Smoke Probe (design-only)

Status: design-only. No code, no tasks, no tools, no models, no commit. This document decides what to do
*after* the `workflow_handoff_0003` k=1 smoke probe, and recommends a concrete next direction.

## 1. Current state

- Current HEAD: `4a31fb3` (`docs: report p14 v2 workflow hazard smoke probe`).
- Latest tag: `synthetic-p14-v2-smoke-checkpoint-4a31fb3` (object `e5883db`), bundle backed up out-of-repo.
- p14 has three generated tasks:
  - `workflow_handoff_0001`: evidence_steps=1 baseline (p13-style single-stage reproduction).
  - `workflow_handoff_0002`: evidence_steps=2 ordered chain (stage2 binds stage1 via `upstream_evidence_digest`).
  - `workflow_handoff_0003`: cross-source conflict / authority diagnosis (lying v2-claiming manifest + stale v1 decoy).
- p14 v1 k=3 tiny probe: Qwen3.7-Max and DeepSeek-V4-Pro **saturated** on 0002 (ordered chain not a wall).
- p14 v2 0003 k=1 smoke: Qwen and DeepSeek each solved 0003 **once** with authority-consistent recovery;
  MiniMax-M3 failed on **protocol** (malformed-command collapse), not authority diagnosis.
- 0003 k=3 was **stopped** before launch of trials 2–3: trial1 = ¥17.02, projected k=3 ≈ ¥51, k=2 ≈ ¥34,
  both over the approved ¥30 cap.

## 2. What we know

- The p14 generator substrate is **validated** (golden 1.0; deterministic nonces; dispatch parity intact).
- Ordered evidence-chain alone (0002) is **insufficient** to challenge Qwen/DeepSeek.
- A single cross-source conflict (0003) is **also not an obvious frontier capability wall** — both top
  agents recovered correctly in one trial.
- MiniMax remains a **reliability/protocol signal**, not a capability signal, on these tracks.
- The p14 oracle is **useful and tight**: on real PT, no wrong-authority, stale, hand-edited (semantic),
  wrong-package, partial-chain, or trust-decoy shortcut passed; only the authority-consistent fresh chain
  scored at the pass gate.
- The main current bottlenecks are:
  - **task difficulty** (the frontier solves single-hazard authority recovery),
  - **token cost** (~¥17 for 3 episodes via the b04 forwarder; each episode ~20 min, ~¥5–6),
  - **FINISH / confidence / budget_exhausted artifacts** (passing episodes that never emit clean FINISH).

## 3. What we do not know

- We do not know **pass^k** for `workflow_handoff_0003` (k=1 only).
- We do not know the **flip rate** or repeated-run reliability for 0003.
- We do not know whether Qwen/DeepSeek would **fail under a stronger** cross-source conflict (e.g.
  scenario/corner provenance, multiple partial-truth decoys).
- We do not know whether **k=3 on 0003 is worth the cost** without first reducing token use.
- We do not know whether the **FINISH/confidence artifact will distort trust metrics** on longer tasks
  (it already produced `budget_exhausted` + empty confidence on a capability-1.0 DeepSeek episode).

## 4. Option A — finish k=3 on workflow_handoff_0003

**Pros**
- Clean pass^k / flip-rate / trust for 0003.
- Direct, apples-to-apples comparison with the earlier p14 v1 k=3 probe.

**Cons**
- Projected cost ≈ ¥51 (over the ¥30 cap).
- Likely Qwen/DeepSeek saturation, based on the k=1 read — pass^k probably ≈ 1.0 for both.
- Still affected by the FINISH/confidence artifact, which would muddy the trust signal.
- Unlikely to change the research direction (we would learn "saturated, with protocol noise").

**Recommendation: not first.** Paying ¥51 to most-likely confirm saturation — while the confidence
artifact still contaminates the only genuinely new (reliability) signal — is poor value. Do this only
after cost reduction and the FINISH/confidence cleanup, and only if the question truly needs repeated-run
reliability rather than capability.

## 5. Option B — cheaper probe protocol

Ways to reduce cost:
- Run only **Qwen + DeepSeek** first (drop MiniMax when the question is frontier *capability*).
- Omit MiniMax entirely if the question is capability (it is a reliability-only signal here).
- Lower k for expensive reliability-only models; keep k high only where variance matters.
- Pre-trim public files / reduce redundant report dumps the agent re-`cat`s.
- Add a **compact task-context mode** (smaller prompt, fewer verbose tool echoes).
- Cache common read-only file summaries so the agent need not re-read static inputs.
- **Separate** the capability probe from the reliability/protocol probe (different model sets, different k).
- Stop reading full netlists/reports once digest evidence is sufficient (the digest, not the body, is
  load-bearing).
- Summarize the authority hierarchy in the prompt **without leaking the fix** (state "manifest is
  authority", not "set netlist to v2").
- Add **per-episode token-cost diagnostics** so we can attribute spend (read-loops vs. tool retries vs.
  verification overrun — DeepSeek's overrun was exactly this).

**Cheaper future probe (defined):**
- Task: `workflow_handoff_0003`.
- Models: **Qwen + DeepSeek only**.
- k=3.
- Cap target: **under ¥30** (Qwen+DeepSeek k=3 ≈ 2 models × 3 × ~¥5.5 ≈ ¥33 at today's cost → needs the
  cost-reduction items above, or a small cap bump, to land under ¥30).
- MiniMax: optional later, **reliability-only**, possibly at lower k.

## 6. Option C — FINISH/confidence harness fix

The repeated artifact:
- Passing episodes score capability 1.0 but fail to emit a clean FINISH + confidence (tagged
  `budget_exhausted`, empty confidence). DeepSeek's 0003 episode is the canonical case.
- This distorts trust/format metrics: a correct solve is recorded as a protocol/reliability failure.

Design constraints for any fix:
- **Do not change scoring semantics** — task score must stay exactly as is.
- Add a cleaner separation between four distinct things currently entangled:
  - task score,
  - protocol finish (did the agent signal completion?),
  - confidence elicitation (did it declare confidence?),
  - action-budget termination (did it hit the action/wall limit?).
- Consider a **post-score confidence prompt** or an explicit finalization step that runs even when the
  action budget is nearly spent, so a correct-but-verbose agent can still finalize.
- Ensure any such step **does not leak answers** or grant extra solving ability (it must only ask the
  agent to commit + state confidence, not re-open the task).

**Recommendation:** this should happen **before** any k=5 or larger probe. At k=1 the artifact is a
footnote; at k=5 it would dominate the trust/flip metrics and make them uninterpretable. It is a
prerequisite for trustworthy reliability numbers.

## 7. Option D — stronger p14 v3 hazard design

Stronger hazards beyond the single-conflict 0003:
- **Multiple decoys with partial truth** — each lower source is right about one field and wrong about
  another, so no single "trust the most detailed file" heuristic works.
- **Scenario/corner conflict** — the netlist/clock are right but the provenance corner/scenario is wrong.
- **Report A matches manifest but wrong corner**; **report B matches corner but wrong netlist** — the
  agent must cross-check two reports, not trust either alone.
- **Evidence manifest fresh but from the wrong scenario** — freshness ≠ authority-consistency.
- **Two-stage chain where the upstream digest is syntactically valid but semantically the wrong
  authority** — the digest binds, but to a package the manifest does not endorse.
- **Public log that is recent but non-authoritative** — recency is a distractor, not a signal.
- **Partial conflict across spec / manifest / config / report / evidence** — the conflict is spread, so
  the agent must reconcile the whole hierarchy, not flip one field.
- **Dependency-repair planning** — one already-present stage is invalid and must be *invalidated and
  rerun*, not merely appended to.
- **Tool-output drift** — two reports disagree and the agent must cross-check to find which is
  authority-consistent.

**Key principle:** difficulty must come from **authority diagnosis and recovery planning**, not from
bumping `evidence_steps` to 3. A longer chain is more tokens, not more reasoning.

## 8. Recommended next step

**Do a design + cost-reduction pass first, not another expensive probe.**

Recommended sequence:
1. Write this Phase-4E design (this document).
2. Implement a small FINISH/confidence artifact fix or probe-protocol cleanup — **only if needed**, and
   without changing scoring semantics (Option C).
3. Design a stronger p14 v3 hazard preset (Option D).
4. Generate exactly **one** p14 v3 task.
5. Validate its acceptance matrix on real PT (golden 1.0; every shortcut below pass; deterministic).
6. Then run a **cheaper Qwen + DeepSeek k=3 capability probe** (Option B), targeting under the cap.
7. Run MiniMax **separately**, reliability/protocol only, possibly at lower k.

## 9. GO / NO-GO for another 0003 probe

**GO** only if:
- an explicit higher cap is approved, **or**
- the cheaper protocol (Option B) gets expected total under the cap, **and**
- FINISH/confidence handling is acceptable (Option C done or judged non-distorting), **and**
- no harness/provisioning bugs are present, **and**
- the research question requires repeated-run **reliability** rather than only capability.

**NO-GO** if:
- expected cost exceeds the cap,
- the likely result will not change design direction (probable saturation),
- confidence artifacts remain the main measured signal,
- per-episode token-cost diagnostics are unavailable.

## 10. GO / NO-GO for p14 v3 design

**GO** if:
- v3 introduces at least one **new hazard dimension** beyond 0003,
- wrong-authority and stale-but-plausible evidence shortcuts fail,
- there is **exactly one** authority-consistent recovery,
- no ambiguity,
- cost remains manageable,
- the acceptance matrix is deterministic.

**NO-GO** if:
- v3 just adds `evidence_steps=3`,
- the public prompt reveals authority too clearly,
- multiple valid recoveries exist,
- the hidden oracle is too brittle,
- the PT substrate is too tiny to support the intended semantic distinction.

## 11. Concrete proposed p14 v3 first hazard

**Preferred candidate: scenario/corner cross-source conflict.**

The netlist and clock are *correct*; the bug is in **provenance** — the evidence was generated under the
wrong scenario/corner, and a downstream artifact lies about it.

Setup:
- spec/manifest authority says **slow / func / netlist_v2 / clk_main**.
- `flow_config.json` selects `netlist_v2` correctly.
- `constraints.sdc` uses `clk_main` correctly.
- stage1 `timing_report.rpt` is **fresh but generated under typ/test (the wrong corner)**.
- `evidence_manifest.json` **claims** slow/func.
- `stage2_summary.json` `upstream_evidence_digest` is **syntactically valid but semantically tied to the
  wrong corner** (it binds the wrong-corner stage1 report).
- The agent must detect that **netlist/clock are right but scenario/corner provenance is wrong**, and
  recover by **rerunning the correct stage(s) under slow/func** — not by editing netlist/clock.

Acceptance filters:
- green PT under the **wrong corner** → fails.
- evidence generated from the **wrong corner** → fails.
- **editing the manifest down** to typ/test (changing authority to match the bad evidence) → fails.
- **rerun under slow/func** (authority-consistent) → passes.

Why this is harder than 0003: the obvious "fix the netlist/clock to match authority" move is a no-op here
(they are already correct), so the agent cannot shortcut on the most salient field. It must reason about
**corner/scenario provenance**, which is less visually obvious and forces a genuine rerun-planning step.

## 12. Final recommendation

- **Do not run more 0003 trials right now.** Probable saturation; poor value at ¥51; confidence artifact
  would dominate the only new signal.
- **Do not scale the generator yet.** One strong v3 task first, validated, before any breadth.
- **Do write this next-steps design** (done).
- **Likely next implementation: p14 v3 scenario/corner cross-source conflict**, after a small
  cost/protocol cleanup (Option B probe-protocol + Option C FINISH/confidence separation, only as needed).

Net: design + cost/protocol cleanup → one validated p14 v3 task → cheaper Qwen+DeepSeek k=3 capability
probe → MiniMax reliability separately. No expensive repeat of 0003 until a cap bump or cheaper protocol
makes it worthwhile.
