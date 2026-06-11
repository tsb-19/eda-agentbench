# Current Benchmark Status

**Phase**: 3C complete

## Task Inventory

| Track | Count | Tool(s) | Source |
|-------|-------|---------|--------|
| P1 RTL Debug | 1001 | VCS | 1 handcrafted + 1000 generated |
| P4 SPICE Sim | 102 | HSPICE, Spectre | 2 smoke + 100 generated |
| P5 SPICE Deck Debug | 10 | HSPICE | Imported from external bundle |
| **Total** | **1113** | | |

## P1 Bug Type Distribution

10 bug types, 100 tasks each:

| Bug Type | Count |
|----------|-------|
| sensitivity_list | 100 |
| blocking_nonblocking | 100 |
| reset_polarity | 100 |
| width_truncation | 100 |
| comparison_boundary | 100 |
| wrong_mux_select | 100 |
| priority_order | 100 |
| fsm_transition_error | 100 |
| counter_off_by_one | 100 |
| enable_condition | 100 |

## P4 Configuration Distribution

100 generated tasks: 50 HSPICE + 50 Spectre from 5 RC parameter sets (10 pairs each):

| Config | R_bug | R_sol | C |
|--------|-------|-------|------|
| 0 | 10k | 1.2k | 10p |
| 1 | 22k | 2.2k | 4.7p |
| 2 | 4.7k | 560 | 22p |
| 3 | 15k | 1.5k | 6.8p |
| 4 | 33k | 3.3k | 3.3p |

Plus 2 smoke tasks (1 HSPICE, 1 Spectre).

## P5 Error Category Distribution

| Category | Count |
|----------|-------|
| missing_model | 2 |
| missing_subckt | 2 |
| duplicate_element | 2 |
| wrong_pin_count | 1 |
| missing_include | 1 |
| unsupported_dialect | 1 |
| invalid_directive | 1 |

## Test Suite

| Category | Count | Status |
|----------|-------|--------|
| pytest tests | 118 | All passing |
| RTL smoke tests | 5 | Passing |
| HSPICE smoke tests | 7 | Passing |
| Spectre smoke tests | 12 | Passing |
| Dataset smoke tests | 15 | Passing |

## Dataset Evaluation Results

| Mode | Tasks | Avg Score | Buggy Lower |
|------|-------|-----------|-------------|
| Solution | 1113/1113 | 1.00 | N/A |
| Buggy | 1113/1113 | < 1.00 | 1113/1113 |

All tasks verified: solution scores perfect, buggy scores strictly less.

## Tools Detected

| Tool | Vendor | Status |
|------|--------|--------|
| VCS | Synopsys | Available |
| HSPICE | Synopsys | Available |
| Spectre | Cadence | Available |

## CLI Commands

| Command | Status |
|---------|--------|
| `eda-bench detect-tools` | Working |
| `eda-bench validate-task` | Working |
| `eda-bench evaluate-task` | Working |
| `eda-bench evaluate-dataset` | Working |
| `eda-bench report` | Working |

## Known Limitations

1. No agentic runner (submission/workspace mode only; agent cannot run tools during evaluation).
2. No LLM API integration (explanation scoring defaults to 1.0 in submission mode).
3. No P2 RTL generation track (tasks are debug-only, not generation).
4. No P3 timing track.
5. No P6 lint track (no SpyGlass tasks).
6. No P7 physical track (no ICC2/Innovus/StarRC/Sentaurus tasks).
7. P4 is RC-filter only (single circuit topology).
8. P5 has 10 tasks (small set, execution-validated).
9. No `generate` CLI command (generation requires running Python scripts directly).
10. Spectre measurement uses `-format nutascii` + Python waveform parsing.

## Next Phases

- **Phase 4A**: P2 Testbench/SVA Generation
- **Phase 4B**: P3 Timing Report QA
- **Phase 4C**: Docs/Datacard/Release Policy (current)
