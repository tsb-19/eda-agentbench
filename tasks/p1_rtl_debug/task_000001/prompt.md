# RTL Debug Task: Combinational MUX

## Description

The module `mux2` below is a 2-to-1 multiplexer. It has a bug: the output `y` does not correctly follow input `b` under certain conditions.

Your task: find and fix the bug in `design.sv` so that the module passes all test cases.

## Files

- `design.sv` — the buggy design (you may edit this file)
- `tb_public.sv` — public testbench (do not modify)
- `run_public.sh` — public test runner (do not modify)

## Constraints

- Only modify `design.sv`
- Do not modify `tb_public.sv`, `run_public.sh`, or any other files
- The fix should be minimal — change only what is necessary

## Hints

- Pay attention to the sensitivity list
- Think about when combinational logic should re-evaluate
