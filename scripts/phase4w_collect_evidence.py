#!/usr/bin/env python3
"""Collect sanitized real-PT evidence for the Phase-4W pre-run commit.

For each (task, candidate), copy the grading's score.json + sanitized_hidden.log + sanitized_public.log
from the gate runs_root (0011 from the re-run runs_root), mapped by chronological order to the
candidate order [golden, wrong_axis, stale_decoy, unchanged_mutant]. Secondary username sanitize.
Write reports/evidence/p14_phase4w_fairness/pt_evidence/<task>_<candidate>.* + SHA256SUMS + MANIFEST.
"""
import json, glob, shutil, hashlib, os
from pathlib import Path
_REAL_USER = os.environ.get("USER", "")  # strip the runtime username from any retained log path

OUT = Path("reports/evidence/p14_phase4w_fairness")
EVD = OUT / "pt_evidence"; EVD.mkdir(parents=True, exist_ok=True)
TASKS = ["workflow_handoff_0009", "workflow_handoff_0010", "workflow_handoff_0011",
         "workflow_handoff_0012", "workflow_handoff_0013", "workflow_handoff_0014"]
CANDS = ["golden", "wrong_axis", "stale_decoy", "unchanged_mutant"]

def sanitize(t: str) -> str: return t.replace(_REAL_USER, "<USER>") if _REAL_USER else t
def find_runs(task: str):
    # 0011 -> re-run runs_root (single nesting); others -> full 24-grading main runs_root (double nesting)
    if task.endswith("0011"):
        r = "/tmp/rerun0011_runs_na1_cq1x"
        return sorted(glob.glob(f"{r}/{task}/*/"))
    r = "/tmp/phase4w_gate_runs_15877aid"
    return sorted(glob.glob(f"{r}/{task}/{task}/*/"))

manifest = {"evidence": {}}
for tid in TASKS:
    dirs = find_runs(tid)
    if len(dirs) < 4:
        print(f"WARN: {tid} has {len(dirs)} grading dirs (expected 4)")
    for i, cand in enumerate(CANDS):
        if i >= len(dirs): break
        gd = dirs[i]
        base = f"{tid}_{cand}"
        for fn in ("score.json", "sanitized_hidden.log", "sanitized_public.log"):
            src = Path(gd) / fn
            if src.exists():
                dst = EVD / f"{base}__{fn.replace('sanitized_','')}"
                dst.write_text(sanitize(src.read_text(errors="replace")))
        manifest["evidence"][base] = {"grading_dir": gd, "candidate": cand, "task": tid}

# gate_results.json + fairness_verdict also go in the hashed set (already in OUT)
# write SHA256SUMS over pt_evidence/ + the top-level jsons
import subprocess
files = sorted(EVD.rglob("*"))
with open(OUT / "SHA256SUMS", "w") as f:
    for p in files:
        if p.is_file():
            f.write(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  pt_evidence/{p.relative_to(EVD).as_posix()}\n")
(OUT / "pt_evidence_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"collected {len(files)} files; tasks={len(TASKS)}; sample mapping:")
for k in list(manifest["evidence"])[:3]:
    print(" ", k, "->", manifest["evidence"][k]["candidate"])
