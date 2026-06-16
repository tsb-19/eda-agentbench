"""Tests for the EDA_TOOL_ROOT detector override (custom install prefix)."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from eda_agentbench.tools.detector import ToolEnvironmentDetector, _tool_root


def _make_exe(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("#!/bin/sh\necho stub\n")
    p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def test_tool_root_replaces_eda_prefix(monkeypatch):
    monkeypatch.setenv("EDA_TOOL_ROOT", "/opt/eda")
    assert _tool_root("/EDA/soft2/synopsys/vcs") == "/opt/eda/soft2/synopsys/vcs"


def test_tool_root_noop_without_override(monkeypatch):
    monkeypatch.delenv("EDA_TOOL_ROOT", raising=False)
    assert _tool_root("/EDA/soft2/synopsys/vcs") == "/EDA/soft2/synopsys/vcs"


def test_detect_via_override_prefix(tmp_path, monkeypatch):
    # Mirror the vcs probe glob: <root>/soft2/synopsys/vcs/*/amd64/bin/vcs
    root = tmp_path / "EDA"
    _make_exe(root / "soft2/synopsys/vcs/V-2023.12/amd64/bin/vcs")
    monkeypatch.setenv("EDA_TOOL_ROOT", str(root))

    det = ToolEnvironmentDetector().detect_one("vcs")
    assert det is not None and det.available is True
    assert str(det.binary_path).endswith("/amd64/bin/vcs")
    assert str(root) in str(det.binary_path)


def test_no_detection_without_override(monkeypatch):
    # On a machine without /EDA and no override, the tool is unavailable.
    monkeypatch.delenv("EDA_TOOL_ROOT", raising=False)
    if Path("/EDA/soft2/synopsys/vcs").is_dir():
        return  # skip on a real EDA host
    det = ToolEnvironmentDetector().detect_one("vcs")
    assert det is not None and det.available is False
