# Reproducibility

## Overview

Every task in EDA-AgentBench is designed to be reproducible. This document describes the mechanisms that ensure deterministic task generation, consistent evaluation, and verifiable results.

## Deterministic Task Generation

### Generators

P1 and P4 tasks are produced by generator scripts:

- `scripts/generate_p1_tasks.py` — generates P1 RTL Debug tasks
- `scripts/generate_p4_spice_tasks.py` — generates P4 SPICE Sim tasks

Both generators accept a `--seed` parameter for deterministic output:

```bash
python scripts/generate_p1_tasks.py --count 100 --seed 42
python scripts/generate_p4_spice_tasks.py --count 10 --seed 42
```

Given the same seed, generators produce identical tasks. Each task's `metadata.json` records the generator script, seed, and parameters used:

```json
{
  "generator": {
    "script": "p1_rtl_debug_gen.py",
    "seed": 42,
    "config_index": 0,
    "bug_type": "sensitivity_list"
  }
}
```

### P5 Import

P5 tasks are imported from an external bundle via `scripts/import_p5_tasks.py`. The import is a read-only copy from the sibling repository `../eda-bench-prototypes/tasks_eval_private/`. The main repository does not modify the external bundle.

## Evaluation Modes

Each task supports two submission modes for validation and calibration:

### Solution Mode

The task's `solution/` directory is used as the agent's submission. This verifies that the correct answer always produces a perfect score:

```
eda-bench evaluate-dataset tasks --submission-mode solution
```

**Expected**: All tasks score exactly 1.00.

### Buggy Mode

The task's visible/editable files (the buggy original) are used as the submission. This verifies that the baseline bug always produces a sub-perfect score:

```
eda-bench evaluate-dataset tasks --submission-mode buggy
```

**Expected**: All tasks score strictly less than 1.00.

### Calibration Property

For a well-calibrated benchmark:

- `solution_score == 1.0` for every task
- `buggy_score < 1.0` for every task
- `buggy_score < solution_score` for every task

The dataset evaluation script tracks `buggy_lower_than_solution_count` to verify this property holds across all tasks.

## Smoke Tests

Smoke tests verify the end-to-end evaluation pipeline for each track:

| Script | What It Tests |
|--------|---------------|
| `scripts/run_smoke.sh` | P1 RTL Debug: compile, public test, hidden test |
| `scripts/run_spice_smoke.sh` | P4 HSPICE: tool run, metric extraction |
| `scripts/run_spectre_smoke.sh` | P4 Spectre: tool run, metric extraction |
| `scripts/run_pt_report_smoke.sh` | P3 PT Prototype: handcrafted task generation, validation, scoring (skips if PT unavailable) |
| `scripts/evaluate_dataset_smoke.sh` | All tracks: solution and buggy mode on small subsets |

Run all smoke tests:

```bash
bash scripts/run_smoke.sh
bash scripts/run_spice_smoke.sh
bash scripts/run_spectre_smoke.sh
bash scripts/evaluate_dataset_smoke.sh
```

## Dataset Evaluation Scripts

| Script | Purpose |
|--------|---------|
| `scripts/evaluate_dataset_smoke.sh` | Quick smoke across all tracks (small subset) |
| `scripts/evaluate_dataset_fast.sh` | Fast sampled evaluation (all tracks, ~2 min) |
| `scripts/evaluate_p1_generated.sh` | Full P1 generated task evaluation |
| `scripts/evaluate_p5_spice_deck_debug.sh` | Full P5 evaluation |
| `scripts/evaluate_large_dataset.sh` | Full dataset evaluation (all tracks) |

## Sampled Evaluation

For fast integration checks, the CLI supports sampled evaluation:

```bash
# Sample N tasks per track (deterministic with seed)
eda-bench evaluate-dataset tasks --sample-per-track 1 --seed 42 --submission-mode solution

# Evaluate at most N tasks total
eda-bench evaluate-dataset tasks --limit 10 --seed 42 --submission-mode solution
```

Sampled evaluation is deterministic: the same seed and task tree always produce the same selection. The summary JSON includes `sampled: true`, `seed`, `total_candidates`, and `selected_task_ids` for transparency.

**Warning:** Sampled evaluation is not a substitute for full evaluation. Use it for fast iteration during development; run full evaluation before final validation.

## Anti-Cheat Verification

The evaluator snapshots SHA-256 hashes of all forbidden files before execution and recomputes them after. If any hash differs, the evaluation fails. This ensures:

- Agents cannot modify testbenches to force pass
- Agents cannot modify scoring scripts
- Agents cannot modify hidden test infrastructure

## Log Sanitization

All EDA tool output is sanitized before storage. The sanitizer replaces:

- Usernames → `<USER>`
- Hostnames → `<HOST>`
- Absolute paths → `<PROJECT_ROOT>`, `<EDA_ROOT>`
- License servers → `<LICENSE_SERVER>`
- Machine names → `<HOST>`

This ensures evaluation logs can be shared without leaking environment details.

## Environment Detection

The benchmark probes the filesystem for EDA tools at runtime. No hardcoded paths are stored in task definitions. The `eda-bench detect-tools` command reports which tools are available:

```bash
eda-bench detect-tools
```

Expected paths (probed, not hardcoded):
- Synopsys: `/EDA/soft2/synopsys/`
- Cadence: `/EDA/soft2/cadence/`

## Reproducing a Specific Evaluation

To reproduce an evaluation result:

1. Install the benchmark: `pip install -e ".[test]"`
2. Detect tools: `eda-bench detect-tools`
3. Run smoke tests to verify tool availability
4. Evaluate the specific task:
   ```bash
   eda-bench evaluate-task tasks/<track>/<task_id> \
     --submission tasks/<track>/<task_id>/solution
   ```
5. Compare `score.json` output with the expected result

## Versioning

Each task's `metadata.json` includes a `version` field (currently `"1.0.0"`). The benchmark package version is in `pyproject.toml` (currently `0.1.0`).

## Benchmark Inventory Export

A deterministic inventory and summary can be generated from the task metadata:

```bash
python scripts/export_benchmark_summary.py
```

This produces all report artifacts under `reports/` (task inventory, track/tool/scoring distributions, per-track breakdowns, leaderboard template, and markdown summary). The output is fully deterministic — running it twice on the same task tree produces identical files.
