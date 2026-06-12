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

The generator uses 5 design templates:

1. **mux2** (easy): 2-to-1 multiplexer
2. **counter4** (easy): 4-bit counter with enable
3. **fsm_simple** (medium): 3-state FSM
4. **handshake_reg** (medium): valid/ready handshake register
5. **priority_enc** (easy): 4-to-2 priority encoder

Each template has 2 mutant variants (10 total mutants across 5 templates).

## Task ID Range

P2 tasks use task IDs starting at `task_200000` to avoid collisions with P1 (0-199999).

## Expected Counts

- Smoke: 1 task (task_200000, handcrafted mux2)
- Generated: 20 tasks (task_200001 - task_200020)
- Total: 21 tasks

## Commands

```bash
# Generate tasks
python3 scripts/generate_p2_tasks.py --count 20 --seed 42

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
