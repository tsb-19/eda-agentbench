**English | [中文](current_v0_status.zh.md)**

# EDA-AgentBench v0 Status

> **⚠️ Frozen historical snapshot.** This documents the v0 milestone (1113 tasks,
> commit `960677c`) and is kept for reference only. For the live benchmark status
> (Phase 8A, 2710 tasks) see [current_status.md](current_status.md).

**Checkpoint commit:** `960677c`

## Task Inventory

| Track | Count | Tool(s) | Source |
|-------|-------|---------|--------|
| P1 RTL Debug | 1001 | VCS | 1 handcrafted + 1000 generated |
| P4 SPICE Sim | 102 | HSPICE, Spectre | 2 smoke + 100 generated |
| P5 SPICE Deck Debug | 10 | HSPICE | Imported from external bundle |
| **Total** | **1113** | | |

### P1 Bug Type Distribution

10 bug types, 10 tasks each:

| Bug Type | Count |
|----------|-------|
| sensitivity_list | 10 |
| blocking_nonblocking | 10 |
| reset_polarity | 10 |
| width_truncation | 10 |
| comparison_boundary | 10 |
| wrong_mux_select | 10 |
| priority_order | 10 |
| fsm_transition_error | 10 |
| counter_off_by_one | 10 |
| enable_condition | 10 |

### P4 Configuration Distribution

5 RC parameter sets, each generating 1 HSPICE + 1 Spectre task:

| Config | R_bug | R_sol | C |
|--------|-------|-------|------|
| 0 | 10k | 1.2k | 10p |
| 1 | 22k | 2.2k | 4.7p |
| 2 | 4.7k | 560 | 22p |
| 3 | 15k | 1.5k | 6.8p |
| 4 | 33k | 3.3k | 3.3p |

## Test Suite

- **63** pytest tests
- **5** RTL smoke tests (`scripts/run_smoke.sh`)
- **7** HSPICE smoke tests (`scripts/run_spice_smoke.sh`)
- **12** Spectre smoke tests (`scripts/run_spectre_smoke.sh`)
- **15** dataset smoke tests (`scripts/evaluate_dataset_smoke.sh`)

## Dataset Evaluation Results

| Mode | Tasks | Avg Score | Buggy Lower |
|------|-------|-----------|-------------|
| Solution | 113/113 | 1.00 | N/A |
| Buggy | 113/113 | 0.51 | 113/113 |

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

1. **No agentic runner**: only submission/workspace mode. Agent cannot run tools during evaluation.
2. **No LLM API integration**: explanation scoring defaults to 1.0 in submission mode.
3. **No P2 RTL generation track**: tasks are debug-only, not generation.
4. **No P5 timing track** (note: P5 is SPICE Deck Debug, not timing)
5. **No P6 lint track**: no SpyGlass tasks.
6. **No P7 physical track**: no ICC2/Innovus/StarRC/Sentaurus tasks.
7. **P4 is RC-filter only**: single circuit topology, no op-amp or digital SPICE tasks.
8. **P5 is execution-only**: 10 tasks from external bundle, no generated tasks yet.
9. **No `generate` CLI command**: generation requires running Python scripts directly.
10. **Python 3.9**: uses `from __future__ import annotations` for forward references.
11. **Spectre measurement**: uses `-format nutascii` + Python waveform parsing (Spectre 21.1 lacks `.measure` support).
