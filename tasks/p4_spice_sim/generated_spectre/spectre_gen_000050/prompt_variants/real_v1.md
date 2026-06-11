# Task: Correct Excessive Delay in RC Low-Pass Filter

## Problem

The low-pass RC filter defined in `circuit.scs` exhibits an overly sluggish rising response. A voltage pulse serves as the input, transitioning from 0V to 1.8V with rise and fall times of 500ps each.

The required 50% rising edge propagation delay—measured as the time for the output voltage to reach 0.9V—must fall within the window of 2128.28ns to 3415.72ns.

## Your Objective

1. Examine the circuit schematic in `circuit.scs` to understand its configuration and component values.
2. Determine which single component is responsible for the excessive rise time delay.
3. Adjust the values within the editable netlist file to meet the specified delay requirement.
4. Execute `bash run_public.sh` to validate that your modification satisfies the timing constraint.

## Constraints

- Modifications are permitted only in the `circuit.scs` file.
- Alterations to `run_public.sh` or any other files are strictly forbidden.
- The fundamental series-resistor, shunt-capacitor topology of the RC filter must be preserved.
- All parameters defining the input voltage pulse must remain unchanged.

## Provided Files

- `circuit.scs` — The editable Spectre netlist containing the filter circuit.
- `run_public.sh` — The read-only script for public verification of the fix.