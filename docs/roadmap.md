**English | [中文](roadmap.zh.md)**

# Roadmap

## Completed

- **Phase 0 (P0)**: Unified benchmark harness, CLI, schema, evaluators
- **Phase 1 (P1)**: RTL Debug (1001 tasks: 1 handcrafted + 1000 generated)
- **Phase 2A–E**: HSPICE/Spectre smoke, SPICE evaluator, dataset + report CLI, controlled scaling
- **Phase 4A–F**: P2 Testbench/SVA Gen, P3 Timing Report QA, docs/datacard/release policy, integration audit, P2 naming cleanup, sampled evaluation mode
- **Phase 5A/B/E/F**: P3 scaled to 1008, P2 scaled to 101, PrimeTime prototype (8 tasks), P5 scaled to 100
- **Phase 6A/B/C/D**: P4 scaled to 302 (RC rise/fall + RLC), P6 DC Synthesis QA (51), P6 DC Constraint Debug (13), baseline runner + leaderboard
- **Phase 7A/B/C**: P7 SpyGlass Lint Debug (16), P7 PrimeTime STA Debug (17), Agentic Runner MVP
- **Phase 8A**: P8 PnR Report QA prototype (101 tasks)

Total: **2710 tasks across 10 tracks**. See [current_status.md](current_status.md) for the live inventory.

## Next Phases

### Scale the debug prototypes
- P6 DC Constraint Debug: scale to 50+ tasks
- P7 SpyGlass Lint Debug: scale to 50+ tasks
- P7 PrimeTime STA Debug: scale to 50+ tasks

### P5 Spectre dialect
- Spectre-dialect SPICE deck repair (P5 is currently HSPICE only)

### Expert physical-design tracks
- ICC2 / Innovus place-and-route execution tasks (beyond P8 report QA)
- StarRC parasitic extraction
- Sentaurus TCAD

### Agentic + scoring infrastructure
- Interactive agentic loop with per-tool-call transcripts (beyond the current MVP)
- LLM-judged explanation scoring (currently defaults to 1.0 in submission mode)
- Leaderboard / API submission infrastructure
