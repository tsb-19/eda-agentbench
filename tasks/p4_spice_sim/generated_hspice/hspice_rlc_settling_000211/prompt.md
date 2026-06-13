# Task: Fix RLC Filter Response Time

## Problem

The RLC bandpass filter in `circuit.sp` has a response time that is too slow.
The input signal is a pulse from 0V to 1.8V with 500ps rise/fall times.

The 50% rise delay (time for output to reach 0.9V on the rising edge) must be
between 104.67ns and 184.11ns.

## Your Task

1. Analyze the circuit in `circuit.sp`
2. Identify the component causing the slow response
3. Modify the editable file to fix the rise delay
4. Run `bash run_public.sh` to verify your fix

## Constraints

- You may only modify `circuit.sp`
- Do not modify `run_public.sh` or any other files
- The RLC filter topology must remain the same (series L, series R, shunt C)
- The input signal parameters must not change

## Hint

- An overdamped RLC circuit responds more slowly than a well-damped one
- The damping ratio depends on R, L, and C values

## Files

- `circuit.sp` — HSPICE netlist (editable)
- `run_public.sh` — Public test script (read-only)
