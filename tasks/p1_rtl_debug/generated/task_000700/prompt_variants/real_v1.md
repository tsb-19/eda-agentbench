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