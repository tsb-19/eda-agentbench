"""Global configuration for EDA-AgentBench."""

from __future__ import annotations

from pathlib import Path

SYNOPSYS_ROOT = Path("/EDA/soft2/synopsys")
CADENCE_ROOT = Path("/EDA/soft2/cadence")

RESOURCE_PRESETS = {
    "fast": {"max_wall_time_sec": 60, "max_tool_calls": 10, "max_patch_attempts": 3, "max_output_tokens": 16000},
    "standard": {"max_wall_time_sec": 300, "max_tool_calls": 30, "max_patch_attempts": 8, "max_output_tokens": 32000},
    "expert": {"max_wall_time_sec": 900, "max_tool_calls": 80, "max_patch_attempts": 15, "max_output_tokens": 64000},
}

TASKS_ROOT = Path("tasks")
RUNS_ROOT = Path("runs")
