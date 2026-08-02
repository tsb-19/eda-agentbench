"""Regression tests for the canonical-tree integrity guard (scripts/canonical_integrity.py) and its
chain_executor integration.

Locks in:
  (a) Runtime cannot write canonical `solution/` files: enforce() makes canonical non-writable while
      the runtime workspace copy (create_agent_workspace, /tmp) stays writable and isolated.
  (b) A simulated canonical mutation mid-chain is detected post-episode -> run marked FAILED_INTEGRITY
      (exit 3), remaining slots NOT executed, an incident sidecar records before/after hash + path + ts,
      and the mutated file is NOT silently restored+continued.
Plus unit coverage of freeze/verify (modified/missing/added/head_mismatch) and enforce->relax.
"""
import json, os, subprocess, sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import canonical_integrity as cig  # noqa: E402

TRACK = "p14_workflow_handoff"
TASK = "workflow_handoff_FAKE"
TASK_ROOT = f"tasks/{TRACK}/{TASK}"


def _seed_fake_task(repo):
    root = repo / "tasks" / TRACK / TASK
    (root / "files").mkdir(parents=True)
    (root / "files" / "run_public.sh").write_text("#!/bin/bash\necho hi\n")
    (root / "hidden").mkdir(parents=True)
    (root / "hidden" / "grade.py").write_text("x=1\n")
    (root / "solution").mkdir(parents=True)
    (root / "solution" / "flow_config.json").write_text('{"netlist":"netlist_v2.v"}\n')
    (root / "metadata.json").write_text("{}")
    (root / "prompt.md").write_text("p")
    return root


def _git_init(repo):
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "seed"], check=True)


# --------------------------------------------------------------------------- unit tests

def test_freeze_verify_clean_roundtrip(tmp_path):
    _seed_fake_task(tmp_path); _git_init(tmp_path)
    m = cig.freeze(tmp_path, [TASK_ROOT], [], [])
    assert m["head"] and m["scope_dirs"] == [TASK_ROOT]
    assert len(m["task_hashes"]) == 5  # run_public.sh, grade.py, flow_config.json, metadata.json, prompt.md
    ok, inc = cig.verify(tmp_path, m)
    assert ok and inc == []


def test_verify_detects_modified_and_missing(tmp_path):
    _seed_fake_task(tmp_path); _git_init(tmp_path)
    m = cig.freeze(tmp_path, [TASK_ROOT], [], [])
    sol = tmp_path / TASK_ROOT / "solution" / "flow_config.json"
    # modified
    sol.write_text("{}")
    ok, inc = cig.verify(tmp_path, m)
    assert not ok
    mod = [i for i in inc if i["kind"] == "modified"][0]
    assert mod["path"].endswith("solution/flow_config.json")
    assert mod["expected"] != mod["actual"] and mod["ts"]
    # missing
    sol.unlink()
    ok, inc = cig.verify(tmp_path, m)
    assert any(i["kind"] == "missing" for i in inc)


def test_verify_detects_added_file(tmp_path):
    _seed_fake_task(tmp_path); _git_init(tmp_path)
    m = cig.freeze(tmp_path, [TASK_ROOT], [], [])
    # drop a new file under the task root (untracked; not in task_hashes) -> added
    (tmp_path / TASK_ROOT / "files" / "dropped.py").write_text("evil\n")
    ok, inc = cig.verify(tmp_path, m)
    assert not ok
    assert any(i["kind"] == "added" and i["path"].endswith("dropped.py") for i in inc)


def test_verify_detects_head_mismatch(tmp_path):
    _seed_fake_task(tmp_path); _git_init(tmp_path)
    # add a second commit so we can reset HEAD BEHIND the freeze (ancestor semantics)
    (tmp_path / "marker.txt").write_text("m")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "c1"], check=True)  # HEAD = c1
    m = cig.freeze(tmp_path, [TASK_ROOT], [], [])  # frozen head = c1
    # a clean descendant commit is ACCEPTED (no head_mismatch) ...
    (tmp_path / "ok.txt").write_text("x")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "descendant"], check=True)
    ok, inc = cig.verify(tmp_path, m)
    assert not any(i["kind"] == "head_mismatch" for i in inc)  # descendant allowed
    # ... but resetting HEAD behind the freeze (c1 not an ancestor of c0) IS a mismatch
    subprocess.run(["git", "-C", str(tmp_path), "reset", "--hard", "HEAD~2"], check=True)  # back to c0
    ok, inc = cig.verify(tmp_path, m)
    assert not ok
    assert any(i["kind"] == "head_mismatch" for i in inc)


def test_enforce_relax_roundtrip(tmp_path):
    _seed_fake_task(tmp_path)
    plan = cig.enforce(tmp_path, [TASK_ROOT])
    sol = tmp_path / TASK_ROOT / "solution" / "flow_config.json"
    assert not os.access(sol, os.W_OK)
    with pytest.raises(PermissionError):
        sol.write_text("{}")
    cig.relax(plan)
    assert os.access(sol, os.W_OK)


# --------------------------------------------------------------------------- (a) runtime cannot write canonical

def test_runtime_cannot_write_canonical_solution_and_copy_is_isolated(tmp_path):
    """enforce() locks canonical; create_agent_workspace hands the runtime a WRITABLE /tmp copy that is
    a separate path. (Requires workspace.py copy_function=shutil.copy — fails otherwise.)"""
    _seed_fake_task(tmp_path)
    root = tmp_path / TASK_ROOT
    plan = cig.enforce(tmp_path, [TASK_ROOT])
    # every canonical file is non-writable
    for f in root.rglob("*"):
        if f.is_file():
            assert not os.access(f, os.W_OK), f"{f} still writable"
    # the exact silent-rewrite attack on canonical solution is blocked
    sol = root / "solution" / "flow_config.json"
    with pytest.raises(PermissionError):
        sol.write_text("{}")
    # the runtime gets a SEPARATE writable /tmp copy (not canonical)
    from eda_agentbench.agentic.workspace import create_agent_workspace
    ws = create_agent_workspace(root, {"track": TRACK})
    assert str(ws).startswith("/tmp/") and Path(ws) != root
    (ws / "run_public.sh").write_text("#!/bin/bash\necho mutated\n")  # editable copy IS writable
    cig.relax(plan)
    assert os.access(sol, os.W_OK)


def test_evaluator_workspace_overlay_works_under_enforce(tmp_path):
    """Regression: under the integrity guard (canonical a-w), create_evaluator_workspace's copytree
    creates a-w copies; the overlay (copy2 of the agent's edit) must be able to overwrite them.
    _ensure_writable must run AFTER the copytree and BEFORE the overlay (the original bug: overlay hit
    an a-w destination -> PermissionError -> every guarded episode scored 0.00)."""
    root = tmp_path / TASK_ROOT
    _seed_fake_task(tmp_path)
    (root / "files" / "constraints.sdc").write_text("orig\n")  # an editable file
    plan = cig.enforce(tmp_path, [TASK_ROOT])
    from eda_agentbench.agentic.workspace import create_agent_workspace, create_evaluator_workspace
    meta = {"track": TRACK, "files": {"editable": ["constraints.sdc"],
            "visible": ["constraints.sdc", "run_public.sh"], "hidden": ["grade.py"], "forbidden": []}}
    aw = create_agent_workspace(root, meta)
    (aw / "constraints.sdc").write_text("edited\n")  # agent edits the writable copy
    ew = create_evaluator_workspace(root, meta, aw)   # must NOT raise PermissionError
    assert (ew / "constraints.sdc").read_text() == "edited\n"          # overlay applied
    assert os.access(ew / "constraints.sdc", os.W_OK)                  # grader may write it
    cig.relax(plan)


# --------------------------------------------------------------------------- (b) simulated mutation stops the chain

# Mock runner that writes a valid ACCEPT result, and on block2 mutates the canonical solution file at
# the absolute path passed via --mutate-path (forwarded through chain_executor --extra-runner-args).
MUTATING_RUNNER = r"""
import argparse, json, sys
from pathlib import Path
ap = argparse.ArgumentParser()
ap.add_argument("sub"); ap.add_argument("--models"); ap.add_argument("--track"); ap.add_argument("--task-ids")
ap.add_argument("--results"); ap.add_argument("--max-actions"); ap.add_argument("--timeout")
ap.add_argument("--temperature"); ap.add_argument("--concurrency")
ap.add_argument("--elicit-confidence", action="store_true")
ap.add_argument("--mutate-path", default=None)
a = ap.parse_args()
model = json.load(open(a.models))["models"][0]["name"]
out = Path(a.results) / model / a.track; out.mkdir(parents=True, exist_ok=True)
rec = {"total_score": 1.0, "passed": True, "agent": {"timed_out": False, "anti_cheat_clean": True},
       "components": [], "error": None}
(out / f"{a.task_ids}.json").write_text(json.dumps(rec))
(out / f"{a.task_ids}.agentlog.json").write_text(json.dumps({
    "model": model, "transport_summary": {"logical_requests": 1, "total_physical_attempts": 1,
    "recovered_failed_attempts": 0, "recovered_hard_deadlines": 0, "cumulative_retry_wall_s": 0.0,
    "terminal_transport_valid": True, "recovered_transport_degradation": False},
    "actions": [{"type": "finish"}], "usage": {}, "error": None, "retries": 0, "confidence": "high"}))
# parse block number from the results dir name (..._<blk>_<cond>_<pos>_a<attempt>) and mutate on block 2
leaf = Path(a.results).name  # "results"
parent = Path(a.results).parent.name  # "ep_2_C24_0_a1"
parts = parent.split("_")
blk = parts[1] if len(parts) > 1 else ""
if blk == "2" and a.mutate_path:
    Path(a.mutate_path).write_text("{}")  # the silent-rewrite attack; no enforce here so it succeeds
"""


def test_mutation_stops_chain_failed_integrity(tmp_path):
    _seed_fake_task(tmp_path); _git_init(tmp_path)
    m = cig.freeze(tmp_path, [TASK_ROOT], [], [])
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(m))
    sol = tmp_path / TASK_ROOT / "solution" / "flow_config.json"

    mock = tmp_path / "mock_runner.py"; mock.write_text(MUTATING_RUNNER)
    models = tmp_path / "models.json"; models.write_text(json.dumps({"models": [{"name": "TestModel"}]}))
    # 3 distinct blocks: block1 (clean), block2 (mutates canonical), block3 (must NOT run)
    sched = {"flat": [
        {"block_id": "block1", "position_in_block": 0, "condition": "C24", "task_id": TASK},
        {"block_id": "block2", "position_in_block": 0, "condition": "C24", "task_id": TASK},
        {"block_id": "block3", "position_in_block": 0, "condition": "C24", "task_id": TASK},
    ], "counts": {"C24": 3}}
    sp = tmp_path / "schedule.json"; sp.write_text(json.dumps(sched))
    state = tmp_path / "run_state.json"; log = tmp_path / "chain.log"; prefix = str(tmp_path / "ep")

    r = subprocess.run([sys.executable, str(REPO / "scripts" / "chain_executor.py"),
                        "--schedule", str(sp), "--models", str(models), "--track", TRACK,
                        "--runner", str(mock), "--model-name", "TestModel",
                        "--results-prefix", prefix, "--state", str(state), "--log", str(log),
                        "--integrity-manifest", str(manifest), "--integrity-repo", str(tmp_path),
                        "--max-replacements", "0",
                        "--extra-runner-args", f"--mutate-path {sol}"],
                       capture_output=True, text=True)
    assert r.returncode == 3, r.stderr[-800:]
    s = json.loads(state.read_text())
    assert s["state"] == "FAILED_INTEGRITY"
    assert s["executor_exit_code"] == 3
    assert s["completed_primary_slots"] == 1  # block1 completed; block2's mutation aborted before accept
    # durable sidecar with before/after hash + path + ts
    side = json.loads(Path(str(state) + ".integrity_incidents.json").read_text())
    assert side["state"] == "FAILED_INTEGRITY"
    inc = side["incidents"]
    assert any(i["kind"] == "modified" and i["path"].endswith("solution/flow_config.json")
               and i["expected"] != i["actual"] and i["ts"] for i in inc)
    # remaining slot NOT executed (no block3 results)
    assert not list(tmp_path.glob("ep_3_*_a1"))
    # NOT restored+continued: the canonical file still holds the attack bytes
    assert json.loads(sol.read_text()) == {}
