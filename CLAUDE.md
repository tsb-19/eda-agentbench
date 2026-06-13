# CLAUDE.md

## Project Mission

This repository builds **EDA-AgentBench**, a benchmark for evaluating LLMs and coding agents on realistic EDA workflows using commercial Synopsys and Cadence tools.

The benchmark must evaluate both:

1. **Non-agentic mode**: the model produces a single answer, patch, script, or explanation without running tools.
2. **Agentic mode**: the agent can inspect files, edit allowed files, run provided scripts, observe EDA tool feedback, and iterate under resource limits.

The primary goal is not EDA trivia QA. The primary goal is tool-grounded EDA engineering ability.

## Current Status (Phase 7C — Agentic Runner MVP)

Phase 7C adds the agentic runner infrastructure. This is not a new task track — it is an evaluation mode that can run an external agent command in a sandboxed workspace, capture output, enforce limits, and grade using existing evaluators. CLI subcommands: `run-agent` and `run-agent-dataset`. Two-phase workspace model: agent sees only visible+editable files; hidden/oracle files are added to a separate evaluator workspace after the agent exits.

Phase 6 scaled P4 to 302 tasks (3 circuit types), added P6 DC Synthesis QA (51 tasks), added P6 DC Constraint Debug (13 tasks), and added baseline runner. 2576 total tasks across 7 tracks:

| Track | Count | Tool(s) | Source |
|-------|-------|---------|--------|
| P1 RTL Debug | 1001 | VCS | 1 handcrafted + 1000 generated |
| P2 Testbench/SVA Gen | 101 | VCS | 1 smoke + 100 generated (10 templates) |
| P3 Timing Report QA | 1008 | pt (synthetic) | 1 smoke + 999 synthetic + 8 PT prototype |
| P4 SPICE Sim | 302 | HSPICE, Spectre | 2 smoke + 300 generated (3 circuit types) |
| P5 SPICE Deck Debug | 100 | HSPICE | Imported from external bundle |
| P6 DC Synthesis QA | 51 | dc (synthetic) | 1 smoke + 50 generated (10 question types) |
| P6 DC Constraint Debug | 13 | dc | 1 smoke + 12 generated (6 reliable bug categories) |

Key results:
- pytest: all pass
- Solution mode: 2576/2576 = 1.00
- Buggy mode: 2576/2576 all < 1.0
- P6 DC Constraint accepts equivalent non-identical fixes (execution-based, no exact diff)
- P5 accepts equivalent non-identical fixes (execution-based, no exact diff)
- P6 is parser-based QA, no DC execution required

P2 naming was cleaned up in Phase 4E: track is now `p2_tb_sva_gen`, evaluator is `tb_sva_gen.TBSVAGenEvaluator`.
P2 scaled to 101 tasks (10 templates, 20 mutant variants) in Phase 5B.

### P3 Diversity (Phase 5A)

- 30 unique clock names, 15 path groups, 50 module names, 27 instance prefixes
- ~30% multi-clock reports (different clocks per path)
- Path counts: 3–50, WNS range: -5.0 to -0.01, TNS range: -75 to -0.3
- Signal names with hierarchical depth and optional bit indices
- Generated task IDs start at p3_timing_000001 (smoke is p3_timing_000000)

## Available EDA Tool Roots

Synopsys tools are under:

```text
/EDA/soft2/synopsys/
```

Cadence tools are under:

```text
/EDA/soft2/cadence/
```

Do not assume open-source EDA tools are installed. This benchmark targets commercial EDA tools.

Expected tools may include:

* VCS
* Verdi
* HSPICE
* PrimeTime
* Design Compiler
* SpyGlass
* ICC / ICC2
* StarRC
* Sentaurus
* Xcelium
* Spectre
* Innovus

Always implement environment detection instead of hardcoding one shell setup.

## Benchmark Priority

### Completed

1. P0: unified benchmark harness
2. P1: VCS/Xcelium RTL debug (1001 tasks)
3. P4: HSPICE/Spectre netlist simulation (102 tasks)
4. P5: SPICE Deck Debug (100 tasks, imported from external bundle)

### Next Phases

5. Phase 4A: P2 Testbench/SVA Generation — DONE
6. Phase 4B: P3 Timing Report QA — DONE
7. Phase 4C: Docs/Datacard/Release Policy — DONE
8. Phase 5A: P3 scale to 1000 — DONE
9. Phase 5B: P2 scale to 101 — DONE
10. Phase 5E: PT prototype (8 tasks) — DONE
11. Phase 5F: P5 scale to 100 — DONE
12. Phase 6C: P6 DC Constraint Debug prototype — DONE
13. Phase 7C: Agentic Runner MVP — DONE

### Later

- P5 Spectre dialect repair
- P6 DC Constraint Debug scale to 50+
- SpyGlass lint
- ICC2/Innovus/StarRC/Sentaurus expert tracks

Do not start expert tracks before Phase 4A–4C are stable.

## Core Design Principles

* Every task must be reproducible from a task directory.
* Every task must have machine-readable metadata.
* Every task must have a runner.
* Every task must produce a machine-readable score JSON.
* Tool execution results are the primary source of truth.
* LLM-judged explanation scores may be included only as low-weight auxiliary scores.
* Synthetic labels should come from generators, oracles, and tools, not from unverified LLM answers.
* Keep public tests and hidden tests structurally separate, even if the current release chooses to publish everything.

## Data Types

Support three synthetic data categories:

1. `template_synthetic`

   * generated from controlled templates
   * useful for scale and clean labels

2. `mutation_synthetic`

   * start from a correct design, then inject bugs
   * useful for debug, repair, lint, and verification tasks

3. `flow_synthetic`

   * generated by running real EDA tools and collecting logs/reports
   * useful for realistic tool-feedback and agentic tasks

## Required Task Directory Shape

Supported layouts depend on the track:

### Standard layout (P1, P4)

```text
task_xxxxxx/
  prompt.md
  metadata.json
  files/            # visible + editable files
  hidden/           # test scripts, testbenches
  solution/         # correct answer
```

### External bundle layout (P5)

```text
spice_deck_debug_NNNN/
  prompt.md
  metadata.json
  grader_contract.json
  visible/          # buggy deck (editable)
  hidden/           # golden fixed deck
  oracle/           # human-readable answer
  validation/       # validation records, normalized errors, raw_log.sha256
```

### Local output directories (never committed)

```text
runs/               # evaluation outputs
workspaces/         # temporary evaluation workdirs
```

The exact files depend on the track.

## Metadata Requirements

Each task must define:

* task id
* track
* tool
* difficulty
* data type
* visible files
* editable files
* forbidden files
* run command
* scoring weights
* timeout
* expected output files
* sanitizer rules if logs are included

## Agentic Evaluation Rules

For debug-style tasks:

Allowed by default:

* read visible files
* edit files listed in `editable_files`
* run the provided command
* iterate until timeout or tool-call limit

Forbidden by default:

* modifying public testbench
* modifying hidden testbench
* modifying oracle files
* modifying scoring scripts
* modifying `run.sh`, unless the task is explicitly a script-repair task
* deleting checkers
* hardcoding PASS output
* bypassing the intended EDA tool

The evaluator must check for forbidden modifications.

## Resource Limit Presets

Use these presets unless a task overrides them:

Fast:

```json
{
  "max_wall_time_sec": 60,
  "max_tool_calls": 10,
  "max_patch_attempts": 3,
  "max_output_tokens": 16000
}
```

Standard:

```json
{
  "max_wall_time_sec": 300,
  "max_tool_calls": 30,
  "max_patch_attempts": 8,
  "max_output_tokens": 32000
}
```

Expert:

```json
{
  "max_wall_time_sec": 900,
  "max_tool_calls": 80,
  "max_patch_attempts": 15,
  "max_output_tokens": 64000
}
```

## Scoring Principles

Use partial scoring.

Example RTL debug score:

```json
{
  "compile": 0.2,
  "public_test": 0.3,
  "hidden_test": 0.4,
  "explanation": 0.1
}
```

Example SPICE/Spectre score:

```json
{
  "tool_run": 0.3,
  "output_generated": 0.3,
  "numeric_metrics": 0.3,
  "explanation": 0.1
}
```

Explanation score must never dominate the score.

## Log Sanitization

Before publishing logs or reports, remove or replace:

* usernames
* home directories
* absolute server paths
* license server names
* machine names
* internal project names
* timestamps when they leak environment details

Use stable placeholders such as:

```text
<USER>
<HOST>
<PROJECT_ROOT>
<LICENSE_SERVER>
<EDA_ROOT>
```

## Development Rules

* Prefer Python for generators, runners, evaluators, and report scripts.
* Prefer simple shell wrappers for tool invocation.
* Keep all tool-specific setup isolated under `tools/` or `scripts/env/`.
* Do not scatter hardcoded EDA paths across generators.
* Every new track must include at least one smoke test.
* Every generator must support deterministic seeds.
* Every evaluator must produce JSON.
* Every runner must save raw logs and sanitized logs separately.
* Do not make large architectural changes without first updating docs.

## Sibling Repository Contract

The dataset factory lives in a sibling repository:

```text
../eda-bench-prototypes/
```

Rules:
* Main repo (`eda-agentbench`) may **read** exported bundles from `../eda-bench-prototypes/tasks_eval_private/`.
* Main repo must **not modify** any files inside `../eda-bench-prototypes/`.
* P5 imported tasks are local copies under `tasks/p5_spice_deck_debug/imported/`.
* To re-import or import new bundles, run `python3 scripts/import_p5_tasks.py`.

## Parallel Worktree Development Rules

When running multiple agents in parallel:

* **Main worktree** (`eda-agentbench`): integration branch, merges completed work.
* Each worktree commits to its own branch.
* Avoid modifying shared core files (`schema.py`, `cli.py`, `task/loader.py`, `evaluator/`) unless strictly required.
* Do not run multiple agents in the same working tree.

## Track Ownership Rules

* **P2 agent** must not modify P1/P4/P5 task generation or scoring.
* **P3 agent** must not require PrimeTime in MVP; use synthetic normalized reports first.
* **Docs agent** must not modify evaluator core, schema, generators, or task files unless strictly necessary.
* Any change to `schema.py`, `cli.py`, `task/loader.py`, dataset evaluator, or shared report code should be minimal and documented in the commit message.

## Do Not Commit

These files and directories must never be committed to git:

* `.env` — API keys and secrets
* `.cache/` — LLM response cache
* `runs/` — evaluation outputs
* `workspaces/` — temporary evaluation workdirs
* Raw simulator outputs: `*.log`, `*.lis`, `*.raw`, `*.trn`, `*.st0`, `*.sw0`, `*.ac0`, `*.ic0`
* License paths or API keys in any file
* Anything under `../eda-bench-prototypes/`

## Expected First Milestone

All first-milestone items are complete:

* unified schema
* evaluator CLI
* tool detection script
* RTL debug smoke task (P1)
* RTL generation smoke task (P1 generated)
* VCS runner
* HSPICE smoke task (P4)
* Spectre smoke task (P4)
* log sanitizer
* benchmark summary report script
* prompt diversification infrastructure
* P5 SPICE Deck Debug (imported)
* sampled evaluation mode (--sample-per-track, --limit, --seed)
* P2 scaled to 101 tasks with 10 design templates (Phase 5B)

