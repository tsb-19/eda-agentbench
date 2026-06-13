**English | [中文](benchmark_spec.zh.md)**

# Benchmark Specification

## Overview

EDA-AgentBench evaluates LLM/Agent ability to perform real EDA engineering tasks using commercial tools. The benchmark measures whether an agent can correctly modify designs to pass simulation-based tests.

## Evaluation Modes

### Submission/Workspace Mode (v0)

The current mode evaluates a pre-produced submission against a task:

1. Agent receives task files (prompt, visible files)
2. Agent produces modified files (submission directory)
3. Evaluator copies submission into a workspace, runs tests, computes score

No tool calls happen during evaluation. The agent's output is a static set of files.

### Agentic Mode (Future)

In agentic mode, the agent runs inside a sandboxed workspace with:

- Read access to visible files
- Write access to editable files
- Ability to run the provided command
- Iteration until timeout or tool-call limit

The evaluator captures the final workspace state and scores it identically.

## File Visibility Model

Each task defines four file categories:

| Category | Agent Can Read? | Agent Can Edit? | Used in Scoring? |
|----------|----------------|-----------------|-------------------|
| visible | Yes | No (unless also editable) | Yes |
| editable | Yes | Yes | Yes |
| hidden | No | No | Yes |
| forbidden | No | No | Checked for tampering |

Constraints:

- `editable` must be a subset of `visible`
- `hidden` must not overlap with `visible`
- `forbidden` must be a subset of `visible + hidden`

## Evaluation Flow

```
1. Load task metadata and validate schema
2. Detect required EDA tools (best-effort)
3. Snapshot SHA-256 hashes of all forbidden files
4. Build workspace:
   - Copy files/ -> work_dir/
   - Copy submission editable files -> work_dir/ (overwrite)
5. Run public test:   bash run_public.sh in work_dir
6. Run hidden test:   bash run_hidden.sh in work_dir
7. Verify anti-cheat: forbidden file hashes unchanged
8. Sanitize all logs
9. Compute score per metadata.scoring.weights
10. Write score.json to runs/<task_id>/<timestamp>/
11. Cleanup work_dir
```

## Public vs Hidden Evaluation

- **Public tests**: visible to the agent via `run_public.sh` and `tb_public.sv`. The agent can iterate against these.
- **Hidden tests**: only used during scoring via `run_hidden.sh` and `tb_hidden.sv`. The agent never sees these.

This prevents gaming specific test cases. A correct solution must generalize.

## Anti-Cheat

Before running any test, the evaluator computes SHA-256 hashes of all files listed in `metadata.files.forbidden`. After execution, it recomputes and compares. If any hash differs, the evaluation fails with an anti-cheat violation.

Forbidden files typically include:

- `tb_public.sv` / `run_public.sh` (public test infrastructure)
- `tb_hidden.sv` / `run_hidden.sh` (hidden test infrastructure)

## Log Sanitization

All EDA tool output is sanitized before storage. The sanitizer replaces:

- Usernames -> `<USER>`
- Hostnames -> `<HOST>`
- Absolute paths -> `<PROJECT_ROOT>`, `<EDA_ROOT>`
- License servers -> `<LICENSE_SERVER>`

This allows sharing evaluation logs without leaking environment details.

## Dataset Evaluation

`eda-bench evaluate-dataset` discovers all tasks under a root directory and evaluates each one. Two submission modes:

- **solution**: each task's `solution/` directory is the submission (expected: all score 1.00)
- **buggy**: each task's `files/` editable files are the submission (expected: all score < 1.00)

Dataset-level aggregation computes per-track, per-tool, and per-difficulty statistics with score distribution buckets.

## Report Generation

`eda-bench report` reads evaluation results and produces:

- **Terminal**: colored table with pass/fail counts and score distribution
- **JSON**: machine-readable `summary.json` with full aggregation
- **Markdown**: human-readable `report.md` with tables and statistics
