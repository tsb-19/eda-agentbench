**English | [中文](release_checklist.zh.md)**

# Release Safety Checklist

## What May Be Published

| Directory/File | Publishable? | Notes |
|----------------|-------------|-------|
| `tasks_public/` | **Yes** | Public-safe task packages. Hidden/oracle stripped. |
| `schemas/` | **Yes** | JSON schemas for tasks, validation records, grader contracts. |
| `generators/` | **Yes** | Synthetic task generators. |
| `validators/common/` | **Yes** | Shared validation utilities. |
| `docs/` | **Yes** | Documentation. |
| `scripts/generate_prototypes.sh` | **Yes** | Task generation script. |
| `scripts/smoke_static.sh` | **Yes** | Static smoke tests. |
| `scripts/package_public_task.sh` | **Yes** | Public packaging script. |
| `scripts/package_spice_public_batch.sh` | **Yes** | Batch public packaging. |
| `scripts/check_release_safety.sh` | **Yes** | Release safety scanner. |
| `tests/` | **Yes** | Test suite. |
| `pyproject.toml` | **Yes** | Project configuration. |
| `README.md` | **Yes** | Project readme. |

## What Must NOT Be Published

| Directory/File | Reason |
|----------------|--------|
| `tasks_eval_private/` | Contains hidden/oracle solutions. Evaluator-only. |
| `.local_runs/` | Contains raw commercial tool logs. |
| `tasks_validated/*/hidden/` | Golden solution files. |
| `tasks_validated/*/oracle/` | Reference answers. |
| Any `*.log`, `*.lis`, `*.trn`, `*.dsn`, `*.raw` files | Raw simulator output. |
| Any `*.st0`, `*.sw0`, `*.ac0`, `*.ic0` files | HSPICE raw output. |

## What Requires Safety Checks Before Publishing

| Item | Check Required |
|------|---------------|
| `tasks_validated/` (without hidden/oracle) | Must pass `check_release_safety.sh` |
| `validation_record.json` | Must contain only normalized data, no raw logs |
| `raw_log.sha256` | SHA-256 hash only, no log content |
| `normalized_errors.json` | Sanitized error summaries only |

## Safety Scan Checklist

Before any release, run:

```bash
bash scripts/check_release_safety.sh tasks_public
```

The scanner checks for:

1. **Hidden/oracle directories** — must not exist in public packages
2. **Raw simulator files** — `.log`, `.lis`, `.trn`, `.dsn`, `.raw`, `.st0`, `.sw0`, `.ac0`, `.ic0`
3. **Absolute paths** — `/EDA/`, `/home/`, `/data1/`, `/tmp/`, `/tools/`, `/usr/local/`
4. **License variables** — `LM_LICENSE_FILE`, `SNPSLMD_LICENSE_FILE`, `CDS_LIC_FILE`
5. **Hostnames/usernames** — detectable host/user references
6. **Private bundle leakage** — `tasks_eval_private/` must not be in public release

## Publication Tiers

### Tier 1: Public Release (safe to publish)

- `tasks_public/` — fully sanitized, no hidden/oracle
- `schemas/` — JSON schemas
- `generators/` — synthetic generators
- `docs/` — documentation
- `scripts/` — generation and packaging scripts
- `tests/` — test suite

### Tier 2: Private Evaluator Bundle (share with evaluator repo only)

- `tasks_eval_private/` — contains grader contracts and hidden/oracle
- Must be transmitted via private channel, not public repository

### Tier 3: Never Publish

- `.local_runs/` — raw commercial tool logs
- Any file containing absolute paths to commercial tools
- Any file containing license server information
- Any file containing hostnames or usernames

## Emergency Checklist

If a file is accidentally committed with proprietary data:

1. Remove the file from the repository
2. Rewrite git history if the file was pushed to a remote
3. Rotate any exposed credentials or license information
4. Run `bash scripts/check_release_safety.sh` to verify cleanup
