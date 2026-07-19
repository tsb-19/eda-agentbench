#!/usr/bin/env python3
"""Phase-4W held-out variant generator: workflow_handoff_0017 = frozen 0011 + exactly {C1,C2,C4,C7}.

Implemented as 0012 - public_check_summary - C6, the SAME transformation that produced the development
BundleS (0015 = 0010 - public_check_summary - C6 = 0009 + C1/C2/C4/C7, scripts/gen_phase4w_run2.py).
Since 0012 = 0011 + full clarity bundle (frozen at 97fe789), removing C3/C5 (public_check_summary.json)
and C6 (the signoff-pair assertion) yields 0017 = 0011 + {C1 canonical labels + disjoint-typed-axes
declaration, C2 PVT-def, C4 glossary, C7 contract wording}.

NO NEW WORDING: every replacement string below is copied byte-identically from gen_phase4w_run2.py
(none contains an axis value). The only axis-bearing string is C6_LINE, which is REMOVED content
(0012's own frozen wording), never added. glossary.md is inherited byte-identical from 0012 (itself
byte-identical to 0010's). 0011 and 0012 are never modified.

Fail-closed: assert source commit + source hashes; assert component presence/absence; assert no
C6-style pair statement and no directive-style golden-pair phrase in public directive files.
"""
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TRACK = REPO / "tasks/p14_workflow_handoff"
EXPECTED_COMMIT = "fde9dda2c77c2822daf6521bec331f95fe128a61"

SRC_HASHES = {
    "0012/flow_config": "c69a0ef3f5b9edccbf8d6e48ba869bec31570c84001e61a8911e3f9418e5e26a",
    "0011/flow_config": "d5dcb3484e7bc23b0216c4a42fc8a66b5c9ab6c19f28d54f0a73b31fb1822f46",
}
# 0012's frozen C6 assertion (held-out axis values; REMOVED, never rewritten)
C6_LINE = "- The setup signoff is taken at the **typ scenario** in the **test corner**."

class FailClosed(Exception): pass

def sha_file(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def make_heldout(out: Path):
    # ---- 0017 = 0012 - public_check_summary - C6 (mirror of the 0010->0015 transformation) ----
    s = out / "workflow_handoff_0017"
    if s.exists(): shutil.rmtree(s)
    shutil.copytree(TRACK / "workflow_handoff_0012", s)
    # remove the summary file (C3 coverage fact + C5 pairwise conflicts)
    (s / "files/public_check_summary.json").unlink()
    # remove C6 assertion from spec.md
    spec = s / "files/spec.md"; t = spec.read_text()
    if C6_LINE not in t: raise FailClosed("C6 line not found in 0012 spec")
    t = t.replace(C6_LINE + "\n", "")
    # remove the public_check_summary bullet + clean step-1 wording (strings verbatim from gen_phase4w_run2.py)
    t = t.replace("- `public_check_summary.json` — pairwise inconsistency symptoms + the coverage fact (verdict-first; never the answer/schema).\n", "")
    t = t.replace("glossary.md + public_check_summary.json give the disjoint-axis rule and the coverage fact",
                  "glossary.md gives the disjoint-axis rule")
    spec.write_text(t)
    # prompt.md + flow_config + manifests: drop "+ public_check_summary.json" refs (verbatim from gen_phase4w_run2.py)
    for f, old, new in [
        (s/"prompt.md", "glossary.md + public_check_summary.json state the disjoint typed axes and the coverage fact",
                        "glossary.md states the disjoint typed axes"),
        (s/"files/flow_config.json", "glossary.md + public_check_summary.json state the disjoint typed axes and the coverage fact",
                                    "glossary.md states the disjoint typed axes"),
        (s/"files/handoff_manifest.json", "glossary.md + public_check_summary.json state the disjoint typed axes and the coverage fact",
                                          "glossary.md states the disjoint typed axes"),
        (s/"files/evidence_manifest.json", "see glossary.md + public_check_summary.json", "see glossary.md"),
    ]:
        txt = f.read_text()
        if old not in txt: raise FailClosed(f"ref not found in {f.name}: {old[:40]}")
        f.write_text(txt.replace(old, new, 1))
    _patch_meta(s, "workflow_handoff_0017", "BundleS-heldout = 0012 - public_check_summary - C6 (= 0011 + C1+C2+C4+C7)")

def _patch_meta(task, tid, note):
    mf = task/"metadata.json"; md = json.loads(mf.read_text())
    md["task_id"] = tid; md["phase4w_heldout"] = note
    for key in ("visible", "forbidden"):
        lst = md["files"].get(key, [])
        lst = [x for x in lst if x != "public_check_summary.json"]
        md["files"][key] = lst
    mf.write_text(json.dumps(md, indent=2, ensure_ascii=False) + "\n")

def assert_components(out):
    """Fail-closed component presence/absence + disclosure pre-checks for 0017."""
    S = out/"workflow_handoff_0017/files"
    spec = (S/"spec.md").read_text()
    # C6 excluded
    if "setup signoff is taken at" in spec: raise FailClosed("C6 assertion present in 0017")
    # C4 present and BYTE-IDENTICAL to the development BundleS glossary (no held-out-specific wording)
    assert (S/"glossary.md").exists(), "0017 missing glossary"
    if sha_file(S/"glossary.md") != sha_file(TRACK/"workflow_handoff_0015/files/glossary.md"):
        raise FailClosed("0017 glossary differs from dev BundleS glossary (must be byte-identical)")
    # C3/C5 excluded
    assert not (S/"public_check_summary.json").exists(), "0017 must NOT have public_check_summary"
    # C1 canonical shipped labels (no op_point in shipped report_A)
    if "op_point=" in (S/"report_A_role_swap.rpt").read_text(): raise FailClosed("0017 must use canonical shipped labels")
    # directive-style golden-pair statement must be absent from directive files (formal audit is separate)
    for fname in ("spec.md", "glossary.md"):
        txt = (S/fname).read_text()
        for pat in ("typ scenario", "test corner", "typ/test", "(typ, test)"):
            if pat in txt: raise FailClosed(f"golden-pair phrase '{pat}' present in 0017 {fname}")
    ptxt = (out/"workflow_handoff_0017/prompt.md").read_text()
    for pat in ("typ scenario", "test corner", "typ/test", "(typ, test)"):
        if pat in ptxt: raise FailClosed(f"golden-pair phrase '{pat}' present in 0017 prompt.md")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(TRACK)); a = ap.parse_args()
    out = Path(a.out)
    head = subprocess.run(["git","-C",str(REPO),"rev-parse","HEAD"],capture_output=True,text=True).stdout.strip()
    if head != EXPECTED_COMMIT: raise FailClosed(f"HEAD {head} != {EXPECTED_COMMIT}")
    for tag,p in SRC_HASHES.items():
        h = sha_file(TRACK/f"workflow_handoff_{tag.split('/')[0]}/files/flow_config.json")
        if h != p: raise FailClosed(f"source hash mismatch {tag}")
    make_heldout(out)
    assert_components(out)
    print(json.dumps({"ok": True, "variant": "workflow_handoff_0017 (BundleS-heldout = 0011 + C1+C2+C4+C7)",
                      "source_commit": EXPECTED_COMMIT}, indent=2))

if __name__ == "__main__":
    try: main()
    except FailClosed as e: print("FAIL-CLOSED:", e, file=sys.stderr); sys.exit(1)
