# Task: Fix RC Low-Pass Filter Fall Time

## Problem

The RC low-pass filter in `circuit.sp` has a fall time that is too slow.
The input signal is a pulse from 0V to 1.8V with 500ps rise/fall times.

The 50% fall delay (time for output to reach 0.9V on the falling edge) must be
between 357.61ns and 629.39ns.

## Your Task

1. Analyze the circuit in `circuit.sp`
2. Identify the component causing the slow fall time
3. Modify the editable file to fix the fall delay
4. Run `bash run_public.sh` to verify your fix

## Constraints

- You may only modify `circuit.sp`
- Do not modify `run_public.sh` or any other files
- The RC filter topology must remain the same (series R, shunt C)
- The input signal parameters must not change

## Files

- `circuit.sp` — HSPICE netlist (editable)
- `run_public.sh` — Public test script (read-only)
