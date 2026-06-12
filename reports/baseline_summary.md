# EDA-AgentBench — Baseline Results

**Date:** 2026-06-12  
**Commit:** `639776c`  
**Sampling:** sample_per_track=1, seed=123

## Overview

| Mode | Tasks Evaluated | Avg Score | Pass Rate |
|------|----------------|-----------|-----------|
| solution | 5 | 1.0000 | 1.0000 |
| buggy | 5 | 0.3267 | 0.4000 |

## Per-Track Breakdown

### Solution Mode

| Track | Tasks | Avg Score | Pass Rate |
|-------|------:|----------:|----------:|
| P1 RTL Debug | 1 | 1.0000 | 1.0000 |
| P2 Testbench/SVA Gen | 1 | 1.0000 | 1.0000 |
| P3 Timing Report QA | 1 | 1.0000 | 1.0000 |
| P4 SPICE Sim | 1 | 1.0000 | 1.0000 |
| P5 SPICE Deck Debug | 1 | 1.0000 | 1.0000 |

### Buggy Mode

| Track | Tasks | Avg Score | Pass Rate |
|-------|------:|----------:|----------:|
| P1 RTL Debug | 1 | 0.7333 | 1.0000 |
| P2 Testbench/SVA Gen | 1 | 0.2000 | 0.0000 |
| P3 Timing Report QA | 1 | 0.0000 | 0.0000 |
| P4 SPICE Sim | 1 | 0.6000 | 1.0000 |
| P5 SPICE Deck Debug | 1 | 0.1000 | 0.0000 |

## Score Distribution

### Solution

| Bucket | Count |
|--------|------:|
| 1.0 | 5 |
| [0.8,1.0) | 0 |
| [0.5,0.8) | 0 |
| <0.5 | 0 |

### Buggy

| Bucket | Count |
|--------|------:|
| 1.0 | 0 |
| [0.8,1.0) | 0 |
| [0.5,0.8) | 2 |
| <0.5 | 3 |

## Interpretation

- **solution mode** (oracle baseline): expected avg=1.00, pass_rate=1.00. Verifies that the evaluation pipeline correctly rewards perfect submissions.
- **buggy mode** (weak baseline): expected avg<1.00. Uses unmodified editable files (or wrong answers for QA tracks) to verify that evaluators distinguish correct from incorrect submissions.

These baselines establish floor and ceiling scores for the benchmark.
Any real LLM submission should score between the buggy and solution baselines.

## Artifacts

| File | Description |
|------|-------------|
| `baseline_results_solution.csv` | Per-task results for solution mode |
| `baseline_results_buggy.csv` | Per-task results for buggy mode |
| `leaderboard_baseline_filled.csv` | Leaderboard template filled with baseline rows |
| `baseline_summary.md` | This summary file |
