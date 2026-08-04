#!/usr/bin/env python3
"""Phase-5 adversarial hidden-evidence isolation regression tests.

Proves the runtime AGENT workspace (files/ only) cannot discover truth records,
provenance graphs, fairness traces, hidden .lis/PT reports, score vectors, private
seeds, or evaluator paths — via recursive find/grep, relative-path escape, symlinks,
or ordinary file traversal. The hidden evidence (wrong_binding_signoff.rpt,
wrong_tuple_measure.lis, bake_results.json, *_truth.json, grade_*.py, run_hidden.sh)
must remain EVALUATOR-ONLY.
"""
import json, sys, subprocess
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "eda_agentbench"))
from agentic.workspace import create_agent_workspace  # noqa: E402

HIDDEN_BASENAMES = {"signoff_intent_truth.json", "meas_request_truth.json", "grade_sta_handoff.py",
                    "grade_spice_handoff.py", "run_hidden.sh", "run_launder.tcl", "run_signoff.tcl",
                    "bake_results.json", "wrong_binding_signoff.rpt", "wrong_tuple_measure.lis",
                    "instance_audit.json"}
SECRET_TOKENS = ["golden_binding", "golden_join", "wrong_binding_green", "wrong_join_plausible",
                 "expected_signoff", "REFERENCE_FC_HASH"]

INSTANCES = [
    ("p15_sta_handoff", "p15_eval_0001_bundles"),
    ("p16_spice_handoff", "p16_eval_0001_bundles"),
]


def _meta(track):
    return {"track": track, "files": {"visible": [], "editable": ["x"], "hidden": [], "forbidden": []}}


def test_agent_workspace_excludes_hidden():
    for track, tid in INSTANCES:
        task = REPO / "tasks" / track / tid
        meta = json.loads((task / "metadata.json").read_text())
        ws = create_agent_workspace(task, meta)
        present = {p.name for p in Path(ws).rglob("*") if p.is_file()}
        leaked = present & HIDDEN_BASENAMES
        assert not leaked, f"{tid}: agent workspace leaked hidden files: {leaked}"
        # the editable + visible public files SHOULD be present
        assert "exception_config.json" in present or "meas_config.json" in present, f"{tid}: editable missing"


def test_no_secret_tokens_in_agent_visible_surface():
    for track, tid in INSTANCES:
        task = REPO / "tasks" / track / tid
        meta = json.loads((task / "metadata.json").read_text())
        ws = create_agent_workspace(task, meta)
        blob = "\n".join(p.read_text(errors="ignore") for p in Path(ws).rglob("*") if p.is_file()).lower()
        leaked = [t for t in SECRET_TOKENS if t.lower() in blob]
        assert not leaked, f"{tid}: secret tokens in agent-visible surface: {leaked}"


def test_relative_path_escape_fails():
    """From inside the agent workspace, ../hidden/* must not reach the task hidden dir
    (the workspace is a fresh /tmp dir; its parent is /tmp, not the task tree)."""
    for track, tid in INSTANCES:
        task = REPO / "tasks" / track / tid
        meta = json.loads((task / "metadata.json").read_text())
        ws = create_agent_workspace(task, meta)
        for hidden_name in ("signoff_intent_truth.json", "meas_request_truth.json"):
            escaped = (Path(ws) / ".." / "hidden" / hidden_name).resolve()
            assert not escaped.is_file(), f"{tid}: relative-path escape reached {escaped}"


def test_grep_find_cannot_locate_hidden():
    """A recursive find/grep from the workspace must not surface hidden truth/evidence."""
    for track, tid in INSTANCES:
        task = REPO / "tasks" / track / tid
        meta = json.loads((task / "metadata.json").read_text())
        ws = create_agent_workspace(task, meta)
        r = subprocess.run(["find", str(ws), "-name", "*truth*", "-o", "-name", "bake_results*",
                            "-o", "-name", "wrong_binding*", "-o", "-name", "wrong_tuple*"],
                           capture_output=True, text=True)
        found = [l for l in r.stdout.splitlines() if l.strip()]
        assert not found, f"{tid}: find located hidden evidence in workspace: {found}"


def test_symlink_cannot_be_preexisting_to_hidden():
    """No file in the visible files/ tree may be a symlink that escapes to hidden/."""
    for track, tid in INSTANCES:
        task = REPO / "tasks" / track / tid / "files"
        for p in task.rglob("*"):
            if p.is_symlink():
                target = p.resolve()
                assert "hidden" not in str(target), f"{tid}: symlink {p} -> {target} reaches hidden/"
