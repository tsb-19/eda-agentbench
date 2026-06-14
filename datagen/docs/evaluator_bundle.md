**English | [中文](evaluator_bundle.zh.md)**

# Evaluator Bundle

## Public Package vs Private Eval Bundle

| Aspect | `tasks_public/` | `tasks_eval_private/` |
|--------|-----------------|----------------------|
| Audience | Researchers, public benchmark | Evaluator repo only |
| `hidden/` | Stripped | Included |
| `oracle/` | Stripped | Included |
| `grader_contract.json` | Not included | Included |
| `validation/` | Normalized records | Normalized records |
| Raw `.log` files | Never | Never |
| Git tracked | Yes | No (`.gitignore`) |

## Why Oracle Is Withheld from Public Package

The oracle files (`hidden/*.sp`, `oracle/answer.md`) contain the reference solution.
If published, agents could trivially copy the answer instead of solving the task.
The public package provides only the buggy prompt and validation metadata.

## Grader Contract

The `grader_contract.json` file tells the main evaluator repo how to grade an agent's attempt.

### Key Fields

| Field | Purpose |
|-------|---------|
| `editable_files` | Files the agent may modify (under `visible/`) |
| `hidden_files` | Files used for grading (under `hidden/`) |
| `oracle_files` | Reference solution files |
| `backend` | Commercial tool to run the agent's output |
| `backend_env_var` | Env var for the tool command |
| `command_template` | Command to execute with `{file}` placeholder |
| `success_criteria` | What constitutes a passing grade |
| `failure_patterns` | Error patterns that indicate failure |

### Success Criteria for SPICE Debug Tasks

SPICE deck debug tasks use **execution-based grading**, not exact text matching:

```json
{
  "exit_code": 0,
  "no_fatal_errors": true,
  "execution_based": true,
  "notes": "Agent output must run with HSPICE (exit 0) and produce no fatal errors."
}
```

This means:
1. The agent produces a fixed `.sp` file
2. The evaluator runs it with HSPICE
3. If HSPICE exits 0 with no fatal errors, the agent passes
4. The fix does NOT need to be identical to `oracle/fixed.sp`

### Why Execution-Based Grading

Circuit design problems often have multiple valid solutions.
For example, a missing model can be fixed by:
- Adding a `.model` statement inline
- Including a model library
- Using a different model name that already exists

Exact text matching would reject valid alternatives.
Execution-based grading verifies the fix is functionally correct.

## Consuming the Bundle

The main evaluator repo should:

1. Clone or symlink `tasks_eval_private/`
2. For each task, read `grader_contract.json`
3. Copy `editable_files` to a working directory
4. Let the agent modify the editable files
5. Run `command_template` with the agent's output
6. Check `success_criteria` against the run result
7. Compare against `failure_patterns` from the validation record

### Example Flow

```python
import json
import subprocess

contract = json.load(open("tasks_eval_private/spice_deck_debug_0001/grader_contract.json"))

# Agent modifies visible/spice_deck_debug_0001_bug.sp
agent_file = contract["editable_files"][0]

# Run HSPICE on agent's output
cmd = contract["command_template"].format(
    hspice_cmd=os.environ["EDA_HSPICE_CMD"],
    file=agent_file,
)
result = subprocess.run(cmd.split(), timeout=contract["timeout_sec"])

# Check success
passed = (
    result.returncode == contract["success_criteria"]["exit_code"]
    and no_fatal_errors(result.stdout)
)
```

## Directory Structure

```
tasks_eval_private/
  manifest.jsonl                    # Machine-readable index
  spice_deck_debug_0001/
    metadata.json
    prompt.md
    grader_contract.json            # Grading instructions
    visible/
      spice_deck_debug_0001_bug.sp  # Buggy deck (agent sees this)
    hidden/
      spice_deck_debug_0001_fixed.sp  # Golden fix (grader uses this)
    oracle/
      answer.md                     # Reference answer
    validation/
      validation_record.json        # Normalized validation data
      normalized_errors.json
      raw_log.sha256
  ...
```
