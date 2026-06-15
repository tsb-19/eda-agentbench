**English | [中文](p6_dc_constraint_debug.zh.md)**

# P6 DC Constraint Debug Track

## Overview

The P6 DC Constraint Debug track evaluates an agent's ability to fix buggy SDC
(Synopsys Design Constraints) or DC TCL scripts so that Design Compiler synthesis
completes successfully.

## Task Format

Each task provides:

- A small RTL design (`design.v`)
- A buggy constraint file (`constraints.sdc`) — **editable**
- DC TCL scripts (`run_public.tcl`, `run_hidden.tcl`) — read-only
- Shell run scripts (`run_public.sh`, `run_hidden.sh`) — read-only

The agent must fix only `constraints.sdc` so that DC synthesis passes.

## Bug Categories (Retained)

Only categories that produce **detectable failures** under DC are included.

| Bug | Difficulty | Detection Method |
|-----|-----------|-----------------|
| missing_clock | easy | `all_clocks` returns 0 clocks |
| wrong_port_name | easy | DC outputs "Can't find port" warning |
| invalid_get_ports | medium | DC outputs "Can't find ports matching" warning |
| wrong_top_module | hard | DC outputs "Can't find port" for prefixed ports |
| syntax_error | easy | DC exits nonzero (TCL parse error) |
| unsupported_command | medium | DC outputs "unknown command" error |

## Removed/Deferred Categories

The following categories were removed because DC accepts them silently:

| Bug | Reason |
|-----|--------|
| wrong_period | DC accepts any period value without error |
| missing_input_delay | DC accepts missing delays without error |
| missing_output_delay | DC accepts missing delays without error |
| tight_constraint | DC accepts overly tight constraints without error |

These may be revisited as report-QA / diagnosis tasks (non-execution-based).

## Detection Mechanism

The TCL script uses `redirect -file` to capture SDC source output, then checks:

1. Source output for `Error:`, `Can't find`, or `unknown command` patterns
2. `all_clocks` returns at least one clock
3. All design ports resolve via `get_ports`
4. `compile_ultra` succeeds

Markers:
- `CONSTRAINTS_OK` — all checks passed
- `CONSTRAINTS_FAIL: reason1,reason2` — one or more checks failed

The evaluator uses `^CONSTRAINTS_OK` (anchored) to avoid matching echoed TCL code.

## RTL Templates

10 small synthesizable templates (`compile_ultra` with `lsi_10k.db`):

- `counter` — 8-bit counter with enable
- `updown_counter` — up/down counter
- `accumulator` — accumulator register
- `shift_reg` — shift register
- `adder_pipe` — pipelined adder
- `alu_reg` — registered ALU
- `comparator_reg` — registered comparator
- `decoder_reg` — registered decoder
- `mux_reg` — mux + register
- `fsm_ctrl` — 3-state FSM controller

## Scoring

| Component | Weight | Description |
|-----------|--------|-------------|
| constraint_pass | 0.6 | CONSTRAINTS_OK marker present |
| execution_pass | 0.3 | DC ran and constraints passed |
| explanation | 0.1 | Always 1.0 in submission mode |

## Tool Requirements

- Design Compiler (`dc_shell`) — optional for unit tests, required for execution
- Standard cell library (`lsi_10k.db`) from Synopsys default installation

## Known Limitations

- DC is lenient with many constraint issues; only 6 categories produce detectable failures
- Scale: 61 tasks (1 smoke + 60 generated, 6 bug categories × 10 RTL templates)
- No Spectre dialect support
- No agentic runner integration yet
