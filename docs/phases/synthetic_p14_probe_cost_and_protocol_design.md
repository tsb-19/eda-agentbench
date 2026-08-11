# Phase-4F — p14 Probe Cost & Protocol Design (design-only)

Status: design-only. No code, no harness changes, no tasks, no tools, no models, no commit. This document
designs a **cheaper and cleaner p14 probe protocol** to run *before* generating or evaluating p14 v3.

It addresses two problems found in the p14 probes:
1. **Token/cost blow-up** — p14 v1 k=3 ≈ ¥49.71; p14 v2 0003 k=3 projected ≈ ¥51; long trajectories
   reread large public files/reports; MiniMax adds cost for a mostly-known protocol signal.
2. **FINISH/confidence artifact** — some agents score 1.0 but end `budget_exhausted` / empty confidence /
   no clean FINISH, distorting trust/format metrics and getting confused with capability.

## 1. Current evidence

**p14 v1 k=3 probe (workflow_handoff_0002):**
- Saturated for Qwen3.7-Max and DeepSeek-V4-Pro (ordered evidence chain is not a capability wall).
- MiniMax-M3 mostly reliability/protocol signal.
- Cost ≈ **¥49.71**.
- `budget_exhausted` / empty-confidence artifacts already appeared.

**p14 v2 k=1 smoke (workflow_handoff_0003):**
- Qwen solved cleanly (FINISH + confidence=high, protocol ok).
- DeepSeek solved capability (total_score 1.0) **but** no FINISH / `budget_exhausted` artifact.
- MiniMax failed on **malformed-command** protocol collapse (never built a chain).
- Projected k=3 cost ≈ **¥51**, over the ¥30 cap → stopped at k=1.
- **No wrong-authority shortcut passed**; oracle behaved unambiguously.

## 2. Why this matters

- **pass^k requires repeated trials**, so k=1 is not a reliability result — it is a capability smoke read.
- But repeated trials are **too expensive** if per-episode token load stays high (~¥5–6/episode via the
  b04 forwarder, ~20 min each).
- **Protocol-status artifacts must be separated from capability success** — a capability-1.0 episode that
  failed to FINISH is not a capability failure, and must not be scored as one.
- Future p14 v3 probes **should not spend most of the budget re-measuring the already-known MiniMax
  protocol failure**.
- We therefore need **cheaper capability probes first**, and **reliability/protocol probes separately**,
  with different model sets and different k.

## 3. Cost anatomy

Likely cost drivers (per observed trajectories):
- repeated **full-file reads** (agents re-`cat` the same static inputs across turns),
- repeated **netlist / report reads** (large bodies re-pulled),
- large **prompt / task context**,
- long **public outputs** (verbose runner echoes),
- **stage1/stage2 evidence scripts** re-run and re-inspected,
- **agent over-exploration** (DeepSeek's baroque Tcl JSON-parse loop is the canonical case),
- **confidence elicitation after long trajectories** (extra round after budget is nearly gone),
- running **MiniMax in the same expensive k=3 matrix** (cost for known protocol signal),
- **unnecessary reruns of already-validated baseline tasks** (0001/0002).

Per-episode logging that should exist to attribute spend:
- input tokens,
- output tokens,
- tool calls,
- file-read counts (and per-file repeat counts),
- top-N largest observations,
- wall time,
- model cost,
- termination status,
- score,
- protocol status.

## 4. Capability-vs-reliability split

Two separate probe modes, run independently.

**Mode A — frontier capability probe**
- Models: **Qwen3.7-Max, DeepSeek-V4-Pro** (no MiniMax).
- Tasks: the **new candidate task only** (e.g. `workflow_handoff_0004`).
- k=3.
- Goal: determine whether top protocol-compliant agents solve the new hazard.
- Target cost: **under ¥30**.

**Mode B — reliability/protocol probe**
- Models: **MiniMax-M3**, optionally one frontier model as an anchor.
- k=1 or k=2.
- Goal: expose nocommit, malformed command, partial-chain, wrong-authority, no-FINISH.
- Target cost: **lower cap, run separately** from Mode A.

Rationale: Mode A buys the expensive repeated-trial signal only where it is informative (the frontier);
Mode B buys the cheap, already-largely-known protocol signal at low k. Splitting them stops the known
MiniMax failure from consuming the capability budget.

## 5. Cheaper task-context design

Reduce token cost **without leaking answers**:
- shorter prompt with a clear **artifact inventory** (what each file is, not what to change),
- **compact authority-hierarchy statement** (spec/manifest are authority — already public, legitimate),
- avoid embedding **long reports** directly in public output,
- **verdict-first runner** only (the public runner prints the verdict line, not a full dump),
- **report-digest summaries** instead of full report dumps,
- a small **public diagnosis summary** that says "conflict detected" but **not** the fix,
- avoid **large netlist reads** unless necessary,
- provide a **file map / purpose table** so the agent need not read every file to learn its role,
- make spec/manifest **concise but authoritative**,
- ensure public evidence is **sufficient for diagnosis by cross-checking** (so the agent doesn't have to
  brute-force-read everything).

**Must NOT be done:**
- do not reveal the exact fix,
- do not reveal hidden truth (`handoff_truth.json` stays hidden),
- do not leak the authority target beyond what public spec/manifest already legitimately says,
- do not weaken the oracle.

## 6. Observation trimming / caching idea (not implemented yet)

Possible **harness-side** improvements — designed here, deferred to a later gated phase:
- cap repeated **identical file observations** (Nth identical read returns a short "unchanged" notice),
- **summarize repeated read-only files** after the first read,
- add a **per-file observation budget**,
- expose a **cached digest/summary** for frozen files,
- store **large reports as files** rather than dumping them to stdout,
- make the **public runner output concise and verdict-first**.

Risks to weigh before any implementation:
- summaries might **leak the fix** (a digest of the right answer is a leak),
- summaries might **hide useful clues** the agent legitimately needs,
- changing observations **affects comparability** with earlier probes (0001/0002/0003 baselines),
- needs **careful regression tests** (oracle unchanged, dispatch unchanged, no leak).

## 7. FINISH/confidence cleanup design

Candidate fixes:

**A. Post-score finalization prompt** — after task score reaches a terminal state, ask the model only for
FINISH + confidence.
- Risk: introduces a nonstandard second phase; must not re-open the task or grant extra solving ability.

**B. Separate protocol-status from task-score** — keep the task score from the oracle, record
FINISH/confidence on a **separate channel**, and **do not** mark a capability failure when total_score=1.0
but FINISH is missing. Trust metrics consume the protocol channel only.
- Risk: low; this is bookkeeping, not scoring. Preserves comparability.

**C. Reserve action budget for finalization** — stop tool-use at `max_tool_calls - N` and force a final
response.
- Risk: may prematurely stop valid work (would have cut DeepSeek's real exploration short).

**D. Simpler confidence elicitation** — accept explicit confidence in the final message; default to
`missing_confidence` if absent; never block the task score.
- Risk: low.

**Recommended safest minimal approach: B + D.** Separate protocol-status from task-score (B) and make
confidence best-effort with a `missing_confidence` default (D). Both are **pure reporting/bookkeeping
changes** — they do not alter the oracle, do not add a second solving phase, and do not risk truncating
valid work. Defer A and C (they change agent dynamics) unless B+D prove insufficient.

## 8. Metrics contract

Reporting fields for future p14 probes:
- `total_score`
- `capability_pass`
- `protocol_clean`
- `finish_status`
- `confidence_status`
- `evidence_chain_completed`
- `authority_recovery_completed`
- `wrong_authority_attempted`
- `stale_evidence_reuse`
- `hand_edit_attempt`
- `forbidden_edit`
- `no_commit`
- `malformed_command`
- `budget_exhausted`
- `input_tokens`
- `output_tokens`
- `cost`

Rules:
- **pass@1 / pass@k / pass^k are based on `capability_pass`** unless explicitly reporting `protocol_pass^k`.
- **Trust score is reported separately** for capability and protocol.
- **overconfident-wrong requires BOTH** a wrong score **and** a usable (non-empty, parseable) confidence —
  an empty-confidence episode is `missing_confidence`, not overconfident-wrong.

## 9. Proposed p14 v3 probe protocol

The intended probe **after** the p14 v3 task exists:
- Task: `workflow_handoff_0004` only.
- Models: **Qwen3.7-Max, DeepSeek-V4-Pro** (Mode A).
- k=3.
- `max_tool_calls`: **60**, unless v3 validation shows higher is required.
- Cap: **target ¥30**.
- MiniMax: run **separately** (Mode B) only if we want the reliability/protocol signal.

Stop rules (any one → stop and report):
- cost projection exceeds the cap,
- oracle ambiguity,
- a wrong-authority shortcut passes,
- a harness/provisioning bug appears.

## 10. Required implementation tests for any future cleanup

If a harness or protocol cleanup is later implemented (a separate gated phase), tests must ensure:
- oracle score **unchanged** (golden 1.0; every shortcut below pass; deterministic),
- p13/p14 evaluator **dispatch unchanged** (parity in cli.py and runner.py),
- **no hidden leak** (hidden/ not exposed),
- **no answer leak** (no fix or truth surfaced in public artifacts/summaries),
- **public verdict remains first** in runner output,
- repeated-file-observation cache **does not change task files** (read-only),
- protocol-status separation **does not alter scoring** (total_score identical pre/post),
- **old reports remain interpretable** (field names additive, not breaking).

## 11. Recommendation

- **Do not complete 0003 k=3 now** (probable saturation; over cap; artifact-contaminated).
- **Do not modify the harness yet in this phase** — this is design-only.
- **Use this document as the design basis** for the cheaper/cleaner probe protocol.
- **Next implementation should be the p14 v3 scenario/corner cross-source-conflict task**, designed with
  the cheaper-probe protocol (Mode A capability probe, verdict-first runner, concise context) in mind.
- **Only implement harness cleanup (Section 6/7) if** v3 probe cost or the FINISH artifact again blocks
  interpretation. Prefer the bookkeeping-only B+D split before any observation-trimming change.

## 12. Open questions

- Should `capability_pass` and `protocol_clean` be two **separate pass^k metrics**?
- Should MiniMax be **removed from frontier capability probes** entirely (kept only for Mode B)?
- How much **public-artifact summarization is fair** before it leaks the fix?
- Should confidence elicitation be **post-score** (A) or only **best-effort** (D)?
- Can we reduce **file-read cost** without giving models extra information?
- Should the p14 v3 prompt include an explicit **artifact purpose table**?
- What **target max token budget per episode** is realistic (to land k=3 under ¥30)?
