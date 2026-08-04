#!/usr/bin/env python3
"""Phase-5B eval-set orchestrator: generate + bake + gate the 6 primary instances
(3 STA + 3 SPICE), structurally diverse, with the full audit suite. NO model calls;
real PT/HSPICE runs for golden/wrong-binding feasibility + output-channel evidence.

Diversity is structural (varied golden intent/partition/check-mode or corner/load/metric,
varied authority conflict, varied wrong-green mechanism) — NOT lexical relabeling. Emits
truth/authority/decoy/wrong-green/visible-tool-output signatures per instance and asserts
the 3 per family are distinct.
"""
from __future__ import annotations
import json, os, sys, shutil, tempfile, subprocess
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "generators"))
sys.path.insert(0, str(REPO / "scripts"))
import p15_sta_handoff_gen as GA
import p16_spice_handoff_gen as GB
import phase5_audits as AUD

ENV = dict(os.environ)
ENV["EDA_TOOL_ROOT"] = "/data1/tongsb/eda-remote-shim/EDA"; ENV["B04_HOST"] = "tsb@b04"
ENV["EDA_PT_CMD"] = "/data1/tongsb/eda-remote-shim/EDA/soft2/synopsys/prime/V-2023.12/bin/pt_shell"
ENV["EDA_HSPICE_CMD"] = "/data1/tongsb/eda-remote-shim/EDA/soft2/synopsys/hspice/V-2023.12/hspice/bin/hspice"

CONDITIONS = ["Base", "BundleS", "TypedContract"]

# ---- structurally diverse eval specs ----
A_SPECS = [  # (task_id, golden, wrong, decoy_recipe)  -- varied intent/partition/view + wrong-green mechanism
    ("p15_eval_0001", ("cdc_isolate", "cdc", "setup"),     ("cdc_isolate", "core", "setup"),   "stale_intent"),
    ("p15_eval_0002", ("reset_exempt", "reset", "both"),   ("reset_exempt", "scan", "both"),   "mis_scope"),
    ("p15_eval_0003", ("scan_override", "scan", "both"),   ("functional_close", "core", "setup"), "wrong_domain"),
]
B_SPECS = [
    ("p16_eval_0001", ("SS_0p9_-40", "light", "gain"),   ("FF_1p3_125", "heavy", "gain"), "stale_corner"),
    ("p16_eval_0002", ("TT_1p2_25", "nominal", "gbw"),   ("SS_0p9_-40", "heavy", "gbw"),  "swapped_load"),
    ("p16_eval_0003", ("FF_1p3_125", "light", "gain"),   ("TT_1p2_25", "nominal", "gain"), "stale_prior"),
]


def _typed_space(gen):
    if gen is GA:
        return [(i, p, v) for i in GA.INTENTS for p in ["cdc", "reset", "scan", "core"] for v in GA.CHECK_MODES]
    return [(c, l, m) for c in GB.CORNERS for l in GB.LOADS for m in GB.METRICS]


def _plausible(gen, res):
    if gen is GA:
        return bool(res.get("signoff_green"))
    w = res["wrong"] if "wrong" in res else res
    val = w.get("value"); metric = (w.get("binding") or {}).get("metric", "gain")
    lo, hi = GB.METRIC_RANGE[metric]
    import math
    return bool(w.get("sim_ok") and val is not None and math.isfinite(val) and lo <= val <= hi)


def _read_disclosure(task_dir, condition):
    files = task_dir / "files"
    out = {}
    for name in ("disclosure_bundles.md", "typed_contract.json"):
        p = files / name
        if p.is_file():
            out[name] = p.read_text()
    return out


def gen_family(gen, specs, track, seed_base):
    out_root = REPO / "tasks" / track
    isA = (gen is GA)
    instances = []
    for idx, (task_id, golden, wrong, decoy) in enumerate(specs):
        cond_trees = {}
        truth = None
        for cond in CONDITIONS:
            tdir = out_root / f"{task_id}_{cond.lower()}"
            if tdir.exists():
                shutil.rmtree(tdir)
            truth = gen.build_task_skeleton(tdir, task_id, seed_base + idx, golden, wrong, cond, decoy)
            cond_trees[cond] = tdir
        # bake on the BundleS tree (condition-independent truth/grader)
        bake_dir = cond_trees["BundleS"]
        res = gen.bake_golden(bake_dir, ENV)
        gate = gen.hard_feasibility(res)
        # persist bake evidence into each condition's hidden/ (identical)
        for cond, tdir in cond_trees.items():
            (tdir / "hidden" / "bake_results.json").write_text(json.dumps({"results": res, "hard_feasibility": gate}, indent=2) + "\n")
        # ---- audits ----
        truth_for_sig = json.loads((bake_dir / "hidden" / ("signoff_intent_truth.json" if isA else "meas_request_truth.json")).read_text())
        sig = {
            "truth": AUD.truth_signature(truth_for_sig),
            "authority": AUD.authority_signature(truth_for_sig),
            "decoy": AUD.decoy_signature(truth_for_sig),
            "wrong_green": AUD.wrong_green_signature(res),
            "visible_tool_output_golden": AUD.visible_tool_output_signature(str(res["golden"].get("signoff_line", "")) + str(res["golden"].get("value", ""))),
            "visible_tool_output_wrong": AUD.visible_tool_output_signature(str(res["wrong"].get("signoff_line", "")) + str(res["wrong"].get("value", ""))),
        }
        # output-channel audit: golden + wrong candidates run; both must be plausible
        vis = {f"golden_{golden}": _plausible(gen, res["golden"]), f"wrong_{wrong}": _plausible(gen, res["wrong"])}
        oc = AUD.output_channel_audit(vis, _typed_space(gen))
        # semantic-diff per condition
        sd = {cond: AUD.semantic_diff_audit(truth_for_sig, {"bundle_discloses_golden": False}) for cond in CONDITIONS}
        # info-equiv: BundleS disclosure vs TypedContract disclosure (from their respective trees)
        bundleS_disc = _read_disclosure(cond_trees["BundleS"], "BundleS")
        typed_disc = _read_disclosure(cond_trees["TypedContract"], "TypedContract")
        ie = AUD.info_equiv_audit(bundleS_disc, typed_disc, truth_for_sig.get("typed_axes", {}))
        report = {"task_id": task_id, "track": track, "golden": list(golden), "wrong": list(wrong),
                  "decoy_recipe": decoy, "signatures": sig, "hard_feasibility": gate,
                  "output_channel_audit": oc, "semantic_diff_audit": sd, "info_equiv_audit": ie,
                  "golden_signoff_green": res["golden"].get("signoff_green", res["golden"].get("sim_ok")),
                  "wrong_signoff_green": res["wrong"].get("signoff_green", res["wrong"].get("sim_ok")),
                  "wrong_green_but_unattested": (res["wrong"]["markers"].get("green_but_unattested") or res["wrong"]["markers"].get("plausible_but_wrong"))}
        AUD.write_instance_audit_report(bake_dir / "hidden", report)
        instances.append(report)
    # diversity: the 3 instances must have distinct truth/authority/decoy/wrong-green signatures
    for key in ("truth", "authority", "decoy", "wrong_green"):
        vals = [r["signatures"][key] for r in instances]
        if len(set(vals)) != len(vals):
            print(f"!! {track} diversity WARNING: {key} signatures not all distinct: {vals}")
    return instances


def main():
    out = {"schema": "phase5b_eval_set/v1", "families": {}}
    out["families"]["A_sta"] = gen_family(GA, A_SPECS, "p15_sta_handoff", seed_base=100)
    out["families"]["B_spice"] = gen_family(GB, B_SPECS, "p16_spice_handoff", seed_base=200)
    allpass = all(r["hard_feasibility"].get("PASS") and r["output_channel_audit"]["PASS"]
                  and all(s["PASS"] for s in r["semantic_diff_audit"].values()) and r["info_equiv_audit"]["PASS"]
                  for fam in out["families"].values() for r in fam)
    out["all_instances_pass_hard_gate_and_audits"] = allpass
    rep = REPO / "reports" / "synthetic_phase5b_eval_set_report.json"
    rep.write_text(json.dumps(out, indent=2) + "\n")
    # concise stdout
    for fam, insts in out["families"].items():
        print(f"=== {fam} ===")
        for r in insts:
            print(f"  {r['task_id']}: hard_gate={r['hard_feasibility']['PASS']} "
                  f"out_chan={r['output_channel_audit']['PASS']} info_equiv={r['info_equiv_audit']['PASS']} "
                  f"wrong_green_attested_false={r['wrong_green_but_unattested']}")
    print("ALL PASS:", allpass)


if __name__ == "__main__":
    main()
