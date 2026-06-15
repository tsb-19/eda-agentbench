**English | [中文](p7_primetime_sta_debug.zh.md)**

# P7 PrimeTime STA Debug

**Goal**: Fix a buggy SDC constraint file so PrimeTime STA timing checks pass.

**What it measures**: The agent's ability to diagnose SDC constraint bugs using PrimeTime timing analysis feedback and produce correct constraint repairs.

**Track ID**: `p7_primetime_sta_debug`

**Tool**: PrimeTime (pt_shell)

**Evaluation**: Execution-based — the TCL run script validates constraints via PrimeTime and emits markers.

## Task Structure

```
pt_sta_debug_NNNN/
  metadata.json
  prompt.md
  files/
    design.v            # RTL design (visible, read-only)
    constraints.sdc      # Buggy SDC (visible, editable)
    run_public.sh        # Public run script (visible, read-only)
    run_public.tcl       # PrimeTime TCL script (visible, read-only)
  hidden/
    design_netlist.v     # Structural netlist for PT (hidden)
    run_hidden.sh        # Hidden run script
    run_hidden.tcl       # Hidden PrimeTime TCL script
  solution/
    constraints.sdc      # Correct SDC
```

## Bug Categories (4 reliable)

| Bug Type | Description | Difficulty | Detection Method |
|----------|-------------|------------|------------------|
| missing_clock | Missing `create_clock` definition | easy | `all_clocks` empty → `no_clocks_created` |
| wrong_port_name | Typo in port reference | easy | Source log `Can't find` → `port_or_clock_not_found` |
| syntax_error | Missing bracket in SDC | easy | Source log `Error:` → `pt_error_in_source` |
| invalid_get_ports | Nonexistent port pattern | medium | Source log `Can't find` → `port_or_clock_not_found` |

### Deferred Categories

These categories were considered but deferred because PrimeTime accepts them silently or detection is non-deterministic:

- `wrong_period` — PT accepts any period value; no structural check detects it
- `missing_input_delay` — PT accepts missing delays
- `missing_output_delay` — PT accepts missing delays
- `false_path_too_broad` — requires real timing data
- `multicycle_path_error` — requires real timing data
- `wrong_uncertainty` — PT accepts, only shifts numbers slightly

## Design Templates

13 RTL templates, each paired with a corresponding DFF-based structural netlist:

| Template | Description |
|----------|-------------|
| counter | 8-bit counter |
| updown_counter | up/down counter |
| mod10_counter | modulo-10 counter |
| accumulator | accumulator register |
| toggle_ff | toggle flip-flop |
| shift_reg | shift register |
| parity_reg | registered parity |
| adder_pipe | pipelined adder |
| alu_reg | registered ALU |
| comparator_reg | registered comparator |
| decoder_reg | registered decoder |
| mux_reg | mux + register |
| fsm_ctrl | FSM controller |

## Scoring

| Component | Weight | Description |
|-----------|--------|-------------|
| timing_check | 0.6 | TCL validation markers (TIMING_CHECK_OK / TIMING_CHECK_FAIL) |
| execution_pass | 0.3 | pt_shell execution completed successfully |
| explanation | 0.1 | Always 1.0 in submission mode |

## TCL Validation Script

The TCL script performs these checks after sourcing the SDC:

1. Scans source log for `Error:`, `Can't find`, `unknown command`
2. Verifies at least one clock is created (`all_clocks`)
3. Verifies expected clock name exists in `all_clocks` collection
4. Verifies all design ports resolve (`get_ports`)
5. Verifies `report_timing` succeeds (valid timing graph)
6. Emits `TIMING_CHECK_OK` or `TIMING_CHECK_FAIL: <reasons>`

## PrimeTime Integration

- Uses structural Verilog netlists (DFFX1 primitives) that PrimeTime can read via `read_verilog` + `link_design`
- The netlist is a hidden file — the agent only sees the RTL and SDC
- The bash script checks for `pt_shell` availability and skips gracefully if not found

## Smoke Test

```bash
bash scripts/run_primetime_sta_debug_smoke.sh
```

Expected results:
- Solution mode: score = 1.0 (with PrimeTime available)
- Buggy mode: score < 1.0 (only explanation component passes)
- Graceful skip if PrimeTime not available

## Generator

```bash
python3 scripts/generate_p7_primetime_sta_debug_tasks.py --count 52 --seed 42
```

Deterministic generation with seed-based period variation (2.0, 3.0, 5.0, 10.0 ns).
Round-robin across 4 bug types and 13 RTL templates (52 unique combinations).

Task ID scheme:
- Smoke: `pt_sta_debug_0000` (generated with `--id-start 0`)
- Generated: `pt_sta_debug_0001` through `pt_sta_debug_0052` (default `--id-start 1`)
