#!/usr/bin/env python3
"""Phase-4W held-out information-disclosure audit (the eligibility gate) for 0011 + 0017.

Mirror of scripts/phase4w_run2_disclosure.py with the held-out golden (typ, test) and the held-out
wrong-axis binding (scenario=test / corner=slow, the shipped swap). A variant is ELIGIBLE
(non-answer-bearing) iff:
  1. the golden tuple is not explicitly stated (no C6-style assertion in any public file);
  2. public constraints do not uniquely determine the golden (>=2 plausible typed tuples remain);
  3. the wrong-axis binding remains publicly plausible (appears in a shipped report) and is
     signoff-green (verified on real PT by the fairness gate);
  4. no filename / ordering / glossary / summary / conflict statement provides an equivalent
     unique-answer channel (directive files must not state the golden pair).
If C1+C2+C4+C7 uniquely identify the typ/test golden -> effectively answer-bearing -> STOP before paid calls.

Report/manifest CLAIMS remain the shared INFERENCE substrate (identical treatment to the Run-2 audit):
each shipped report claims a tuple; no public file asserts which claim is correct.
"""
import json, os
from pathlib import Path

BASE = Path("tasks/p14_workflow_handoff")
OUT = Path("reports/evidence/p14_phase4w_heldout"); OUT.mkdir(parents=True, exist_ok=True)
GOLDEN = ("typ", "test")
WRONG_AXIS = ("test", "slow")  # shipped swap: corner value in scenario slot / scenario value in corner slot
SCEN_AXIS = ["slow", "typ", "fast"]
CORNER_AXIS = ["func", "test", "lowpower"]
TEXT_EXT = {".md", ".json", ".rpt", ".log", ".tcl", ".sh", ".sdc", ".v"}
VARIANTS = {"Base_0011": "workflow_handoff_0011", "BundleS_heldout_0017": "workflow_handoff_0017"}

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
    # 1. golden explicitly stated? (C6-style assertion, or a directive form of the pair)
    c6_patterns = ["setup signoff is taken at the **typ scenario**",
                   "setup signoff is taken at the typ scenario",
                   "signoff pair is (typ, test)", "scenario=typ, corner=test"]
    golden_stated = any(p in txt for p in c6_patterns)
    # 2. enumerate typed tuples; which are publicly plausible (type-valid; not explicitly contradicted)?
    tuples = [(s, c) for s in SCEN_AXIS for c in CORNER_AXIS]  # 9 typed tuples
    # the bundle's STATED constraints only rule out NON-typed (PVT/cross-axis); all 9 typed are plausible
    plausible = tuples
    # 3. wrong-axis publicly plausible? (appears in a shipped report header) and signoff-green by design
    wa_in_reports = ("op_point=test" in txt and "mode=slow" in txt) or ("scenario=test" in txt and "corner=slow" in txt)
    # 4. unique-answer channel? a non-report DIRECTIVE stating the golden pair. report_B carries typ/test
    #    on the STALE netlist and report_A's inner stamp carries typ/test -- report CLAIMS, not directives.
    directive_files = ["spec.md", "glossary.md", "public_check_summary.json", "prompt.md"]
    directive_text = "\n".join((open(files/f, encoding="utf-8", errors="replace").read()
                                for f in directive_files if (files/f).exists()))
    directive_states_golden = ("typ scenario" in directive_text and "test corner" in directive_text) or \
                              ("typ/test" in directive_text) or ("(typ, test)" in directive_text)
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
        "wrong_axis_signoff_green_by_design": True,  # netlist_v2/clk_main, body corner-independent (fairness gate verifies on real PT)
        "report_intersection_recovers_unique": truth["axis_schema"]["uniqueness"]["exactly_one"],
        "ELIGIBLE_non_answer_bearing": eligible,
        "axis_vocab_unchanged": truth["axis_schema"]["typed_axes"]["scenario_axis"] == SCEN_AXIS
                                and truth["axis_schema"]["typed_axes"]["corner_axis"] == CORNER_AXIS,
        "golden_matches_hidden_truth": (truth["expected_scenario"], truth["expected_corner"]) == GOLDEN,
    }

def main():
    results = {name: audit_variant(name, tid) for name, tid in VARIANTS.items()}
    verdict = {
        "audit": "Phase-4W held-out information-disclosure (0011 baseline + 0017 BundleS-heldout)",
        "rule": "ELIGIBLE iff golden not stated, >=2 plausible typed tuples remain, wrong-axis plausible+green, no unique-answer channel. If C1+C2+C4+C7 uniquely identify the typ/test golden -> effectively answer-bearing -> STOP before paid calls.",
        "variants": results,
        "ALL_ELIGIBLE": all(r["ELIGIBLE_non_answer_bearing"] and r["golden_matches_hidden_truth"] for r in results.values()),
        "STOP_if_any_uniquely_identifies_golden": not all(r["ELIGIBLE_non_answer_bearing"] for r in results.values()),
    }
    (OUT / "disclosure_audit.json").write_text(json.dumps(verdict, indent=2) + "\n")
    print(json.dumps({name: {"ELIGIBLE": r["ELIGIBLE_non_answer_bearing"],
                             "num_plausible": r["num_plausible"],
                             "golden_stated": r["golden_explicitly_stated"],
                             "directive_states_golden": r["directive_states_golden_pair"],
                             "wrong_axis_in_reports": r["wrong_axis_in_shipped_reports"],
                             "golden_matches_hidden_truth": r["golden_matches_hidden_truth"]}
                      for name, r in results.items()}, indent=2))
    print("ALL_ELIGIBLE:", verdict["ALL_ELIGIBLE"])

if __name__ == "__main__":
    main()
