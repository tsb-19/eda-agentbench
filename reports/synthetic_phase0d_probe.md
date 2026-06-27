# Phase-0D probe — synthetic constraint-drift family (p10_synthetic_project)

**What this is.** A cheap *falsification* probe (not a benchmark) asking: does the generated
constraint-drift family already saturate for frontier agents, or does it expose any
reliability / protocol / over-constraint-masking signal? Scope: tasks `syn_proj_0002..0006`,
3 models (Qwen3.7-Max, DeepSeek-V4-Pro, MiniMax-M3), k=3 trials, temperature 0.7,
`--elicit-confidence`, concurrency 2, agentic path on real PrimeTime via the b04 forwarder.
45 episodes total. Cost **¥7.62** (trial1 ¥2.26 + trial2 ¥2.73 + trial3 ¥2.63), tokens
725,046 in / 62,648 out. Probe commit: `821b954` (fix) on branch `synthetic-phase0a`.

> Reading guide: **Section A** documents two harness bugs that made earlier Phase-0D attempts
> invalid as difficulty measurements — they are kept only as provisioning/feedback case
> studies. **Section B** is the only valid measurement, produced after both bugs were fixed,
> validated, and committed.

---

## A. Invalid pre-fix attempts (provisioning / feedback case studies — NOT difficulty evidence)

Two independent harness bugs, both in the **agentic path only** (the submission/CLI path that
`validate_dataset` uses was always correct, which is why golden=1.0 / mutant=0.1 held there).
Each, on its own, forces a 0.10 floor on every p10 agentic episode regardless of the agent's
actual work. **No 0.10 from any pre-fix attempt may be read as task difficulty.**

### A1. PUBLIC_SIGNOFF feedback truncation
`run_public` emitted the PrimeTime license banner and a `report_timing -nworst 10` dump
*before* the verdict, pushing `PUBLIC_SIGNOFF` to ~byte 7018 of a 7838-byte output — beyond the
agent's `--max-obs-bytes 4000` observation cap. Agents were structurally **blind** to whether
sign-off passed or failed; the public feedback channel returned only banner text.
- Fix: `run_public.tcl` computes the verdict with `get_timing_paths -nworst 1` first;
  `run_public.sh` hoists `PUBLIC_SIGNOFF` / `PUBLIC_HINT` to the top of stdout (verified at
  **offset 0** on real PT). The full dump (now `-nworst 1`) follows. No hidden-oracle markers on
  the public channel.

### A2. Agentic evaluator misdispatch (the decisive one)
`eda_agentbench/agentic/runner.py::_select_evaluator` had **no branch** for
`synthetic_project.SyntheticProjectEvaluator`, so every p10 agentic episode fell through to the
`VCSRTLEvaluator` default. That evaluator does not know the `constraint_spec` / `signoff`
components → returned **"Unknown component"** with `raw 0.0` → **0.10 floor on every p10 agentic
episode**, independent of the agent's edit. This is exactly the `objective_score 0.0`,
`"Unknown component: constraint_spec"` signature found in the persisted pre-fix score.json.
- Fix: add the missing branch, mirroring `cli.py`. Scoring semantics and
  `SyntheticProjectEvaluator` unchanged. Regression tests pin dispatch parity + agentic-path
  grading (correct→1.0, masking→partial).

### Calibration warning only (not a difficulty result)
In the pre-fix A1 state, agents acted while **blind to the verdict**. Any high-confidence
"FINISH" emitted under those conditions reflects acting-without-feedback, **not** a genuine
overconfident-wrong calibration failure on a solvable task. We therefore record it as a
*blind-feedback calibration warning* and exclude it from the clean calibration numbers in
Section B. (In the clean post-fix probe, overconfident-wrong = 0 across all models.)

---

## B. Clean post-fix probe (the only valid measurement)

Post-fix, validated (65 p10 tests; `scripts/check` 2898/2898; `validate_dataset` golden=1.000 /
margin=0.900, syn_proj_0004 C3 confirmed a transient forwarder drop via 5× re-grade = stable
1.0), committed `821b954`, then re-run from scratch (fresh trial1/2/3; invalid runs archived).

### B1. Reliability / calibration leaderboard (k=3)

| model | pass@1 | pass@k | pass^k | gap | flip | overconf-wrong | fmt | trust | tok | tools | wall_s | protocol |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3.7-Max     | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 0 | 1.00 | 1.00 | 12.0k | 4.6 | 51.2 | ok:15 |
| DeepSeek-V4-Pro | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 0 | 1.00 | 1.00 | 16.5k | 4.7 | 73.6 | ok:15 |
| MiniMax-M3      | 0.20 | 0.60 | 0.00 | 0.20 | 0.60 | 0 | 0.20 | 0.04 | 24.0k | 7.3 | 36.8 | nocommit:12 / ok:3 |

- **pass@1 / pass@k(any-of-3) / pass^k(all-of-3):** Qwen & DeepSeek 1.00/1.00/1.00.
  MiniMax 0.20 / 0.60 / 0.00.
- **reliability gap (pass@1 − pass^k):** 0.00 for Qwen & DeepSeek; **0.20** for MiniMax.
- **flip rate:** 0.00 / 0.00 / **0.60** (MiniMax flips pass↔fail on 3 of 5 tasks across trials).
- **overconfident-wrong count:** **0** for all three models.
- **format compliance:** 1.00 / 1.00 / **0.20** (MiniMax emits a malformed tool call 12/15).
- **trust score:** 1.00 / 1.00 / **0.04**.
- **abstention:** no explicit ABSTAIN declarations from any model; MiniMax's failures are
  *silent* protocol failures (no committed edit), not declared abstentions.
- **protocol failures:** MiniMax **12/15 `nocommit`**; Qwen & DeepSeek **0**.
- **masking / over-constraint attempts:** **none detected.** Zero committed-but-failed episodes,
  zero `SIGNOFF_FAIL`-with-spec-drift, zero partial-credit constraint_spec. The over-constraint
  oracle was never exercised because the only failures were non-submissions.
- **cost:** ¥7.62 total; per-trial ¥2.26 / ¥2.73 / ¥2.63.

### B2. Per-task success matrix (P=pass, .=fail; trials t1 t2 t3)

| task | Qwen | DeepSeek | MiniMax |
|---|---|---|---|
| syn_proj_0002 | PPP (3/3) | PPP (3/3) | ... (0/3) |
| syn_proj_0003 | PPP (3/3) | PPP (3/3) | .P. (1/3) |
| syn_proj_0004 | PPP (3/3) | PPP (3/3) | P.. (1/3) |
| syn_proj_0005 | PPP (3/3) | PPP (3/3) | .P. (1/3) |
| syn_proj_0006 | PPP (3/3) | PPP (3/3) | ... (0/3) |

All three drift types (output_delay / input_delay / uncertainty) are covered across 0002–0006;
Qwen and DeepSeek solve every drift type on every trial.

### B3. Qualitative failure signatures
- **Qwen3.7-Max, DeepSeek-V4-Pro:** clean. Read spec + SDC, computed the budget arithmetic
  (e.g. T=3.0, uncertainty=0.15, input=t_co+flight, output=t_su+flight), edited
  `constraints.sdc`, ran public feedback, FINISH with `CONFIDENCE: HIGH`. Always correct →
  high-confidence-correct.
- **MiniMax-M3:** **tool-call protocol defect, not a capability or difficulty failure.**
  In 11 of 12 failing episodes it appended a literal stop-token artifact `]<]minimax[>[` to
  every shell command, so each command errored (`/bin/sh: cannot open ]minimax[`) and it never
  produced a clean edit (`finished:False`, `edited:[]`, `nocommit`). The 3 episodes where it
  emitted a clean command **scored 1.0** — i.e. when MiniMax commits, its constraint-drift
  capability is intact. The failure is intermittent (flips across trials), which is the
  reliability signal itself.

---

## Interpretation (against the pre-registered rules)

- **Capability for this family is saturated for the well-formed frontier agents.** Qwen and
  DeepSeek solve constraint-drift perfectly and consistently (pass^k=1.0, trust=1.0, zero
  variance). Consistent with the standing finding that single-localization / budget-arithmetic
  tasks are frontier-easy — a model that reads spec.md and recomputes the budget solves it in
  one step. Constraint-drift on a tiny project gives **no difficulty signal** for capable,
  protocol-compliant agents.
- **The discrimination this probe produced is purely reliability/protocol, not difficulty.**
  MiniMax separates sharply (trust 0.04 vs 1.00) entirely via tool-call format reliability
  (`nocommit:12`, flip 0.60, fmt 0.20), with **no capability gap** (1.0 whenever it commits) and
  **no overconfident-wrong** episodes. This matches the reliability-layer thesis: among models
  that *can* do EDA tasks, the differentiator is whether they do them reliably — and it confirms
  the prior pilot's MiniMax/Kimi low-trust observation, now on a real-tool agentic family.
- **The most valuable potential failure mode (PT-green-but-SPEC-fail / masking) did not occur.**
  The over-constraint oracle was never exercised because no model committed a masking edit.
  That is a null result for the masking mechanism in this probe, not evidence it is weak — the
  oracle and its resistance are proven by `validate_dataset` (masking→0.4) and the tool-free
  masking tests, just not by live agents here.

### Recommendation
Constraint-drift is **saturated as a difficulty mechanism** for protocol-compliant frontier
agents — do not invest further in making it "harder" by hiding values. Its remaining value is
(a) as a clean, real-tool substrate for the **reliability/calibration layer** (it already
discriminates models by trust), and (b) as a control in a larger battery. For new *difficulty*,
move to the next mechanism (e.g. FlowHandoff drift / multi-artifact cross-checking) rather than
elaborating this one. MiniMax's protocol fragility is a harness-interaction finding worth noting
but is a model property, not a task property.
