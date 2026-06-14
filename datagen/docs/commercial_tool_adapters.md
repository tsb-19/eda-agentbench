**English | [中文](commercial_tool_adapters.zh.md)**

# Commercial Tool Adapters

## Overview

Each adapter wraps a commercial EDA tool invocation, handling:
- Command construction from environment variables
- Timeout enforcement
- Exit code capture
- Raw log storage (under `.local_runs/`)
- Log normalization (stripping proprietary info)
- Validation record generation

## Adapter Architecture

```
validators/
  common/
    run_command.py       # Generic command runner with timeout
    log_normalizer.py    # Log sanitization utilities
    validation_record.py # Record creation and validation
  vcs/
    validate_rtl.py      # VCS compilation and simulation
  hspice/
    validate_spice.py    # HSPICE simulation
  spectre/
    validate_spectre.py  # Spectre simulation
  pt/
    parse_report.py      # PrimeTime report parsing
```

## Environment Variables

| Variable         | Description                   | Example |
|------------------|-------------------------------|---------|
| `EDA_VCS_CMD`    | VCS executable path/command   | `<set-to-your-vcs-path>` |
| `EDA_HSPICE_CMD` | HSPICE executable path/command | `<set-to-your-hspice-path>` |
| `EDA_SPECTRE_CMD`| Spectre executable path/command | `<set-to-your-spectre-path>` |
| `EDA_PT_CMD`     | PrimeTime executable path/command | `<set-to-your-pt-path>` |

## Graceful Skip Behavior

When an environment variable is not set:
1. Print: `[SKIP] EDA_<TOOL>_CMD not set, skipping <tool> validation`
2. Exit with code 0
3. Do not create a validation record

## Log Normalization

The `log_normalizer` module removes:
- Lines matching license banner patterns
- Hostname references
- Username references
- Absolute path prefixes
- Tool version banners
- Timestamp patterns

Normalization is applied before storing the validation record. The SHA-256 hash is computed on the raw (pre-normalization) log.
