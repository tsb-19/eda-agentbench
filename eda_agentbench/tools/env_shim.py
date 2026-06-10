"""Builds environment dicts for subprocess calls with correct EDA tool paths."""

from __future__ import annotations

import os
from pathlib import Path

from eda_agentbench.types import DetectedTool


class EnvShim:
    """Constructs a subprocess env dict with EDA tool paths injected."""

    def __init__(self, detected_tools: list[DetectedTool]):
        self.tools = [t for t in detected_tools if t.available]

    def get_env(self) -> dict[str, str]:
        """Return env dict with tool paths prepended to PATH."""
        env = os.environ.copy()
        for tool in self.tools:
            env[tool.env_var] = str(tool.tool_home)
            env["PATH"] = str(tool.binary_path.parent) + ":" + env.get("PATH", "")
        return env
