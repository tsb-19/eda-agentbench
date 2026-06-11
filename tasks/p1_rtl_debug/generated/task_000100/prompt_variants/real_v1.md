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