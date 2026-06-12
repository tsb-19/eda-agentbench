# Testbench Generation Task: Pulse Detector

## Description

Write a SystemVerilog testbench for the `pulse_detect` module.

Rising-edge pulse detector: pulse = sig & ~sig_d.

Ports: input clk, rst_n, sig; output pulse

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
