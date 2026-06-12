# Current Benchmark Status

**Phase**: 5A — P3 scaled to 1000 tasks

## Task Inventory

| Track | Count | Tool(s) | Source |
|-------|-------|---------|--------|
| P1 RTL Debug | 1001 | VCS | 1 handcrafted + 1000 generated |
| P2 Testbench/SVA Gen | 21 | VCS | 1 smoke + 20 generated |
| P3 Timing Report QA | 1000 | pt (synthetic) | 1 smoke + 999 generated |
| P4 SPICE Sim | 102 | HSPICE, Spectre | 2 smoke + 100 generated |
| P5 SPICE Deck Debug | 10 | HSPICE | Imported from external bundle |
| **Total** | **2134** | | |

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

## P2 Testbench/SVA Generation

21 tasks (1 smoke + 20 generated). Mutation-based grading:
- Agent writes a testbench for a golden RTL design
- Testbench must pass on golden design and catch 2 mutants
- Scoring: compile (0.2) + golden_pass (0.4) + mutant_1 (0.2) + mutant_2 (0.2)

## P3 Timing Report QA

1000 tasks (1 smoke + 999 generated). Synthetic normalized reports:
- Agent answers questions about timing report fields (WNS, TNS, slack, etc.)
- 10 question types with round-robin distribution (99–100 each)
- 30 unique clocks, 15 path groups, ~30% multi-clock reports
- Path counts 3–50, WNS range -5.0 to -0.01, TNS range -75 to -0.3
- Scoring: answer_match (1.0)
- No real PrimeTime tool required (uses synthetic reports)
- Full solution evaluation: 1000/1000 = 1.00

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
| pytest tests | 187 | All passing (2 skipped) |
| RTL smoke tests | 5 | Passing |
| P2 smoke tests | 4 | Passing |
| P3 smoke tests | 7 | Passing |
| HSPICE smoke tests | 7 | Passing |
| Spectre smoke tests | 12 | Passing |
| P5 batch evaluation | 10/10 + 10/10 | Passing |

## Dataset Evaluation Results

| Mode | Tasks | Avg Score | Buggy Lower |
|------|-------|-----------|-------------|
| Solution | 2134/2134 | 1.00 | N/A |
| Buggy | 2134/2134 | < 1.00 | 2134/2134 |

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
3. P2 naming was cleaned up in Phase 4E: `p2_tb_sva_gen` track, `tb_sva_gen.TBSVAGenEvaluator`.
4. P3 uses `tool: ["pt"]` in metadata but skips tool detection (synthetic reports, no real PrimeTime).
5. No P6 lint track (no SpyGlass tasks).
6. No P7 physical track (no ICC2/Innovus/StarRC/Sentaurus tasks).
7. P4 is RC-filter only (single circuit topology).
8. P5 has 10 tasks (small set, execution-validated).
9. No `generate` CLI command (generation requires running Python scripts directly).
10. Spectre measurement uses `-format nutascii` + Python waveform parsing.

## Next Phases

- **Phase 4A**: P2 Testbench/SVA Generation — DONE
- **Phase 4B**: P3 Timing Report QA — DONE
- **Phase 4C**: Docs/Datacard/Release Policy — DONE
- **Phase 4D**: Integration audit — DONE
