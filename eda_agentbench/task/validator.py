"""Task validation utilities."""

from __future__ import annotations

import re
from pathlib import Path


def check_submission_forbidden(submission_dir: Path, forbidden_files: list[str]) -> list[str]:
    """Check if submission contains any forbidden files. Returns list of violations."""
    violations: list[str] = []
    if not submission_dir.is_dir():
        return violations
    for f in forbidden_files:
        if (submission_dir / f).is_file():
            violations.append(f)
    return violations


# --- TCL injection guard for editable constraint files -----------------------
#
# P6 (dc_shell) and P7-PT (pt_shell) graders `source` the agent-EDITABLE
# constraints.sdc into the SAME Tcl interpreter that then grades it. A single
# line in that file can subvert the grader, e.g. `proc incr {args} {}` makes
# every `incr error_count` a no-op so the grader emits CONSTRAINTS_OK /
# TIMING_CHECK_OK on a broken constraint set. We reject such files.
#
# This is a denylist STOP-GAP: it blocks the obvious/literal forms but a
# determined agent can still subvert via indirection (e.g. `set c proc; $c ...`).
# The robust fix is to source the SDC in a process isolated from grading.
_TCL_INJECTION_COMMANDS = frozenset({
    # interpreter / definition manipulation (the grader-subversion vectors)
    "proc", "rename", "interp", "namespace", "eval", "uplevel", "upvar",
    "trace", "apply", "coroutine", "tailcall", "alias", "unknown",
    # IO / external execution (no place in an SDC)
    "exec", "open", "socket", "source", "load", "package", "vwait",
    "after", "fileevent", "chan", "gets", "puts",
})

# A command starts a statement: at line start, or just after ; [ or {
# (each optionally followed by spaces/tabs). Tcl `#` comments only begin a
# comment at command position, so denylisted words living inside a trailing
# comment are never at one of these anchors and are correctly ignored.
_TCL_CMD_AT_START = re.compile(r"(?:^|[;\[{])[ \t]*([A-Za-z_]\w*)", re.MULTILINE)

# Editable files we treat as Tcl (sourced by dc_shell / pt_shell).
_TCL_EDITABLE_SUFFIXES = (".sdc", ".tcl")


def check_tcl_injection(submission_dir: Path, editable_files: list[str]) -> list[str]:
    """Scan editable .sdc/.tcl files for Tcl commands that could subvert a grader
    which sources them. Returns ``["<file>: <command>", ...]`` for each distinct
    offending command, or an empty list when clean.
    """
    violations: list[str] = []
    if not submission_dir.is_dir():
        return violations
    for rel in editable_files:
        if not rel.lower().endswith(_TCL_EDITABLE_SUFFIXES):
            continue
        fpath = submission_dir / rel
        if not fpath.is_file():
            continue
        text = fpath.read_text(errors="replace")
        found = {
            m.group(1)
            for m in _TCL_CMD_AT_START.finditer(text)
            if m.group(1) in _TCL_INJECTION_COMMANDS
        }
        for cmd in sorted(found):
            violations.append(f"{rel}: {cmd}")
    return violations
