# PrimeTime STA Debug Task: Missing Clock

## Description

The design `comparator_reg` has a constraint file (`constraints.sdc`) with a bug.
Fix the constraint file so that PrimeTime STA timing checks pass.

## Bug Category

Missing create_clock definition — PrimeTime has no clocks, timing checks fail

## Files

- `design.v` — RTL design (do not modify)
- `constraints.sdc` — constraint file (you may edit this file)
- `run_public.sh` — public test runner (do not modify)
- `run_public.tcl` — PrimeTime TCL script (do not modify)

## Constraints

- Only modify `constraints.sdc`
- Do not modify any other files
- The design has clock `clk` with period 2.0ns
- Design ports: clk, rst_n, a, b, gt, eq

## Hint

The run script checks that:
1. At least one clock is created with the expected clock name
2. All design ports resolve correctly
3. report_timing succeeds

Check the SDC file for: missing clock definitions, wrong port names,
syntax errors, or invalid port references.
