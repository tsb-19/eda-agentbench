# Agentic Runner

## Overview

The agentic runner evaluates agents that can iteratively interact with task files in a sandboxed workspace. Unlike the standard evaluation mode where a model produces a static submission, agentic mode lets an external agent command read files, edit editable files, and run EDA tools before being scored.

## Non-Agentic vs Agentic

| Aspect | Non-Agentic | Agentic |
|--------|-------------|---------|
| Agent produces | Static files | Iterative edits via shell command |
| Workspace | Created from submission dir | Created from task, agent runs inside |
| Tool execution | Agent cannot run tools | Agent can run EDA tools |
| Evaluation | `_evaluate_single()` | `run_single_agentic()` |
| Mode in score.json | `submission` | `agentic` |

## CLI Usage

### Single Task

```bash
eda-bench run-agent TASK_PATH --agent-cmd "YOUR_AGENT_COMMAND"
```

Options:
- `--agent-cmd` (required): Shell command to execute as the agent
- `--timeout N`: Override task timeout in seconds
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
| `EDA_WORKSPACE` | Absolute path to the workspace directory |
| `EDA_TASK_PATH` | Absolute path to the task directory |
| `EDA_TASK_ID` | Task ID string |
| `EDA_TIMEOUT` | Timeout in seconds |

The command runs with `shell=True` and `cwd=workspace`. Simple shell one-liners work directly.

### Examples

**No-op agent** (does nothing):
```bash
eda-bench run-agent tasks/p3_timing_report_qa/smoke --agent-cmd "true"
```

**Copy-solution agent** (copies correct answer):
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
    workspace_manifest.json # SHA-256 hashes before/after agent runs
    modified_files.json     # List of file changes and anti-cheat violations
    metadata.json           # Run metadata (task_id, agent_cmd, mode, etc.)
```

For dataset runs, a `summary.json` is written at `runs/<run_id>/`.

## Safety

- **Editable files only**: The agent should only modify files listed in `metadata.files.editable`. The runner detects modifications to forbidden files via SHA-256 comparison.
- **Anti-cheat**: If forbidden files are modified, the score is forced to 0.
- **Hidden files**: Present in workspace (needed for EDA tool execution) but snapshotted and verified.
- **Timeout**: Agent command is killed after the timeout period.

## Test Agents

Built-in test agent factories in `eda_agentbench/agentic/test_agents.py`:

| Factory | Behavior | Expected Score |
|---------|----------|----------------|
| `make_noop_agent()` | Does nothing | ~0 (no answer) |
| `make_copy_solution_agent(task_path)` | Copies solution/ files | 1.0 (file-edit tasks) |
| `make_copy_answer_agent(task_path)` | Copies solution/answer.txt | 1.0 (QA tasks) |
| `make_buggy_answer_agent()` | Writes wrong answer | 0 |

## MVP Limitations

- Agent is a single shell command, not an interactive loop
- No per-tool-call transcript (only stdout/stderr capture)
- No max_tool_calls enforcement (timeout only)
- No sandboxing beyond workspace isolation (agent can access filesystem outside workspace)
- No streaming output capture
