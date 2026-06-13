**English | [中文](p2_tb_sva.zh.md)**

# P2: Testbench / SVA Generation

## Overview

The P2 track evaluates whether an agent can write a useful testbench or SystemVerilog assertion (SVA) file for a given RTL module.

## Task Concept

Each task provides:

- A correct golden RTL design (visible to the agent)
- A prompt asking the agent to write a testbench

The submitted testbench is evaluated using **mutation-based grading**:

1. The testbench is compiled with the golden design (should pass)
2. The testbench is compiled with mutant designs (should fail/detect bugs)

## Scoring

| Component     | Weight | Criteria                                      |
|---------------|--------|-----------------------------------------------|
| compile       | 0.2    | VCS compilation succeeds                      |
| golden_pass   | 0.4    | Golden design passes all tests                |
| mutant_1      | 0.2    | Mutant 1 is detected (test fails or error)    |
| mutant_2      | 0.2    | Mutant 2 is detected (test fails or error)    |

**Pass criteria:** total_score = 1.00 (golden passes AND all mutants caught)

**Weak baseline:** empty/no-op testbench scores 0.0 (golden has no pass indicator)

## Task Layout

```
task_200000/
  prompt.md                  # Task description
  metadata.json              # Machine-readable spec
  files/                     # Visible to agent
    design_golden.sv         # Correct design (read-only)
    run_public.sh            # Runs golden test (read-only)
  hidden/                    # Used for grading only
    design_mutant1.sv        # Mutant 1
    design_mutant2.sv        # Mutant 2
    run_hidden.sh            # Runs mutant tests
  solution/                  # Correct answer
    tb.sv                    # Testbench that catches all mutants
  buggy_submission/          # Weak baseline
    tb.sv                    # Empty testbench
```

## Design Templates

The generator uses 10 design templates:

| # | Template          | Module           | Difficulty | Mutant 1                | Mutant 2                  |
|---|-------------------|------------------|------------|-------------------------|---------------------------|
| 1 | mux2              | `mux2`           | easy       | select_swapped          | stuck_at_zero             |
| 2 | counter           | `counter4`       | easy       | enable_inverted         | off_by_one                |
| 3 | fsm               | `fsm_simple`     | medium     | wrong_transition        | missing_busy              |
| 4 | handshake         | `handshake_reg`  | medium     | ready_inverted          | data_not_captured         |
| 5 | priority_encoder  | `priority_enc`   | easy       | reversed_priority       | wrong_encoding            |
| 6 | pulse_detector    | `pulse_detect`   | easy       | missing_pulse           | wrong_edge                |
| 7 | arbiter           | `arbiter_rr`     | medium     | fixed_priority          | grant_two_bits            |
| 8 | edge_detector     | `edge_detect`    | easy       | rising_falling_swapped  | registered_output         |
| 9 | valid_ready_fsm   | `vr_pipe`        | medium     | ready_inverted          | data_not_latched          |
|10 | fifo_status       | `fifo_status`    | easy       | empty_inverted          | wrong_threshold           |

Each template has 2 mutant variants (20 total mutants across 10 templates).

**Mutant diversity:**
- Select/polarity inversion: select_swapped, enable_inverted, ready_inverted, empty_inverted, rising_falling_swapped
- Missing/wrong behavior: stuck_at_zero, missing_busy, missing_pulse, data_not_captured, data_not_latched
- Priority/order: reversed_priority, fixed_priority, wrong_transition
- Off-by-one/threshold: off_by_one, wrong_threshold, wrong_encoding
- Multi-signal: grant_two_bits, registered_output, wrong_edge

## Template Distribution

With 100 generated tasks and 10 templates, the generator cycles through templates every 4 tasks:

- Tasks 0–39: templates 0–9 (4 tasks each)
- Tasks 40–79: templates 0–9 (4 tasks each)
- Tasks 80–99: templates 0–4 (4 tasks each)

Result: templates 0–4 get 12 tasks each, templates 5–9 get 8 tasks each.

## Task ID Range

P2 tasks use task IDs starting at `task_200000` to avoid collisions with P1 (0-199999).

## Expected Counts

- Smoke: 1 task (task_200000, handcrafted mux2)
- Generated: 100 tasks (task_200001 - task_200100)
- Total: 101 tasks

## Commands

```bash
# Generate tasks
python3 scripts/generate_p2_tasks.py --count 100 --seed 42

# Run smoke test
bash scripts/run_p2_smoke.sh

# Validate a task
eda-bench validate-task tasks/p2_tb_sva_gen/smoke/task_200000

# Evaluate with solution
eda-bench evaluate-task tasks/p2_tb_sva_gen/smoke/task_200000 \
    --submission tasks/p2_tb_sva_gen/smoke/task_200000/solution

# Evaluate dataset
eda-bench evaluate-dataset tasks --submission-mode solution --track p2_tb_sva_gen
```

## Testbench Requirements

The submitted testbench must:

1. Instantiate the design module (by name, e.g., `mux2`)
2. Drive stimulus to exercise the design
3. Check outputs against expected values
4. Print `ALL_TESTS_PASS: N/M` on success
5. Print `TEST_FAIL: N/M` on any failure
6. Call `$finish` when done
