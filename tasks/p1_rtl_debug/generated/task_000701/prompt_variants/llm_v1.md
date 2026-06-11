# RTL Debug Task

For a gate-level netlist,

## Description

The module below has a bug. Find and fix the bug in `design.sv` so that it passes all test cases.

## Files

- `design.sv` — the design under test (you are allowed to edit this file)
- `tb_public.sv` — public testbench (do not modify)
- `run_public.sh` — public test runner (do not modify)

## Constraints

- You should only need to modify the design file
- Leave all other files unchanged

## Hint

Check the FSM transitions. Does the completed signal pulse after the operation finishes?

A correct fix should pass both public and hidden tests.