# Task: Fix RC Low-Pass Filter Rise Time

When working with synthesis tools,

## Problem

The RC low-pass filter in `circuit.scs` has a rise time that is too slow.
The input signal is a pulse from 0V to 1.8V with 500ps rise/fall times.

The 50% rise delay (time for output to reach 0.9V on the rising edge) must be
between 74.43ns and 103.23ns.

## Your Task

1. Analyze the circuit in `circuit.scs`
2. Identify the component causing the slow rise time
3. Modify the editable file to fix the rise delay
4. Run `bash run_public.sh` to verify your fix

## Constraints

- You may only modify `circuit.scs`
- Leave all other files unchanged
- The RC filter topology must remain the same (series R, shunt C)
- The input signal parameters must not change

## Files

- `circuit.scs` — Spectre netlist (editable)
- `run_public.sh` — Public test script (read-only)

Verify your solution against all test cases.