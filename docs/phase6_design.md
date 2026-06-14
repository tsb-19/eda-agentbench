**English | [中文](phase6_design.zh.md)**

# Phase 6 Design and Benchmark Roadmap

> **Historical planning doc.** Captures the Phase 6 design as of the date below;
> the numbers reflect the v0.3 baseline at that time, not current status. See
> [current_status.md](current_status.md) and [roadmap.md](roadmap.md) for the live state.

**Date**: 2026-06-12
**Baseline**: v0.3 (2312 tasks, 5 tracks, tag v0.3-phase5f-2312)

## Current State

| Track | Tasks | Tools | Grading |
|-------|-------|-------|---------|
| P1 RTL Debug | 1001 | VCS | Execution-based (compile + test) |
| P2 Testbench/SVA Gen | 101 | VCS | Mutation-based (golden + mutant) |
| P3 Timing Report QA | 1008 | pt (synthetic) | Exact match |
| P4 SPICE Sim | 102 | HSPICE, Spectre | Metric extraction |
| P5 SPICE Deck Debug | 100 | HSPICE | Execution-based (exit code) |
| **Total** | **2312** | | |

Key strengths: execution-based grading, deterministic generation, sampled evaluation, anti-cheat.
Key gaps: no synthesis tasks, no physical design, no lint, no CDC, limited analog, no agentic runner.

---

## Candidate Track Evaluation

### 1. PrimeTime STA Debug

**Concept**: Given a gate-level netlist with timing violations, fix setup/hold violations by adjusting constraints, inserting buffers, or modifying RTL.

| Criterion | Assessment |
|-----------|------------|
| Benchmark value | HIGH — timing closure is the #1 bottleneck in real chip design |
| Realism | HIGH — mirrors daily STA debug workflow |
| Execution-based grading | HIGH — run PrimeTime, check WNS/TNS improvement |
| Auto-generation difficulty | MEDIUM — can inject timing violations into netlists by adding delay paths or removing buffers |
| Tool dependency | PrimeTime + Design Compiler (for synthesis) |
| Expected scale | 100–500 tasks |
| Implementation effort | HIGH — requires DC synthesis pipeline, PT wrapper, netlist mutation |

**Verdict**: High value but high effort. Requires synthesis infrastructure first.

### 2. PrimeTime Report QA (Extended)

**Concept**: Expand P3 beyond synthetic reports. Use real PrimeTime output with realistic formatting, multi-corner analysis, clock groups, and exception paths.

| Criterion | Assessment |
|-----------|------------|
| Benchmark value | MEDIUM — P3 already covers core parsing skills |
| Realism | HIGH — real PT output has noise (info lines, warnings, version strings) |
| Execution-based grading | N/A — still text QA, not execution |
| Auto-generation difficulty | LOW — extend existing P3 generator with PT-specific formatting |
| Tool dependency | PrimeTime optional (can handcraft realistic reports) |
| Expected scale | 200–500 additional tasks |
| Implementation effort | LOW — extend P3 generator, add PT-specific question types |

**Verdict**: Quick win if realism matters, but lower marginal value since P3 already has 1008 tasks.

### 3. Design Compiler Synthesis QA

**Concept**: Given RTL + SDC constraints, answer questions about synthesis results (area, timing, cell usage, hierarchy).

| Criterion | Assessment |
|-----------|------------|
| Benchmark value | HIGH — synthesis is a core EDA skill |
| Realism | HIGH — real DC reports are standard industry knowledge |
| Execution-based grading | MEDIUM — can run DC and check area/timing targets |
| Auto-generation difficulty | MEDIUM — need RTL library + constraint generation pipeline |
| Tool dependency | Design Compiler |
| Expected scale | 100–300 tasks |
| Implementation effort | HIGH — DC wrapper, synthesis report parser, constraint generation |

**Verdict**: Valuable but requires DC infrastructure. Consider as a report-QA track first (like P3).

### 4. Design Compiler Constraint Debug

**Concept**: Given broken SDC constraints that cause synthesis failures or timing violations, fix the constraint file.

| Criterion | Assessment |
|-----------|------------|
| Benchmark value | HIGH — constraint errors are extremely common |
| Realism | HIGH — mirrors real debug workflow |
| Execution-based grading | HIGH — run DC, check for clean synthesis |
| Auto-generation difficulty | MEDIUM — inject SDC errors (wrong clock period, missing false path, etc.) |
| Tool dependency | Design Compiler |
| Expected scale | 50–200 tasks |
| Implementation effort | HIGH — DC wrapper, SDC error injection, synthesis validation |

**Verdict**: Excellent execution-based track. Pairs well with DC Synthesis QA.

### 5. SpyGlass Lint Debug

**Concept**: Given RTL with lint violations (width mismatch, undriven nets, etc.), fix the code to pass SpyGlass checks.

| Criterion | Assessment |
|-----------|------------|
| Benchmark value | MEDIUM-HIGH — lint is a standard pre-synthesis check |
| Realism | HIGH — SpyGlass is widely used in industry |
| Execution-based grading | HIGH — run SpyGlass, check for zero violations |
| Auto-generation difficulty | MEDIUM — inject lint-triggerable patterns into RTL |
| Tool dependency | SpyGlass |
| Expected scale | 100–300 tasks |
| Implementation effort | MEDIUM — SpyGlass wrapper, violation injection, report parser |

**Verdict**: Good execution-based track. SpyGlass is relatively fast to run.

### 6. SpyGlass CDC QA

**Concept**: Given RTL with clock domain crossing issues, identify and fix CDC violations.

| Criterion | Assessment |
|-----------|------------|
| Benchmark value | HIGH — CDC bugs cause real silicon failures |
| Realism | HIGH — CDC is a critical verification concern |
| Execution-based grading | MEDIUM — SpyGlass CDC can report violations, but CDC fixes need careful validation |
| Auto-generation difficulty | HARD — CDC violations require multi-clock designs with specific crossing patterns |
| Tool dependency | SpyGlass (CDC mode) |
| Expected scale | 50–150 tasks |
| Implementation effort | HIGH — CDC pattern library, multi-clock RTL generation, SpyGlass CDC wrapper |

**Verdict**: High value but hard to generate. Consider for Phase 7.

### 7. ICC2 Flow QA

**Concept**: Given a placed design, answer questions about PnR results (timing, congestion, utilization, DRC).

| Criterion | Assessment |
|-----------|------------|
| Benchmark value | HIGH — physical design is the final step |
| Realism | HIGH — ICC2 is industry standard for PnR |
| Execution-based grading | LOW — full PnR flow is too slow for benchmarking |
| Auto-generation difficulty | HARD — requires placed designs, which need synthesis + placement |
| Tool dependency | ICC2, StarRC, PrimeTime |
| Expected scale | 50–100 tasks |
| Implementation effort | VERY HIGH — full PnR pipeline, report extraction, multi-tool coordination |

**Verdict**: High realism but impractical for execution-based grading at scale. Report-QA variant is feasible.

### 8. Innovus Flow QA

**Concept**: Same as ICC2 but using Cadence Innovus.

| Criterion | Assessment |
|-----------|------------|
| Benchmark value | HIGH — Innovus is the Cadence PnR standard |
| Realism | HIGH |
| Execution-based grading | LOW — same as ICC2 |
| Auto-generation difficulty | HARD |
| Tool dependency | Innovus |
| Expected scale | 50–100 tasks |
| Implementation effort | VERY HIGH |

**Verdict**: Same as ICC2. Consider unified PnR report-QA track covering both tools.

### 9. Spectre Analog Debug

**Concept**: Given a broken analog circuit (op-amp, PLL, bandgap), fix component values or topology to meet specs.

| Criterion | Assessment |
|-----------|------------|
| Benchmark value | HIGH — analog design is underserved by current benchmarks |
| Realism | HIGH — real analog design workflow |
| Execution-based grading | HIGH — run Spectre, check spec compliance |
| Auto-generation difficulty | MEDIUM — can parameterize circuit topologies and inject spec violations |
| Tool dependency | Spectre |
| Expected scale | 100–300 tasks |
| Implementation effort | MEDIUM — extend P4 framework, add op-amp/PLL topologies, spec extraction |

**Verdict**: Natural extension of P4. Good execution-based grading. High priority.

### 10. Verilog Repair / Auto-Fix

**Concept**: Given RTL with functional bugs (beyond P1's 10 types), fix the design using simulation feedback.

| Criterion | Assessment |
|-----------|------------|
| Benchmark value | MEDIUM — P1 already covers this well |
| Realism | MEDIUM — P1 bug types are realistic |
| Execution-based grading | HIGH — same as P1 |
| Auto-generation difficulty | LOW — extend P1 generator with new bug types |
| Tool dependency | VCS |
| Expected scale | 500–1000 additional tasks |
| Implementation effort | LOW — new bug type templates, extend generator |

**Verdict**: Easy to scale but lower marginal value. Good for padding volume.

---

## Comparative Summary

| Track | Value | Realism | Grading | Gen Effort | Tool Cost | Scale | Priority |
|-------|-------|---------|---------|------------|-----------|-------|----------|
| PT STA Debug | ★★★★★ | ★★★★★ | ★★★★★ | ★★★☆☆ | High | 100–500 | 2 |
| PT Report QA (ext) | ★★★☆☆ | ★★★★★ | ★★★☆☆ | ★★★★★ | Low | 200–500 | 6 |
| DC Synthesis QA | ★★★★☆ | ★★★★★ | ★★★☆☆ | ★★★☆☆ | High | 100–300 | 4 |
| DC Constraint Debug | ★★★★★ | ★★★★★ | ★★★★★ | ★★★☆☆ | High | 50–200 | 3 |
| SpyGlass Lint | ★★★★☆ | ★★★★★ | ★★★★★ | ★★★★☆ | Medium | 100–300 | 5 |
| SpyGlass CDC | ★★★★★ | ★★★★★ | ★★★☆☆ | ★★☆☆☆ | Medium | 50–150 | 8 |
| ICC2 Flow QA | ★★★★★ | ★★★★★ | ★☆☆☆☆ | ★☆☆☆☆ | Very High | 50–100 | 9 |
| Innovus Flow QA | ★★★★★ | ★★★★★ | ★☆☆☆☆ | ★☆☆☆☆ | Very High | 50–100 | 9 |
| Spectre Analog Debug | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★☆ | Medium | 100–300 | 1 |
| Verilog Auto-Fix | ★★★☆☆ | ★★★☆☆ | ★★★★★ | ★★★★★ | Low | 500–1000 | 7 |

---

## Proposed Roadmap

### Phase 6: Analog Expansion + DC Foundation

**Theme**: Expand analog circuit coverage and build Design Compiler infrastructure.

**Tracks**:

1. **P4 Analog Expansion** (Spectre Analog Debug)
   - Extend P4 from RC filter to op-amp, bandgap, PLL topologies
   - 5 new circuit topologies × 20 parameter sets × 2 tools (HSPICE + Spectre) = 200 tasks
   - Execution-based grading: run simulator, check spec compliance
   - Effort: Medium (extend existing P4 generator/evaluator)

2. **P6 DC Synthesis QA** (new track)
   - Report-QA style: given DC synthesis report, answer questions about area, timing, cells
   - Synthetic reports initially (like P3), real DC reports later
   - 100 tasks
   - Effort: Medium (new generator, new evaluator, DC report format)

3. **P7 DC Constraint Debug** (new track)
   - Given RTL + broken SDC, fix constraints for clean synthesis
   - Start with synthetic validation (check SDC syntax + constraint semantics)
   - 50 smoke tasks
   - Effort: High (DC wrapper, SDC parser, constraint validation)

**Expected total after Phase 6**: ~2662 tasks (2312 + 200 + 100 + 50)

**Rationale**: Analog expansion is the highest-ROI track (extends existing infrastructure, high value, proven grading). DC tracks build foundation for future STA work.

### Phase 7: Timing Closure + Lint

**Theme**: PrimeTime execution-based tracks and SpyGlass lint.

**Tracks**:

1. **P8 PrimeTime STA Debug** (new track)
   - Gate-level netlist + timing violations → fix setup/hold
   - Execution-based: run PT, check WNS > 0
   - Requires DC synthesis pipeline (built in Phase 6)
   - 100 tasks
   - Effort: High (DC + PT pipeline, netlist mutation, timing violation injection)

2. **P9 SpyGlass Lint Debug** (new track)
   - RTL + lint violations → fix code
   - Execution-based: run SpyGlass, check zero violations
   - 100 tasks
   - Effort: Medium (SpyGlass wrapper, violation pattern library)

3. **P10 PrimeTime Report QA** (new track)
   - Extended version of P3 with real PT output
   - Multi-corner, clock groups, exception paths, noise lines
   - 200 tasks
   - Effort: Low (extend P3 generator)

**Expected total after Phase 7**: ~3062 tasks

**Rationale**: PrimeTime is the most-requested EDA tool for benchmarks. Lint is a natural companion. Both have strong execution-based grading.

### Phase 8: Physical Design + CDC

**Theme**: Physical design report-QA and CDC verification.

**Tracks**:

1. **P11 PnR Report QA** (new track)
   - Unified ICC2/Innovus report-QA
   - Questions about timing, congestion, utilization, DRC violations
   - Synthetic reports (no real PnR runs)
   - 100 tasks
   - Effort: Medium (new generator, PnR report format)

2. **P12 SpyGlass CDC QA** (new track)
   - Multi-clock RTL with CDC violations → identify/fix
   - Semi-execution-based: run SpyGlass CDC, check violation count reduction
   - 50 tasks
   - Effort: High (CDC pattern library, multi-clock generation)

3. **Agentic Runner** (infrastructure)
   - Sandboxed workspace execution with tool-call limits
   - Agent can read, edit, run, observe, iterate
   - Resource enforcement: wall time, tokens, tool calls
   - Applies to all existing tracks
   - Effort: High

**Expected total after Phase 8**: ~3212 tasks

**Rationale**: PnR is too slow for execution-based grading but report-QA is feasible. CDC is high-value but hard to generate. Agentic runner unlocks the full benchmark vision.

---

## Phase Summary

| Phase | Theme | New Tasks | Cumulative | New Tracks |
|-------|-------|-----------|------------|------------|
| 5 (done) | Scale P2/P3/P5 | 1079 | 2312 | — |
| 6 | Analog + DC foundation | ~350 | ~2662 | P4 analog, P6 DC QA, P7 DC constraint |
| 7 | Timing + Lint | ~400 | ~3062 | P8 PT STA, P9 SpyGlass lint, P10 PT QA |
| 8 | Physical + CDC + Agentic | ~150 | ~3212 | P11 PnR QA, P12 CDC, agentic runner |

---

## Key Design Decisions

### 1. Report-QA before Execution

For tools where full-flow execution is expensive (DC, PT, ICC2, Innovus), start with report-QA tracks using synthetic or handcrafted reports. This:
- Validates the evaluation framework cheaply
- Builds parser infrastructure
- Provides immediate benchmark value
- Defers expensive tool integration

### 2. Execution-Based Grading First

Every new track should prioritize execution-based grading over text matching. The existing P1/P4/P5 tracks prove this works at scale. Report-QA (P3-style) is the fallback for tools where execution is too expensive.

### 3. Analog Before Digital Back-End

Analog (P4 expansion) is prioritized over DC/PT because:
- Infrastructure already exists (P4 generator, HSPICE/Spectre evaluators)
- Lower tool dependency (no synthesis pipeline needed)
- Higher marginal value (P4 only has RC filter currently)
- Faster iteration cycle (simulation is faster than synthesis)

### 4. SpyGlass as Stepping Stone

SpyGlass lint is a good intermediate complexity track between RTL debug and full synthesis. It:
- Uses existing RTL infrastructure
- Has fast execution (no synthesis, no simulation)
- Provides execution-based grading
- Builds lint-violation pattern library useful for other tracks

### 5. Agentic Runner Last

The agentic runner is infrastructure, not a track. It applies to all tracks and should be built after the track portfolio is stable. Starting with submission/workspace mode (current) is correct.

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| PrimeTime license unavailable | Blocks P8/P10 | Handcrafted reports for P10; skip P8 if no PT |
| DC synthesis pipeline fragile | Blocks P7/P8 | Start with synthetic SDC validation; real DC later |
| SpyGlass not installed | Blocks P9/P12 | Graceful skip (like P3 PT skip) |
| Analog topology diversity | Limits P4 expansion | Start with well-understood topologies (op-amp, bandgap) |
| CDC generation difficulty | Limits P12 | Start with simple 2-clock crossings; expand later |

---

## Tool Dependency Matrix

| Phase | Required | Optional | Graceful Skip |
|-------|----------|----------|---------------|
| 6 | VCS, HSPICE, Spectre | DC | P7 DC constraint |
| 7 | VCS, HSPICE, Spectre | PT, SpyGlass | P8 PT, P9 lint, P10 PT |
| 8 | VCS, HSPICE, Spectre | SpyGlass, ICC2/Innovus | P11 PnR, P12 CDC |

All phases degrade gracefully: tracks with missing tools are skipped, remaining tracks evaluate normally.

---

## Appendix: Tool Wrapper Requirements

| Tool | Wrapper | Status | Phase |
|------|---------|--------|-------|
| VCS | `tools/wrappers/vcs.py` | Done | P0 |
| HSPICE | `tools/wrappers/hspice.py` | Done | P0 |
| Spectre | `tools/wrappers/spectre.py` | Done | P0 |
| Design Compiler | `tools/wrappers/dc.py` | Needed | 6 |
| PrimeTime | `tools/wrappers/pt.py` | Needed | 7 |
| SpyGlass | `tools/wrappers/spyglass.py` | Needed | 7 |
| ICC2 | `tools/wrappers/icc2.py` | Needed | 8 |
| Innovus | `tools/wrappers/innovus.py` | Needed | 8 |
| StarRC | `tools/wrappers/starrc.py` | Needed | 8 |
