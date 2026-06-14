**English | [中文](task_schema.zh.md)**

# Task Schema

Each benchmark task lives in its own directory under `tasks_candidates/`, `tasks_validated/`, or `tasks_public/`.

## Directory Layout

```
<task_id>/
  metadata.json        # Task metadata (see schema below)
  prompt.md            # Natural-language prompt given to the agent
  visible/             # Files visible to the agent during evaluation
  hidden/              # Files hidden from the agent (used by the grader)
  oracle/              # Reference solution and grading data
```

## Task ID Format

Task IDs follow the pattern: `<domain>_NNNN`

- `domain` matches the `domain` field in metadata
- `NNNN` is a 4-digit zero-padded number (0001-0100)
- Examples: `spice_deck_debug_0001`, `spice_deck_debug_0100`

## Metadata Schema

The full JSON Schema is at `schemas/task_schema.json`. Key fields:

| Field                  | Type     | Description |
|------------------------|----------|-------------|
| `task_id`              | string   | Unique identifier: `<domain>_NNNN` |
| `domain`               | enum     | `spice_deck_debug` (the factory's only active domain) |
| `task_family`          | string   | Sub-family within domain |
| `difficulty`           | enum     | `easy`, `medium`, `hard` |
| `tags`                 | string[] | Searchable tags |
| `prompt_file`          | string   | Relative path to `prompt.md` |
| `visible_files`        | string[] | Files the agent can read |
| `hidden_files`         | string[] | Files only the grader uses |
| `expected_outputs`     | string[] | Files the agent should produce |
| `grader`               | object   | Grading strategy and criteria |
| `timeout_sec`          | int      | Max seconds for task completion |
| `license_notes`        | string   | License for task content |
| `generation_source`    | enum     | `synthetic`, `derived`, `manual` |
| `oracle_description`   | string   | Description of the expected solution |
| `validation_status`    | enum     | Current validation state |
| `optional_tool_backends` | string[] | Commercial tools that can validate |
| `public_release_safe`  | bool     | Safe for public release |

## Validation Record Schema

When a task is validated by a commercial tool, a validation record is produced following `schemas/validation_record_schema.json`. Records contain normalized data only — raw commercial logs are never stored in task packages.
