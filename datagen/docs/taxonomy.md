**English | [中文](taxonomy.zh.md)**

# Task Taxonomy

> **Scope:** This module owns only the `spice_deck_debug` domain. The earlier
> `rtl_debug` and `timing_report_qa` prototype domains were retired — RTL-debug
> and timing-report-QA tasks are generated directly by the parent repo's
> `generators/` (tracks p1/p3). See `CLAUDE.md` for the retirement note.

## Naming Convention

Task IDs follow the pattern: `<domain>_NNNN`

Where:
- `domain` is `spice_deck_debug`
- `NNNN` is a 4-digit zero-padded number (0001, 0002, ..., 0100)

Examples:
- `spice_deck_debug_0001`
- `spice_deck_debug_0100`

File names within a task directory include the full task_id prefix:
- `visible/spice_deck_debug_0001_bug.sp`
- `hidden/spice_deck_debug_0001_fixed.sp`

## Domains

### spice_deck_debug
Tasks involving debugging SPICE circuit simulation decks.

**Task Families:**
- `syntax_error` — Malformed SPICE syntax (missing nodes, bad values)
- `convergence_issue` — Simulation convergence failures
- `wrong_topology` — Incorrect circuit topology or connections
- `parameter_error` — Wrong component values or model parameters
- `missing_ground` — Missing or incorrect ground reference

**SPICE Error Categories (observed during validation):**

| Category | HSPICE Catchable | Example |
|----------|-----------------|---------|
| `missing_model` | Yes | `Definition of model/subckt "pmos_typo" is not found` |
| `missing_subckt` | Yes | `Definition of model/subckt "buf" is not found` (X element) |
| `wrong_pin_count` | Yes | `Number of nodes mismatch between instance "x1" and subcircuit "inv"` |
| `duplicate_element` | Yes | `attempts to redefine r1` |
| `missing_include` | Yes | `unable to open file "nonexistent.lib"` |
| `unsupported_dialect` | Yes | `Invalid model level 99` |
| `invalid_directive` | Yes | `.include` with no filename → `syntax error` |
| `floating_node` | Warning only | HSPICE warns but does not abort |
| `convergence_failure` | Warning only | HSPICE typically converges or warns, rarely aborts |
| `invalid_measure` | Warning only | `.measure` errors are warnings, not fatal |
| `unknown` | Varies | Catch-all for uncategorized errors |

**Note:** `floating_node`, `convergence_failure`, and `invalid_measure` produce HSPICE warnings but
do not cause the simulation to abort (exit != 0). For debug contrast validation, these categories
use alternative HSPICE-catchable bugs that exercise the same circuit topology. See task metadata
`notes` field for the mapping.

## Difficulty Levels

| Level   | Description |
|---------|-------------|
| `easy`  | Single obvious error, straightforward fix |
| `medium` | Multiple interacting issues or non-obvious root cause |
| `hard`  | Requires deep domain knowledge, subtle interactions |
