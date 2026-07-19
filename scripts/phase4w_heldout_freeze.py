#!/usr/bin/env python3
"""Phase-4W held-out pre-run freeze: collect fairness PT evidence, leak-scan, and write the frozen
pre-run manifest (SHA-256 of every 0011/0017 task byte, gate scripts, and evidence files).

Steps:
  1. copy per-candidate regenerated PT evidence (timing_report.rpt / evidence_manifest.json /
     stage2_summary.json) from the fairness-gate /tmp workspaces into
     reports/evidence/p14_phase4w_heldout/fairness/pt_evidence/;
  2. leak-scan every evidence file (usernames / hosts / site paths must be absent);
  3. write MANIFEST.json + SHA256SUMS over the whole evidence dir;
  4. write prerun_freeze_manifest.json: sha256 of every file in tasks 0011 + 0017, the four gate
     scripts, and the frozen randomization/interpretation/audit artifacts.
Fail-closed: exits non-zero on any missing workspace or leak hit.
"""
import glob, hashlib, json, re, shutil, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TRACK = REPO / "tasks/p14_workflow_handoff"
OUT = REPO / "reports/evidence/p14_phase4w_heldout"
EV = OUT / "fairness/pt_evidence"
LEAK = re.compile(r"/data1|tongsb|tsb@|b04|/EDA/")

def sha(p: Path) -> str: return hashlib.sha256(p.read_bytes()).hexdigest()

def collect() -> int:
    EV.mkdir(parents=True, exist_ok=True)
    n = 0
    for tid in ("workflow_handoff_0011", "workflow_handoff_0017"):
        for cand in ("golden", "wrong_axis", "stale_decoy", "unchanged_mutant"):
            dirs = sorted(glob.glob(f"/tmp/ev_{tid}_{cand}_*"), key=lambda p: Path(p).stat().st_mtime)
            if not dirs:
                print(f"FAIL: missing fairness workspace for {tid}/{cand}"); sys.exit(1)
            d = Path(dirs[-1])
            for f in ("timing_report.rpt", "evidence_manifest.json", "stage2_summary.json"):
                src = d / f
                if src.is_file():
                    shutil.copy2(src, EV / f"{tid.replace('workflow_handoff_', '')}_{cand}_{f}")
                    n += 1
    return n

def main():
    n = collect()
    print(f"collected {n} pt_evidence files")
    # leak scan over ALL evidence files under OUT
    bad = [str(f.relative_to(OUT)) for f in sorted(OUT.rglob("*")) if f.is_file()
           and f.suffix in {".json", ".rpt", ".txt", ".md"} and LEAK.search(f.read_text(errors="replace"))]
    for b in bad: print("LEAK:", b)
    if bad:
        print("FAIL: leak scan flagged files"); sys.exit(2)
    print("leak-scan: CLEAN")
    # freeze: hash every 0011/0017 file + gate scripts
    frozen = {}
    for tid in ("workflow_handoff_0011", "workflow_handoff_0017"):
        for f in sorted((TRACK / tid).rglob("*")):
            if f.is_file(): frozen[str(f.relative_to(REPO))] = sha(f)
    for s in ("gen_phase4w_heldout17.py", "phase4w_heldout_equiv.py",
              "phase4w_heldout_disclosure.py", "phase4w_heldout_fairness.py", "phase4w_heldout_freeze.py"):
        frozen[f"scripts/{s}"] = sha(REPO / "scripts" / s)
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    manifest = {
        "freeze": "Phase-4W held-out pre-run manifest (frozen BEFORE any paid call)",
        "code_commit_at_freeze_base": head,
        "task_file_hashes": frozen,
        "rule": "FROZEN. Confirmatory test: after the first held-out result is observed, 0011, 0017, the BundleS definition, the grader, and the stopping rule must not be modified.",
    }
    (OUT / "prerun_freeze_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    # MANIFEST + SHA256SUMS over the evidence dir (excluding the two files being written)
    entries, sums = {}, []
    for f in sorted(OUT.rglob("*")):
        if f.is_file() and f.name not in ("MANIFEST.json", "SHA256SUMS"):
            rel = str(f.relative_to(OUT)); h = sha(f)
            entries[rel] = h; sums.append(f"{h}  {rel}")
    (OUT / "MANIFEST.json").write_text(json.dumps(
        {"evidence_root": "reports/evidence/p14_phase4w_heldout", "files": entries}, indent=2) + "\n")
    (OUT / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    print(f"froze {len(frozen)} task/script hashes; manifested {len(entries)} evidence files")

if __name__ == "__main__":
    main()
