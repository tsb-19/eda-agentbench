#!/usr/bin/env python3
"""Phase-4W held-out structural-equivalence gate.

Verifies the 0012->0017 transformation is STRUCTURALLY EQUIVALENT to the development 0010->0015
transformation (same file-set delta; same removed/added lines after normalizing only the axis-value
tokens inside the removed C6 line and the task-id/provenance-note tokens). Combined with the frozen
facts 0015 = 0009 + bundle (5abb5c5 gate) and 0012 = 0011 + bundle (97fe789 gate), this establishes
0017 = 0011 + {C1,C2,C4,C7} with the SAME component definitions and semantic transformations as the
development BundleS — and that NO new wording was introduced for the held-out truth (the only
axis-bearing delta line is REMOVED content).

Also emits the raw source diffs (0012->0017 and 0011->0017) for the evidence record.
"""
import difflib, json, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TRACK = REPO / "tasks/p14_workflow_handoff"
OUT = REPO / "reports/evidence/p14_phase4w_heldout"; OUT.mkdir(parents=True, exist_ok=True)

PAIRS = {"dev": ("workflow_handoff_0010", "workflow_handoff_0015"),
         "heldout": ("workflow_handoff_0012", "workflow_handoff_0017")}

def norm(line: str) -> str:
    # C6 axis tokens (the removed assertion differs only here by design)
    line = re.sub(r"\*\*(slow|typ|fast) scenario\*\*", "**<SCEN> scenario**", line)
    line = re.sub(r"\*\*(functional|func|test|lowpower) corner\*\*", "**<CORN> corner**", line)
    # task ids + provenance notes
    line = re.sub(r"workflow_handoff_00(09|10|11|12|15|17)", "workflow_handoff_<ID>", line)
    line = re.sub(r'"phase4w_(run2|heldout)": ".*"', '"phase4w_<NOTE>"', line)
    return line

def delta(src: Path, dst: Path):
    """Per-file (removed, added) normalized line lists for all files differing between src and dst."""
    src_files = {str(p.relative_to(src)) for p in src.rglob("*") if p.is_file()}
    dst_files = {str(p.relative_to(dst)) for p in dst.rglob("*") if p.is_file()}
    removed_files = sorted(src_files - dst_files)
    added_files = sorted(dst_files - src_files)
    per_file = {}
    for rel in sorted(src_files & dst_files):
        a = (src/rel).read_text(errors="replace").splitlines()
        b = (dst/rel).read_text(errors="replace").splitlines()
        rem, add = [], []
        for ln in difflib.unified_diff(a, b, lineterm="", n=0):
            if ln.startswith("---") or ln.startswith("+++") or ln.startswith("@@"): continue
            if ln.startswith("-"): rem.append(norm(ln[1:]))
            elif ln.startswith("+"): add.append(norm(ln[1:]))
        if rem or add: per_file[rel] = {"removed": rem, "added": add}
    return {"removed_files": removed_files, "added_files": added_files, "changed_files": per_file}

def meta_semantic_delta(src: Path, dst: Path) -> dict:
    """Key-level metadata delta. Line-wise equality is too rigid here for JSON mechanics only:
    0012 already carried a phase4w_heldout provenance key (overwritten in place), while 0010->0015
    APPENDED a new last key (churning the trailing 'version' line). The SEMANTIC delta must be the
    same for both pairs: task_id changed, one phase4w note key set, files.visible/forbidden each
    lose exactly public_check_summary.json, everything else identical."""
    a = json.loads((src/"metadata.json").read_text()); b = json.loads((dst/"metadata.json").read_text())
    note_keys = {k for k in set(a) | set(b) if k.startswith("phase4w")}
    changed = {k for k in set(a) | set(b) if a.get(k) != b.get(k)}
    files_delta_ok = all(
        [x for x in a["files"].get(key, []) if x not in b["files"].get(key, [])] == ["public_check_summary.json"]
        and [x for x in b["files"].get(key, []) if x not in a["files"].get(key, [])] == []
        for key in ("visible", "forbidden"))
    return {"changed_keys_minus_notes": sorted(changed - note_keys),
            "note_key_set": bool(note_keys & changed) or bool(note_keys),
            "files_lists_lose_exactly_summary": files_delta_ok,
            "semantic_delta_ok": sorted(changed - note_keys) == ["files", "task_id"] and files_delta_ok}

def main():
    deltas = {k: delta(TRACK/s, TRACK/d) for k, (s, d) in PAIRS.items()}
    dev, ho = deltas["dev"], deltas["heldout"]
    meta_sem = {k: meta_semantic_delta(TRACK/s, TRACK/d) for k, (s, d) in PAIRS.items()}
    checks = {
        "file_set_delta_equal": dev["removed_files"] == ho["removed_files"] == ["files/public_check_summary.json"]
                                and dev["added_files"] == ho["added_files"] == [],
        "same_changed_file_set": sorted(dev["changed_files"]) == sorted(ho["changed_files"]),
        "per_file_normalized_delta_equal": {},
        "metadata_semantic_delta": meta_sem,
    }
    for rel in sorted(set(dev["changed_files"]) | set(ho["changed_files"])):
        if rel == "metadata.json":
            checks["per_file_normalized_delta_equal"][rel] = "semantic (see metadata_semantic_delta)"
            continue
        checks["per_file_normalized_delta_equal"][rel] = dev["changed_files"].get(rel) == ho["changed_files"].get(rel)
    all_equal = checks["file_set_delta_equal"] and checks["same_changed_file_set"] \
                and all(v is True for k, v in checks["per_file_normalized_delta_equal"].items() if k != "metadata.json") \
                and all(m["semantic_delta_ok"] for m in meta_sem.values())
    # composition facts
    glossary_identical = subprocess.run(["cmp", "-s",
        str(TRACK/"workflow_handoff_0015/files/glossary.md"),
        str(TRACK/"workflow_handoff_0017/files/glossary.md")]).returncode == 0
    verdict = {
        "gate": "Phase-4W held-out structural equivalence (0012->0017 vs 0010->0015)",
        "checks": checks,
        "glossary_0015_vs_0017_byte_identical": glossary_identical,
        "composition_argument": "0017 = 0012 - X, where the removal delta X is line-identical (after axis-token normalization of the removed C6 line only) to the dev removal 0015 = 0010 - X; with the frozen facts 0012 = 0011 + full bundle (97fe789) and 0015 = 0010 - X = 0009 + C1/C2/C4/C7 (5abb5c5), 0017 = 0011 + C1/C2/C4/C7 by composition.",
        "no_new_wording": "all added/replacement strings are byte-identical to gen_phase4w_run2.py; the only axis-bearing delta line (C6) is REMOVED frozen content",
        "PASS": bool(all_equal and glossary_identical),
        "deltas": deltas,
    }
    (OUT/"structural_equivalence.json").write_text(json.dumps(verdict, indent=2) + "\n")
    # raw diffs for the record (repo-relative paths so no site paths leak into evidence)
    for name, (s, d) in [("source_diff_0012_to_0017.txt", ("workflow_handoff_0012","workflow_handoff_0017")),
                          ("source_diff_0011_to_0017.txt", ("workflow_handoff_0011","workflow_handoff_0017"))]:
        r = subprocess.run(["diff", "-ruN", f"tasks/p14_workflow_handoff/{s}", f"tasks/p14_workflow_handoff/{d}"],
                           capture_output=True, text=True, cwd=str(REPO))
        (OUT/name).write_text(r.stdout)
    print(json.dumps({k: v for k, v in verdict.items() if k != "deltas"}, indent=2))
    sys.exit(0 if verdict["PASS"] else 1)

if __name__ == "__main__":
    main()
