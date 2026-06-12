# Testbench Generation Task: Arbiter

## Description

Write a SystemVerilog testbench for the `arbiter_rr` module.

4-bit round-robin arbiter: rotates priority after each grant.

Ports: input clk, rst_n, [3:0] req; output [3:0] grant

## Files

- `design_golden.sv` — the correct design (do not modify)
- `tb.sv` — the testbench (you must create this file)

## Requirements

Your testbench should:

1. Instantiate the design module
2. Thoroughly test the expected behavior
3. Report pass/fail status using `$display("ALL_TESTS_PASS: ...")` on success
4. Use `$display("TEST_FAIL: ...")` on any failure
5. Call `$finish` when done

## Constraints

- Only submit `tb.sv`
- Do not modify `design_golden.sv`
