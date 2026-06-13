# SpyGlass Lint Debug Task: Blocking In Seq

## Description

The RTL design `design.v` has a lint issue that SpyGlass Lint detects.
Fix the design file so that the lint check passes with zero violations.

## Bug Category

Blocking assignment (=) in sequential always block — use non-blocking (<=)

## Files

- `design.v` — RTL design (you may edit this file)
- `spyglass.prj` — SpyGlass project file (do not modify)
- `run_public.sh` — public test runner (do not modify)
- `run_public.tcl` — SpyGlass TCL script (do not modify)

## Constraints

- Only modify `design.v`
- Do not modify any other files
- The lint check must pass with zero violations

## Hint

Run `bash run_public.sh` to check if your fix passes the lint check.
The script will report `LINT_PASS` if all violations are resolved.
