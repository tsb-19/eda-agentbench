# EDA-AgentBench Dataset Card

## Summary

EDA-AgentBench is a benchmark for evaluating LLMs and coding agents on realistic EDA (Electronic Design Automation) workflows using commercial Synopsys and Cadence tools. It measures whether an agent can correctly modify RTL designs, SPICE netlists, and simulation decks to pass tool-based verification.

## Dataset Composition

| Track | Count | Tool(s) | Data Type | Scoring Method |
|-------|-------|---------|-----------|----------------|
| P1 RTL Debug | 1001 | VCS | mutation_synthetic | compile + public test + hidden test + explanation |
| P2 Testbench/SVA Gen | 21 | VCS | mutation_synthetic | compile + golden_pass + mutant_1 + mutant_2 |
| P3 Timing Report QA | 1000 | pt (synthetic) | template_synthetic | answer_match |
| P4 SPICE Sim | 102 | HSPICE, Spectre | template_synthetic | tool run + output + public metric + hidden metric + explanation |
| P5 SPICE Deck Debug | 10 | HSPICE | mutation_synthetic | execution-based (exit code + no fatal errors) + explanation |
| **Total** | **2134** | | | |

### P1 RTL Debug (1001 tasks)

- 1 handcrafted smoke task
- 1000 generated tasks: 10 bug types x 100 tasks each
- Data type: `mutation_synthetic` (bugs injected into correct designs)

| Bug Type | Count | Description |
|----------|-------|-------------|
| sensitivity_list | 100 | Incomplete `always @(*)` sensitivity |
| blocking_nonblocking | 100 | Wrong `=` vs `<=` usage |
| reset_polarity | 100 | Active-high vs active-low mismatch |
| width_truncation | 100 | Port width mismatch causing data loss |
| comparison_boundary | 100 | Off-by-one in comparisons |
| wrong_mux_select | 100 | Incorrect mux case/select signal |
| priority_order | 100 | Wrong if-else priority |
| fsm_transition_error | 100 | Incorrect state transition |
| counter_off_by_one | 100 | Counter boundary error |
| enable_condition | 100 | Missing or wrong enable guard |

### P2 Testbench/SVA Generation (21 tasks)

- 1 smoke task + 20 generated tasks
- Data type: `mutation_synthetic` (golden design + 2 mutants per task)
- Agent writes a testbench that passes on golden design and catches both mutants
- Scoring: compile (0.2) + golden_pass (0.4) + mutant_1 (0.2) + mutant_2 (0.2)

### P3 Timing Report QA (1000 tasks)

- 1 smoke task + 999 generated tasks
- Data type: `template_synthetic` (synthetic normalized timing reports)
- Agent answers questions about timing report fields (WNS, TNS, slack, etc.)
- 10 question types with round-robin distribution (99–100 each)
- 30 unique clocks, 15 path groups, ~30% multi-clock reports
- No real PrimeTime tool required (uses synthetic reports)
- Scoring: answer_match (1.0)

### P4 SPICE Sim (102 tasks)

- 2 smoke tasks (1 HSPICE, 1 Spectre)
- 100 generated tasks: 50 HSPICE + 50 Spectre
- Data type: `template_synthetic` (RC filter circuits with parameterized component values)

Each task fixes an RC filter circuit to meet rise/fall time specifications. The buggy version has a resistance value that is 5-10x too high, causing slow edges. The solution replaces it with the correct resistance.

### P5 SPICE Deck Debug (10 tasks)

- 10 imported tasks from external debug-contrast validated bundle
- Data type: `mutation_synthetic` (structural/syntax errors injected into valid decks)

| Error Category | Count | Description |
|----------------|-------|-------------|
| missing_model | 2 | References undefined MOSFET/diode model |
| missing_subckt | 2 | References undefined subcircuit |
| duplicate_element | 2 | Two elements share the same name |
| wrong_pin_count | 1 | Subcircuit instance has wrong pin count |
| missing_include | 1 | .include references nonexistent file |
| unsupported_dialect | 1 | Model level not supported by HSPICE |
| invalid_directive | 1 | Malformed .include (no filename) |

## Evaluation Modes

Each task supports two submission modes for validation:

- **Solution mode**: the task's `solution/` directory is the submission. Expected: all tasks score 1.00.
- **Buggy mode**: the task's visible/editable files (the buggy original) are the submission. Expected: all tasks score < 1.00.

These modes validate that tasks are well-calibrated: correct answers always pass, buggy baselines always fail.

## Current Validation Results

| Mode | Tasks | Avg Score | Buggy Lower |
|------|-------|-----------|-------------|
| Solution | 2134/2134 | 1.00 | N/A |
| Buggy | 2134/2134 | < 1.00 | 2134/2134 |

## Test Suite

- 187 pytest tests (all passing, 2 skipped)
- Smoke scripts per track (VCS, P2, P3, HSPICE, Spectre, P5)
- Dataset evaluation smoke (all tracks)

## File Visibility

| Category | Agent Can Read? | Agent Can Edit? | Used in Scoring? |
|----------|----------------|-----------------|-------------------|
| visible | Yes | No (unless also editable) | Yes |
| editable | Yes | Yes | Yes |
| hidden | No | No | Yes |
| forbidden | No | No | Checked for tampering |

## Known Limitations

1. No agentic runner yet (submission/workspace mode only).
2. P1 and P4 use exact solution matching; P5 accepts any functionally correct fix.
3. P4 covers RC filter topology only (no op-amp or digital SPICE).
4. P5 has 10 tasks (small set, execution-validated).
5. No LLM API integration for explanation scoring in submission mode.

## Intended Use

This benchmark is designed for:

- Evaluating LLM/agent ability to perform EDA engineering tasks
- Comparing models on tool-grounded code repair and optimization
- Research on agentic workflows for hardware design

This benchmark is NOT designed for:

- Trivia-style EDA knowledge questions
- Tasks that can be solved without running EDA tools
- Training data (tasks are synthetic, not from real designs)

## Ethical Considerations

- All tasks use synthetic designs; no real IP is included.
- Commercial EDA tool outputs are sanitized before storage.
- Logs strip usernames, hostnames, absolute paths, and license server names.
- No API keys or credentials are stored in task files.
