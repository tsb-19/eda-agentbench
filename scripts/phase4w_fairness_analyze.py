#!/usr/bin/env python3
"""Phase-4W fairness gate: merge 0011 re-run + run hard-gate analysis.

Merges /tmp/rerun0011.json into gate_results.json (replacing 0011's transient-failure vectors),
then applies the hard gates:
  #1 source equivalence: 0013 vector == 0010 ; 0014 vector == 0009 (all components + total).
  #2 held-out: 0011/0012 golden==1.0; wrong-axis typed-binding-rejected & signoff-green;
     stale/unchanged-mutant low; signoff pattern preserved vs source.
Emits reports/evidence/p14_phase4w_fairness/fairness_verdict.json + .md.
"""
import json
from pathlib import Path

OUT = Path("reports/evidence/p14_phase4w_fairness")
GR = json.loads((OUT / "gate_results.json").read_text())
RERUN = json.loads(Path("/tmp/rerun0011.json").read_text())

# --- merge 0011 re-run (format components) ---
for cand, r in RERUN.items():
    comps = [{"name": n, "raw": v, "weight": None} for n, v in r["comps"].items()]
    GR["workflow_handoff_0011"]["candidates"][cand] = {
        "ok": True, "total_score": r["total"], "passed": r["passed"], "objective_score": None,
        "components": comps, "anti_cheat": None, "error": None, "reliability": {},
        "submitted": r["submitted"], "candidate": cand,
        "note": "re-run; original run hit a transient empty-PT-body (digest 01ba4719=sha256('\\n')) on b04"}
(OUT / "gate_results.json").write_text(json.dumps(GR, indent=2) + "\n")

def vec(tid, cand):
    c = GR[f"workflow_handoff_{tid}"]["candidates"][cand]
    comps = {x["name"]: round(x["raw"], 3) for x in c.get("components", [])}
    return {"total": c.get("total_score"), **comps}

CANDS = ["golden", "wrong_axis", "stale_decoy", "unchanged_mutant"]

# --- hard gate #1: source equivalence ---
equiv = {}
for new, src in [("0013", "0010"), ("0014", "0009")]:
    rows = {}
    ok = True
    for cand in CANDS:
        v_new, v_src = vec(new, cand), vec(src, cand)
        match = (v_new == v_src)
        ok &= match
        rows[cand] = {"match": match, "new": v_new, "src": v_src}
    equiv[f"{new}_vs_{src}"] = {"all_match": ok, "per_candidate": rows}

# --- hard gate #2: held-out relational equivalence ---
heldout = {}
for tid in ("0011", "0012"):
    g = vec(tid, "golden"); wa = vec(tid, "wrong_axis")
    heldout[tid] = {
        "golden_total_1.0": g["total"] == 1.0,
        "golden_all_components_1.0": all(v == 1.0 for k, v in g.items() if k != "total") ,
        "wrong_axis_signoff_green": wa.get("signoff") == 1.0,
        "wrong_axis_evidence_rejected": wa.get("evidence_generation") == 0.0,
        "wrong_axis_total_0.2": wa["total"] == 0.2,
        "stale_decoy_low": vec(tid, "stale_decoy")["total"] <= 0.2,
        "unchanged_mutant_low": vec(tid, "unchanged_mutant")["total"] <= 0.2,
    }
# plausibility: wrong-axis signoff-green in source AND held-out (preserved)
plaus = {
    "wrong_axis_signoff_green_all_tasks": all(vec(t, "wrong_axis").get("signoff") == 1.0
                                              for t in ("0009", "0010", "0011", "0012", "0013", "0014")),
    "stale_decoy_signoff_red_source_and_heldout": all(vec(t, "stale_decoy").get("signoff") == 0.0
                                                       for t in ("0009", "0010", "0011", "0012")),
    "stale_decoy_note": "stale-decoy is a netlist-family rejection (netlist_v1 under pinned clk_main has no clk_main -> PT red); red in source AND held-out alike (faithful preservation). signoff-green-while-rejected holds for wrong-axis (the role-binding decoy relevant to C6).",
}
# overall verdict
equiv_ok = all(equiv[k]["all_match"] for k in equiv)
held_ok = all(all(v.values()) for v in heldout.values())
plaus_ok = plaus["wrong_axis_signoff_green_all_tasks"]
verdict = {
    "commit": "97fe789 (held-out frozen) + per-candidate evidence regen",
    "gate1_source_equivalence_PASS": equiv_ok,
    "gate2_heldout_relational_PASS": held_ok,
    "plausibility_PASS": plaus_ok,
    "ALL_HARD_GATES_PASS": equiv_ok and held_ok and plaus_ok,
    "transient_note": "0011 golden original run: transient empty-PT-body on b04 (digest 01ba4719=sha256 newline); re-run = 1.0. Merged into gate_results.json.",
    "source_equivalence": equiv,
    "heldout_relational": heldout,
    "plausibility": plaus,
}
(OUT / "fairness_verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")

# markdown table
md = ["# Phase-4W fairness gate verdict", "",
      f"- Gate #1 source equivalence (0013==0010, 0014==0009, full vectors): **{'PASS' if equiv_ok else 'FAIL'}**",
      f"- Gate #2 held-out relational (golden=1.0; wrong-axis typed-rejected+signoff-green; stale/mutant low): **{'PASS' if held_ok else 'FAIL'}**",
      f"- Plausibility (wrong-axis signoff-green all tasks): **{'PASS' if plaus_ok else 'FAIL'}**",
      f"- **ALL HARD GATES: {'PASS' if verdict['ALL_HARD_GATES_PASS'] else 'FAIL'}**", "",
      "## candidate vectors (total | signoff/evidence_gen/explanation)", "",
      "| task | golden | wrong_axis | stale_decoy | unchanged_mutant |", "|---|---|---|---|---|"]
for tid in ("0009", "0010", "0011", "0012", "0013", "0014"):
    cells = []
    for cand in CANDS:
        v = vec(tid, cand)
        cells.append(f"{v['total']} | {v.get('signoff')}/{v.get('evidence_generation')}/{v.get('explanation')}")
    md.append(f"| {tid} | " + " | ".join(cells) + " |")
md += ["", "## source-equivalence detail",
       f"- 0013 vs 0010 all candidates match: `{equiv['0013_vs_0010']['all_match']}`",
       f"- 0014 vs 0009 all candidates match: `{equiv['0014_vs_0009']['all_match']}`",
       "", "## held-out", json.dumps(heldout, indent=2), "", "## plausibility", json.dumps(plaus, indent=2)]
(OUT / "fairness_verdict.md").write_text("\n".join(str(x) for x in md) + "\n")
print(json.dumps({"ALL_HARD_GATES_PASS": verdict["ALL_HARD_GATES_PASS"],
                  "gate1": equiv_ok, "gate2": held_ok, "plausibility": plaus_ok}, indent=2))
