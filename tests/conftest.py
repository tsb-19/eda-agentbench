"""Shared pytest configuration for the harness test suite.

The commercial EDA tools (VCS, HSPICE, PrimeTime, Design Compiler, Spectre,
SpyGlass) are not installed locally -- they live on b04 and are reached through
the transparent shim (see CLAUDE.md). Tests that genuinely need a tool are
marked ``@pytest.mark.requires_tools``.

``scripts/check`` excludes those tests by marker (``-m "not requires_tools"``).
A bare ``pytest tests/`` does not, and without this hook the tool-backed tests
*fail* rather than *skip*, which makes a healthy checkout look broken. Skip them
when no tool is reachable, and let them run normally once the shim env is
sourced.
"""
from __future__ import annotations

import shutil

import pytest

# One representative executable per vendor tool family the suite can exercise.
_TOOL_EXECUTABLES = ("vcs", "hspice", "spectre", "pt_shell", "dc_shell", "sg_shell")


def _any_tool_available() -> bool:
    return any(shutil.which(exe) for exe in _TOOL_EXECUTABLES)


def pytest_collection_modifyitems(config, items):
    """Skip ``requires_tools`` tests when no commercial EDA tool is on PATH."""
    if _any_tool_available():
        return
    skip = pytest.mark.skip(
        reason="no commercial EDA tool on PATH; source the b04 shim env to run "
               "(tool-free gate: scripts/check)"
    )
    for item in items:
        if "requires_tools" in item.keywords:
            item.add_marker(skip)
