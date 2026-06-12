# Benchmark Tracks

## Track Overview

| Track | ID | Count | Tool(s) | Purpose | Scoring |
|-------|----|-------|---------|---------|---------|
| P1 RTL Debug | `p1_rtl_debug` | 1001 | VCS | Code repair using simulation feedback | Compile + public test + hidden test + explanation |
| P2 Testbench/SVA Gen | `p2_tb_sva_gen` | 101 | VCS | Testbench/SVA generation for RTL verification | Compile + golden_pass + mutant_1 + mutant_2 |
| P3 Timing Report QA | `p3_timing_report_qa` | 1008 | pt (synthetic) | Timing report field extraction and QA | Answer match |
| P4 SPICE Sim | `p4_spice_sim` | 102 | HSPICE, Spectre | Metric-driven RC/SPICE optimization | Tool run + output + public metric + hidden metric + explanation |
| P5 SPICE Deck Debug | `p5_spice_deck_debug` | 100 | HSPICE | Execution-based netlist/deck repair | Execution pass + explanation |

## P1: RTL Debug

**Goal**: Fix a buggy SystemVerilog design so it passes both public and hidden testbenches under VCS simulation.

**What it measures**: The agent's ability to diagnose RTL bugs using simulation feedback (compile errors, test failures) and produce correct repairs.

**Task structure**:
- `design.sv` — buggy RTL (editable by agent)
- `tb_public.sv` — public testbench (2-3 test cases, visible to agent)
- `tb_hidden.sv` — hidden testbench (1-2 test cases, agent never sees)
- `run_public.sh` / `run_hidden.sh` — VCS compile-and-sim scripts

**Bug types** (10 types, 100 tasks each):

| Bug Type | Description | Difficulty Range |
|----------|-------------|------------------|
| sensitivity_list | Incomplete `always @(*)` sensitivity | easy–medium |
| blocking_nonblocking | Wrong `=` vs `<=` usage | easy–medium |
| reset_polarity | Active-high vs active-low mismatch | easy |
| width_truncation | Port width mismatch | medium |
| comparison_boundary | Off-by-one in comparisons | medium |
| wrong_mux_select | Incorrect mux select signal | medium |
| priority_order | Wrong if-else priority | medium–hard |
| fsm_transition_error | Incorrect state transition | hard |
| counter_off_by_one | Counter boundary error | medium |
| enable_condition | Missing or wrong enable guard | easy–medium |

**Scoring weights**:
```json
{
  "compile": 0.2,
  "public_test": 0.3,
  "hidden_test": 0.4,
  "explanation": 0.1
}
```

**Pass condition**: `total_score >= 0.5`

**Validation**: Solution mode scores 1.00; buggy mode scores < 1.00 for all 1001 tasks.

## P2: Testbench/SVA Generation

**Goal**: Write a SystemVerilog testbench that verifies a golden RTL design and catches known mutants.

**What it measures**: The agent's ability to write effective verification code — testbenches or SVA assertions — that detect design bugs through simulation.

**Task structure**:
- `design_golden.sv` — correct RTL design (visible, read-only)
- `tb.sv` — empty testbench template (editable by agent)
- `design_mutant1.sv` / `design_mutant2.sv` — buggy designs (hidden, for scoring)
- `run_public.sh` — compiles and simulates with golden design
- `run_hidden.sh` — compiles and simulates with mutant designs

**Scoring**: Mutation-based grading:
1. Compile: testbench compiles with VCS (0.2)
2. Golden pass: testbench passes on golden design (0.4)
3. Mutant 1: testbench catches first mutant (0.2)
4. Mutant 2: testbench catches second mutant (0.2)

**Scoring weights**:
```json
{
  "compile": 0.2,
  "golden_pass": 0.4,
  "mutant_1": 0.2,
  "mutant_2": 0.2
}
```

**Note**: Track ID was renamed from `p2_rtl_gen` to `p2_tb_sva_gen` in Phase 4E. Old metadata referencing `rtl_gen.RTLGenEvaluator` is still accepted via compatibility shim.

**Validation**: Solution mode scores 1.00; buggy mode scores 0.20 for all 101 tasks.

## P3: Timing Report QA

**Goal**: Answer questions about timing report fields (WNS, TNS, slack, etc.) from synthetic normalized timing reports.

**What it measures**: The agent's ability to parse and extract information from EDA timing reports — a key skill for timing closure workflows.

**Task structure**:
- `timing_report.rpt` — synthetic normalized timing report (visible, read-only)
- `answer.txt` — empty answer file (editable by agent)
- `solution/answer.txt` — correct answer

**Key design choice**: Uses synthetic normalized reports instead of real PrimeTime output. This allows the track to work without a PrimeTime license while still testing the same parsing skills.

**Diversity**:
- 30 unique clock names, 15 path groups, 50 module names, 27 instance prefixes
- ~30% multi-clock reports (different clocks per path)
- Path counts: 3–50, WNS range: -5.0 to -0.01, TNS range: -75 to -0.3
- Signal names with hierarchical depth and optional bit indices
- 10 question types with round-robin distribution (99–100 each)

**Scoring**:
```json
{
  "answer_match": 1.0
}
```

**Validation**: Solution mode scores 1.00; buggy mode scores 0.00 for all 1000 tasks.

## P4: SPICE Sim

**Goal**: Fix a buggy RC filter SPICE netlist so that the rise time and fall time measurements meet specification ranges.

**What it measures**: The agent's ability to diagnose analog circuit issues using HSPICE or Spectre simulation feedback and optimize component values.

**Task structure**:
- `circuit.sp` (HSPICE) or `circuit.scs` (Spectre) — buggy netlist (editable)
- `run_public.sh` — runs simulation, extracts public measurement
- `run_hidden.sh` — runs simulation, extracts hidden measurement
- `solution/` — correct netlist with proper R/C values

**Circuit**: Single-stage RC lowpass filter. Buggy version has R_bug (5-10x too high), solution has R_sol (correct value).

**Generated configurations** (5 RC parameter sets, each producing 1 HSPICE + 1 Spectre task = 10 generated pairs, 50 of each tool):

| Config | R_bug | R_sol | C |
|--------|-------|-------|------|
| 0 | 10k | 1.2k | 10p |
| 1 | 22k | 2.2k | 4.7p |
| 2 | 4.7k | 560 | 22p |
| 3 | 15k | 1.5k | 6.8p |
| 4 | 33k | 3.3k | 3.3p |

**Scoring weights**:
```json
{
  "tool_run": 0.3,
  "output_generated": 0.2,
  "public_metric": 0.2,
  "hidden_metric": 0.2,
  "explanation": 0.1
}
```

**Metric extraction**:
- HSPICE: parses `.lis` file for `.measure` results with engineering suffixes
- Spectre: reads `metrics.json` from Python waveform parser (uses `-format nutascii`)

**Validation**: Solution mode scores 1.00; buggy mode scores < 1.00 for all 102 tasks.

## P5: SPICE Deck Debug

**Goal**: Fix a SPICE simulation deck that HSPICE rejects due to syntax or structural errors.

**What it measures**: The agent's ability to diagnose and fix netlist-level errors (missing models, wrong pin counts, duplicate elements, etc.) using HSPICE error messages as feedback.

**Key difference from P4**: P4 tasks have correct syntax but wrong component values. P5 tasks have broken syntax/structure that prevents the simulator from running at all.

**Task structure** (external bundle layout):
- `visible/*_bug.sp` — buggy deck (editable)
- `hidden/*_fixed.sp` — golden fixed deck (for solution mode)
- `oracle/answer.md` — human-readable expected fix
- `grader_contract.json` — execution-based grading rules
- `validation/` — debug-contrast validation records

**Scoring**: Execution-based, not exact diff matching:
1. Run HSPICE on submitted deck
2. Check exit code == 0
3. Check for no fatal error patterns from `grader_contract.json`
4. Pass if both conditions met

**Scoring weights**:
```json
{
  "execution_pass": 0.9,
  "explanation": 0.1
}
```

**Error categories** (100 tasks total):

| Category | Count | Description |
|----------|-------|-------------|
| missing_model | 15 | References undefined MOSFET/diode model |
| duplicate_element | 15 | Two elements share the same name |
| missing_subckt | 14 | References undefined subcircuit |
| wrong_pin_count | 14 | Subcircuit instance has wrong pin count |
| missing_include | 14 | .include references nonexistent file |
| unsupported_dialect | 14 | Model level not supported by HSPICE |
| invalid_directive | 14 | Malformed .include (no filename) |

**Why exact diff is not required**: A SPICE deck can be fixed in multiple valid ways. Any syntactically valid fix that HSPICE can execute is accepted.

## Future Tracks (Planned)

| Track | ID | Tool(s) | Status |
|-------|----|---------|--------|
| P5 Spectre dialect | `p5_spice_deck_debug` | Spectre | Spectre dialect repair |
| P6 SpyGlass Lint | `p6_lint` | SpyGlass | Future |
| P7 Physical Design | `p7_physical` | ICC2/Innovus/StarRC | Future |
