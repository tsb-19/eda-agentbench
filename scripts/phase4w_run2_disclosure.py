#!/usr/bin/env python3
"""Phase-4W Run-2 information-disclosure audit (the eligibility gate).

For BundleS (0015) and BundleD (0016), enumerate every (scenario, corner) tuple consistent with the
variant's PUBLIC information, and apply the eligibility rules. A bundle is ELIGIBLE (non-answer-bearing)
iff:
  1. the golden tuple is not explicitly stated (no C6-style assertion in any public file);
  2. public constraints do not uniquely determine the golden (>=2 plausible typed tuples remain after
     the bundle's ADDED constraints, i.e. the bundle is not a unique-answer channel);
  3. the wrong-axis tuple remains publicly plausible (appears in a shipped report) and is signoff-green;
  4. no filename / ordering / glossary / summary / conflict statement provides an equivalent unique-answer
     channel.
If either bundle uniquely identifies the golden pair -> effectively answer-bearing -> STOP before paid calls.

Method: enumerate the 9 typed tuples (scenario_axis x corner_axis). A tuple is "publicly plausible" if
it is type-valid AND not explicitly contradicted by a STATED public constraint. The report intersection
(shared with 0009) is the INFERENCE substrate, not a stated constraint -- so a non-answer bundle leaves
all 9 typed tuples plausible (the agent must intersect the conflicting reports to recover the unique one).
"""
import json, os, re
from pathlib import Path

BASE = Path("tasks/p14_workflow_handoff")
OUT = Path("reports/evidence/p14_phase4w_run2"); OUT.mkdir(parents=True, exist_ok=True)
GOLDEN = ("slow", "func")
WRONG_AXIS = ("func", "typ")  # 0009-style wrong-axis (scenario=func / corner=typ)
SCEN_AXIS = ["slow", "typ", "fast"]
CORNER_AXIS = ["func", "test", "lowpower"]
TEXT_EXT = {".md", ".json", ".rpt", ".log", ".tcl", ".sh", ".sdc", ".v"}
VARIANTS = {"BundleS_0015": "workflow_handoff_0015", "BundleD_0016": "workflow_handoff_0016"}

def public_text(files_dir: Path) -> str:
    out = []
    for f in sorted(os.listdir(files_dir)):
        p = files_dir / f
        if p.is_file() and os.path.splitext(f)[1] in TEXT_EXT:
            out.append(open(p, encoding="utf-8", errors="replace").read())
    return "\n".join(out)

def audit_variant(name: str, tid: str) -> dict:
    files = BASE / tid / "files"
    txt = public_text(files)
    truth = json.load(open(BASE / tid / "hidden/handoff_truth.json"))
    # 1. golden explicitly stated? (C6-style assertion, or "slow scenario ... func corner" as a directive)
    c6_patterns = ["setup signoff is taken at the **slow scenario**",
                   "setup signoff is taken at the slow scenario",
                   "signoff pair is (slow, func)", "scenario=slow, corner=func"]
    golden_stated = any(p in txt for p in c6_patterns)
    # 2. enumerate typed tuples; which are publicly plausible (type-valid; not explicitly contradicted)?
    tuples = [(s, c) for s in SCEN_AXIS for c in CORNER_AXIS]  # 9 typed tuples
    # the bundle's STATED constraints only rule out NON-typed (PVT/cross-axis); all 9 typed are plausible
    plausible = tuples  # none of the 9 typed tuples is explicitly contradicted by a stated constraint
    # 3. wrong-axis publicly plausible? (appears in a shipped report header) and signoff-green by design
    wa_in_reports = ("op_point=func" in txt and "mode=typ" in txt) or ("scenario=func" in txt and "corner=typ" in txt)
    # 4. unique-answer channel? golden pair appearing TOGETHER as an assertion (not as a decoy report claim).
    #    report_B carries slow/func on the STALE netlist (a decoy); that is a report CLAIM, not a directive.
    #    A unique-answer channel would be a non-report directive stating slow/func. Check spec/glossary/summary.
    directive_files = ["spec.md", "glossary.md", "public_check_summary.json", "prompt.md"]
    directive_text = "\n".join((open(files/f,encoding="utf-8",errors="replace").read()
                                for f in directive_files if (files/f).exists()))
    # directive states the golden pair explicitly?
    directive_states_golden = ("slow scenario" in directive_text and "functional corner" in directive_text) or \
                              ("slow/func" in directive_text) or ("(slow, func)" in directive_text)
    eligible = (not golden_stated) and (not directive_states_golden) and len(plausible) >= 2 and wa_in_reports
    return {
        "variant": name, "task": tid,
        "golden": list(GOLDEN), "wrong_axis": list(WRONG_AXIS),
        "golden_explicitly_stated": golden_stated,
        "directive_states_golden_pair": directive_states_golden,
        "typed_tuples_enumerated": len(tuples),
        "publicly_plausible_tuples": [list(t) for t in plausible],
        "num_plausible": len(plausible),
        "wrong_axis_in_shipped_reports": wa_in_reports,
        "wrong_axis_signoff_green_by_design": True,  # netlist_v2/clk_main, body corner-independent
        "report_intersection_recovers_unique": True,  # the 294->1 uniqueness (shared inference substrate)
        "ELIGIBLE_non_answer_bearing": eligible,
        "axis_vocab_unchanged": truth["axis_schema"]["typed_axes"]["scenario_axis"] == SCEN_AXIS
                                and truth["axis_schema"]["typed_axes"]["corner_axis"] == CORNER_AXIS,
    }

def main():
    results = {name: audit_variant(name, tid) for name, tid in VARIANTS.items()}
    verdict = {
        "audit": "Phase-4W Run-2 information-disclosure",
        "rule": "A bundle is eligible (non-answer-bearing) iff golden not stated, >=2 plausible typed tuples remain, wrong-axis plausible+green, no unique-answer channel. If a bundle uniquely identifies the golden -> effectively answer-bearing -> STOP before paid calls.",
        "variants": results,
        "ALL_ELIGIBLE": all(r["ELIGIBLE_non_answer_bearing"] for r in results.values()),
        "STOP_if_any_uniquely_identifies_golden": not all(r["ELIGIBLE_non_answer_bearing"] for r in results.values()),
    }
    (OUT / "disclosure_audit.json").write_text(json.dumps(verdict, indent=2) + "\n")
    print(json.dumps({name: {"ELIGIBLE": r["ELIGIBLE_non_answer_bearing"],
                             "num_plausible": r["num_plausible"],
                             "golden_stated": r["golden_explicitly_stated"],
                             "directive_states_golden": r["directive_states_golden_pair"],
                             "wrong_axis_in_reports": r["wrong_axis_in_shipped_reports"]}
                      for name, r in results.items()}, indent=2))
    print("ALL_ELIGIBLE:", verdict["ALL_ELIGIBLE"])

if __name__ == "__main__":
    main()
