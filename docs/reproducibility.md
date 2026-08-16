**English | [中文](reproducibility.zh.md)**

# Reproducibility

Two things can be reproduced here, and it matters which one you mean:

1. **The paper's numbers** — every table, exact interval, sensitivity band and *p*-value.
   Reproducible right now, with no commercial tool, no network and no model call. Do this first.
2. **The paid episodes that produced those records** — not reproducible from this repository. The
   experimental program is permanently closed at the frozen experiment HEAD, and re-running would
   need PrimeTime, HSPICE and paid API access. See [`provenance.md`](provenance.md).

What *is* reproducible is the whole chain from the preserved per-episode records to the typeset
table. No number in `submission/main.tex` is transcribed by hand: `main.tex` `\input`s what the
scripts below emit.

## Reproduce the paper (tool-free)

```bash
pip install -e ".[test]"

# 1. the repository is internally consistent
scripts/check
#    [1] pytest, tool-free subset      [2] task structure, 84/84
#    [3] frozen membership: all 1065 path->sha256 pins re-hashed against the baseline

# 2. the derived tables recompute from the frozen records
python3 scripts/phase7c_study1_ledger.py    --check   # Study I ledger: 21 cells, 58 + 12 = 70 episodes
python3 scripts/phase7c_claim_statistics.py --check   # 12.5 / [-12.5, 41.7] / -16.7; Fisher .4/.4/1.0

# 3. no documentation points at anything that no longer exists
python3 scripts/slim_link_check.py

# 4. the manuscript builds, byte for byte
cd submission && make distclean && make               # 15 pp, 268 459 bytes
```

`--check` recomputes from `reports/evidence/` and diffs against the committed JSON, exiting
non-zero on any drift. Drop `--check` to rewrite the outputs.

`make clean` deliberately keeps `main.pdf`, so plain `make` after `clean` is a no-op. Use
`distclean` before any build whose log you intend to measure — a v9 page-count measurement was once
taken off a stale PDF for exactly that reason. The PDF is byte-reproducible because
`SOURCE_DATE_EPOCH` is pinned in the Makefile; its sha256 is in `submission/FREEZE_HASHES.md`.

### Which script writes which table

| Script | Reads | Writes |
|---|---|---|
| `scripts/phase7c_study1_ledger.py` | `reports/evidence/p14_phase4*_episodes/<trial>/{flow_config.submitted.json,result.json,agentlog.sanitized.json}`, the frozen program manifest | `reports/synthetic_p14_study1_ledger.json` → `submission/tables/study1_ledger.tex` |
| `scripts/phase7c_claim_statistics.py` | that ledger, `synthetic_phase7a_sta72_report.json`, `synthetic_phase5d_collection_report.json`, `reports/evidence/` | `reports/synthetic_p14_claim_statistics.json` → `submission/tables/{claim_stats,sta_pilot}.tex` |
| `scripts/phase4z_figures_tables.py` | the controlled-pair matrix and the preserved episode ledgers | `reports/synthetic_p14_phase4z_figures_tables.md` |

Both `phase7c_*` scripts assert each stage's episode count against the frozen program manifest and
abort on mismatch. That check exists because an earlier aggregation of these same records keyed
cells by `(condition, model)` in a dictionary and silently dropped repeat measurements of a
condition — collapsing 70 episodes to 54. A stated inclusion rule does not prevent that; an
assertion in the code does.

## Deterministic task generation

Each family is produced by a seeded generator, and each task's `metadata.json` records the
generator, seed and parameters that produced it.

| Family | Generator | Notes |
|---|---|---|
| p14 workflow | `generators/p14_workflow_handoff_gen.py` (driver: `scripts/generate_workflow_handoff_tasks.py`) | reads its asset substrate from `tasks/p13_trajectory_handoff/traj_handoff_0001/` |
| p15 STA (Family A) | `generators/p15_sta_handoff_gen.py` (12-instance panel: `scripts/phase7a_generate_sta12.py`) | substrate in `generators/p15_sta_handoff/substrate/` |
| p16 SPICE (Family B) | `generators/p16_spice_handoff_gen.py` | grader and plausibility spec in `generators/p16_spice_handoff/` |

Admission is gated, not merely seeded. Before an instance is accepted:

- **uniqueness** — exhaustive enumeration over the declared domains must yield exactly one
  assignment satisfying the instance's constraints (294 → 1 for the worked instance). "Correct" is
  fixed by the constraint system, not by grader judgement.
- **hard feasibility** — the bake must produce a wrong-binding artifact that the tool accepts,
  executes, and signs off plausibly, that is nonetheless semantically wrong and *is* rejected by
  the typed oracle. If the wrong binding is trivially tool-red or unparsable, the instance is
  ineligible and regenerated.

Two generators were edited after their pre-run freeze; `frozen_membership_verify.py` reports those
2 mismatches, and the paper's numbers derive from the pinned versions. This is stated in
[`provenance.md`](provenance.md) rather than erased.

## Grading a family instance (needs the real tool)

Semantic correctness is decided by the typed provenance/authority oracle, never by tool exit
status — so grading needs the tool to run *and* the oracle to reject a green run. PrimeTime for
p14/p15, HSPICE for p16.

```bash
eda-bench detect-tools

# golden must score 1.00
eda-bench evaluate-task tasks/p14_workflow_handoff/workflow_handoff_0009 \
    --submission tasks/p14_workflow_handoff/workflow_handoff_0009/solution

# the shipped (mis-bound) visible files must score < 1.00 while the tool stays green
eda-bench evaluate-task tasks/p14_workflow_handoff/workflow_handoff_0009 \
    --submission tasks/p14_workflow_handoff/workflow_handoff_0009/files
```

The golden-versus-buggy pair is the fairness gate: grade the known-correct solution through the
same path first. If it does not score ~1.00, the grader or the environment is distorting the
measurement, and no model score from that path can be trusted.

`scripts/validate_dataset.py` automates that gate across a family, with a content-hash cache so
`--changed` re-grades only what moved while still reporting the cached verdict of everything else:

```bash
python3 scripts/validate_dataset.py --structural --tasks-root tasks          # tool-free
python3 scripts/validate_dataset.py --tasks-root tasks/p15_sta_handoff \
    --glob 'p15_eval_*' --concurrency 4                                       # real PrimeTime
```

## Reproducibility of the *measurement*, not just the score

The paper's second axis is that a number can be wrong for reasons that have nothing to do with the
model. The controls that make an episode's measurement trustworthy are part of the reproducible
path, and each has a test:

| Control | Script | Test |
|---|---|---|
| exact-commit isolated worktree; canonical hash verified before and after every episode | `canonical_integrity.py`, `chain_executor.py`, `run_chain_guarded.py` | `test_canonical_integrity.py`, `test_chain_executor.py`, and the tripwire in `test_fullpath_check.py` |
| terminal-valid versus recovered episode arbitration | `episode_arbiter.py` | `test_episode_arbiter.py`, `test_transport_telemetry.py` |
| SSE streaming (a non-streaming transport censors long-reasoning models mid-generation) | `eda_agentbench/llm/openai_provider.py`, `llm_agent_driver.py` | `test_llm_streaming.py`, `test_llm_driver_{timeout,deadline}.py` |
| tool-health sentinel with run bookends | `pt_health_sentinel.py`, `hspice_health_sentinel.py` | `test_pt_health_sentinel.py` |
| infrastructure-only retry (a valid wrong score is a hard failure and is never retried) | `fairness_retry.py`, `measurement_control.py` | `test_fairness_retry.py`, `test_measurement_control.py` |
| position-balanced blocked randomization, frozen before any paid call | `phase4w_randomize.py`, `phase5b_schedules.py`, `phase7a_sta72_schedule.py` | the schedules are committed artifacts |

An infrastructure timeout, gateway error or worker failure is **measurement-invalid** and is never
counted as a capability failure. The converse also holds and matters more: a *valid* wrong score is
a real result and may not be retried away.

## Environment

- Python ≥ 3.10; the installed package is dependency-free. `pip install -e ".[test]"` adds pytest.
- Commercial Synopsys tools for the family graders; nothing else substitutes. Probes look under
  `/EDA/soft2/synopsys/` and `/EDA/soft2/cadence/`; set `EDA_TOOL_ROOT` to replace the leading
  `/EDA`. See [`commercial_tool_policy.md`](commercial_tool_policy.md).
- Model access is needed only to run *new* episodes, which the freeze forbids. Driver controls are
  documented in [`agentic_runner.md`](agentic_runner.md).
- `runs/` and `workspaces/` are local output and are never committed.
