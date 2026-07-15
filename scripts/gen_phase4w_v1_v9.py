#!/usr/bin/env python3
"""Phase-4W Run-1 variant generator: V1 = 0010-C6, V9 = 0009+C6 (symmetric C6 ablation).

Derives two NEW task dirs from the frozen 0009/0010 source by a single, minimal, deterministic edit
to spec.md (the C6 signoff-pair assertion bullet). 0009 and 0010 are NEVER modified. The entire
hidden/ layer (handoff_truth.json, grade_workflow.py, gen_evidence_stage*.py, run_*.tcl/sh, netlists,
library) and all evidence-flow files are copied BYTE-IDENTICAL, so the grader inputs for V1/V9 are
identical to 0010/0009 and the static fairness gate (golden=1.0, wrong-axis/stale-decoy rejected) is
inherited. The ONLY semantic change is the visible C6 assertion:

  C6 bullet (present in 0010 spec.md Terminology):
    "- The setup signoff is taken at the **slow scenario** in the **functional corner**."

  V1 (0013 = 0010 - C6): remove that bullet.
  V9 (0014 = 0009 + C6): add that bullet verbatim to the Terminology section.

Usage: python3 scripts/gen_phase4w_v1_v9.py
Writes tasks/p14_workflow_handoff/workflow_handoff_0013 (V1) and ..._0014 (V9).
"""
import json
import shutil
from pathlib import Path

BASE = Path("tasks/p14_workflow_handoff")
SRC_CLEAR = BASE / "workflow_handoff_0010"      # V1 source (full bundle)
SRC_AMBIG = BASE / "workflow_handoff_0009"      # V9 source (no bundle)
C6_BULLET = "- The setup signoff is taken at the **slow scenario** in the **functional corner**."

def copy_tree(src: Path, dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

def patch_metadata(task_dir: Path, new_id: str, variant_note: str):
    mf = task_dir / "metadata.json"
    md = json.loads(mf.read_text())
    old_id = md.get("task_id")
    md["task_id"] = new_id
    md["phase4w_variant"] = variant_note
    md["phase4w_derived_from"] = old_id
    # keep variant/authority intact (provenance); the grader ignores task_id/variant for scoring
    mf.write_text(json.dumps(md, indent=2, ensure_ascii=False) + "\n")

def make_v1():
    """0013 = 0010 - C6: remove the C6 bullet from spec.md."""
    dst = BASE / "workflow_handoff_0013"
    copy_tree(SRC_CLEAR, dst)
    spec = dst / "files" / "spec.md"
    text = spec.read_text()
    assert C6_BULLET in text, "C6 bullet not found in 0010 spec.md"
    lines = text.splitlines()
    out = [ln for ln in lines if ln.strip() != C6_BULLET.strip()]
    spec.write_text("\n".join(out).rstrip() + "\n")
    patch_metadata(dst, "workflow_handoff_0013", "V1 = clear_control (0010) MINUS C6 signoff-pair assertion")
    # remove the one-line C6 mention from prompt.md if present (it is not; C6 lives only in spec.md)
    return dst

def make_v9():
    """0014 = 0009 + C6: add the C6 bullet to spec.md Terminology (verbatim, canonical wording)."""
    dst = BASE / "workflow_handoff_0014"
    copy_tree(SRC_AMBIG, dst)
    spec = dst / "files" / "spec.md"
    text = spec.read_text()
    assert C6_BULLET not in text, "C6 bullet already present in 0009 spec.md"
    assert "No value-to-axis mapping is provided." in text
    # insert the C6 bullet right before the "No value-to-axis mapping" closing line of Terminology
    lines = text.splitlines()
    out = []
    inserted = False
    for ln in lines:
        if (not inserted) and ln.strip() == "- The consumed clock is the one that yields non-zero intended-clock path coverage on the design.":
            out.append(ln)
            out.append(C6_BULLET)
            inserted = True
        else:
            out.append(ln)
    assert inserted, "Terminology clock bullet anchor not found in 0009 spec.md"
    spec.write_text("\n".join(out).rstrip() + "\n")
    patch_metadata(dst, "workflow_handoff_0014", "V9 = ambiguous (0009) PLUS C6 signoff-pair assertion")
    return dst

def main():
    v1 = make_v1()
    v9 = make_v9()
    print("generated:", v1, v9)
    # verify only spec.md + metadata.json differ from source (hidden/ + evidence flow byte-identical)
    for new, src in [(v1, SRC_CLEAR), (v9, SRC_AMBIG)]:
        import subprocess
        d = subprocess.run(["diff", "-rq", str(src), str(new)], capture_output=True, text=True).stdout
        print(f"--- diff {src.name} vs {new.name} ---")
        print(d.strip() or "(identical)")

if __name__ == "__main__":
    main()
