#!/usr/bin/env python3
"""Phase-7A Study A — generate + bake + gate the 12 prospective STA instances.

Mirrors scripts/phase5b_generate_eval_sets.gen_family for Family A only, over the
FROZEN 12-spec table (scripts/phase7a_sta12_specs.py). No model calls. Real
PrimeTime bake (via the transparent b04 shim) for golden/wrong-binding
feasibility + output-channel evidence. Emits the full Phase-5B audit suite per
instance + a construction/gate report. The 72 model episodes are NOT executed
here (gated on review of this report).

Reuses the frozen generator (p15_sta_handoff_gen) and audit module (phase5_audits)
unchanged. Conditions: Base, BundleS, TypedContract (frozen treatment mapping).
"""
from __future__ import annotations
import json, os, sys, shutil, hashlib
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "generators"))
sys.path.insert(0, str(REPO / "scripts"))
import p15_sta_handoff_gen as GA
import phase5_audits as AUD
import phase7a_sta12_specs as SPECS

CONDITIONS = ["Base", "BundleS", "TypedContract"]

ENV = dict(os.environ)
ENV["EDA_TOOL_ROOT"] = "/data1/tongsb/eda-remote-shim/EDA"; ENV["B04_HOST"] = "tsb@b04"
ENV["EDA_PT_CMD"] = "/data1/tongsb/eda-remote-shim/EDA/soft2/synopsys/prime/V-2023.12/bin/pt_shell"


def _typed_space():
    return [(i, p, v) for i in GA.INTENTS for p in ["cdc", "reset", "scan", "core"] for v in GA.CHECK_MODES]


def _plausible(res):
    return bool(res.get("signoff_green"))


def _read_disclosure(task_dir, condition):
    out = {}
    for name in ("disclosure_bundles.md", "typed_contract.json"):
        p = task_dir / "files" / name
        if p.is_file():
            out[name] = p.read_text()
    return out


def _custody(root):
    """sha256 custody over every file under root (deterministic)."""
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            h.update(p.relative_to(root).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def generate():
    out_root = REPO / "tasks" / GA.TRACK
    instances = []
    for tid, golden, wrong, decoy, axis in SPECS.STA12_SPECS:
        cond_trees = {}
        truth = None
        for cond in CONDITIONS:
            tdir = out_root / f"{tid}_{cond.lower()}"
            if tdir.exists():
                shutil.rmtree(tdir)
            truth = GA.build_task_skeleton(tdir, tid, 700 + int(tid.split("_")[-1]), golden, wrong, cond, decoy)
            cond_trees[cond] = tdir
        bake_dir = cond_trees["BundleS"]
        res = GA.bake_golden(bake_dir, ENV)
        gate = GA.hard_feasibility(res)
        for cond, tdir in cond_trees.items():
            (tdir / "hidden" / "bake_results.json").write_text(json.dumps({"results": res, "hard_feasibility": gate}, indent=2) + "\n")
        truth_for_sig = json.loads((bake_dir / "hidden" / "signoff_intent_truth.json").read_text())
        sig = {
            "truth": AUD.truth_signature(truth_for_sig),
            "authority": AUD.authority_signature(truth_for_sig),
            "decoy": AUD.decoy_signature(truth_for_sig),
            "wrong_green": AUD.wrong_green_signature(res),
            "visible_tool_output_golden": AUD.visible_tool_output_signature(str(res["golden"].get("signoff_line", ""))),
            "visible_tool_output_wrong": AUD.visible_tool_output_signature(str(res["wrong"].get("signoff_line", ""))),
        }
        vis = {f"golden_{golden}": _plausible(res["golden"]), f"wrong_{wrong}": _plausible(res["wrong"])}
        oc = AUD.output_channel_audit(vis, _typed_space())
        sd = {cond: AUD.semantic_diff_audit(truth_for_sig, {"bundle_discloses_golden": False}) for cond in CONDITIONS}
        ie = AUD.info_equiv_audit(_read_disclosure(cond_trees["BundleS"], "BundleS"),
                                  _read_disclosure(cond_trees["TypedContract"], "TypedContract"),
                                  truth_for_sig.get("typed_axes", {}))
        custodies = {cond: _custody(cond_trees[cond]) for cond in CONDITIONS}
        report = {"task_id": tid, "track": GA.TRACK, "golden": list(golden), "wrong": list(wrong),
                  "decoy_recipe": decoy, "conflict_axis": axis, "signatures": sig,
                  "hard_feasibility": gate, "output_channel_audit": oc, "semantic_diff_audit": sd,
                  "info_equiv_audit": ie, "custody_sha256": custodies,
                  "golden_signoff_green": res["golden"].get("signoff_green"),
                  "wrong_signoff_green": res["wrong"].get("signoff_green"),
                  "wrong_green_but_unattested": (res["wrong"]["markers"].get("green_but_unattested") or res["wrong"]["markers"].get("plausible_but_wrong"))}
        AUD.write_instance_audit_report(bake_dir / "hidden", report)
        instances.append(report)
    # diversity: distinct truth/authority/decoy/wrong-green signatures across the 12
    diversity_ok = {}
    for key in ("truth", "authority", "decoy", "wrong_green"):
        vals = [r["signatures"][key] for r in instances]
        diversity_ok[key] = (len(set(vals)) == len(vals))
    allpass = (all(r["hard_feasibility"].get("PASS") for r in instances)
               and all(r["output_channel_audit"]["PASS"] for r in instances)
               and all(s["PASS"] for r in instances for s in r["semantic_diff_audit"].values())
               and all(r["info_equiv_audit"]["PASS"] for r in instances)
               and all(diversity_ok.values()))
    return {"schema": "phase7a_sta12_construction/v1", "n_instances": len(instances),
            "conditions": CONDITIONS, "hard_gate_criteria": list(instances[0]["hard_feasibility"].keys() - {"PASS"}) if instances else [],
            "instances": instances, "signatures_distinct": diversity_ok,
            "all_instances_pass_hard_gate_and_audits": allpass,
            "note": "prospective confirmatory batch; pilot instances 0001-0003 excluded; 72 model episodes NOT executed"}


def main():
    report = generate()
    out = REPO / "reports" / "synthetic_phase7a_sta12_construction.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    md = REPO / "reports" / "synthetic_phase7a_sta12_construction.md"
    md.write_text("# Phase-7A Study A — 12-instance STA construction/gate report\n\n"
                  f"**All pass hard gate + audits:** {report['all_instances_pass_hard_gate_and_audits']}\n\n"
                  f"**Distinct signatures:** {report['signatures_distinct']}\n\n"
                  "| instance | golden | wrong | axis | hard_gate | output_channel | info_equiv | wrong_green_unattested |\n"
                  "|---|---|---|---|---|---|---|---|\n"
                  + "\n".join(f"| {r['task_id']} | {r['golden']} | {r['wrong']} | {r['conflict_axis']} | "
                              f"{r['hard_feasibility']['PASS']} | {r['output_channel_audit']['PASS']} | "
                              f"{r['info_equiv_audit']['PASS']} | {r['wrong_green_but_unattested']} |" for r in report["instances"]) + "\n")
    print(f"instances={report['n_instances']} all_pass={report['all_instances_pass_hard_gate_and_audits']} "
          f"distinct={report['signatures_distinct']}")
    print(f"report: {out}")
    sys.exit(0 if report["all_instances_pass_hard_gate_and_audits"] else 2)


if __name__ == "__main__":
    main()
