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
# Defense-in-depth against grader subversion via the agent-EDITABLE
# constraints.sdc (P6 dc_shell / P7-PT pt_shell).
#
# The PRIMARY defense is structural (see generators/p6_dc_constraint_debug_gen
# and p7_primetime_sta_debug_gen): the apply phase ingests the agent SDC with
# `read_sdc` (which sandboxes Tcl `proc`/`exit`) and re-emits a canonical file
# with `write_sdc`; a separate bash phase -- running no agent code -- computes
# the pass/fail verdict from that laundered file. An injected `proc incr {} {}`,
# `exit 0`, or `echo CONSTRAINTS_OK` can no longer reach or forge the verdict.
#
# This denylist is the SECONDARY layer: it flags obvious injection attempts as
# an explicit anti-cheat violation (hard zero, recorded in the result) before
# the tool ever runs. It is a denylist, not a sandbox -- a determined agent can
# evade it via indirection (e.g. `set c proc; $c ...`) -- which is exactly why
# the structural defense above, not this list, is what guarantees verdict
# integrity.
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
