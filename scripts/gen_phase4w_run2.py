#!/usr/bin/env python3
"""Phase-4W Run-2 variant generator: BundleS (0015) + BundleD (0016), both = 0009 + a NON-C6 subset.

BundleS (schema/contract) = 0010 - public_check_summary - C6  ==  0009 + {C1 labels+type-decls,
    C2 PVT-def, C4 glossary, C7 contract-wording}.  Derived from 0010 by removing public_check_summary.json,
    the C6 spec assertion, and dangling public_check_summary references (keeps glossary + canonical labels
    + PVT-def + clear-control wording).
BundleD (decoy-disambiguation) = 0009 + {C3 coverage-fact, C5 pairwise-conflict-info}.  Derived from 0009
    by adding ONLY public_check_summary.json (coverage + conflicts in op_point/mode terms; NO PVT concept,
    NO canonical labels, NO contract rewording, NO C6).

Fail-closed: assert source commit + source hashes; assert component presence/absence per bundle;
both exclude C6. 0009/0010 never modified. No manual post-edits.
"""
import argparse, hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TRACK = REPO / "tasks/p14_workflow_handoff"
EXPECTED_COMMIT = "74890d2cea5c7b36e59c8dc10db18083f6e09a89"

SRC_HASHES = {
    "0010/flow_config": "7d56dbefafc27215217e9ca9ffe20b26cd428b1fb2b9c2df1a9418dd5f9242e6",
    "0009/flow_config": "65d3682943022f6306a5ef1391d322a03695cb7c285c364b1aa50f983d75b203",
}
C6_LINE = "- The setup signoff is taken at the **slow scenario** in the **functional corner**."

class FailClosed(Exception): pass

def sha_file(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def make_bundles(out: Path):
    # ---- BundleS (0015) = 0010 - public_check_summary - C6 ----
    s = out / "workflow_handoff_0015"
    if s.exists(): shutil.rmtree(s)
    shutil.copytree(TRACK / "workflow_handoff_0010", s)
    # remove the summary file
    (s / "files/public_check_summary.json").unlink()
    # remove C6 assertion from spec.md
    spec = s / "files/spec.md"; t = spec.read_text()
    if C6_LINE not in t: raise FailClosed("C6 line not found in 0010 spec")
    t = t.replace(C6_LINE + "\n", "")
    # remove the public_check_summary bullet + clean step-1 / wording refs
    t = t.replace("- `public_check_summary.json` — pairwise inconsistency symptoms + the coverage fact (verdict-first; never the answer/schema).\n", "")
    t = t.replace("glossary.md + public_check_summary.json give the disjoint-axis rule and the coverage fact",
                  "glossary.md gives the disjoint-axis rule")
    spec.write_text(t)
    # prompt.md + flow_config + manifests: drop "+ public_check_summary.json" refs
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
        if old not in txt: raise FailClosed(f"BundleS ref not found in {f.name}: {old[:40]}")
        f.write_text(txt.replace(old, new, 1))
    _patch_meta(s, "workflow_handoff_0015", "BundleS = 0010 - public_check_summary - C6 (= 0009 + C1+C2+C4+C7)")

    # ---- BundleD (0016) = 0009 + public_check_summary (C3 coverage + C5 conflicts, op_point/mode) ----
    d = out / "workflow_handoff_0016"
    if d.exists(): shutil.rmtree(d)
    shutil.copytree(TRACK / "workflow_handoff_0009", d)
    summary = {
        "_comment": "Public pairwise consistency summary. Reports SYMPTOMS only; never the recovery target or the verdict.",
        "intended_clock_coverage": {"clk_main": 1, "clk_old": 0, "clk": 0},
        "pairwise_conflicts": [
            "report_A_role_swap.rpt op_point/mode disagree with report_B_role_stale.rpt",
            "report_C_role_pvt.rpt mode value disagrees with the other reports' mode values",
            "flow_config.json op_point/mode disagree with report_B_role_stale.rpt",
            "evidence_D_role_mismatch.json op_point/mode disagree internally",
        ],
        "note": "These are symptom-level pairwise conflicts; the globally-consistent assignment is NOT stated here.",
    }
    (d / "files/public_check_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    _patch_meta(d, "workflow_handoff_0016", "BundleD = 0009 + public_check_summary (C3 coverage + C5 conflicts; op_point/mode; no C6)")

def _patch_meta(task, tid, note):
    mf = task/"metadata.json"; md = json.loads(mf.read_text())
    md["task_id"] = tid; md["phase4w_run2"] = note
    # public_check_summary.json lives in files.visible + files.forbidden (not read_only)
    for key in ("visible", "forbidden"):
        lst = md["files"].get(key, [])
        if tid.endswith("016") and "public_check_summary.json" not in lst:
            lst.append("public_check_summary.json")
        if tid.endswith("015"):
            lst = [x for x in lst if x != "public_check_summary.json"]
        md["files"][key] = lst
    mf.write_text(json.dumps(md, indent=2, ensure_ascii=False) + "\n")

def assert_components(out):
    """Fail-closed component presence/absence checks."""
    S = out/"workflow_handoff_0015/files"; D = out/"workflow_handoff_0016/files"
    # both exclude C6
    for base in (S, D):
        spec = (base/"spec.md").read_text()
        if "setup signoff is taken at" in spec: raise FailClosed(f"C6 assertion present in {base}")
    # BundleS: glossary present, summary absent, canonical SHIPPED labels (no op_point in report_A shipped header)
    assert (S/"glossary.md").exists(), "BundleS missing glossary"
    assert not (S/"public_check_summary.json").exists(), "BundleS must NOT have summary"
    if "op_point=" in (S/"report_A_role_swap.rpt").read_text(): raise FailClosed("BundleS must use canonical shipped labels")
    # BundleD: summary present, glossary absent, op_point/mode SHIPPED labels (0009), no PVT/label leak in summary
    assert (D/"public_check_summary.json").exists(), "BundleD missing summary"
    assert not (D/"glossary.md").exists(), "BundleD must NOT have glossary"
    if "op_point=" not in (D/"report_A_role_swap.rpt").read_text(): raise FailClosed("BundleD must keep op_point/mode shipped labels")
    dsum = (D/"public_check_summary.json").read_text()
    if "PVT descriptor" in dsum or "scenario/corner" in dsum: raise FailClosed("BundleD summary leaks C1/C2")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(TRACK)); a = ap.parse_args()
    out = Path(a.out)
    head = subprocess.run(["git","-C",str(REPO),"rev-parse","HEAD"],capture_output=True,text=True).stdout.strip()
    if head != EXPECTED_COMMIT: raise FailClosed(f"HEAD {head} != {EXPECTED_COMMIT}")
    for tag,p in SRC_HASHES.items():
        h = sha_file(TRACK/f"workflow_handoff_{tag.split('/')[0]}/files/flow_config.json")
        if h != p: raise FailClosed(f"source hash mismatch {tag}")
    make_bundles(out)
    assert_components(out)
    print(json.dumps({"ok": True, "bundles": ["workflow_handoff_0015 (BundleS)", "workflow_handoff_0016 (BundleD)"],
                      "source_commit": EXPECTED_COMMIT}, indent=2))

if __name__ == "__main__":
    try: main()
    except FailClosed as e: print("FAIL-CLOSED:", e, file=sys.stderr); sys.exit(1)
