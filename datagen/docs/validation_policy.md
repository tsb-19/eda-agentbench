**English | [中文](validation_policy.zh.md)**

# Validation Policy

## Pipeline

```
tasks_candidates/  -->  validate  -->  tasks_validated/  -->  package  -->  tasks_public/
     (generated)       (commercial)     (with validation/)     (safety)     (public-safe)
```

Validated tasks contain a `validation/` subdirectory with:
- `validation_record.json` — full normalized record
- `normalized_errors.json` — extracted error summaries
- `raw_log.sha256` — SHA-256 hash of the raw log

Raw `.log` files remain only under `.local_runs/` (git-ignored).

## Two-Mode Validation

### Static Mode (Default)

Static mode validates task structure and metadata without invoking any EDA tool. It is the default and always available.

**Checks performed:**
- `metadata.json` validates against `schemas/task_schema.json`
- All referenced files exist in the task directory
- `prompt.md` is non-empty
- Directory layout matches expected structure
- Oracle files exist and are non-empty
- Generator output is deterministic (re-running produces identical tasks)

Static mode never calls: `vcs`, `xrun`, `hspice`, `spectre`, `pt_shell`, `dc_shell`, `innovus`, `icc2`, `iverilog`, `verilator`, `yosys`, `ngspice`, `opensta`, `openroad`.

### Commercial Validation Mode (Opt-In)

Commercial mode runs actual EDA tools to verify that tasks are valid and solvable. It is explicitly opt-in.

**Activation:**
- Set the relevant `EDA_*_CMD` environment variable
- Run validation scripts explicitly (e.g., `bash scripts/validate_commercial_example.sh`)

**Commercial tools supported:**
| Backend  | Env Var          | Tool |
|----------|------------------|------|
| VCS      | `EDA_VCS_CMD`    | Synopsys VCS |
| HSPICE   | `EDA_HSPICE_CMD` | Synopsys HSPICE |
| Spectre  | `EDA_SPECTRE_CMD`| Cadence Spectre |
| PT       | `EDA_PT_CMD`     | Synopsys PrimeTime |

**Behavior when env vars are missing:**
- Scripts print a clear skip message
- Exit code 0 (not failure)
- Static smoke tests remain unaffected

## Validation Records

Every commercial validation produces a normalized record following `schemas/validation_record_schema.json`. Records contain:
- Task ID, backend, tool name, normalized version
- Status and exit code
- Normalized error summaries
- Parsed metrics
- SHA-256 hash of the raw log
- Whether the raw log was retained in `.local_runs/`
- UTC timestamp and notes

Raw logs are stored only under `.local_runs/` (git-ignored) and are never included in public task packages.
