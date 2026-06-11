# Testbench Generation Task: Handshake

## Description

Write a SystemVerilog testbench for the `handshake_reg` module.

valid/ready handshake register with 8-bit data path.

Ports: input clk, rst_n, valid_in, ready_in, [7:0] data_in; output valid_out, ready_out, [7:0] data_out

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
