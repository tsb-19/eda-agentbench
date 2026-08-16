#!/usr/bin/env python3
"""Verify every frozen path->sha256 pin recorded anywhere under reports/.

The pre-run freeze manifests under `reports/evidence/` record the sha256 of the exact
"membership code" (generators, graders, drivers, freeze/fairness scripts, tests) that was in
force when a set of paid episodes ran.  Those hashes are the reason a reader can believe the
reported numbers were produced by the committed code and not by something edited afterwards.

This script re-derives that check mechanically: it walks every JSON under reports/, extracts
every `<repo path>: <sha256>` pair it can find, re-hashes the target, and classifies:

  pins      total distinct repo paths pinned
  missing   pinned path absent from the working tree
  mismatch  present, single pinned sha, content differs
  multi     pinned with more than one sha across phases (a legitimately versioned file);
            counted separately because "differs from one of them" is not drift

A *passing* run is one that reproduces the recorded baseline exactly -- not one that reports
zero findings.  Two mismatches and nine missing files pre-date this branch (see
`docs/provenance.md`); pretending they are absent would hide real drift rather than surface it.

Usage:
    python3 scripts/frozen_membership_verify.py            # summary + findings
    python3 scripts/frozen_membership_verify.py --json     # machine-readable
    python3 scripts/frozen_membership_verify.py --expect docs/frozen_membership_baseline.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCAN_ROOT = REPO / "reports"
SHA_LEN = 64
PATH_ROOTS = ("scripts/", "eda_agentbench/", "generators/", "tests/", "docs/", "tasks/", "configs/")


def _is_sha(v: object) -> bool:
    return isinstance(v, str) and len(v) == SHA_LEN and all(c in "0123456789abcdef" for c in v)


def _is_repo_path(v: object) -> bool:
    return isinstance(v, str) and v.startswith(PATH_ROOTS)


def collect_pins(root: Path) -> dict[str, set[tuple[str, str]]]:
    """path -> {(sha256, manifest-relative-path)}"""
    pins: dict[str, set[tuple[str, str]]] = {}

    def add(path: str, sha: str, src: Path) -> None:
        pins.setdefault(path, set()).add((sha, str(src.relative_to(REPO))))

    def walk(node: object, src: Path) -> None:
        if isinstance(node, dict):
            for key, val in node.items():
                # {"<repo path>": "<sha256>"}
                if _is_repo_path(key) and _is_sha(val):
                    add(key, val, src)
                # {"<repo path>": {"sha256": "<sha256>", ...}}
                elif _is_repo_path(key) and isinstance(val, dict) and _is_sha(val.get("sha256")):
                    add(key, val["sha256"], src)
                else:
                    walk(val, src)
        elif isinstance(node, list):
            for item in node:
                if isinstance(item, dict):
                    # [{"path": "<repo path>", "sha256": "<sha256>"}]
                    p = item.get("path") or item.get("file")
                    s = item.get("sha256") or item.get("sha")
                    if _is_repo_path(p) and _is_sha(s):
                        add(p, s, src)
                walk(item, src)

    for manifest in sorted(root.rglob("*.json")):
        try:
            walk(json.loads(manifest.read_text()), manifest)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            continue
    return pins


def classify(pins: dict[str, set[tuple[str, str]]]) -> dict[str, list]:
    missing, mismatch, multi = [], [], []
    for path, records in sorted(pins.items()):
        shas = {sha for sha, _ in records}
        target = REPO / path
        if not target.exists():
            missing.append({"path": path, "manifests": sorted({m for _, m in records})[:3]})
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual in shas:
            continue
        if len(shas) > 1:
            multi.append({"path": path, "actual": actual, "pinned": sorted(shas)})
        else:
            mismatch.append({
                "path": path,
                "actual": actual,
                "pinned": sorted(shas)[0],
                "manifests": sorted({m for _, m in records})[:3],
            })
    return {"missing": missing, "mismatch": mismatch, "multi": multi}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="emit the full finding set as JSON")
    ap.add_argument("--expect", metavar="FILE",
                    help="baseline JSON to compare counts against; non-zero exit on any drift")
    args = ap.parse_args()

    pins = collect_pins(SCAN_ROOT)
    found = classify(pins)
    summary = {
        "pins": len(pins),
        "missing": len(found["missing"]),
        "mismatch": len(found["mismatch"]),
        "multi_sha": len(found["multi"]),
    }

    if args.json:
        print(json.dumps({"summary": summary, **found}, indent=2))
    else:
        print(f"pinned paths : {summary['pins']}")
        print(f"missing      : {summary['missing']}")
        for m in found["missing"]:
            print(f"    {m['path']}")
        print(f"mismatch     : {summary['mismatch']}")
        for m in found["mismatch"]:
            print(f"    {m['path']}  now {m['actual'][:12]}  pinned {m['pinned'][:12]}")
        print(f"multi-sha    : {summary['multi_sha']}")
        for m in found["multi"]:
            print(f"    {m['path']}")

    if not args.expect:
        return 0

    baseline = json.loads((REPO / args.expect).read_text())["summary"]
    drift = {k: (baseline.get(k), v) for k, v in summary.items() if baseline.get(k) != v}
    if drift:
        print("\nFROZEN MEMBERSHIP DRIFT (expected -> actual):", file=sys.stderr)
        for key, (want, got) in sorted(drift.items()):
            print(f"    {key}: {want} -> {got}", file=sys.stderr)
        return 1
    print("\nfrozen membership matches the recorded baseline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
