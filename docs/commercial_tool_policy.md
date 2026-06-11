# Commercial Tool Policy

## Overview

EDA-AgentBench is designed exclusively for commercial EDA tools. It does not use or require open-source EDA alternatives. This policy documents which tools are used, how they are detected, and what licensing constraints apply.

## Supported Tools

| Tool | Vendor | Used By | Purpose |
|------|--------|---------|---------|
| VCS | Synopsys | P1 RTL Debug | RTL compilation and simulation |
| HSPICE | Synopsys | P4 SPICE Sim, P5 SPICE Deck Debug | SPICE netlist simulation |
| Spectre | Cadence | P4 SPICE Sim | SPICE netlist simulation |

## Future Tools (Planned)

| Tool | Vendor | Planned Track |
|------|--------|---------------|
| Xcelium | Cadence | P2 RTL Generation |
| Design Compiler | Synopsys | P3 Timing Report QA |
| PrimeTime | Synopsys | P3 Timing Report QA |
| SpyGlass | Synopsys | P6 Lint |
| ICC2 | Synopsys | P7 Physical Design |
| Innovus | Cadence | P7 Physical Design |
| StarRC | Synopsys | P7 Physical Design |
| Sentaurus | Synopsys | P7 Physical Design |
| Verdi | Synopsys | Debug visualization |

## Tool Detection

The benchmark probes the filesystem for tools at runtime. No tool paths are hardcoded in task definitions.

```bash
eda-bench detect-tools
```

Expected install locations (probed, not hardcoded):

```
Synopsys: /EDA/soft2/synopsys/
Cadence:  /EDA/soft2/cadence/
```

The detection script searches for tool binaries under these roots and reports availability. Tasks that require unavailable tools are skipped during evaluation.

## Licensing

All supported tools require commercial licenses. The benchmark:

- Does not bundle or redistribute any EDA tool binaries
- Does not include license files or license server configurations
- Does not store license server names in task files (they are sanitized from logs)
- Assumes the host environment has valid licenses for the tools being evaluated

Users must ensure they have appropriate licenses before running evaluations.

## Log Sanitization

EDA tool outputs often contain environment-specific information. Before any logs are stored or shared, the sanitizer replaces:

| Pattern | Replacement | Example |
|---------|-------------|---------|
| Username | `<USER>` | `/home/jdoe/project` → `/home/<USER>/project` |
| Hostname | `<HOST>` | `server01.company.com` → `<HOST>` |
| Absolute paths | `<PROJECT_ROOT>`, `<EDA_ROOT>` | `/EDA/soft2/synopsys/vcs/...` → `<EDA_ROOT>/vcs/...` |
| License server | `<LICENSE_SERVER>` | `license.company.com` → `<LICENSE_SERVER>` |
| Machine names | `<HOST>` | `hostname` in tool output → `<HOST>` |

This allows evaluation logs to be shared publicly without leaking infrastructure details.

## No Open-Source Alternatives

The benchmark intentionally does not support open-source EDA tools (e.g., Icarus Verilog, Ngspice, Xyce). The rationale:

1. The benchmark evaluates ability to work with commercial tool chains, which dominate industrial EDA workflows.
2. Commercial tools have different error messages, behaviors, and capabilities than open-source alternatives.
3. Task generators and evaluators are tuned for commercial tool output formats.
4. Supporting open-source tools would require separate evaluators and would dilute the benchmark's industrial relevance.

## Environment Setup

Users should:

1. Install commercial EDA tools under the expected roots (`/EDA/soft2/synopsys/`, `/EDA/soft2/cadence/`).
2. Set up license environment variables as required by their tool vendor.
3. Run `eda-bench detect-tools` to verify availability.
4. Run smoke tests to confirm tools work end-to-end.
