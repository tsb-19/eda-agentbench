# Task: Fix RC Low-Pass Filter Rise Time

## Problem

The RC low-pass filter in `circuit.scs` has a rise time that is too slow.
The input signal is a pulse from 0V to 1.8V with 500ps rise/fall times,
100ns pulse width, and 200ns period.

The 50% rise delay (time for output to reach 0.9V on the rising edge) must be
between 8ns and 15ns. Currently it is outside this range.

The 50% fall delay (time for output to fall to 0.9V on the falling edge) must
also be between 8ns and 15ns.

## Your Task

1. Analyze the circuit in `circuit.scs`
2. Identify the component causing the slow rise/fall times
3. Modify the editable file to fix the rise and fall delays
4. Run `bash run_public.sh` to verify your fix

## Constraints

- You may only modify `circuit.scs`
- Do not modify `run_public.sh` or any other files
- The RC filter topology must remain the same (series R, shunt C)
- The input signal parameters must not change

## Files

- `circuit.scs` — Spectre netlist (editable)
- `run_public.sh` — Public test script (read-only)
