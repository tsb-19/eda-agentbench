# SPICE Simulation Task: RC Delay Circuit

## Description

The file `circuit.sp` contains an RC delay circuit. The delay measurement (`tdrise`) is outside the target range. Your task is to modify the resistor parameter so that the delay falls within the specified range.

## Files

- `circuit.sp` — the circuit netlist (you may modify the resistor parameter `rp`)
- `run_public.sh` — public test runner (do not modify)

## Constraints

- Only modify the `.param rp=...` line in `circuit.sp`
- Do not change the capacitor value, voltage source, or simulation commands
- Target delay range: 8ns to 15ns

## Hint

- The RC time constant is R × C
- For a 50% delay, the approximate time is 0.693 × RC
- Adjust R to achieve the target delay
