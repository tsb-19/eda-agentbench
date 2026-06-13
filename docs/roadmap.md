**English | [中文](roadmap.zh.md)**

# Roadmap

## Completed

- **Phase 0 (P0)**: Unified benchmark harness, CLI, schema, evaluators
- **Phase 1 (P1)**: RTL Debug smoke task + 100 generated tasks
- **Phase 2A-C**: HSPICE smoke, Spectre smoke, SPICE evaluator
- **Phase 2D**: Dataset evaluation and report CLI
- **Phase 2E**: Controlled scaling to 113 tasks

## Next Phases (Suggested)

### Phase 3A: P2 RTL Generation

- Tasks where the agent writes RTL from a specification
- Smoke: simple combinational module (adder, mux, decoder)
- Generator: template-based with parameterized specs
- Scoring: compile + public test + hidden test + explanation

### Phase 3B: Agentic Runner

- Sandboxed workspace execution with tool-call limits
- Agent can read files, edit allowed files, run commands
- Resource enforcement: wall time, token count, tool calls
- Submission mode preserved as fallback

### Phase 3C: P5 Timing / DC / PrimeTime

- Tasks involving SDC constraints, timing reports, synthesis
- Tools: Design Compiler, PrimeTime
- Smoke: fix a timing violation in a small gate-level netlist

### Phase 3D: P6 SpyGlass Lint

- Tasks where the agent fixes lint violations
- Tool: SpyGlass
- Smoke: resolve a CDC or RDC lint warning

### Phase 3E: LLM / API Integration

- Explanation scoring via LLM judge
- API endpoint for programmatic submission
- Leaderboard infrastructure

### Phase 3F: Larger-Scale Generation

- 1000+ tasks per track
- Randomized circuit parameters (not just 5 configs)
- Multiple circuit topologies for P4
- Flow-synthetic tasks from real EDA runs
