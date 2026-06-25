"""Agentic provisioning invariants — the public flow must be runnable in the agent workspace.

Regression guard for the Phase-2 p7_primetime flaw: `design_netlist.v` was a HIDDEN artifact
that the agent-visible `run_public.tcl` tried to `read_verilog`. The agent workspace holds only
visible+editable files, so the public flow was un-runnable and tempted models into fabricating the
hidden netlist — which `detect_hidden_shadows` then (correctly) flagged as anti-cheat. The fix made
the netlist a visible, read-only (forbidden-to-edit) input. These tests would have caught the bug
and protect every track from re-introducing the same provisioning anti-pattern.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from eda_agentbench.agentic.workspace import create_agent_workspace

TASKS_ROOT = Path(__file__).resolve().parent.parent / "tasks"
PT_DIR = TASKS_ROOT / "p7_primetime_sta_debug"

# Agent-visible runner scripts are the ones the agent is told to run to see the symptom.
_SCRIPT_SUFFIXES = (".sh", ".tcl")
# read_verilog / read_sdc / source / read_db ... — file-consuming Tcl/bash commands, matched only
# when they START a (non-comment) line, so prose like "read_sdc sandboxes Tcl proc" is ignored.
_READ_RE = re.compile(r"^(?:read_verilog|read_sdc|read_db|read_file|source)\s+(\S+)")


def _reads_from_script(text: str) -> set[str]:
    """Basenames of files a script reads via read_*/source (skips comment lines + prose)."""
    out: set[str] = set()
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = _READ_RE.match(s)
        if m:
            out.add(Path(m.group(1).strip("\"'")).name)
    return out


def _iter_task_dirs():
    """Yield every task dir under tasks/ that has a metadata.json."""
    for meta_path in TASKS_ROOT.rglob("metadata.json"):
        yield meta_path.parent


def _hidden_only_basenames(meta: dict) -> set[str]:
    files = meta.get("files", {})
    visible = {Path(f).name for f in files.get("visible", [])}
    hidden = {Path(f).name for f in files.get("hidden", [])}
    return hidden - visible


def test_visible_scripts_never_reference_hidden_only_artifacts():
    """No agent-visible runner script may reference a hidden-only file basename.

    This is the general invariant the p7_primetime bug violated. A public script that reads a
    hidden-only artifact cannot run in the agent workspace (the file isn't there), which is unfair
    and induces fabrication.
    """
    offenders: list[str] = []
    n_scripts = 0
    for task_dir in _iter_task_dirs():
        meta = json.loads((task_dir / "metadata.json").read_text())
        hidden_only = _hidden_only_basenames(meta)
        if not hidden_only:
            continue
        for vis in meta.get("files", {}).get("visible", []):
            if not vis.endswith(_SCRIPT_SUFFIXES):
                continue
            sp = task_dir / "files" / vis
            if not sp.is_file():
                continue
            n_scripts += 1
            text = sp.read_text()
            for base in _reads_from_script(text):
                if base in hidden_only:
                    offenders.append(f"{task_dir.name}/{vis} reads hidden-only '{base}'")
    assert not offenders, "Agent-visible scripts reference hidden-only artifacts:\n" + "\n".join(offenders)


def test_pt_public_flow_runnable_in_agent_workspace():
    """For every PT task, a fresh agent workspace must contain every file run_public.tcl reads.

    Directly proves the provisioning fix: the netlist (and SDC) the public PrimeTime flow consumes
    are present without any hidden overlay, so the agent never needs to fabricate them.
    """
    if not PT_DIR.is_dir():
        pytest.skip("p7_primetime tasks not generated")
    task_dirs = [d for d in sorted(PT_DIR.rglob("metadata.json"))]
    assert task_dirs, "no PT tasks found"
    for meta_path in task_dirs:
        task_dir = meta_path.parent
        meta = json.loads(meta_path.read_text())
        tcl = (task_dir / "files" / "run_public.tcl").read_text()
        reads = _reads_from_script(tcl)
        assert "design_netlist.v" in reads, f"{task_dir.name}: run_public.tcl should read the netlist"
        ws = create_agent_workspace(task_dir, meta)
        try:
            for fname in reads:
                assert (ws / fname).is_file(), \
                    f"{task_dir.name}: run_public.tcl reads '{fname}' but it is absent from the agent workspace"
        finally:
            import shutil
            shutil.rmtree(ws, ignore_errors=True)


def test_pt_netlist_is_visible_and_forbidden_to_edit():
    """The netlist must be a visible, read-only input: in `visible` (agent can read it) and in
    `forbidden` (editing it is still caught), and NOT in `hidden`."""
    if not PT_DIR.is_dir():
        pytest.skip("p7_primetime tasks not generated")
    for meta_path in sorted(PT_DIR.rglob("metadata.json")):
        meta = json.loads(meta_path.read_text())
        files = meta["files"]
        name = "design_netlist.v"
        assert name in files["visible"], f"{meta_path.parent.name}: netlist must be visible"
        assert name in files["forbidden"], f"{meta_path.parent.name}: netlist must be forbidden-to-edit"
        assert name not in files["hidden"], f"{meta_path.parent.name}: netlist must not be hidden"
        assert name not in files["editable"], f"{meta_path.parent.name}: netlist must not be editable"
