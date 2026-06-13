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

## Bug Categories

| Bug | Difficulty | Description |
|-----|-----------|-------------|
| missing_clock | easy | Missing `create_clock` definition |
| wrong_period | medium | Clock period too tight or too loose |
| wrong_port_name | easy | Typo in port name reference |
| invalid_get_ports | medium | Invalid wildcard in `get_ports` |
| missing_input_delay | medium | Missing `set_input_delay` on data port |
| missing_output_delay | medium | Missing `set_output_delay` on output |
| wrong_top_module | hard | Wrong module name in port references |
| syntax_error | easy | Missing bracket or syntax error |
| unsupported_command | medium | Unsupported SDC command |
| tight_constraint | hard | Overly tight timing constraints |

## RTL Templates

- `counter` — 8-bit counter with enable
- `fsm_ctrl` — 3-state FSM controller
- `adder_pipe` — 16-bit pipelined adder
- `mux_reg` — 4:1 registered mux

## Scoring

| Component | Weight | Description |
|-----------|--------|-------------|
| execution_pass | 0.4 | DC ran without crashing |
| check_pass | 0.3 | `check_design` passed |
| synthesis_pass | 0.2 | Synthesis completed |
| explanation | 0.1 | Always 1.0 in submission mode |

## Tool Requirements

- Design Compiler (`dc_shell`) — optional for unit tests, required for execution
- Standard cell library (`lsi_10k.db`) from Synopsys default installation

## Known Limitations

- DC is lenient with constraint issues; some bugs (e.g., missing clock) produce
  warnings but don't cause hard failures. The evaluator uses run script markers
  (`PUBLIC_RESULT: PASS/FAIL`) as the authoritative success indicator.
- Prototype scale: 21 tasks (1 smoke + 20 generated)
- No Spectre dialect support
- No agentic runner integration yet
