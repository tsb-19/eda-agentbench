# EDA-Agent-Bench: Public SPICE Deck Debug Tasks

This directory contains the public-safe release of the SPICE deck debug task subset
from EDA-Agent-Bench.

## Contents

- **10 SPICE deck debug tasks** (`spice_deck_debug_0001` through `spice_deck_debug_0010`)
- **manifest.jsonl** — Machine-readable task index (one JSON object per line)

## Task Structure

Each task contains:
- `prompt.md` — Natural-language task description
- `metadata.json` — Task metadata and validation status
- `visible/` — Buggy SPICE deck visible to the agent
- `validation/` — Normalized validation results

## Validation

All tasks are **debug_contrast_verified** via commercial HSPICE validation:
- Buggy deck fails with the expected error category
- Golden/fixed deck passes
- Error category matches task metadata

## Error Categories Covered

| Category | Count | Description |
|----------|-------|-------------|
| missing_model | 2 | Model name typo or absent |
| missing_subckt | 2 | Undefined subcircuit |
| wrong_pin_count | 1 | Pin count mismatch |
| duplicate_element | 2 | Same element name used twice |
| missing_include | 1 | .include references nonexistent file |
| unsupported_dialect | 1 | Invalid model level |
| invalid_directive | 1 | Malformed .include |

## Safety

All tasks are verified to contain:
- No raw commercial tool logs
- No absolute local paths
- No license variable references
- No hostname/username leakage
- No raw simulator output files

## License

Apache-2.0. Synthetic content only — no proprietary circuit data.
