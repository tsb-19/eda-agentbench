**English | [中文](agentic_runner.zh.md)**

# Agentic Runner

## Overview

The agentic runner evaluates agents that can interact with task files in a sandboxed workspace. Unlike the standard evaluation mode where a model produces a static submission, agentic mode lets an external agent command read and edit files before being scored.

## Security Model: Two-Phase Workspace

The agentic runner uses a strict two-phase workspace model to prevent information leakage:

### Phase 1: Agent Workspace (visible+editable only)

- Contains ONLY files from `files/` (or `visible/` for P5)
- The agent process runs here
- Hidden testbenches, oracle files, scoring scripts, and solution files are **never copied here**
- The agent cannot read, list, or discover hidden/oracle files

### Phase 2: Evaluator Workspace (agent output + hidden files)

- Created AFTER the agent process exits
- Starts with visible files from the task root
- Overlays the agent's edits (only editable files)
- Adds hidden/oracle files from the task root
- EDA tool execution and scoring happen here
- The agent process has already terminated and cannot access this workspace

### What the agent can access

| Resource | Agent can read? | Agent can write? |
|----------|----------------|-----------------|
| Visible files (`files/`) | Yes | No (unless editable) |
| Editable files | Yes | Yes |
| Hidden files (`hidden/`) | **No** | **No** |
| Oracle files (`oracle/`) | **No** | **No** |
| Solution files (`solution/`) | **No** | **No** |
| `$EDA_TASK_PATH` | Yes (read-only) | No |

The agent receives `$EDA_TASK_PATH` pointing to the original task directory. The agent CAN read solution/ from there (since it's on the filesystem), but this is by design — the agent wrapper decides what to expose. The key guarantee is that hidden/oracle files are NOT in the agent's workspace.

## Non-Agentic vs Agentic

| Aspect | Non-Agentic | Agentic |
|--------|-------------|---------|
| Agent produces | Static files | Edits via shell command |
| Workspace | Created from submission dir | Agent-only (no hidden files) |
| Hidden files | Copied for evaluation | Added only after agent exits |
| Tool execution | Agent cannot run tools | Agent can run tools (in agent workspace) |
| Evaluation | `_evaluate_single()` | `run_single_agentic()` |
| Mode in score.json | `submission` | `agentic` |

## CLI Usage

### Single Task

```bash
eda-bench run-agent TASK_PATH --agent-cmd "YOUR_AGENT_COMMAND"
```

Options:
- `--agent-cmd` (required): Shell command to execute as the agent
- `--timeout N`: Override timeout in seconds
- `--run-id ID`: Custom run identifier
- `--output-dir DIR`: Override output directory

### Sampled Dataset

```bash
eda-bench run-agent-dataset tasks --agent-cmd "YOUR_AGENT_COMMAND" \
    --sample-per-track 1 --seed 42
```

Options:
- `--agent-cmd` (required): Shell command to execute
- `--track TRACK`: Filter to a single track
- `--sample-per-track N`: Sample N tasks per track
- `--limit N`: Global task limit
- `--seed N`: Sampling seed (default: 42)
- `--timeout N`: Override timeout

## Agent Interface

The agent command receives these environment variables:

| Variable | Description |
|----------|-------------|
| `EDA_WORKSPACE` | Path to agent workspace (visible+editable only) |
| `EDA_TASK_PATH` | Path to original task directory (has solution/, hidden/) |
| `EDA_TASK_ID` | Task ID string |
| `EDA_TIMEOUT` | Timeout in seconds |

The command runs with `shell=True` and `cwd=EDA_WORKSPACE`.

### Examples

**No-op agent** (does nothing):
```bash
eda-bench run-agent tasks/p3_timing_report_qa/smoke --agent-cmd "true"
```

**Copy-answer agent** (copies correct answer from task path):
```bash
eda-bench run-agent tasks/p3_timing_report_qa/smoke \
    --agent-cmd "cp \$EDA_TASK_PATH/solution/answer.txt \$EDA_WORKSPACE/"
```

**Custom agent script**:
```bash
eda-bench run-agent tasks/p3_timing_report_qa/smoke \
    --agent-cmd "python3 my_agent.py --workspace \$EDA_WORKSPACE --task \$EDA_TASK_PATH"
```

## Output Structure

Each agentic run produces:

```
runs/<run_id>/<task_id>/<timestamp>/
    transcript.jsonl        # JSONL events: start, stdout, stderr, file_changes, score, end
    stdout.log              # Raw agent stdout
    stderr.log              # Raw agent stderr
    score.json              # ScoreResult (same format as non-agentic)
    workspace_manifest.json # SHA-256 of agent-visible files before/after
    modified_files.json     # File changes and anti-cheat violations
    metadata.json           # Run metadata (task_id, agent_cmd, mode, etc.)
```

The `workspace_manifest.json` contains only agent-visible files. Hidden/oracle files are never included.

For dataset runs, a `summary.json` is written at `runs/<run_id>/`.

## Anti-Cheat

- **Editable enforcement**: Only files in `metadata.files.editable` may be modified
- **Forbidden file check**: SHA-256 snapshot/verify of forbidden visible files
- **Hidden file isolation**: Hidden files never enter the agent workspace
- **Score zeroing**: Anti-cheat violations force score to 0
- **SDC grader isolation (P6 / P7-PT)**: the agent's editable `constraints.sdc` is ingested with `read_sdc` and re-emitted with `write_sdc` in a process that runs no grading; a separate bash phase computes the pass/fail verdict from that laundered file. Injected Tcl (`proc incr {} {}`, `exit 0`, `echo CONSTRAINTS_OK`) cannot reach or forge the marker. A secondary denylist (`check_tcl_injection`) flags obvious injection attempts as an explicit violation.
- **Timeout**: Agent command is killed after timeout period

## Test Agents

Built-in test agent factories in `eda_agentbench/agentic/test_agents.py`:

| Factory | Behavior | Expected Score |
|---------|----------|----------------|
| `make_noop_agent()` | Does nothing | ~0 (no answer) |
| `make_copy_solution_agent(task_path)` | Copies solution/ via $EDA_TASK_PATH | 1.0 (file-edit tasks) |
| `make_copy_answer_agent(task_path)` | Copies solution/answer.txt | 1.0 (QA tasks) |
| `make_buggy_answer_agent()` | Writes wrong answer | 0 |

## MVP Limitations

- Agent is a single shell command, not an interactive loop
- No per-tool-call transcript (only stdout/stderr capture)
- No max_tool_calls enforcement (timeout only)
- No filesystem sandboxing beyond workspace isolation (agent could access other paths via $EDA_TASK_PATH)
- No streaming output capture
