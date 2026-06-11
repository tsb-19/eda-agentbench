# Task: Correct the RC Filter's Rise Delay

## Issue

The rise time of the RC low-pass filter defined in `circuit.sp` is insufficiently fast.
The input stimulus is a 0V to 1.8V pulse having 500ps for both its rising and falling transitions.

The measured 50% rise delay—which is the time for the output voltage to reach 0.9V during the upward edge—must fall within the window of 277.55ns to 415.45ns.

## Procedure

1. Inspect the circuit netlist provided in `circuit.sp`.
2. Locate the component responsible for the excessive rise time.
3. Adjust the values in the editable netlist to meet the specified rise delay.
4. Execute the verification by running `bash run_public.sh`.

## Limitations

- Modification is restricted to the file `circuit.sp`.
- Altering `run_public.sh` or any other file is not permitted.
- The series-R, shunt-C topology of the filter must be preserved.
- All input signal characteristics (pulse levels and edge times) must remain as specified.

## Available Files

- `circuit.sp` — Editable HSPICE netlist.
- `run_public.sh` — Read-only test script.