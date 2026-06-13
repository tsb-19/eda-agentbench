"""Core dataclasses for EDA-AgentBench."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DetectedTool:
    name: str
    vendor: str
    version: str
    binary_path: Path
    tool_home: Path
    env_var: str
    available: bool


@dataclass
class ResourceLimits:
    max_wall_time_sec: int = 300
    max_tool_calls: int = 30
    max_patch_attempts: int = 8
    max_output_tokens: int = 32000

    @classmethod
    def from_preset(cls, preset: str) -> ResourceLimits:
        presets = {
            "fast": cls(60, 10, 3, 16000),
            "standard": cls(300, 30, 8, 32000),
            "expert": cls(900, 80, 15, 64000),
        }
        if preset not in presets:
            raise ValueError(f"Unknown preset: {preset!r}. Choose from {list(presets)}")
        return presets[preset]


@dataclass
class RunResult:
    task_id: str
    mode: str
    success: bool
    wall_time_sec: float
    raw_log_path: Path | None = None
    sanitized_log_path: Path | None = None
    model_output: str | None = None
    produced_files: dict[str, Path] = field(default_factory=dict)
    error: str | None = None


@dataclass
class ScoreComponent:
    name: str
    weight: float
    raw_score: float
    weighted_score: float
    details: str
    tool_output_snippet: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "weight": self.weight,
            "raw_score": self.raw_score,
            "weighted_score": self.weighted_score,
            "details": self.details,
            "tool_output_snippet": self.tool_output_snippet,
        }


@dataclass
class ScoreResult:
    task_id: str
    track: str
    mode: str
    total_score: float
    max_possible: float
    components: list[ScoreComponent]
    passed: bool
    passing_threshold: float
    evaluation_time_sec: float
    anti_cheat: dict[str, Any]
    resource_usage: dict[str, Any]
    metadata: dict[str, Any]
    objective_score: float = 0.0
    explanation_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "task_id": self.task_id,
            "track": self.track,
            "mode": self.mode,
            "total_score": self.total_score,
            "objective_score": self.objective_score,
            "explanation_score": self.explanation_score,
            "max_possible": self.max_possible,
            "passed": self.passed,
            "passing_threshold": self.passing_threshold,
            "evaluation_time_sec": self.evaluation_time_sec,
            "components": [c.to_dict() for c in self.components],
            "anti_cheat": self.anti_cheat,
            "resource_usage": self.resource_usage,
            "metadata": self.metadata,
        }


@dataclass
class AgentSubprocessResult:
    """Result of running an agent subprocess."""
    return_code: int
    stdout: str
    stderr: str
    wall_time_sec: float
    timed_out: bool = False


@dataclass
class AgenticRunResult:
    """Complete result of an agentic run (agent + evaluation)."""
    task_id: str
    agent_cmd: str
    agent_exit_code: int
    agent_wall_time_sec: float
    agent_timed_out: bool
    file_changes: dict[str, str]
    forbidden_violations: list[str]
    anti_cheat_clean: bool
    total_score: float
    passed: bool
    transcript_path: Path
    score_path: Path
