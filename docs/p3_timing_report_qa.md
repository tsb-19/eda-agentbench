# P3 Timing Report QA

## Overview

The P3 Timing Report QA track evaluates whether an agent can read an STA-style timing report and answer precise quantitative questions.

## Task Concept

Given:
- A normalized PrimeTime/OpenSTA-style timing report
- A natural-language question

The model should answer facts such as:
- WNS (Worst Negative Slack)
- TNS (Total Negative Slack)
- Number of violating paths
- Worst startpoint / endpoint
- Path group / clock name
- Required time / arrival time
- Slack of a named path

## Question Types

| Type | Description | Answer Type | Difficulty |
|------|-------------|-------------|------------|
| `wns` | Worst Negative Slack | numeric | easy |
| `tns` | Total Negative Slack | numeric | easy |
| `violating_paths` | Count of paths with negative slack | numeric | easy |
| `worst_endpoint` | Endpoint of worst path | string | medium |
| `worst_startpoint` | Startpoint of worst path | string | medium |
| `path_group` | Path group of worst path | string | medium |
| `clock_name` | Clock of worst path | string | medium |
| `required_time` | Required time of worst path | numeric | hard |
| `arrival_time` | Arrival time of worst path | numeric | hard |
| `slack_of_named_path` | Slack of a specific named path | numeric | hard |

## Scoring

- Numeric answers: tolerance-based matching (default 1% relative tolerance)
- String answers: exact normalized match (case-insensitive, whitespace-stripped)
- Score = 1.00 if correct, 0.00 otherwise

## Task Structure

```
tasks/p3_timing_report_qa/
  smoke/                          # Handcrafted smoke task
    files/timing_report.rpt       # Timing report (visible)
    solution/answer.txt           # Correct answer
    prompt.md                     # Question prompt
    metadata.json                 # Task metadata
  generated/                      # Generated tasks
    p3_timing_000001/ ... p3_timing_000999
```

Note: generated task IDs start at 000001 to avoid collision with the smoke task (p3_timing_000000).

## Generation

```bash
python3 scripts/generate_p3_tasks.py --count 999 --seed 42
```

Options:
- `--count`: Number of tasks to generate (default: 100)
- `--seed`: Random seed (default: 42)
- `--output-dir`: Output directory (default: `tasks/p3_timing_report_qa/generated`)

## Smoke Test

```bash
bash scripts/run_p3_smoke.sh
```

## PrimeTime Prototype (Phase 5E)

A small set of prototype tasks backed by real or handcrafted PrimeTime reports.
Stored under `tasks/p3_timing_report_qa/pt_prototype/` (8 tasks, IDs 900000–900007).

These tasks use the same schema, evaluator, and parser as synthetic P3 tasks.
The difference is that reports include realistic PrimeTime informational lines
and are sanitized via `LogSanitizer` before storage.

### Generation

```bash
# Handcrafted (no PrimeTime required)
python3 scripts/generate_pt_report_prototypes.py --mode handcrafted --seed 42

# Real PrimeTime (requires pt_shell)
python3 scripts/generate_pt_report_prototypes.py --mode real --seed 42
```

### Smoke Test

```bash
bash scripts/run_pt_report_smoke.sh
```

The smoke script checks PrimeTime availability and skips gracefully if unavailable.

### Question Types Covered

| Index | Scenario | Question Type |
|-------|----------|---------------|
| 900000 | Simple reg2reg setup path | wns |
| 900001 | Multi-path, 3 violating | tns |
| 900002 | Combinational in2reg path | worst_endpoint |
| 900003 | Clock domain crossing | worst_startpoint |
| 900004 | Hold violation path | violating_paths |
| 900005 | Reg2out path group | path_group |
| 900006 | Multi-clock design | clock_name |
| 900007 | Deep combinational path | arrival_time |

## Scope

- No PrimeTime invocation for synthetic tasks (synthetic normalized reports only)
- 1 smoke task + 999 generated tasks (1000 synthetic total)
- 8 PrimeTime prototype tasks (900000–900007, handcrafted or real PT-backed)
- 1008 P3 tasks total
- 10 question types with round-robin distribution (99–100 each)
- 30 unique clocks, 15 path groups, ~30% multi-clock reports
- Path counts 3–50, WNS range -5.0 to -0.01, TNS range -75 to -0.3
- Signal names with hierarchical depth and optional bit indices
- Deterministic generation with seeded RNG
- Full solution evaluation: 1000/1000 = 1.00
