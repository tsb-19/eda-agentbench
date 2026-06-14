**English | [中文](public_release_policy.zh.md)**

# Public Release Policy

## Principles

Public task packages must be safe to share without exposing proprietary information.

## What Must Be Removed

Before a task moves from `tasks_validated/` to `tasks_public/`:

1. **Raw commercial tool logs** — never include
2. **License banners** — strip all EDA vendor license text
3. **Hostnames** — remove any host-specific information
4. **Usernames** — remove user-identifying information
5. **Absolute paths** — convert to relative paths only
6. **Tool version banners** — normalize to major.minor only
7. **Timestamps** — remove build timestamps that could identify infrastructure
8. **Proprietary PDK data** — no foundry-specific device models or parameters
9. **License server info** — no FlexLM/LM-X server references

## What Is Kept

- Task structure and metadata
- Synthetic RTL, SPICE decks, and timing reports
- Normalized validation summaries
- Error category and message (sanitized)
- Parsed metrics (timing, power, area)
- SHA-256 hashes of raw logs (for reproducibility without exposing content)

## Validation Before Release

Every task in `tasks_public/` must have:
- `public_release_safe: true` in metadata
- `validation_status` of `validated_static` or `validated_commercial`
- No references to `.local_runs/` paths
- No absolute paths of any kind

## Automated Check

The static smoke test includes a check that no task in `tasks_public/` contains absolute paths or `.local_runs/` references.
