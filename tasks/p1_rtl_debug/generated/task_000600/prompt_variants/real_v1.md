# RTL Debug: Incorrect Priority Handling

## Objective

There is a fault in the provided design. Identify and correct the bug in `design.sv` to ensure the design passes all test cases.

## Files

- `design.sv` — the faulty design file (this is the only file you should edit)
- `tb_public.sv` — public testbench (must not be altered)
- `run_public.sh` — public test runner (must not be altered)

## Restrictions

- Modifications are only permitted in `design.sv`.
- No changes are allowed to any other files.

## Hint

Examine the request priority scheme. When multiple requests are asserted simultaneously, which one should be given precedence?