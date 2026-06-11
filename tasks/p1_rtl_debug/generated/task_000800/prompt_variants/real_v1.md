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