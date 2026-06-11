# RTL Bug Hunt: Boundary Condition Error

## Task Description

The `design.sv` file contains a design flaw causing test failures. Your mission is to identify and resolve the issue within the specified constraints.

## Provided Files

- `design.sv` — contains the flawed implementation (this is the only file you should modify)
- `tb_public.sv` — verification testbench (must remain unchanged)
- `run_public.sh` — test execution script (must remain unchanged)

## Requirements

- Your modifications must be limited exclusively to `design.sv`
- All other files must remain in their original state

## Debugging Guidance

Carefully examine how boundary values are handled in comparisons. The correctness of the implementation may depend on whether certain comparisons use inclusive or exclusive operators.