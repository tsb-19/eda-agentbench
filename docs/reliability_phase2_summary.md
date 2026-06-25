# Reliability Phase-2 — Summary

Status: **accepted checkpoint** (commit `caddf53`, branch `feat/benchmark-hardening`, not pushed). This
is the short phase summary; the full numbers live in `reports/reliability_phase2_repaired.md` (clean) and
`reports/reliability_phase2.md` (contaminated integrity case study).

## 1. What was tested

- **Matrix:** 5 tracks × 3 stratified tasks × 5 models × **k=3** = 225 agentic episodes, temperature 0.7,
  `--elicit-confidence`, concurrency 2, seed 42, full commercial tools on b04.
  - Tracks: `p4_spice_sim` (known-floor control), `p5_spice_deck_debug`, `p6_dc_constraint_debug`,
    `p7_spyglass_lint_debug`, `p7_primetime_sta_debug`.
  - Models: Qwen3.7-Max, DeepSeek-V4-Pro, GLM-5.1, Kimi-K2.6, MiniMax-M3.
- **Instrument:** the reliability/calibration layer over the existing P1–P9 battery — pass@1, pass@k
  (any-of-k), pass^k (all-of-k), reliability gap, flip-rate, trust, overconfident-wrong, format
  compliance, and a protocol-failure tally with **infra (429/empty) excluded from capability**.
- **PT contamination + repair:** the original `p7_primetime` run was contaminated by a task-provisioning
  flaw; it was fixed and re-run (PT-only, k=3) and the leaderboard recomputed in two views (clean =
  PT excluded; repaired = fixed PT grafted in). Cost: Phase-2 ¥132.6 + repair ¥3.2 + smoke ¥0.35 ≈ **¥136**,
  zero non-Kimi infra failures.

## 2. Clean conclusions

- **pass@1 alone is insufficient.** It hides large run-to-run differences and conflates models that fail
  in opposite ways.
- **trust / pass^k / flip-rate / protocol failures separate models** that pass@1 ranks similarly
  (e.g. MiniMax vs Kimi tie on pass@1 but fail by flipping vs by giving up).
- **Qwen3.7-Max and DeepSeek-V4-Pro are the reliable top** (repaired trust 1.00 and 0.93; high pass^k,
  low flip, clean protocol).
- **GLM / MiniMax / Kimi fail mostly by protocol, budget, instability, or format**, not by being unable to
  solve: GLM is the most *overconfident* (highest confident-wrong, lowest format compliance); MiniMax is
  the most *inconsistent* (flip 0.67, pass^k 0.27, frequent nocommit); Kimi *burns budget / never commits*
  (highest tool use, budget-exhausted + nocommit). Genuine wrong-answer failures were rare (~5/225);
  the mass of non-passes was protocol.
- **Fixed PT is near-saturated** (pass@1 0.94, pass^k 0.83, flip 0.17 over the 4 measurable models) —
  it behaves like the other clean debug tracks, not like a discriminator.
- **The strongest signal is in unstable tracks (notably P5, gap 0.27 / flip 0.40) and in model-side
  protocol behaviour** (flips, nocommit, budget-exhaustion, format) — not in any single saturated track.
  Abstention was 0.00 for every model: none used the abstain option even when blocked.

## 3. Benchmark integrity conclusion

- The **contaminated p7_primetime result must not be used as a model capability/reliability score.**
- It is nonetheless **valuable as an integrity case study.**
- The cause was **bad task provisioning**: the agent-visible `run_public.tcl` read a *hidden*
  `design_netlist.v`, so the public flow was un-runnable in the agent workspace, which **induced
  hidden-netlist fabrication**.
- **Anti-cheat correctly caught it** (`detect_hidden_shadows` → ANTI-CHEAT → 0.00); the guard was right,
  the task setup was wrong.
- **After repair** (netlist made a visible, read-only input), **Qwen's anti-cheat count went 9/9 → 0/9**
  (and 0 pass → 9/9 pass, mean 1.00), proving the original penalty was a provisioning artifact, not model
  behaviour. A general regression test (`tests/test_agentic_provisioning.py`) now blocks any agent-visible
  runner from referencing a hidden-only artifact, across all tracks.

## 4. Recommended next steps

- **No global k=5.**
- **Optional targeted k=5 later, only for the unstable subset:** MiniMax / Kimi / P5 — where flips and
  pass^k drops are large enough that more trials would sharpen the estimate. The saturated top
  (Qwen/DeepSeek) and saturated tracks (p6, p7_spyglass, fixed PT) do not need it.
- **Kimi should only be re-run when its gateway 429 is stable** — its clean PT was infra-blocked (9/9
  HTTP 429, persistent across a retry), so Kimi's repaired-PT capability is currently unmeasured.
- **Synthetic generator implementation remains paused** until we decide the next phase.

## 5. Open research direction

- **Reliability/calibration is validated** as a real, discriminating measurement layer over the existing
  battery — it surfaces capability-vs-reliability gaps that pass@1 misses.
- **Small single-root-cause EDA tasks are saturated** for frontier agents (the recurring collapse across
  P5–P9, LEC, MCMM, sequential equivalence); fixed PT joining the near-saturated cluster is one more data
  point.
- **The next major direction is synthetic industrial EDA project generation** — mini multi-artifact
  projects with cross-stage failure mechanisms and machine-checkable commercial-tool oracles. It is
  already scoped in the synthetic worktree (`branch synthetic-project-generator`, commit `fec9adc`):
  `docs/synthetic_eda_project_generator_plan.md`, `docs/synthetic_failure_taxonomy.md`,
  `docs/synthetic_phase0_mvp.md`. The provisioning lesson from this phase (agent-visible runners must only
  reference agent-workspace files) is a hard invariant for that generator's Phase-0A golden-project check.
