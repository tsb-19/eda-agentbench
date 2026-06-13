**English | [中文](p6_dc_synthesis_qa.zh.md)**

# P6 DC Synthesis Report QA

## Overview

P6 is a report-QA track for Design Compiler synthesis reports. Given a sanitized synthesis report, the task is to answer precise questions about synthesis metrics.

**No EDA tool execution required.** Answers are validated by parser-based extraction from synthetic reports.

## Task Layout

Same as P3 Timing Report QA:

```
p6_dc_syn_NNNNNN/
  prompt.md
  metadata.json
  files/
    synthesis_report.rpt   # read-only synthesis report
    answer.txt             # editable, empty placeholder
  hidden/                  # empty
  solution/
    answer.txt             # expected answer
```

## Question Types (10)

| Type | Answer | Example |
|------|--------|---------|
| `total_area` | numeric (tol=0.01) | 21250.75 |
| `combinational_area` | numeric (tol=0.01) | 12500.50 |
| `sequential_area` | numeric (tol=0.01) | 8750.25 |
| `cell_count` | numeric (exact) | 3500 |
| `register_count` | numeric (exact) | 1200 |
| `top_module` | string | alu_top |
| `worst_slack` | numeric (tol=0.01) | -0.1500 |
| `compile_status` | string | 0 errors, 3 warnings |
| `clock_period` | numeric (tol=0.01) | 10.0000 |
| `warning_count` | numeric (exact) | 3 |

## Scoring

Single component: `answer_match` (weight 1.0)

- Numeric answers: relative tolerance (default 1%)
- String answers: case-insensitive, whitespace-normalized

## Generator

`generators/p6_dc_synthesis_qa_gen.py`

- Deterministic seed (default 42)
- 50 module names, 30 clock names
- Round-robin across 10 question types
- 5 tasks per question type per 50-task batch

## Parser

`eda_agentbench/synthesis/dc_report_parser.py`

Extracts: top module, area breakdown, cell/register counts, timing, compile status, warning/error counts.

## Evaluator

`eda_agentbench/evaluator/dc_synthesis_qa.py`

Reuses the same answer-matching logic as P3 TimingReportQAEvaluator.

## Current Scale

- Smoke: 1 task (`p6_dc_syn_000000`)
- Generated: 50 tasks
- Total: 51 tasks

## DC Detection

DC (`dc_shell`) is detected but not required for evaluation. The smoke test reports whether DC is available.
