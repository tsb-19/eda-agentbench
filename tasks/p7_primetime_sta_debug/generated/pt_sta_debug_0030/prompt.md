# PrimeTime STA Debug Task: Wrong Port Name

## Description

The design `alu_reg` has a constraint file (`constraints.sdc`) with a bug.
Fix the constraint file so that PrimeTime STA timing checks pass.

## Bug Category

Wrong port name in constraint — PrimeTime reports 'Can't find port'

## Files

- `design.v` — RTL design (do not modify)
- `constraints.sdc` — constraint file (you may edit this file)
- `run_public.sh` — public test runner (do not modify)
- `run_public.tcl` — PrimeTime TCL script (do not modify)

## Constraints

- Only modify `constraints.sdc`
- Do not modify any other files
- The design has clock `clk` with period 2.0ns
- Design ports: clk, rst_n, op, a, b, result

## Hint

The run script checks that:
1. At least one clock is created with the expected clock name
2. All design ports resolve correctly
3. report_timing succeeds

Check the SDC file for: missing clock definitions, wrong port names,
syntax errors, or invalid port references.
