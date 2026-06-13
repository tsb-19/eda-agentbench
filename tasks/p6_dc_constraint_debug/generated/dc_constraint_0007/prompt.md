# DC Constraint Debug Task: Wrong Port Name

## Description

The design `fsm_ctrl` has a constraint file (`constraints.sdc`) with a bug.
Fix the constraint file so that Design Compiler synthesis completes successfully.

## Bug Category

Wrong port name in constraint — DC reports 'Can't find port'

## Files

- `design.v` — RTL design (do not modify)
- `constraints.sdc` — constraint file (you may edit this file)
- `run_public.sh` — public test runner (do not modify)
- `run_public.tcl` — DC TCL script (do not modify)

## Constraints

- Only modify `constraints.sdc`
- Do not modify any other files
- The design has clock `clk` with period 2.0ns
- Design ports: clk, rst_n, start, busy, done

## Hint

The run script checks that:
1. At least one clock is created
2. All design ports resolve correctly
3. compile_ultra succeeds

Check the SDC file for: missing clock definitions, wrong port names,
syntax errors, or invalid port references.
