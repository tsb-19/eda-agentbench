# Public Release Policy

## Overview

This document defines what is included in a public release of EDA-AgentBench, what is excluded, and the release checklist.

## What Is Included

### Task Files (Public)

Each task directory contains:

- `prompt.md` — task description (public)
- `metadata.json` — machine-readable task specification (public)
- `files/` or `visible/` — visible and editable files provided to the agent (public)
- `solution/` or `hidden/` — correct answer for solution-mode evaluation (public for benchmark validation)

### Documentation

- `README.md` — overview and quick start
- `docs/` — all documentation files
- `CLAUDE.md` — development instructions

### Infrastructure

- `eda_agentbench/` — Python package (evaluators, CLI, schema)
- `generators/` — task generator base classes
- `scripts/` — generation, evaluation, and smoke scripts
- `tests/` — pytest test suite
- `pyproject.toml` — package metadata

## What Is Excluded

### Evaluation Artifacts

| Item | Reason |
|------|--------|
| `runs/` | Evaluation outputs (local only) |
| `workspaces/` | Temporary evaluation workdirs (local only) |
| `.cache/` | LLM response cache (local only) |

### Raw Simulator Outputs

| Item | Reason |
|------|--------|
| `*.log` | Raw simulator logs (may contain environment details) |
| `*.lis` | HSPICE listing files |
| `*.raw` | Binary waveform data |
| `*.tr0`, `*.st0`, `*.sw0`, `*.ac0`, `*.ic0` | Simulator transient/sweep outputs |
| `spectre.out/` | Spectre output directory |
| `psf/` | Parameter sweep files |

### Secrets and Credentials

| Item | Reason |
|------|--------|
| `.env` | API keys and secrets |
| License paths | EDA license server configurations |
| API keys | Any third-party API keys |

### Private Oracle Bundles

The external P5 bundle source (`../eda-bench-prototypes/tasks_eval_private/`) is not included in the main repository release. Only the imported copies under `tasks/p5_spice_deck_debug/imported/` are released.

## Release Checklist

Before any public release, verify:

- [ ] No `runs/` directory in the repository
- [ ] No `workspaces/` directory in the repository
- [ ] No `*.log`, `*.lis`, `*.raw` simulator output files
- [ ] No `*.tr0`, `*.st0`, `*.sw0`, `*.ac0`, `*.ic0` files
- [ ] No `spectre.out/` or `psf/` directories
- [ ] No `.env` file
- [ ] No license server names or paths in any file
- [ ] No API keys in any file
- [ ] No usernames, hostnames, or absolute paths in task files
- [ ] No private oracle bundles (only imported copies)
- [ ] All log files are sanitized (placeholders for `<USER>`, `<HOST>`, etc.)
- [ ] `git status` shows no untracked secrets
- [ ] `.gitignore` covers all excluded patterns
- [ ] All 118 pytest tests pass
- [ ] All smoke tests pass
- [ ] Solution mode: all 1113 tasks score 1.00
- [ ] Buggy mode: all 1113 tasks score < 1.00

## .gitignore Coverage

The repository's `.gitignore` excludes:

```
.env
.cache/
runs/
workspaces/
tmp/
*.log
*.lis
*.raw
*.tr0
*.st0
*.sw0
*.ac0
*.ic0
spectre.out/
psf/
```

## Sanitization Rules

Before publishing any evaluation logs or reports, the sanitizer replaces:

| Pattern | Replacement |
|---------|-------------|
| `/home/<username>/` | `/home/<USER>/` |
| Hostnames | `<HOST>` |
| Absolute paths | `<PROJECT_ROOT>`, `<EDA_ROOT>` |
| License servers | `<LICENSE_SERVER>` |
| Machine names | `<HOST>` |

See `eda_agentbench/sanitizer/` for implementation.

## Public vs Private Split

| Content | Public | Private |
|---------|--------|---------|
| Task prompt | Yes | — |
| Visible files | Yes | — |
| Editable files | Yes | — |
| Solution files | Yes | — |
| Hidden testbenches | Yes (for validation) | — |
| Oracle answers | Yes (P5) | — |
| Validation records | Yes (P5) | — |
| Raw EDA logs | — | Yes (sanitized only) |
| Evaluation workspaces | — | Yes (never committed) |
| External oracle bundles | — | Yes (not in main repo) |
| License configurations | — | Yes (never committed) |
