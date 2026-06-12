# P5: SPICE Deck Debug

## What P5 Measures

P5 evaluates an agent's ability to diagnose and fix syntax/structural errors in SPICE simulation decks. Unlike P4 (which tests metric-driven circuit optimization), P5 focuses on **debugging broken decks** that fail to run.

Each task provides a buggy `.sp` file that HSPICE rejects. The agent must identify the error and produce a corrected deck that HSPICE can execute successfully.

## How P5 Differs from P4 SPICE Sim

| Aspect | P4 SPICE Sim | P5 SPICE Deck Debug |
|--------|-------------|---------------------|
| Goal | Optimize circuit metrics (rise time, etc.) | Fix syntax/structural errors |
| Bug type | Wrong component values | Missing models, wrong pins, duplicates, etc. |
| Scoring | Metric-based (tolerance ranges) | Execution-based (exit code + no fatal errors) |
| Oracle required | Yes (target values) | No (any working fix accepted) |
| Exact diff | N/A | Not required |

## External Bundle Source

P5 tasks are imported from the sibling repository:

```
../eda-bench-prototypes/tasks_eval_private/
```

This bundle was generated and validated externally. The main benchmark imports it read-only via:

```
python3 scripts/import_p5_tasks.py
```

The import converts external metadata to the main schema while preserving `grader_contract.json`, `visible/`, `hidden/`, `oracle/`, and `validation/` directories.

## Task Structure

Each imported P5 task has this layout:

```
spice_deck_debug_NNNN/
  metadata.json           # Main schema format
  prompt.md               # Task description
  grader_contract.json    # Execution-based grading rules
  visible/
    *_bug.sp              # Buggy deck (editable by agent)
  hidden/
    *_fixed.sp            # Golden fixed deck (for solution mode)
  oracle/
    answer.md             # Human-readable expected fix
  validation/
    validation_record.json
    normalized_errors.json
    raw_log.sha256
```

## Execution-Based Grading

P5 uses **execution-based** grading, not exact diff matching:

1. Run HSPICE on the submitted deck
2. Check exit code == 0
3. Check for no fatal error patterns from `grader_contract.json`
4. Pass if both conditions met

Any syntactically valid fix that HSPICE can execute is accepted, even if it differs from the oracle.

## Scoring Weights

```json
{
  "execution_pass": 0.9,
  "explanation": 0.1
}
```

## Error Categories

The 100 imported tasks cover these error categories:

| Category | Count | Description |
|----------|-------|-------------|
| missing_model | 15 | References undefined MOSFET/diode model |
| duplicate_element | 15 | Two elements share the same name |
| missing_subckt | 14 | References undefined subcircuit |
| wrong_pin_count | 14 | Subcircuit instance has wrong pin count |
| missing_include | 14 | .include references nonexistent file |
| unsupported_dialect | 14 | Model level not supported by HSPICE |
| invalid_directive | 14 | Malformed .include (no filename) |

## Running P5

### Validate a task

```bash
eda-bench validate-task tasks/p5_spice_deck_debug/imported/spice_deck_debug_0001
```

### Evaluate a single task

```bash
eda-bench evaluate-task tasks/p5_spice_deck_debug/imported/spice_deck_debug_0001 \
  --submission <submission_dir>
```

### Batch evaluation

```bash
bash scripts/evaluate_p5_spice_deck_debug.sh
```

Expected: 100/100 solution pass, 100/100 buggy fail.

### Dataset evaluation

```bash
eda-bench evaluate-dataset tasks --track p5_spice_deck_debug --submission-mode solution
eda-bench evaluate-dataset tasks --track p5_spice_deck_debug --submission-mode buggy
```

## Why Exact Diff Is Not Required

A SPICE deck can be fixed in multiple valid ways. For example, a missing model can be added:

- Before the element that references it
- After the element (HSPICE resolves forward references)
- With different whitespace or comments

All valid fixes that produce exit code 0 and no fatal errors are scored equally. This tests the agent's ability to produce **functionally correct** output, not to memorize a specific answer.

## Public vs Private Bundle

The external bundle at `../eda-bench-prototypes/tasks_eval_private/` is the **private eval bundle**. It contains:

- Buggy decks (visible to agent)
- Fixed decks (hidden, for solution mode evaluation)
- Oracle answers (for human review)
- Validation records (debug contrast verification)

A public release bundle (with a subset of tasks) may be published separately. The import script can handle either bundle.
