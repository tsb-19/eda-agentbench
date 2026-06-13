**English | [中文](p7_spyglass_lint_debug.zh.md)**

# P7 SpyGlass Lint Debug

## Goal

Evaluate an agent's ability to fix RTL lint violations detected by Synopsys SpyGlass.

## What It Measures

- Understanding of common RTL coding errors that create lint violations
- Ability to read SpyGlass lint output and identify the root cause
- Ability to fix RTL code to eliminate lint violations while preserving functionality

## Task Structure

```
sg_lint_NNNN/
  metadata.json
  prompt.md
  files/
    design.v          # buggy RTL (editable)
    spyglass.prj      # SpyGlass project file (not editable)
    run_public.sh     # public test runner (not editable)
    run_public.tcl    # SpyGlass TCL script (not editable)
  hidden/
    run_hidden.sh     # hidden test runner (not editable)
    run_hidden.tcl    # hidden SpyGlass TCL script (not editable)
  solution/
    design.v          # correct RTL (zero violations)
```

## Bug Categories

Only categories verified to produce reliable violations under SpyGlass Lint
(`lint/lint_rtl` goal, default policies) are included.

| Category | Difficulty | Description | SpyGlass Detection |
|----------|-----------|-------------|-------------------|
| `latch_inference` | easy | Incomplete if-else in combinational always block creates inferred latch | Error + Warning |
| `multi_driven` | medium | Same signal assigned in two always blocks | Error + Warning |
| `blocking_in_seq` | medium | Blocking assignment (=) in sequential always block | Error |

### Rejected Categories

These categories were tested but SpyGlass default lint does **not** flag them:

- `width_mismatch`: SpyGlass accepts without warning
- `unused_signal`: SpyGlass accepts without warning
- `undriven_signal`: SpyGlass accepts without warning
- `missing_default`: SpyGlass accepts without warning
- `implicit_net`: SpyGlass accepts without warning

## Scoring

```json
{
  "lint_pass": 0.9,
  "explanation": 0.1
}
```

- **lint_pass**: 1.0 if SpyGlass reports zero violations (Fatals + Errors + Warnings), 0.0 otherwise
- **explanation**: 1.0 in submission mode (no explanation required)

## Run Script Behavior

1. Checks if `sg_shell` is available (graceful skip if not)
2. Runs `sg_shell -tcl run_public.tcl` which:
   - Reads the RTL design
   - Sets the top module
   - Runs the `lint/lint_rtl` goal
3. Parses the "Goal Violation Summary" from SpyGlass output
4. Emits `LINT_PASS` if zero violations, `LINT_FAIL` otherwise

## Validation Results

- **SpyGlass detection**: S-2021.09-SP1 available at `/EDA/soft2/synopsys/spyglass/`
- **Solution mode**: 1.00 (all tasks pass lint)
- **Buggy mode**: 0.10 (all tasks fail lint with violations)
- **pytest**: 31/31 pass
- **Smoke test**: PASS (solution=1.00, buggy=0.10)

## SpyGlass Command Notes

- `sg_shell -tcl <file>` runs a TCL startup script
- `-project` and `-tcl` are mutually exclusive
- `set_option top <module>` is required before `current_goal`
- `report_goal` is not a valid command; results are in the goal summary
- Violation counts are in the "Goal Violation Summary" section:
  ```
  Reported Messages: 0 Fatals, 1 Errors, 1 Warnings, 3 Infos
  ```
