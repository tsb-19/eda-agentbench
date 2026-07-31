#!/usr/bin/env python3
"""Guarded paid-run launcher: executes a chain_executor schedule inside an EXACT-COMMIT ISOLATED git
worktree under the canonical-tree integrity guard.

Flow:
  1. Assert the source canonical tree (tasks/ scripts/ eda_agentbench/) is clean and HEAD == the
     freeze commit pinned in the integrity manifest.
  2. `git worktree add --detach <tmp> <head>` — an isolated checkout at the exact freeze commit.
  3. Inside the worktree: verify HEAD + canonical hashes against the manifest (abort before any paid
     call on mismatch).
  4. `enforce` — chmod the canonical task directories non-writable (OS-level prevention; runtime works
     on /tmp copies via workspace.py's copy_function=shutil.copy).
  5. Run chain_executor with --integrity-manifest (it re-verifies after every episode and post-chain;
     any mutation -> FAILED_INTEGRITY + exit 3, remaining slots stopped, never restored+continued).
  6. Post-chain verify (defense in depth).
  7. Cleanup: relax (restore write bits) + `git worktree remove`.

On integrity failure the run-state + sidecar incident record (under --state, outside the worktree)
persist; the source tree is NEVER silently restored and collection does NOT continue.

Env: invoke from a shell that already sourced the b04 shim env and exported the streaming vars (see
runs/*.sh wrappers); this launcher inherits os.environ and passes it through to chain_executor.
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import canonical_integrity as cig  # noqa: E402


def _git(*args, check=True, capture=True):
    r = subprocess.run(["git", "-C", str(REPO), *args], capture_output=capture, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr}")
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--integrity-manifest", required=True, help="repo-relative or absolute path to canonical_integrity_manifest.json")
    ap.add_argument("--schedule", required=True)
    ap.add_argument("--models", required=True)
    ap.add_argument("--track", required=True)
    ap.add_argument("--runner", required=True, help="repo-relative runner path (resolved inside the worktree)")
    ap.add_argument("--model-name", required=True)
    ap.add_argument("--results-prefix", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--max-replacements", type=int, default=2)
    ap.add_argument("--max-actions", type=int, default=60)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--elicit-confidence", action="store_true")
    ap.add_argument("--extra-runner-args", default=None)
    ap.add_argument("--keep-on-fail", action="store_true", help="keep the worktree for forensics on integrity failure")
    a = ap.parse_args()

    # resolve the manifest (source); it is also present in the worktree at the same repo-relative path
    man_path = Path(a.integrity_manifest)
    if not man_path.is_absolute():
        man_path = REPO / man_path
    m = json.loads(man_path.read_text())
    man_rel = str(man_path.relative_to(REPO)) if man_path.is_relative_to(REPO) else a.integrity_manifest

    # (1) source canonical tree must be clean (the manifests/schedule we pass in are the committed ones)
    dirty = _git("status", "--porcelain", "--", "tasks", "scripts", "eda_agentbench").stdout
    if dirty.strip():
        print(f"ABORT: source canonical tree not clean:\n{dirty}", file=sys.stderr)
        return 3
    head = _git("rev-parse", "HEAD").stdout.strip()

    # (2) isolated exact-commit worktree at the clean source HEAD (detached so it cannot drift).
    # cig.verify inside enforces that the manifest's frozen head is an ancestor-or-equal of HEAD
    # (the run commit may be a clean descendant adding only the freeze manifests; drift/branch-swap
    # is rejected). Content hashes are the authoritative per-file guarantee.
    worktree = Path(tempfile.mkdtemp(prefix="eda_guarded_"))
    _git("worktree", "add", "--detach", str(worktree), head)
    print(f"[guard] worktree at {head[:8]} -> {worktree} (freeze base ancestor {m['head'][:8]})", flush=True)

    rc = 3
    try:
        # (4) pre-launch verify inside the worktree
        ok, inc = cig.verify(worktree, m)
        if not ok:
            print(f"ABORT: pre-launch integrity verify failed: {inc}", file=sys.stderr)
            cig.record_incident_sidecar(a.state, m, inc)
            return 3
        # (5) enforce: canonical task dirs non-writable
        plan = cig.enforce(worktree, m["scope_dirs"])
        try:
            cmd = [sys.executable, str(worktree / "scripts" / "chain_executor.py"),
                   "--schedule", a.schedule, "--models", a.models, "--track", a.track,
                   "--runner", a.runner, "--model-name", a.model_name,
                   "--results-prefix", a.results_prefix, "--state", a.state, "--log", a.log,
                   "--integrity-manifest", man_rel, "--integrity-repo", str(worktree),
                   "--max-replacements", str(a.max_replacements), "--max-actions", str(a.max_actions),
                   "--timeout", str(a.timeout), "--temperature", str(a.temperature)]
            if a.elicit_confidence:
                cmd.append("--elicit-confidence")
            if a.extra_runner_args:
                cmd += ["--extra-runner-args", a.extra_runner_args]
            print(f"[guard] exec chain_executor in worktree (cwd={worktree})", flush=True)
            rc = subprocess.call(cmd, cwd=str(worktree))
        finally:
            cig.relax(plan)  # restore write bits so worktree remove succeeds without --force
        # (6) post-chain verify (defense in depth)
        ok2, inc2 = cig.verify(worktree, m)
        if not ok2:
            print(f"[guard] post-chain integrity verify FAILED: {inc2}", file=sys.stderr)
            cig.record_incident_sidecar(a.state, m, inc2)
            rc = 3
        return rc
    finally:
        if rc == 0 or not a.keep_on_fail:
            _git("worktree", "remove", str(worktree), check=False)
            print(f"[guard] worktree removed (rc={rc})", flush=True)
        else:
            print(f"[guard] worktree KEPT for forensics: {worktree}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
