# EDA-AgentBench

A benchmark for evaluating LLMs and coding agents on realistic EDA workflows using commercial Synopsys and Cadence tools.

## What It Measures

EDA-AgentBench tests whether an agent can:

- Debug RTL designs with simulation feedback (VCS)
- Fix SPICE netlists to meet timing specifications (HSPICE, Spectre)
- (Future) Generate RTL, diagnose EDA logs, run timing closure, lint, and physical design

All tasks use **commercial EDA tools** only. No open-source EDA tools are required.

## Current Coverage (Phase 5B — P2 Scale-Up)

| Track | Tasks | Tool(s) | Description |
|-------|-------|---------|-------------|
| P1 RTL Debug | 1001 | VCS | Fix buggy SystemVerilog designs |
| P2 Testbench/SVA Gen | 101 | VCS | Write testbenches that catch RTL mutants |
| P3 Timing Report QA | 101 | pt (synthetic) | Answer questions about timing reports |
| P4 SPICE Sim | 102 | HSPICE, Spectre | Fix RC filter rise/fall time |
| P5 SPICE Deck Debug | 10 | HSPICE | Fix broken SPICE simulation decks |
| **Total** | **1315** | | |

- 1001 P1 tasks: 1 handcrafted smoke + 1000 generated (10 bug types x 100 each)
- 101 P2 tasks: 1 smoke + 100 generated (10 design templates, 20 mutant variants)
- 101 P3 tasks: 1 smoke + 100 generated (synthetic normalized timing reports)
- 102 P4 tasks: 2 smoke (1 HSPICE, 1 Spectre) + 100 generated (50 HSPICE, 50 Spectre)
- 10 P5 tasks: imported from external debug-contrast validated bundle (7 error categories)

## Tool Dependencies

| Tool | Vendor | Used By |
|------|--------|---------|
| VCS | Synopsys | P1 RTL Debug, P2 Testbench/SVA Gen |
| HSPICE | Synopsys | P4 SPICE Sim, P5 SPICE Deck Debug |
| Spectre | Cadence | P4 SPICE Sim |
| PrimeTime | Synopsys | P3 Timing Report QA (synthetic reports, no real tool needed) |

Expected install paths:

- Synopsys: `/EDA/soft2/synopsys/`
- Cadence: `/EDA/soft2/cadence/`

The benchmark probes the filesystem for tools at runtime. No hardcoded paths in task definitions.

## Installation

```bash
pip install -e ".[test]"
```

## Quick Start

### 1. Detect Tools

```bash
eda-bench detect-tools
```

Expected output: table showing VCS, HSPICE, Spectre availability.

### 2. Run Smoke Tests

```bash
# RTL Debug smoke (VCS)
bash scripts/run_smoke.sh

# SPICE smoke (HSPICE)
bash scripts/run_spice_smoke.sh

# Spectre smoke
bash scripts/run_spectre_smoke.sh

# Dataset smoke (all tracks)
bash scripts/evaluate_dataset_smoke.sh
```

### 3. Validate a Task

```bash
eda-bench validate-task tasks/p1_rtl_debug/task_000001
```

## Evaluating Tasks

### Single Task

```bash
# With correct solution (should score 1.00)
eda-bench evaluate-task tasks/p1_rtl_debug/task_000001 \
    --submission tasks/p1_rtl_debug/task_000001/solution

# With buggy baseline (should score < 1.00)
eda-bench evaluate-task tasks/p1_rtl_debug/task_000001 \
    --submission tasks/p1_rtl_debug/task_000001/files
```

### Full Dataset

```bash
# Solution mode: every task uses its own solution/ as submission
eda-bench evaluate-dataset tasks --submission-mode solution

# Buggy mode: every task uses its own files/ (buggy) as submission
eda-bench evaluate-dataset tasks --submission-mode buggy

# Filter by track
eda-bench evaluate-dataset tasks --submission-mode solution --track p1_rtl_debug
```

### Fast Sampled Evaluation

For quick integration checks (runs in ~2 minutes instead of ~50 minutes):

```bash
# Sample 1 task per track (covers all 5 tracks)
eda-bench evaluate-dataset tasks --sample-per-track 1 --seed 42 --submission-mode solution
eda-bench evaluate-dataset tasks --sample-per-track 1 --seed 42 --submission-mode buggy

# Evaluate at most 10 tasks total
eda-bench evaluate-dataset tasks --limit 10 --seed 42 --submission-mode solution

# Full integration smoke (solution + buggy sampled)
bash scripts/evaluate_dataset_fast.sh
```

**Warning:** Sampled evaluation is not a substitute for full evaluation. Use it for fast iteration during development; run full evaluation before final validation.

### Report

```bash
# Generate all report formats (terminal + JSON + markdown)
eda-bench report runs/dataset_XXXXXXXX --format all
```

## Expected Results

| Mode | Tasks | Avg Score | Notes |
|------|-------|-----------|-------|
| Solution | 1315/1315 | 1.00 | Correct answer always scores perfect |
| Buggy | 1315/1315 | < 1.00 | Buggy baseline always scores < 1.00 |

## Task Structure

Standard layout (P1, P2, P4):
```
task_xxxxxx/
  prompt.md           # Human-readable task description
  metadata.json       # Machine-readable task specification
  files/              # Visible to agent
    design.sv         # Editable (RTL) or circuit.sp (SPICE)
    tb_public.sv      # Public testbench (read-only)
    run_public.sh     # Public test script (read-only)
  hidden/             # Used for scoring only
    tb_hidden.sv      # Hidden testbench
    run_hidden.sh     # Hidden test script
  solution/           # Correct answer
    design.sv
```

External bundle layout (P5):
```
spice_deck_debug_NNNN/
  prompt.md
  metadata.json
  grader_contract.json
  visible/            # Buggy deck (editable)
  hidden/             # Golden fixed deck
  oracle/             # Human-readable answer
  validation/         # Validation records
```

## Scoring

Each task produces a `score.json` with weighted components:

**RTL Debug (P1):**
- compile: 0.2
- public_test: 0.3
- hidden_test: 0.4
- explanation: 0.1

**Testbench/SVA Gen (P2):**
- compile: 0.2
- golden_pass: 0.4
- mutant_1: 0.2
- mutant_2: 0.2

**Timing Report QA (P3):**
- answer_match: 1.0

**SPICE Sim (P4):**
- tool_run: 0.3
- output_generated: 0.2
- public_metric: 0.2
- hidden_metric: 0.2
- explanation: 0.1

**SPICE Deck Debug (P5):**
- execution_pass: 0.9
- explanation: 0.1

Pass threshold: 0.5. See [docs/scoring.md](docs/scoring.md) for details.

## Anti-Cheat

The evaluator snapshots SHA-256 hashes of forbidden files (testbenches, run scripts) before execution and verifies them after. Modifications to forbidden files cause evaluation failure.

## Log Sanitization

All tool output logs are sanitized before storage: usernames, hostnames, absolute paths, and license server names are replaced with stable placeholders.

## Runs Directory

The `runs/` directory is not committed to git. All evaluation artifacts (score.json, logs, workspaces) are written there locally.

## Documentation

- [Benchmark Tracks](docs/benchmark_tracks.md) — Detailed track descriptions and scoring
- [Dataset Card](docs/datacard.md) — Dataset composition and validation results
- [Current Status](docs/current_status.md) — Phase 3C status and known limitations
- [Reproducibility](docs/reproducibility.md) — Deterministic generation and evaluation
- [Public Release Policy](docs/public_release_policy.md) — Release checklist and exclusions
- [Commercial Tool Policy](docs/commercial_tool_policy.md) — Supported tools and licensing
- [Benchmark Specification](docs/benchmark_spec.md) — Overall design and evaluation model
- [Task Schema](docs/task_schema.md) — metadata.json field reference
- [Scoring Rules](docs/scoring.md) — How tasks are scored
- [Adding Tasks](docs/adding_tasks.md) — How to create new tasks
- [Roadmap](docs/roadmap.md) — Future phases

## License

TBD
