# DC Constraint Debug Task: Missing Clock

## Description

The design `fsm_ctrl` has a constraint file (`constraints.sdc`) with a bug.
Fix the constraint file so that Design Compiler synthesis completes successfully.

## Bug Category

Missing create_clock definition

## Files

- `design.v` — RTL design (do not modify)
- `constraints.sdc` — constraint file (you may edit this file)
- `run_public.sh` — public test runner (do not modify)
- `run_public.tcl` — DC TCL script (do not modify)

## Constraints

- Only modify `constraints.sdc`
- Do not modify any other files
- The design has clock `clk` with period 2.0ns

## Hint

Check the SDC file for: missing clock definitions, wrong port names,
syntax errors, or incorrect timing constraints.
