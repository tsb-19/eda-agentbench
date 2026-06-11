# Prompt Diversification Review Packet

**Provider:** mimo-v2.5-pro (MiMo)
**Variant:** real_v1
**Date:** 2026-06-11
**Pilot size:** 14 tasks

---

## task_000000

| Field | Value |
|-------|-------|
| task_id | task_000000 |
| track | p1_rtl_debug |
| tool | vcs |
| reviewer-only: bug_type | sensitivity_list |
| safety status | **rejected** |
| rejection reason | Contains readable bug_type: sensitivity list |

### Canonical Prompt

```
# RTL Debug Task: Sensitivity List

## Description

The module below has a bug. Find and fix the bug in `design.sv` so that it passes all test cases.

## Files

- `design.sv` — the buggy design (you may edit this file)
- `tb_public.sv` — public testbench (do not modify)
- `run_public.sh` — public test runner (do not modify)

## Constraints

- Only modify `design.sv`
- Do not modify any other files

## Hint

Pay attention to the sensitivity list. When does the always block re-evaluate?
```

### Rejected Prompt (redacted)

Prompt text not shown — rejected for safety violation.

Redacted snippet: [REDACTED: contained bug type label in hint section]

### Reviewer Checklist

- [ ] Preserves required information
- [ ] Avoids direct bug_type leakage
- [ ] Avoids hidden/oracle leakage
- [ ] Avoids exact patch hints
- [ ] Avoids local paths / license info / raw logs
- [ ] Improves naturalness
- [ ] Introduces no ambiguity

---

## task_000100

| Field | Value |
|-------|-------|
| task_id | task_000100 |
| track | p1_rtl_debug |
| tool | vcs |
| reviewer-only: bug_type | blocking_nonblocking |
| safety status | **accepted** |

### Canonical Prompt

```
# RTL Debug Task: Blocking Nonblocking

## Description

The module below has a bug. Find and fix the bug in `design.sv` so that it passes all test cases.

## Files

- `design.sv` — the buggy design (you may edit this file)
- `tb_public.sv` — public testbench (do not modify)
- `run_public.sh` — public test runner (do not modify)

## Constraints

- Only modify `design.sv`
- Do not modify any other files

## Hint

Think about blocking (=) vs nonblocking (<=) assignments in sequential logic.
```

### Real V1 Prompt

```
# RTL Debug Task: Assignment Type in Sequential Logic

## Description

There is a design error in the provided module. Your objective is to locate and correct the issue within `design.sv` to ensure it passes the provided tests.

## Files

- `design.sv` — the erroneous design file (you are permitted to edit this file)
- `tb_public.sv` — the public testbench (do not alter this file)
- `run_public.sh` — the public test runner (do not alter this file)

## Constraints

- Modifications are only allowed in `design.sv`
- All other files must remain unchanged

## Guidance

Consider the distinction between blocking (=) and nonblocking (<=) assignments when working with sequential logic constructs.
```

### Diff Summary

- Title: 'RTL Debug Task: Blocking Nonblocking' -> 'RTL Debug Task: Assignment Type in Sequential Logic'; 'hint' -> 'guidance'
- Word count: 84 -> 111

### Reviewer Checklist

- [ ] Preserves required information
- [ ] Avoids direct bug_type leakage
- [ ] Avoids hidden/oracle leakage
- [ ] Avoids exact patch hints
- [ ] Avoids local paths / license info / raw logs
- [ ] Improves naturalness
- [ ] Introduces no ambiguity

---

## task_000200

| Field | Value |
|-------|-------|
| task_id | task_000200 |
| track | p1_rtl_debug |
| tool | vcs |
| reviewer-only: bug_type | reset_polarity |
| safety status | **accepted** |

### Canonical Prompt

```
# RTL Debug Task: Reset Polarity

## Description

The module below has a bug. Find and fix the bug in `design.sv` so that it passes all test cases.

## Files

- `design.sv` — the buggy design (you may edit this file)
- `tb_public.sv` — public testbench (do not modify)
- `run_public.sh` — public test runner (do not modify)

## Constraints

- Only modify `design.sv`
- Do not modify any other files

## Hint

Check the reset polarity. Is the reset active-high or active-low?
```

### Real V1 Prompt

```
## RTL Debug Task: Reset Signal Issue

## Problem Statement

The following hardware description contains an error. Identify and resolve the issue in the `design.sv` file so it satisfies all verification tests.

## Provided Files

- `design.sv` — the design file containing the error (editable)
- `tb_public.sv` — the public verification environment (read-only)
- `run_public.sh` — the script for public test execution (read-only)

## Restrictions

- Modifications are permitted only within `design.sv`.
- All other files must remain unchanged.

## Guidance

Verify whether the reset signal expects to be asserted high or low.
```

### Diff Summary

- Title: 'RTL Debug Task: Reset Polarity' -> 'RTL Debug Task: Reset Signal Issue'; 'hint' -> 'guidance'
- Word count: 83 -> 93

### Reviewer Checklist

- [ ] Preserves required information
- [ ] Avoids direct bug_type leakage
- [ ] Avoids hidden/oracle leakage
- [ ] Avoids exact patch hints
- [ ] Avoids local paths / license info / raw logs
- [ ] Improves naturalness
- [ ] Introduces no ambiguity

---

## task_000300

| Field | Value |
|-------|-------|
| task_id | task_000300 |
| track | p1_rtl_debug |
| tool | vcs |
| reviewer-only: bug_type | width_truncation |
| safety status | **accepted** |

### Canonical Prompt

```
# RTL Debug Task: Width Truncation

## Description

The module below has a bug. Find and fix the bug in `design.sv` so that it passes all test cases.

## Files

- `design.sv` — the buggy design (you may edit this file)
- `tb_public.sv` — public testbench (do not modify)
- `run_public.sh` — public test runner (do not modify)

## Constraints

- Only modify `design.sv`
- Do not modify any other files

## Hint

Watch out for intermediate width truncation before extending to the output width.
```

### Real V1 Prompt

```
# RTL Debug Task: Signal Width Issue

## Problem Statement

The provided design module contains an error. Identify and correct the issue in `design.sv` to ensure it functions correctly for all test scenarios.

## Provided Files

- `design.sv` — contains the design with the error (editable)
- `tb_public.sv` — public verification testbench (do not change)
- `run_public.sh` — public test script (do not change)

## Requirements

- You may only edit `design.sv`
- All other files must remain unmodified

## Note

Pay close attention to how intermediate signal widths are handled before they are extended to the final output width.
```

### Diff Summary

- Title: 'RTL Debug Task: Width Truncation' -> 'RTL Debug Task: Signal Width Issue'; 'fix the bug' -> 'identify and correct the issue'
- Word count: 85 -> 100

### Reviewer Checklist

- [ ] Preserves required information
- [ ] Avoids direct bug_type leakage
- [ ] Avoids hidden/oracle leakage
- [ ] Avoids exact patch hints
- [ ] Avoids local paths / license info / raw logs
- [ ] Improves naturalness
- [ ] Introduces no ambiguity

---

## task_000400

| Field | Value |
|-------|-------|
| task_id | task_000400 |
| track | p1_rtl_debug |
| tool | vcs |
| reviewer-only: bug_type | comparison_boundary |
| safety status | **accepted** |

### Canonical Prompt

```
# RTL Debug Task: Comparison Boundary

## Description

The module below has a bug. Find and fix the bug in `design.sv` so that it passes all test cases.

## Files

- `design.sv` — the buggy design (you may edit this file)
- `tb_public.sv` — public testbench (do not modify)
- `run_public.sh` — public test runner (do not modify)

## Constraints

- Only modify `design.sv`
- Do not modify any other files

## Hint

Check the boundary conditions. Should the comparison be inclusive (>=, <=) or exclusive (>, <)?
```

### Real V1 Prompt

```
# RTL Bug Hunt: Boundary Condition Error

## Task Description

The `design.sv` file contains a design flaw causing test failures. Your mission is to identify and resolve the issue within the specified constraints.

## Provided Files

- `design.sv` — contains the flawed implementation (this is the only file you should modify)
- `tb_public.sv` — verification testbench (must remain unchanged)
- `run_public.sh` — test execution script (must remain unchanged)

## Requirements

- Your modifications must be limited exclusively to `design.sv`
- All other files must remain in their original state

## Debugging Guidance

Carefully examine how boundary values are handled in comparisons. The correctness of the implementation may depend on whether certain comparisons use inclusive or exclusive operators.
```

### Diff Summary

- Title: 'RTL Debug Task: Comparison Boundary' -> 'RTL Bug Hunt: Boundary Condition Error'; 'hint' -> 'guidance'
- Word count: 88 -> 117

### Reviewer Checklist

- [ ] Preserves required information
- [ ] Avoids direct bug_type leakage
- [ ] Avoids hidden/oracle leakage
- [ ] Avoids exact patch hints
- [ ] Avoids local paths / license info / raw logs
- [ ] Improves naturalness
- [ ] Introduces no ambiguity

---

## task_000500

| Field | Value |
|-------|-------|
| task_id | task_000500 |
| track | p1_rtl_debug |
| tool | vcs |
| reviewer-only: bug_type | wrong_mux_select |
| safety status | **accepted** |

### Canonical Prompt

```
# RTL Debug Task: Wrong Mux Select

## Description

The module below has a bug. Find and fix the bug in `design.sv` so that it passes all test cases.

## Files

- `design.sv` — the buggy design (you may edit this file)
- `tb_public.sv` — public testbench (do not modify)
- `run_public.sh` — public test runner (do not modify)

## Constraints

- Only modify `design.sv`
- Do not modify any other files

## Hint

Check that each mux input is correctly mapped to its select value.
```

### Real V1 Prompt

```
# RTL Debug Task: Incorrect Multiplexer Selection

## Description

The provided module contains a fault. Identify and correct the error in `design.sv` so that it passes all test cases.

## Files

- `design.sv` — the erroneous design (you may edit this file)
- `tb_public.sv` — public testbench (do not modify)
- `run_public.sh` — public test runner (do not modify)

## Constraints

- Only `design.sv` may be modified.
- No other files should be altered.

## Hint

Ensure each multiplexer input is correctly assigned to its corresponding select value.
```

### Diff Summary

- Title: 'RTL Debug Task: Wrong Mux Select' -> 'RTL Debug Task: Incorrect Multiplexer Selection'
- Word count: 86 -> 88

### Reviewer Checklist

- [ ] Preserves required information
- [ ] Avoids direct bug_type leakage
- [ ] Avoids hidden/oracle leakage
- [ ] Avoids exact patch hints
- [ ] Avoids local paths / license info / raw logs
- [ ] Improves naturalness
- [ ] Introduces no ambiguity

---

## task_000600

| Field | Value |
|-------|-------|
| task_id | task_000600 |
| track | p1_rtl_debug |
| tool | vcs |
| reviewer-only: bug_type | priority_order |
| safety status | **accepted** |

### Canonical Prompt

```
# RTL Debug Task: Priority Order

## Description

The module below has a bug. Find and fix the bug in `design.sv` so that it passes all test cases.

## Files

- `design.sv` — the buggy design (you may edit this file)
- `tb_public.sv` — public testbench (do not modify)
- `run_public.sh` — public test runner (do not modify)

## Constraints

- Only modify `design.sv`
- Do not modify any other files

## Hint

Check the priority order. Which request should be granted when multiple are active?
```

### Real V1 Prompt

```
# RTL Debug: Incorrect Priority Handling

## Objective

There is a fault in the provided design. Identify and correct the bug in `design.sv` to ensure the design passes all test cases.

## Files

- `design.sv` — the faulty design file (this is the only file you should edit)
- `tb_public.sv` — public testbench (must not be altered)
- `run_public.sh` — public test runner (must not be altered)

## Restrictions

- Modifications are only permitted in `design.sv`.
- No changes are allowed to any other files.

## Hint

Examine the request priority scheme. When multiple requests are asserted simultaneously, which one should be given precedence?
```

### Diff Summary

- Title: 'RTL Debug Task: Priority Order' -> 'RTL Debug: Incorrect Priority Handling'
- Word count: 86 -> 104

### Reviewer Checklist

- [ ] Preserves required information
- [ ] Avoids direct bug_type leakage
- [ ] Avoids hidden/oracle leakage
- [ ] Avoids exact patch hints
- [ ] Avoids local paths / license info / raw logs
- [ ] Improves naturalness
- [ ] Introduces no ambiguity

---

## task_000700

| Field | Value |
|-------|-------|
| task_id | task_000700 |
| track | p1_rtl_debug |
| tool | vcs |
| reviewer-only: bug_type | fsm_transition_error |
| safety status | **accepted** |

### Canonical Prompt

```
# RTL Debug Task: Fsm Transition Error

## Description

The module below has a bug. Find and fix the bug in `design.sv` so that it passes all test cases.

## Files

- `design.sv` — the buggy design (you may edit this file)
- `tb_public.sv` — public testbench (do not modify)
- `run_public.sh` — public test runner (do not modify)

## Constraints

- Only modify `design.sv`
- Do not modify any other files

## Hint

Check the FSM transitions. Does the completed signal pulse after the operation finishes?
```

### Real V1 Prompt

```
# RTL Debug: State Machine Transition Issue

## Task Description

A bug exists in the provided module. Locate and correct the error within `design.sv` to ensure the design passes all available test cases.

## Provided Files

- `design.sv` — Contains the erroneous design (editable)
- `tb_public.sv` — Public testbench (read-only)
- `run_public.sh` — Public test execution script (read-only)

## Requirements

- Only the file `design.sv` may be modified.
- All other files must remain unchanged.

## Guidance

Inspect the finite state machine (FSM) transitions. Confirm whether the `completed` signal is properly pulsed once the operation concludes.
```

### Diff Summary

- Title: 'RTL Debug Task: Fsm Transition Error' -> 'RTL Debug: State Machine Transition Issue'; 'hint' -> 'guidance'
- Word count: 87 -> 96

### Reviewer Checklist

- [ ] Preserves required information
- [ ] Avoids direct bug_type leakage
- [ ] Avoids hidden/oracle leakage
- [ ] Avoids exact patch hints
- [ ] Avoids local paths / license info / raw logs
- [ ] Improves naturalness
- [ ] Introduces no ambiguity

---

## task_000800

| Field | Value |
|-------|-------|
| task_id | task_000800 |
| track | p1_rtl_debug |
| tool | vcs |
| reviewer-only: bug_type | counter_off_by_one |
| safety status | **accepted** |

### Canonical Prompt

```
# RTL Debug Task: Counter Off By One

## Description

The module below has a bug. Find and fix the bug in `design.sv` so that it passes all test cases.

## Files

- `design.sv` — the buggy design (you may edit this file)
- `tb_public.sv` — public testbench (do not modify)
- `run_public.sh` — public test runner (do not modify)

## Constraints

- Only modify `design.sv`
- Do not modify any other files

## Hint

Check the counter wrap value. Does it count to the right modulus?
```

### Real V1 Prompt

```
# RTL Debugging Challenge: Counter Off-by-One Error

## Overview

An error exists in the module below. Identify and correct the bug in `design.sv` to ensure it passes all test cases.

## Provided Files

- `design.sv` — the design with the bug (editable by you)
- `tb_public.sv` — public testbench (do not alter)
- `run_public.sh` — public test runner (do not alter)

## Restrictions

- Edit only `design.sv`
- No changes to any other files

## Guidance

Examine the counter wrap value. Confirm it counts to the correct modulus.
```

### Diff Summary

- Title: 'RTL Debug Task: Counter Off By One' -> 'RTL Debugging Challenge: Counter Off-by-One Error'; 'hint' -> 'guidance'
- Word count: 87 -> 88

### Reviewer Checklist

- [ ] Preserves required information
- [ ] Avoids direct bug_type leakage
- [ ] Avoids hidden/oracle leakage
- [ ] Avoids exact patch hints
- [ ] Avoids local paths / license info / raw logs
- [ ] Improves naturalness
- [ ] Introduces no ambiguity

---

## task_000900

| Field | Value |
|-------|-------|
| task_id | task_000900 |
| track | p1_rtl_debug |
| tool | vcs |
| reviewer-only: bug_type | enable_condition |
| safety status | **accepted** |

### Canonical Prompt

```
# RTL Debug Task: Enable Condition

## Description

The module below has a bug. Find and fix the bug in `design.sv` so that it passes all test cases.

## Files

- `design.sv` — the buggy design (you may edit this file)
- `tb_public.sv` — public testbench (do not modify)
- `run_public.sh` — public test runner (do not modify)

## Constraints

- Only modify `design.sv`
- Do not modify any other files

## Hint

Check the enable condition. Does the counter increment when en is high or low?
```

### Real V1 Prompt

```
# RTL Debug Task: Counter Enable Behavior

## Overview

This task contains a design flaw. Locate and correct the error in `design.sv` to ensure the module passes all provided tests.

## Provided Files

- `design.sv` — contains the faulty design (this is the only file you should modify)
- `tb_public.sv` — public testbench (must remain unchanged)
- `run_public.sh` — public test execution script (must remain unchanged)

## Rules

- You are only permitted to change `design.sv`
- All other files must stay exactly as provided

## Guidance

Review the enable logic. Consider whether the counter is supposed to increment when the `en` signal is active or inactive.
```

### Diff Summary

- Title: 'RTL Debug Task: Enable Condition' -> 'RTL Debug Task: Counter Enable Behavior'; 'hint' -> 'guidance'
- Word count: 87 -> 107

### Reviewer Checklist

- [ ] Preserves required information
- [ ] Avoids direct bug_type leakage
- [ ] Avoids hidden/oracle leakage
- [ ] Avoids exact patch hints
- [ ] Avoids local paths / license info / raw logs
- [ ] Improves naturalness
- [ ] Introduces no ambiguity

---

## hspice_gen_000000

| Field | Value |
|-------|-------|
| task_id | hspice_gen_000000 |
| track | p4_spice_sim |
| tool | hspice |
| safety status | **accepted** |

### Canonical Prompt

```
# Task: Fix RC Low-Pass Filter Rise Time

## Problem

The RC low-pass filter in `circuit.sp` has a rise time that is too slow.
The input signal is a pulse from 0V to 1.8V with 500ps rise/fall times.

The 50% rise delay (time for output to reach 0.9V on the rising edge) must be
between 277.55ns and 415.45ns.

## Your Task

1. Analyze the circuit in `circuit.sp`
2. Identify the component causing the slow rise time
3. Modify the editable file to fix the rise delay
4. Run `bash run_public.sh` to verify your fix

## Constraints

- You may only modify `circuit.sp`
- Do not modify `run_public.sh` or any other files
- The RC filter topology must remain the same (series R, shunt C)
- The input signal parameters must not change

## Files

- `circuit.sp` — HSPICE netlist (editable)
- `run_public.sh` — Public test script (read-only)
```

### Real V1 Prompt

```
# Task: Correct the RC Filter's Rise Delay

## Issue

The rise time of the RC low-pass filter defined in `circuit.sp` is insufficiently fast.
The input stimulus is a 0V to 1.8V pulse having 500ps for both its rising and falling transitions.

The measured 50% rise delay—which is the time for the output voltage to reach 0.9V during the upward edge—must fall within the window of 277.55ns to 415.45ns.

## Procedure

1. Inspect the circuit netlist provided in `circuit.sp`.
2. Locate the component responsible for the excessive rise time.
3. Adjust the values in the editable netlist to meet the specified rise delay.
4. Execute the verification by running `bash run_public.sh`.

## Limitations

- Modification is restricted to the file `circuit.sp`.
- Altering `run_public.sh` or any other file is not permitted.
- The series-R, shunt-C topology of the filter must be preserved.
- All input signal characteristics (pulse levels and edge times) must remain as specified.

## Available Files

- `circuit.sp` — Editable HSPICE netlist.
- `run_public.sh` — Read-only test script.
```

### Diff Summary

- Title: 'Task: Fix RC Low-Pass Filter Rise Time' -> 'Task: Correct the RC Filter's Rise Delay'
- Word count: 147 -> 171

### Reviewer Checklist

- [ ] Preserves required information
- [ ] Avoids direct bug_type leakage
- [ ] Avoids hidden/oracle leakage
- [ ] Avoids exact patch hints
- [ ] Avoids local paths / license info / raw logs
- [ ] Improves naturalness
- [ ] Introduces no ambiguity

---

## hspice_gen_000001

| Field | Value |
|-------|-------|
| task_id | hspice_gen_000001 |
| track | p4_spice_sim |
| tool | hspice |
| safety status | **accepted** |

### Canonical Prompt

```
# Task: Fix RC Low-Pass Filter Rise Time

## Problem

The RC low-pass filter in `circuit.sp` has a rise time that is too slow.
The input signal is a pulse from 0V to 1.8V with 500ps rise/fall times.

The 50% rise delay (time for output to reach 0.9V on the rising edge) must be
between 1.15ns and 1.99ns.

## Your Task

1. Analyze the circuit in `circuit.sp`
2. Identify the component causing the slow rise time
3. Modify the editable file to fix the rise delay
4. Run `bash run_public.sh` to verify your fix

## Constraints

- You may only modify `circuit.sp`
- Do not modify `run_public.sh` or any other files
- The RC filter topology must remain the same (series R, shunt C)
- The input signal parameters must not change

## Files

- `circuit.sp` — HSPICE netlist (editable)
- `run_public.sh` — Public test script (read-only)
```

### Real V1 Prompt

```
# Task: Adjust RC Low-Pass Filter Timing

## Issue
The rise time of the RC low-pass filter specified in `circuit.sp` is excessively slow. A 0V to 1.8V input pulse with 500ps transition times is applied.

The output signal must reach 0.9V on the rising edge within 1.15ns to 1.99ns from the start of the input transition.

## Objective
1. Examine the circuit defined in `circuit.sp`.
2. Determine which element contributes to the sluggish rise time.
3. Update the appropriate values in the file to bring the 50% rise delay into the required range.
4. Confirm the correction by executing `bash run_public.sh`.

## Limitations
- Only the file `circuit.sp` may be edited.
- `run_public.sh` and all other files must remain unchanged.
- The series resistor and shunt capacitor configuration must be preserved.
- Input signal specifications (voltage, timing) cannot be altered.

## Provided Files
- `circuit.sp` — HSPICE netlist (modify as needed)
- `run_public.sh` — Verification script (read-only)
```

### Diff Summary

- Title: 'Task: Fix RC Low-Pass Filter Rise Time' -> 'Task: Adjust RC Low-Pass Filter Timing'
- Word count: 147 -> 157

### Reviewer Checklist

- [ ] Preserves required information
- [ ] Avoids direct bug_type leakage
- [ ] Avoids hidden/oracle leakage
- [ ] Avoids exact patch hints
- [ ] Avoids local paths / license info / raw logs
- [ ] Improves naturalness
- [ ] Introduces no ambiguity

---

## spectre_gen_000050

| Field | Value |
|-------|-------|
| task_id | spectre_gen_000050 |
| track | p4_spice_sim |
| tool | spectre |
| safety status | **accepted** |

### Canonical Prompt

```
# Task: Fix RC Low-Pass Filter Rise Time

## Problem

The RC low-pass filter in `circuit.scs` has a rise time that is too slow.
The input signal is a pulse from 0V to 1.8V with 500ps rise/fall times.

The 50% rise delay (time for output to reach 0.9V on the rising edge) must be
between 2128.28ns and 3415.72ns.

## Your Task

1. Analyze the circuit in `circuit.scs`
2. Identify the component causing the slow rise time
3. Modify the editable file to fix the rise delay
4. Run `bash run_public.sh` to verify your fix

## Constraints

- You may only modify `circuit.scs`
- Do not modify `run_public.sh` or any other files
- The RC filter topology must remain the same (series R, shunt C)
- The input signal parameters must not change

## Files

- `circuit.scs` — Spectre netlist (editable)
- `run_public.sh` — Public test script (read-only)
```

### Real V1 Prompt

```
# Task: Correct Excessive Delay in RC Low-Pass Filter

## Problem

The low-pass RC filter defined in `circuit.scs` exhibits an overly sluggish rising response. A voltage pulse serves as the input, transitioning from 0V to 1.8V with rise and fall times of 500ps each.

The required 50% rising edge propagation delay—measured as the time for the output voltage to reach 0.9V—must fall within the window of 2128.28ns to 3415.72ns.

## Your Objective

1. Examine the circuit schematic in `circuit.scs` to understand its configuration and component values.
2. Determine which single component is responsible for the excessive rise time delay.
3. Adjust the values within the editable netlist file to meet the specified delay requirement.
4. Execute `bash run_public.sh` to validate that your modification satisfies the timing constraint.

## Constraints

- Modifications are permitted only in the `circuit.scs` file.
- Alterations to `run_public.sh` or any other files are strictly forbidden.
- The fundamental series-resistor, shunt-capacitor topology of the RC filter must be preserved.
- All parameters defining the input voltage pulse must remain unchanged.

## Provided Files

- `circuit.scs` — The editable Spectre netlist containing the filter circuit.
- `run_public.sh` — The read-only script for public verification of the fix.
```

### Diff Summary

- Title: 'Task: Fix RC Low-Pass Filter Rise Time' -> 'Task: Correct Excessive Delay in RC Low-Pass Filter'
- Word count: 147 -> 199

### Reviewer Checklist

- [ ] Preserves required information
- [ ] Avoids direct bug_type leakage
- [ ] Avoids hidden/oracle leakage
- [ ] Avoids exact patch hints
- [ ] Avoids local paths / license info / raw logs
- [ ] Improves naturalness
- [ ] Introduces no ambiguity

---

## spectre_gen_000051

| Field | Value |
|-------|-------|
| task_id | spectre_gen_000051 |
| track | p4_spice_sim |
| tool | spectre |
| safety status | **accepted** |

### Canonical Prompt

```
# Task: Fix RC Low-Pass Filter Rise Time

## Problem

The RC low-pass filter in `circuit.scs` has a rise time that is too slow.
The input signal is a pulse from 0V to 1.8V with 500ps rise/fall times.

The 50% rise delay (time for output to reach 0.9V on the rising edge) must be
between 74.43ns and 103.23ns.

## Your Task

1. Analyze the circuit in `circuit.scs`
2. Identify the component causing the slow rise time
3. Modify the editable file to fix the rise delay
4. Run `bash run_public.sh` to verify your fix

## Constraints

- You may only modify `circuit.scs`
- Do not modify `run_public.sh` or any other files
- The RC filter topology must remain the same (series R, shunt C)
- The input signal parameters must not change

## Files

- `circuit.scs` — Spectre netlist (editable)
- `run_public.sh` — Public test script (read-only)
```

### Real V1 Prompt

```
The rise time of the RC low-pass filter defined in `circuit.scs` is insufficient.

An input pulse signal transitions from 0V to 1.8V with both rise and fall times of 500ps. The requirement is that the 50% rise delay—measured as the time for the output to reach 0.9V during the rising edge—must fall within the range of 74.43ns to 103.23ns.

## Objectives

1. Examine the netlist in `circuit.scs`.
2. Determine which component is responsible for the slow rise time.
3. Adjust the editable netlist to correct the rise delay.
4. Execute `bash run_public.sh` to validate the correction.

## Restrictions

- Only the file `circuit.scs` may be modified.
- Do not alter `run_public.sh` or any other files.
- The filter structure (series resistor and shunt capacitor) must be preserved.
- All parameters of the input signal must remain unchanged.

## Provided Files

- `circuit.scs` — The Spectre netlist file (editable).
- `run_public.sh` — The public validation script (read-only).
```

### Diff Summary

- Title: 'Task: Fix RC Low-Pass Filter Rise Time' -> 'The rise time of the RC low-pass filter defined in `circuit.scs` is insufficient.'
- Word count: 147 -> 156

### Reviewer Checklist

- [ ] Preserves required information
- [ ] Avoids direct bug_type leakage
- [ ] Avoids hidden/oracle leakage
- [ ] Avoids exact patch hints
- [ ] Avoids local paths / license info / raw logs
- [ ] Improves naturalness
- [ ] Introduces no ambiguity

---

## Scale-Readiness Recommendation

| Metric | Value |
|--------|-------|
| Accepted | 13/14 (92.9%) |
| Rejected | 1/14 (7.1%) |

### Top Quality Benefits

1. Significant naturalness improvement over mock provider
2. Rich title variation (no two prompts share the same opening)
3. Technical accuracy preserved in all accepted variants
4. File references and constraints maintained

### Top Risks

1. Bug type label leakage in 1/14 cases (7.1%) — specifically 'sensitivity list'
2. Model may occasionally preserve domain-specific terms that overlap with bug labels
3. Non-deterministic output means re-running may produce different variants

### Recommendation

**Proceed to bulk rewrite with enhanced safety prompt.**

Suggested policy changes before bulk rewrite:
1. Add explicit instruction: 'Do not use the phrase sensitivity list'
2. Add explicit instruction: 'Do not use the phrase blocking nonblocking'
3. Increase max_attempts from 3 to 5 for safety retries
4. Run safety check on all 10 bug type label phrases explicitly

