#!/usr/bin/env python3
"""Refresh the G8 block and the recorded HEAD in VERIFICATION.md / VERIFICATION.zh.md.

Kept as a script rather than run as a one-liner because the counts must come from `git` at the
moment of recording, never from a figure typed by hand into the record.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args],
                          capture_output=True, text=True, check=True).stdout


def counts(base: str = "master") -> tuple[int, int, int]:
    status = git("diff", "--name-status", base, "HEAD").splitlines()
    deleted = sum(1 for l in status if l.startswith("D"))
    added = sum(1 for l in status if l.startswith("A"))
    changed = sum(1 for l in status if l[0] in "MR")
    return deleted, added, changed


def tracked(rev: str | None = None) -> tuple[int, int]:
    if rev:
        lines = git("ls-tree", "-r", "-l", rev).splitlines()
        return len(lines), sum(int(p[3]) for p in (l.split() for l in lines) if p[3].isdigit())
    files = git("ls-files").split()
    total = sum((REPO / f).stat().st_size for f in files if (REPO / f).exists())
    return len(files), total


def main() -> int:
    head = git("rev-parse", "--short", "HEAD").strip()
    deleted, added, changed = counts()
    n_master, b_master = tracked("master")
    n_here, b_here = tracked()
    pct = 100 * (1 - n_here / n_master)

    blocks = {
        "VERIFICATION.md": (
            f"{deleted}  files deleted\n"
            f"{added}  files added\n"
            f"{changed}  files modified or renamed\n\n"
            f"tracked files : {n_master} -> {n_here}  (-{pct:.1f}%)\n"
            f"tracked bytes : {b_master / 1024 / 1024:.1f} MB -> {b_here / 1024 / 1024:.1f} MB\n"
        ),
        "VERIFICATION.zh.md": (
            f"删除 {deleted} 个文件\n"
            f"新增 {added} 个文件\n"
            f"修改或重命名 {changed} 个文件\n\n"
            f"跟踪文件：{n_master} -> {n_here}（-{pct:.1f}%）\n"
            f"跟踪字节：{b_master / 1024 / 1024:.1f} MB -> {b_here / 1024 / 1024:.1f} MB\n"
        ),
    }

    for name, block in blocks.items():
        p = REPO / name
        s = p.read_text()
        m = re.search(r"(## G8[^\n]*\n)(.*?)(\n[^\n#`]*(?:tripwire|触发线))", s, re.S)
        if not m:
            print(f"{name}: G8 section not found", file=sys.stderr)
            return 1
        s = s[:m.start(2)] + f"\n```\n{block}```\n" + s[m.start(3) + 1:]
        # The recorded HEAD appears once per file, in differently-worded sentences.
        s = re.sub(r"(Recorded at |记录于 )`[0-9a-f]{7,10}`", rf"\1`{head}`", s)
        # Keep a blank line between the G8 block and the paragraph after it.
        s = s.replace("```\nThe known-recurring", "```\n\nThe known-recurring")
        s = s.replace("```\n那个已知会", "```\n\n那个已知会")
        p.write_text(s)
        print(f"refreshed {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
