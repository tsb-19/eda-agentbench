#!/usr/bin/env python3
"""Fail if any kept file references a repository path that no longer exists.

The `iclr2027-artifact` branch removes roughly 21 500 files. The failure mode that would make
the branch worse than the bloated original is a *dangling* reference: a README pointing at a
deleted doc, a kept script importing a deleted module, an evidence index naming a report that is
gone. A reader following such a pointer learns less than one who was never given it.

Scope and exemptions, each for a stated reason:

  * `reports/evidence/**` is exempt. It is frozen custody evidence and may not be edited, so a
    stale pointer inside it cannot be repaired. Its integrity is covered instead by
    `scripts/frozen_membership_verify.py`, which checks the hashes those manifests pin.
  * `docs/REMOVED.md` and this branch's design spec are exempt: their whole purpose is to name
    removed paths.
  * Paths inside fenced code blocks are still checked -- a broken command is a broken pointer --
    but a reference is only reported when it looks like a concrete file or directory, not a glob,
    a placeholder (`<...>`, `{...}`, `$VAR`, `...`), or a path under a gitignored output tree.

Usage:
    python3 scripts/slim_link_check.py           # report and exit non-zero on any dangling ref
    python3 scripts/slim_link_check.py --list     # also list every resolved reference
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Directories whose contents are deliberately absent from git (build/run output).
IGNORED_PREFIXES = (
    "runs/", "workspaces/", "datagen/tasks_eval_private/", "datagen/.local_runs/", ".cache/",
)

# Files that are allowed -- required -- to mention removed paths.
EXEMPT_FILES = {
    "docs/REMOVED.md",
    "docs/REMOVED.zh.md",
    "docs/frozen_membership_baseline.json",
    "docs/superpowers/specs/2026-08-16-slim-artifact-branch-design.md",
    "docs/superpowers/specs/2026-08-11-repo-cleanup-design.md",
    "scripts/slim_link_check.py",
}
EXEMPT_PREFIXES = ("reports/evidence/",)

TEXT_SUFFIXES = {".md", ".py", ".sh", ".json", ".tex", ".toml", ".cfg", ".txt", ".html", ".bib"}

# Matches that look like paths but are prose or optional inputs. Each is listed with its reason
# because the alternative -- loosening the regex until they vanish -- would also hide real breaks.
# Several sit in generated report JSON or frozen task metadata that must not be edited.
KNOWN_PROSE = {
    "docs/datacard/release": "prose: 'the docs/datacard/release policy'",
    "docs/evidence-only": "prose: 'docs/evidence-only change' in a generated report",
    "generators/graders": "prose: 'generators/graders are independent per family'",
    "reports/spec": "prose: 'reports/spec intersection' in a generator comment",
    "reports/evidence/phase7b_annotation/packets/P": "format-string stem in a log line",
    "reports/evidence/phase7c_terminalbench/tb21_modifications.json":
        "optional operator-supplied input; the script emits a template when absent",
    "submission/workspace": "prose: 'submission/workspace layout'",
    "tasks/grader": "prose: 'tasks/grader pair' in a generated report",
    "tasks/track": "prose: 'tasks/track breakdown' in a generated report",
    "reports/archive/": "a removed directory named inside a generated report that may not be edited; "
                        "the probes it held are listed in docs/REMOVED.md",
    "docs/synthetic_trajectory_handoff_design.md":
        "pre-move path frozen into tasks/p13_trajectory_handoff/traj_handoff_0001/metadata.json; "
        "already dangling on master (the 2026-08-11 doc move), and the metadata is frozen task "
        "data that may not be edited to repair it",
}

# Suffixes tried when a reference names a module or a file stem rather than a full filename
# (`scripts/foo.bar_symbol`, `reports/synthetic_x_manifest`).
STEM_SUFFIXES = (".py", ".md", ".json", ".sh", ".tex", ".csv")

TOP_LEVEL = ("tasks", "scripts", "generators", "eda_agentbench", "tests", "docs", "reports",
             "submission", "configs", "datagen", "experiments")
REF = re.compile(r"\b(?:" + "|".join(TOP_LEVEL) + r")/[A-Za-z0-9_][A-Za-z0-9_./-]*")
PLACEHOLDER = re.compile(r"[<>{}$*?]|\.\.\.|\bNNNN\b|\bxxxxxx\b|\bXXXX")
# A match immediately followed by one of these is the literal stem of a glob or placeholder
# (`docs/synthetic_*.md`, `tasks/p1_rtl_debug/task_{id}`), not a concrete path.
GLOB_NEXT = set("*?{<[")


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "-C", str(REPO), "ls-files"],
                         capture_output=True, text=True, check=True).stdout
    return out.split()


def resolves(ref: str) -> bool:
    """True if `ref` names something real, allowing module.symbol and bare-stem forms."""
    if (REPO / ref).exists():
        return True
    for suffix in STEM_SUFFIXES:                      # reports/x_manifest -> reports/x_manifest.json
        if (REPO / (ref + suffix)).exists():
            return True
    head, dot, _tail = ref.partition(".")             # scripts/mod.symbol -> scripts/mod.py
    if dot:
        for suffix in STEM_SUFFIXES:
            if (REPO / (head + suffix)).exists():
                return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="print resolved references too")
    args = ap.parse_args()

    files = tracked_files()
    dangling: dict[str, list[tuple[str, int]]] = {}
    resolved = 0

    for rel in files:
        if rel in EXEMPT_FILES or rel.startswith(EXEMPT_PREFIXES):
            continue
        path = REPO / rel
        if path.suffix not in TEXT_SUFFIXES or not path.exists():
            continue
        try:
            lines = path.read_text(errors="ignore").splitlines()
        except OSError:
            continue
        for lineno, line in enumerate(lines, 1):
            for match in REF.finditer(line):
                raw = match.group(0)
                after = line[match.end():match.end() + 1]
                if after in GLOB_NEXT or raw.endswith(("_", "-")):
                    continue
                ref = raw.rstrip(".,;:)]\"'`*")
                if PLACEHOLDER.search(ref) or ref.startswith(IGNORED_PREFIXES):
                    continue
                if ref in KNOWN_PROSE:
                    continue
                if resolves(ref):
                    resolved += 1
                    if args.list:
                        print(f"  ok {rel}:{lineno}  {ref}")
                    continue
                dangling.setdefault(ref, []).append((rel, lineno))

    print(f"scanned {len(files)} tracked files; {resolved} references resolved")
    if not dangling:
        print("no dangling repository references")
        return 0

    print(f"\nDANGLING REFERENCES: {len(dangling)}", file=sys.stderr)
    for ref, sites in sorted(dangling.items()):
        where = ", ".join(f"{f}:{n}" for f, n in sites[:4])
        more = f" (+{len(sites) - 4} more)" if len(sites) > 4 else ""
        print(f"    {ref}\n        <- {where}{more}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
