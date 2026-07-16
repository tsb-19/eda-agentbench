#!/usr/bin/env python3
"""Phase-4W axis-domain + lexical audit for the held-out pair (gate #3).

Scans the VISIBLE files of 0011/0012 and emits:
  * legal/public scenario + corner values (from the axis vocabulary, unchanged);
  * every public occurrence of typ/test/slow/func (file, line, context);
  * how typ/test is established as the held-out golden (C5 constraint / intersection;
    C6 analogue in 0012 only);
  * whether the test/slow wrong-axis candidate is syntactically valid (axis members);
  * whether 0011 unintentionally discloses typ/test (filename / enumeration order /
    summary / report order / direct assertion).

Output: reports/evidence/p14_phase4w_fairness/axis_domain_audit.json (+ .md)
"""
import json, re, os
from pathlib import Path

BASE = Path("tasks/p14_workflow_handoff")
TOKENS = ["typ", "test", "slow", "func"]
TEXT_EXT = {".md", ".json", ".rpt", ".log", ".tcl", ".sh", ".sdc", ".v"}

def text_files(d):
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f)
        if os.path.isfile(p) and os.path.splitext(f)[1] in TEXT_EXT:
            yield f, p

def scan_occurrences(tid):
    d = BASE / f"workflow_handoff_{tid}" / "files"
    occ = {t: [] for t in TOKENS}
    for fn, p in text_files(d):
        for i, line in enumerate(open(p, encoding="utf-8", errors="replace").read().splitlines(), 1):
            for t in TOKENS:
                # word-boundary match (typ not inside 'typ_1.0V' counts as typ prefix; track separately)
                for m in re.finditer(r"\b" + re.escape(t) + r"\b", line):
                    occ[t].append({"file": fn, "line": i, "ctx": line.strip()[:90]})
    return occ

def main():
    OUT = Path("reports/evidence/p14_phase4w_fairness"); OUT.mkdir(parents=True, exist_ok=True)
    # axis vocabulary (from truth, unchanged by construction; verify here)
    vocab = {}
    for tid in ("0011", "0012"):
        tr = json.load(open(BASE / f"workflow_handoff_{tid}" / "hidden/handoff_truth.json"))
        vocab[tid] = {
            "scenario_axis": tr["axis_schema"]["typed_axes"]["scenario_axis"],
            "corner_axis": tr["axis_schema"]["typed_axes"]["corner_axis"],
            "C5_allowed": tr["axis_schema"]["constraints"][4]["allowed"],
            "golden": [tr["expected_scenario"], tr["expected_corner"]],
            "stale_mutant": [tr["stale_scenario"], tr["stale_corner"]],
        }
    occ = {tid: scan_occurrences(tid) for tid in ("0011", "0012")}
    # wrong-axis candidate validity: test in scenario slot? slow in corner slot? (test/slow are the swap)
    # test is a CORNER member; placed in scenario slot -> type error (intended wrong-axis). syntactically a string.
    wa = vocab["0011"]
    syntactic = {
        "test_is_corner_member": "test" in wa["corner_axis"],
        "slow_is_scenario_member": "slow" in wa["scenario_axis"],
        "wrong_axis_scenario_slot_test_is_type_error": "test" not in wa["scenario_axis"],
        "wrong_axis_corner_slot_slow_is_type_error": "slow" not in wa["corner_axis"],
        "note": "test/slow wrong-axis is syntactically a valid string submission; PT-executable (signoff green on v2/clk_main because the body is corner-independent); rejected by typed-binding.",
    }
    # 0011 disclosure channels
    f0011 = BASE / "workflow_handoff_0011/files"
    disclosure = {
        "filename_discloses_typ_test": any("typ" in fn or "test" in fn for fn, _ in text_files(f0011)),
        "ships_glossary": os.path.exists(f0011 / "glossary.md"),
        "ships_public_check_summary": os.path.exists(f0011 / "public_check_summary.json"),
        "c6_assertion_present": any("setup signoff is taken at" in open(p, encoding="utf-8", errors="replace").read()
                                    for _, p in text_files(f0011)),
        "verdict_0011_no_new_disclosure_channel_vs_0009":
            os.path.exists(f0011 / "glossary.md") is False
            and os.path.exists(f0011 / "public_check_summary.json") is False,
    }
    audit = {
        "legal_public_scenario_values": vocab["0011"]["scenario_axis"],
        "legal_public_corner_values": vocab["0011"]["corner_axis"],
        "heldout_golden_0011": vocab["0011"]["golden"],
        "heldout_golden_0012": vocab["0012"]["golden"],
        "heldout_mutant_swap": vocab["0011"]["stale_mutant"],
        "how_typ_established_as_scenario": "C5 constraint allows only [[typ,test]]; typ is a scenario_axis member in the scenario slot of the unique satisfying assignment. In 0012 the C6 analogue asserts it directly (answer-bearing); in 0011 it is inferred from the report intersection (not directly asserted).",
        "how_test_established_as_corner": "test is a corner_axis member in the corner slot of the unique satisfying assignment; C5 [[typ,test]].",
        "wrong_axis_candidate_test_slow": syntactic,
        "disclosure_audit_0011": disclosure,
        "public_occurrences_0011": {t: len(occ["0011"][t]) for t in TOKENS},
        "public_occurrences_0012": {t: len(occ["0012"][t]) for t in TOKENS},
        "occurrences_detail_0011": occ["0011"],
        "occurrences_detail_0012": occ["0012"],
    }
    (OUT / "axis_domain_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    # markdown summary
    md = ["# Phase-4W axis-domain + lexical audit (gate #3)", "",
          f"Legal public scenario values: `{audit['legal_public_scenario_values']}`",
          f"Legal public corner values: `{audit['legal_public_corner_values']}`",
          f"Held-out golden (0011 & 0012): scenario=`typ`, corner=`test`",
          f"Held-out mutant swap: `{audit['heldout_mutant_swap']}` (test in scenario slot [corner value -> type error], slow in corner slot [scenario value -> type error])", "",
          "## wrong-axis candidate `test/slow`",
          f"- test is a corner member (`{syntactic['test_is_corner_member']}`); in the scenario slot it is a type error (`{syntactic['wrong_axis_scenario_slot_test_is_type_error']}`).",
          f"- slow is a scenario member (`{syntactic['slow_is_scenario_member']}`); in the corner slot it is a type error (`{syntactic['wrong_axis_corner_slot_slow_is_type_error']}`).",
          "- Syntactically a valid string; PT-executable (signoff green on v2/clk_main; body corner-independent); rejected by typed-binding/evidence.", "",
          "## 0011 disclosure audit",
          f"- filename discloses typ/test: `{disclosure['filename_discloses_typ_test']}`",
          f"- ships glossary: `{disclosure['ships_glossary']}` | ships public_check_summary: `{disclosure['ships_public_check_summary']}` | C6 assertion: `{disclosure['c6_assertion_present']}`",
          f"- no NEW disclosure channel vs 0009: `{disclosure['verdict_0011_no_new_disclosure_channel_vs_0009']}`", "",
          "## public token occurrence counts (visible files)",
          "| token | 0011 | 0012 |", "|---|---|---|"]
    for t in TOKENS:
        md.append(f"| `{t}` | {audit['public_occurrences_0011'][t]} | {audit['public_occurrences_0012'][t]} |")
    (OUT / "axis_domain_audit.md").write_text("\n".join(md) + "\n")
    print(json.dumps({"vocab_unchanged": vocab["0011"]["scenario_axis"] == ["slow","typ","fast"]
                      and vocab["0011"]["corner_axis"] == ["func","test","lowpower"],
                      "golden": audit["heldout_golden_0011"],
                      "wrong_axis_type_errors": syntactic["wrong_axis_scenario_slot_test_is_type_error"]
                        and syntactic["wrong_axis_corner_slot_slow_is_type_error"],
                      "0011_no_new_disclosure": disclosure["verdict_0011_no_new_disclosure_channel_vs_0009"],
                      "counts_0011": audit["public_occurrences_0011"],
                      "counts_0012": audit["public_occurrences_0012"]}, indent=2))

if __name__ == "__main__":
    main()
