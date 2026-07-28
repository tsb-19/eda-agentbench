#!/usr/bin/env python3
"""Phase-4Y Stage-3 disclosure audit for C2-only (0022) + C4-only (0023)."""
import json, os
from pathlib import Path
BASE = Path("tasks/p14_workflow_handoff"); OUT = Path("reports/evidence/p14_phase4y3"); OUT.mkdir(parents=True, exist_ok=True)
GOLDEN, WRONG_AXIS = ("slow", "func"), ("func", "typ")
TEXT_EXT = {".md", ".json", ".rpt", ".log", ".tcl", ".sh", ".sdc", ".v"}
VARIANTS = {"C2_0022": "workflow_handoff_0022", "C4_0023": "workflow_handoff_0023"}


def public_text(d):
    return "\n".join(open(d / f, encoding="utf-8", errors="replace").read()
                     for f in sorted(os.listdir(d)) if (d / f).is_file() and os.path.splitext(f)[1] in TEXT_EXT)


def audit(name, tid):
    files = BASE / tid / "files"; txt = public_text(files)
    truth = json.load(open(BASE / tid / "hidden/handoff_truth.json"))
    golden_stated = any(p in txt for p in ["setup signoff is taken at the **slow scenario**", "signoff pair is (slow, func)", "scenario=slow, corner=func"])
    wa = ("op_point=func" in txt and "mode=typ" in txt) or ("scenario=func" in txt and "corner=typ" in txt)
    directive = "\n".join(open(files / f, encoding="utf-8", errors="replace").read() for f in ["spec.md", "glossary.md", "prompt.md"] if (files / f).exists())
    directive_golden = (("slow scenario" in directive and "functional corner" in directive) or "slow/func" in directive or "(slow, func)" in directive)
    return {"variant": name, "ELIGIBLE_non_answer_bearing": (not golden_stated) and (not directive_golden) and wa,
            "golden_explicitly_stated": golden_stated, "directive_states_golden_pair": directive_golden,
            "num_plausible": 9, "wrong_axis_in_reports": wa,
            "golden_matches_hidden_truth": (truth["expected_scenario"], truth["expected_corner"]) == GOLDEN}


def main():
    res = {n: audit(n, t) for n, t in VARIANTS.items()}
    verdict = {"audit": "Phase-4Y Stage-3 disclosure", "variants": res,
               "ALL_ELIGIBLE": all(r["ELIGIBLE_non_answer_bearing"] and r["golden_matches_hidden_truth"] for r in res.values())}
    (OUT / "disclosure_audit.json").write_text(json.dumps(verdict, indent=2) + "\n")
    print(json.dumps({n: {k: r[k] for k in ("ELIGIBLE_non_answer_bearing", "golden_matches_hidden_truth")} for n, r in res.items()}, indent=2))
    print("ALL_ELIGIBLE:", verdict["ALL_ELIGIBLE"])


if __name__ == "__main__":
    main()
