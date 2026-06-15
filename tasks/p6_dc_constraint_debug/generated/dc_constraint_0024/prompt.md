# DC Constraint Debug Task: Missing Clock

## Description

The design `shift_reg` has a constraint file (`constraints.sdc`) with a bug.
Fix the constraint file so that Design Compiler synthesis completes successfully.

## Bug Category

Missing create_clock definition — DC reports 'Can't find clock'

## Files

- `design.v` — RTL design (do not modify)
- `constraints.sdc` — constraint file (you may edit this file)
- `run_public.sh` — public test runner (do not modify)
- `run_public.tcl` — DC TCL script (do not modify)

## Constraints

- Only modify `constraints.sdc`
- Do not modify any other files
- The design has clock `clk` with period 5.0ns
- Design ports: clk, rst_n, din, dout

## Hint

The run script checks that:
1. At least one clock is created
2. All design ports resolve correctly
3. compile_ultra succeeds

Check the SDC file for: missing clock definitions, wrong port names,
syntax errors, or invalid port references.
