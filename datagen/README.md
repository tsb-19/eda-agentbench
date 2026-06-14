**English | [中文](README.zh.md)**

# EDA-AgentBench: SPICE Deck Debug Dataset Factory (`datagen/`)

This directory is the **in-repo data-generation module** of EDA-AgentBench — a
self-contained tool subtree. Run everything from here (`cd datagen`).

It owns the `spice_deck_debug` domain: task schema, the synthetic SPICE
generator, commercial-tool (HSPICE) validation adapters, normalized public-safe
packaging, and smoke tests.

It does **not** own the agent runner/evaluator harness (that lives in the parent
`eda-agentbench` repo). It is the **sole source of the P5 SPICE-deck-debug
track**; the parent's `scripts/import_p5_tasks.py` imports its exported bundle
(see "Relationship to the Benchmark" in `CLAUDE.md`).

> **Note:** The earlier `rtl_debug` and `timing_report_qa` prototype domains
> were retired. RTL-debug and timing-report-QA tasks are generated directly by
> the parent repo's `generators/` (tracks p1/p3).

## Pipeline

```
tasks_candidates/  -->  validate  -->  tasks_validated/  -->  package  -->  tasks_public/
     (generated)       (commercial)     (with validation/)     (safety)     (public-safe)
```

### Quick Start

```bash
# 1. Generate SPICE deck debug tasks (100 candidates)
bash scripts/generate_prototypes.sh

# 2. Run static smoke tests (no EDA tools required)
bash scripts/smoke_static.sh
python -m pytest tests

# 3. Run commercial validation (requires EDA tool in PATH or env var)
bash scripts/validate_one_candidate.sh tasks_candidates/spice_deck_debug_0001 hspice

# 4. Package validated task for public release
bash scripts/package_public_task.sh tasks_validated/spice_deck_debug_0001
```

## Architecture

```
.
├── schemas/                    # JSON Schema definitions
│   ├── task_schema.json
│   └── validation_record_schema.json
├── generators/                 # Synthetic task generators
│   └── spice_deck_debug/generate.py
├── validators/                 # Validation adapters
│   ├── common/                 # Shared utilities
│   ├── vcs/                    # Synopsys VCS adapter
│   ├── hspice/                 # Synopsys HSPICE adapter
│   ├── spectre/                # Cadence Spectre adapter
│   └── pt/                     # Synopsys PrimeTime adapter
├── tasks_candidates/           # Generated task candidates
├── tasks_validated/            # Tasks that passed validation
│   └── <task_id>/
│       ├── validation/
│       │   ├── validation_record.json
│       │   ├── normalized_errors.json
│       │   └── raw_log.sha256
│       └── ... (task files)
├── tasks_public/               # Public-safe task packages
├── .local_runs/                # Raw commercial logs (git-ignored)
├── tests/                      # Pytest test suite
├── scripts/                    # Shell scripts
└── docs/                       # Documentation
```

## Validation Modes

### Static Mode (Default)

Validates task structure, schema compliance, and generator determinism. No EDA tools required.

```bash
bash scripts/smoke_static.sh
python -m pytest tests
```

### Commercial Validation Mode (Opt-In)

Validates tasks using commercial EDA tools. The tool must be in PATH or set via environment variable:

| Variable         | Tool | PATH fallback |
|------------------|------|---------------|
| `EDA_VCS_CMD`    | Synopsys VCS | `vcs` |
| `EDA_HSPICE_CMD` | Synopsys HSPICE | `hspice` |
| `EDA_SPECTRE_CMD`| Cadence Spectre | `spectre` |
| `EDA_PT_CMD`     | Synopsys PrimeTime | `pt_shell` |

When neither env var nor PATH tool is available, validation skips gracefully (exit 0).

```bash
# Single task validation
bash scripts/validate_one_candidate.sh tasks_candidates/spice_deck_debug_0001 hspice

# Batch validation example
bash scripts/validate_commercial_example.sh
```

## Packaging for Public Release

Only tasks under `tasks_validated/` can be packaged by default:

```bash
bash scripts/package_public_task.sh tasks_validated/spice_deck_debug_0001
```

Override for unvalidated tasks (explicit opt-in):
```bash
bash scripts/package_public_task.sh tasks_candidates/spice_deck_debug_0001 --allow-unvalidated
```

Public packages are verified to contain:
- No `.log`, `.lis`, `.trn`, `.dsn`, `.raw` files
- No absolute paths (`/home/`, `/EDA/`, `/tools/`, `/data1/`, `/tmp/`)
- No license variable references (`LM_LICENSE_FILE`, `SNPSLMD_LICENSE_FILE`, etc.)
- No hostnames or usernames
- Validation summary (`validation/normalized_errors.json`, `validation/raw_log.sha256`)

## Commercial Tool Policy

Raw commercial tool logs are stored only under `.local_runs/` (git-ignored). Public task packages never contain:
- License banners, hostnames, usernames
- Absolute paths, tool version banners, timestamps
- Proprietary PDK data or license server information

See `docs/public_release_policy.md` for details.

## Task Domains

| Domain | Candidates | Validated | Public | Description |
|--------|-----------|-----------|--------|-------------|
| `spice_deck_debug` | 100 | 100 | 10 | Debug SPICE circuit simulation decks |

The `rtl_debug` and `timing_report_qa` prototype domains were retired; those
tracks are generated by the parent repo's `generators/` (p1/p3).

See `docs/taxonomy.md` for the full task family taxonomy.

## License

Apache-2.0
