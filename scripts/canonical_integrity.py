#!/usr/bin/env python3
"""Canonical-tree integrity guard for paid runs.

A frozen canonical reference (task trees incl. files/hidden/solution, graders, generators, membership
code, evidence-input manifests) is hashed pre-run into a manifest. At runtime (inside an exact-commit
isolated git worktree) the canonical task directories are made NON-WRITABLE (OS-level prevention), and
their SHA-256 hashes are verified before the run, after EVERY episode, and after the chain. Any
mutation (modified/missing/added file, or HEAD drift) atomically marks the run FAILED_INTEGRITY and
STOPS the remaining slots; an incident record (before/after hash, repo-relative path, timestamp,
sanitized) is written to a durable sidecar. The guard NEVER silently restores a mutated source tree
and continues.

Why: an unidentified external process kept rewriting the frozen golden
`tasks/p14_workflow_handoff/workflow_handoff_0009/solution/flow_config.json` to `{}` (every few hours),
which caused a ~21h false "b04 outage" via the fairness L2 frozen-hash check. `chmod 444` on that one
file is defense-in-depth only; this module is the authoritative control.

Runtime confinement is already by cwd/env/regex discipline (the agent + grading run on /tmp temp
copies; `solution/` is never copied in agentic mode — see eda_agentbench/agentic/workspace.py), so this
guard hardens a property that already holds operationally and closes the gap that a malicious agent RUN
with an obfuscated absolute path could otherwise write canonical.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, tempfile
from datetime import datetime, timezone
from pathlib import Path


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _atomic_write_json(path: Path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _git_head(repo: Path) -> str:
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()


def freeze(repo, task_roots, code_files=None, evidence_files=None) -> dict:
    """Build the canonical hash manifest at the current HEAD. Paths are repo-relative.

    `task_roots`: repo-relative dirs (e.g. 'tasks/p14_workflow_handoff/workflow_handoff_0021'); every
    file under each is hashed (files/, hidden/, solution/, metadata, prompt). A missing task root is a
    hard error (fail-closed). `code_files`/`evidence_files` are repo-relative files; missing ones are
    skipped (optional).
    """
    repo = Path(repo)
    code_files = code_files or []
    evidence_files = evidence_files or []
    task_hashes = {}
    for root in task_roots:
        base = repo / root
        if not base.exists():
            raise FileNotFoundError(f"freeze: task root missing: {root}")
        for f in sorted(base.rglob("*")):
            if f.is_file():
                task_hashes[str(f.relative_to(repo))] = _sha256(f)
    code_hashes = {rel: _sha256(repo / rel) for rel in code_files if (repo / rel).is_file()}
    evidence_hashes = {rel: _sha256(repo / rel) for rel in evidence_files if (repo / rel).is_file()}
    return {"schema": "canonical_integrity/v1", "head": _git_head(repo), "frozen_at": _now_iso(),
            "task_hashes": task_hashes, "code_hashes": code_hashes, "evidence_hashes": evidence_hashes,
            "scope_dirs": list(task_roots),
            "rule": "FROZEN; any mutation aborts the run as FAILED_INTEGRITY. Never silently restore."}


def verify(repo, manifest):
    """Re-hash and diff against a frozen manifest. Returns (ok, incidents).

    Incidents: head_mismatch | modified | missing | added. Each carries {kind, path(repo-relative),
    expected, actual, ts}. Added-file detection is scoped to scope_dirs (canonical task dirs) so
    __pycache__/runs/reports churn elsewhere never false-positives.

    HEAD check is ancestor-or-equal: the run executes in an exact-commit worktree, and the manifest's
    `head` pins the frozen CODE BASE. The run commit may be a clean descendant that adds only the freeze
    manifests (the manifest cannot store its own commit hash). Exact match OR manifest-head is an ancestor
    of HEAD is accepted; anything else (different branch, HEAD behind the freeze) is head_mismatch. Content
    hashes are the authoritative per-file guarantee.
    """
    repo = Path(repo)
    ts = _now_iso()
    incidents = []
    head = _git_head(repo)
    frozen_head = manifest.get("head")
    if head != frozen_head and frozen_head:
        anc = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", frozen_head, head],
                             capture_output=True, text=True)
        if anc.returncode != 0:  # frozen head NOT an ancestor of HEAD -> drift / wrong branch
            incidents.append({"kind": "head_mismatch", "path": "(HEAD)",
                              "expected": frozen_head, "actual": head, "ts": ts})
    frozen = {}
    for k in ("task_hashes", "code_hashes", "evidence_hashes"):
        frozen.update(manifest.get(k, {}))
    for rel, expected in sorted(frozen.items()):
        f = repo / rel
        if not f.is_file():
            incidents.append({"kind": "missing", "path": rel, "expected": expected, "actual": None, "ts": ts})
            continue
        actual = _sha256(f)
        if actual != expected:
            incidents.append({"kind": "modified", "path": rel, "expected": expected, "actual": actual, "ts": ts})
    known = set(frozen)
    for d in manifest.get("scope_dirs", []):
        base = repo / d
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*")):
            if f.is_file():
                rel = str(f.relative_to(repo))
                if rel not in known:
                    incidents.append({"kind": "added", "path": rel, "expected": None,
                                      "actual": _sha256(f), "ts": ts})
    return (len(incidents) == 0, incidents)


def enforce(repo, scope_dirs) -> dict:
    """chmod every file+dir under the canonical task roots to clear ALL write bits (keep read/exec).

    Returns a restore plan (list of (path, orig_mode_oct)) consumed by relax(). Directories are
    locked too (prevents create/delete inside). Read/execute preserved so copytree/graders still read.
    """
    repo = Path(repo)
    entries = []
    for d in scope_dirs:
        base = repo / d
        if not base.exists():
            continue
        targets = [base] + [p for p in base.rglob("*")]
        for p in targets:
            if p.exists():
                m = p.stat().st_mode
                entries.append((str(p), oct(m & 0o7777)))
                os.chmod(p, m & ~0o222)  # clear ugo write bits
    return {"entries": entries}


def relax(restore_plan):
    """Restore original modes so cleanup (e.g. git worktree remove) succeeds without --force."""
    for path_str, mode_str in restore_plan.get("entries", []):
        try:
            os.chmod(Path(path_str), int(mode_str, 8))
        except OSError:
            pass  # best-effort (worktree may already be gone)


def record_incident_sidecar(state_path, manifest, incidents) -> Path:
    """Durably record the integrity failure to <state>.integrity_incidents.json.

    A SEPARATE file (not the run-state JSON) so the record survives any state overwrite by the
    executor's except handlers. Sanitized: repo-relative paths only, no host/user/abs path.
    """
    sidecar = Path(str(state_path) + ".integrity_incidents.json")
    _atomic_write_json(sidecar, {"state": "FAILED_INTEGRITY", "recorded_at": _now_iso(),
                                 "head_at_freeze": manifest.get("head"),
                                 "n_incidents": len(incidents), "incidents": incidents,
                                 "sanitized": True, "rule": "no silent restore; run STOPPED"})
    return sidecar
