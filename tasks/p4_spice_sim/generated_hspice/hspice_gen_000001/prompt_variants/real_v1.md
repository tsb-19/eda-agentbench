# Task: Adjust RC Low-Pass Filter Timing

## Issue
The rise time of the RC low-pass filter specified in `circuit.sp` is excessively slow. A 0V to 1.8V input pulse with 500ps transition times is applied.

The output signal must reach 0.9V on the rising edge within 1.15ns to 1.99ns from the start of the input transition.

## Objective
1. Examine the circuit defined in `circuit.sp`.
2. Determine which element contributes to the sluggish rise time.
3. Update the appropriate values in the file to bring the 50% rise delay into the required range.
4. Confirm the correction by executing `bash run_public.sh`.

## Limitations
- Only the file `circuit.sp` may be edited.
- `run_public.sh` and all other files must remain unchanged.
- The series resistor and shunt capacitor configuration must be preserved.
- Input signal specifications (voltage, timing) cannot be altered.

## Provided Files
- `circuit.sp` — HSPICE netlist (modify as needed)
- `run_public.sh` — Verification script (read-only)