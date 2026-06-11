# Adding Tasks

This guide explains how to create new tasks for EDA-AgentBench.

## General Workflow

1. Create the task directory structure
2. Write `metadata.json` with all required fields
3. Write `prompt.md` describing the task
4. Create visible/hidden/solution files
5. Verify: solution scores 1.00, buggy scores < 1.00
6. Run `eda-bench validate-task` to check schema

## Directory Structure

```
task_xxxxxx/
  prompt.md
  metadata.json
  files/           # Visible to agent
    ...            # Editable design files + read-only test files
  hidden/          # Scoring only, agent never sees
    ...
  solution/        # Correct answer
    ...
```

## P1 RTL Debug Task

### Files

```
task_000042/
  prompt.md
  metadata.json
  files/
    design.sv           # Buggy design (editable)
    tb_public.sv        # Public testbench (read-only)
    run_public.sh       # Runs VCS with public TB (read-only)
  hidden/
    tb_hidden.sv        # Hidden testbench
    run_hidden.sh       # Runs VCS with hidden TB
  solution/
    design.sv           # Correct design
```

### metadata.json

```json
{
  "task_id": "task_000042",
  "track": "p1_rtl_debug",
  "tool": ["vcs"],
  "difficulty": "easy",
  "data_type": "mutation_synthetic",
  "resource_preset": "fast",
  "timeout_sec": 120,
  "max_tool_calls": 10,
  "max_patch_attempts": 3,
  "max_output_tokens": 16000,
  "files": {
    "visible": ["design.sv", "tb_public.sv", "run_public.sh"],
    "editable": ["design.sv"],
    "hidden": ["tb_hidden.sv", "run_hidden.sh"],
    "forbidden": ["tb_public.sv", "run_public.sh", "tb_hidden.sv", "run_hidden.sh"]
  },
  "run_command": "bash run_public.sh",
  "scoring": {
    "weights": {
      "compile": 0.2,
      "public_test": 0.3,
      "hidden_test": 0.4,
      "explanation": 0.1
    }
  },
  "sanitizer": {"enabled": true},
  "version": "1.0.0"
}
```

### Writing the Bug

Start from a correct `design.sv`, then inject exactly one bug. Supported bug types:

- `sensitivity_list`: incomplete `always @(*)` sensitivity
- `blocking_nonblocking`: wrong `=` vs `<=` usage
- `reset_polarity`: active-high vs active-low mismatch
- `width_truncation`: port width mismatch causing data loss
- `comparison_boundary`: off-by-one in comparisons
- `wrong_mux_select`: incorrect mux case/select signal
- `priority_order`: wrong if-else priority
- `fsm_transition_error`: incorrect state transition
- `counter_off_by_one`: counter boundary error
- `enable_condition`: missing or wrong enable guard

### Writing Testbenches

- `tb_public.sv`: 2-3 test cases visible to the agent
- `tb_hidden.sv`: 1-2 test cases the agent never sees
- Both should print PASS/FAIL counts that the evaluator can parse

### Writing Run Scripts

`run_public.sh`:
```bash
#!/bin/bash
set -e
WORK_DIR="$(pwd)"
vcs -full64 -sverilog \
    "$WORK_DIR/design.sv" \
    "$WORK_DIR/tb_public.sv" \
    -o "$WORK_DIR/simv_public" 2>&1
cd "$WORK_DIR" && ./simv_public
```

`run_hidden.sh`: same pattern with `tb_hidden.sv` and `simv_hidden`.

## P4 SPICE Sim Task

### Files (HSPICE)

```
hspice_custom_000001/
  prompt.md
  metadata.json
  files/
    circuit.sp          # Buggy netlist (editable)
    run_public.sh       # Runs HSPICE, extracts measures
  hidden/
    run_hidden.sh       # Runs hidden measurement
  solution/
    circuit.sp          # Correct netlist
```

### Files (Spectre)

```
spectre_custom_000001/
  prompt.md
  metadata.json
  files/
    circuit.scs         # Buggy netlist (editable)
    run_public.sh       # Runs Spectre, parses waveform
  hidden/
    run_hidden.sh       # Runs hidden measurement
  solution/
    circuit.scs         # Correct netlist
```

### metadata.json

```json
{
  "task_id": "task_000100",
  "track": "p4_spice_sim",
  "tool": ["hspice"],
  "difficulty": "easy",
  "data_type": "template_synthetic",
  "resource_preset": "fast",
  "timeout_sec": 120,
  "max_tool_calls": 10,
  "max_patch_attempts": 3,
  "max_output_tokens": 16000,
  "files": {
    "visible": ["circuit.sp", "run_public.sh"],
    "editable": ["circuit.sp"],
    "hidden": ["run_hidden.sh"],
    "forbidden": ["run_public.sh", "run_hidden.sh"]
  },
  "run_command": "bash run_public.sh",
  "scoring": {
    "weights": {
      "tool_run": 0.3,
      "output_generated": 0.2,
      "public_metric": 0.2,
      "hidden_metric": 0.2,
      "explanation": 0.1
    },
    "evaluator": "spice_sim.SPICESimEvaluator",
    "metrics": {
      "public": {"measure": "tdrise", "min": 8e-9, "max": 15e-9},
      "hidden": {"measure": "tdfall", "min": 8e-9, "max": 15e-9}
    }
  },
  "sanitizer": {"enabled": true},
  "version": "1.0.0"
}
```

### Writing SPICE Run Scripts

HSPICE run scripts should:

1. Run `hspice -i circuit.sp -o <prefix>`
2. The evaluator parses the `.lis` file for `.measure` results

Spectre run scripts should:

1. Run `spectre circuit.scs +escchars +log spectre.out -format nutascii`
2. Parse the `.raw` waveform file with Python
3. Write results to `metrics.json`

See existing tasks in `tasks/p4_spice_sim/` for reference implementations.

## Using Generators

For batch generation, use the generator scripts:

```bash
# Generate 100 P1 tasks
python scripts/generate_p1_tasks.py --count 100 --seed 42

# Generate 10 P4 tasks (5 HSPICE + 5 Spectre)
python scripts/generate_p4_spice_tasks.py --count 10 --seed 42
```

Generators ensure:

- Deterministic output from seed
- Balanced distribution of bug types / configs
- Valid metadata passing schema validation
- Correct solution scoring 1.00

## Verification Checklist

Before committing a new task:

1. `eda-bench validate-task <task_dir>` passes
2. `eda-bench evaluate-task <task_dir> --submission <task_dir>/solution` scores 1.00
3. `eda-bench evaluate-task <task_dir> --submission <task_dir>/files` scores < 1.00
4. All forbidden files are unchanged after evaluation (anti-cheat passes)
5. Task ID is unique (no conflicts with existing tasks)
6. No tool-generated intermediate files in the task directory (`.o`, `.log`, `simv`, etc.)
