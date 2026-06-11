# RTL Debug Task: Counter Enable Behavior

## Overview

This task contains a design flaw. Locate and correct the error in `design.sv` to ensure the module passes all provided tests.

## Provided Files

- `design.sv` — contains the faulty design (this is the only file you should modify)
- `tb_public.sv` — public testbench (must remain unchanged)
- `run_public.sh` — public test execution script (must remain unchanged)

## Rules

- You are only permitted to change `design.sv`
- All other files must stay exactly as provided

## Guidance

Review the enable logic. Consider whether the counter is supposed to increment when the `en` signal is active or inactive.