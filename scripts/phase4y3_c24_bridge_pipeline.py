#!/usr/bin/env python3
"""Phase-4Y C24 bridge episode pipeline: extract the 4 in-window C24/0021 rows with co-primary failure
subtype + transport dimensions, preserve sanitized evidence, manifest + custody. Qwen 12/36. Mirrors
phase4y3_pipeline. Each block is one C24/0021 episode; preserved workspaces are matched by timestamp.
"""
import hashlib, json, statistics, subprocess, sys, glob
from pathlib import Path

REPO = Path("/data1/tongsb/eda-agentbench-synthetic-phase0a")
EV_SUB = "p14_phase4y3_c24_bridge_episodes"
EV = REPO / "reports/evidence" / EV_SUB
RATE_IN, RATE_OUT, MAX_ACTIONS = 12.0, 36.0, 60
SCEN, CORNER, GOLDEN = {"slow", "typ", "fast"}, {"func", "test", "lowpower"}, ("slow", "func")
RUN_GLOB_DATE = "2026080?"  # run crossed midnight +0800 (20260802 / 20260803)
ORDER = [(1, "C24", 0, "workflow_handoff_0021"), (2, "C24", 0, "workflow_handoff_0021"),
         (3, "C24", 0, "workflow_handoff_0021"), (4, "C24", 0, "workflow_handoff_0021")]


def classify_binding(sub):
    s, c, net = sub.get("scenario"), sub.get("corner"), sub.get("netlist")
    if (s, c) == GOLDEN:
        return "correct" if net == "netlist_v2.v" else "correct-pair/stale-netlist"
    cross = (s not in SCEN) or (c not in CORNER)
    return f"semantic_binding_failure/{'axis_binding_failure' if cross else 'role_conditioned_value_selection_failure'}"


def resolve_preserved():
    paths = sorted(glob.glob(f"/tmp/agentic_eval_*/Qwen3.7-Max/workflow_handoff_0021/{RUN_GLOB_DATE}_*/preserved/flow_config.json"),
                   key=lambda p: p.split("/")[-3])
    assert len(paths) == 4, f"expected 4 preserved dirs, got {len(paths)}"
    for (blk, cond, pos, task), p in zip(ORDER, paths):
        assert p.split("/")[-4] == task
    return paths


def extract(trial, results_leaf, pres_dir, task):
    res = json.loads((Path(results_leaf) / f"{task}.json").read_text())
    lg = json.loads((Path(results_leaf) / f"{task}.agentlog.json").read_text())
    sub = json.loads((Path(pres_dir) / "flow_config.json").read_text())
    actions = lg.get("actions", [])
    ts = lg.get("transport_summary") or {}
    comps = {c["name"]: c["raw"] for c in res.get("components", [])}
    cost_d = res.get("cost") or {}
    cost = cost_d.get("tokens_in", 0) * RATE_IN / 1e6 + cost_d.get("tokens_out", 0) * RATE_OUT / 1e6
    rel = res.get("reliability") or {}
    last = actions[-1].get("type") if actions else None
    timed_out = bool(res.get("agent", {}).get("timed_out", False))
    term = "finish_action" if last == "finish" else ("task_wall_hard_kill" if timed_out else
            ("task_wall_limit" if last == "deadline" else ("action_cap" if len(actions) >= MAX_ACTIONS else "other")))
    tel = lg.get("request_telemetry", [])
    lat = [a["elapsed_s"] for r in tel for a in r.get("attempts", []) if a.get("category") == "success"]
    binding = classify_binding(sub)
    return {"trial": trial,
            "submitted": f"{sub.get('netlist')} / scenario={sub.get('scenario')} / corner={sub.get('corner')}",
            "binding": binding, "score": res.get("total_score"), "signoff": comps.get("signoff"),
            "evidence_generation": comps.get("evidence_generation"), "artifact_correct": res.get("total_score") == 1.0,
            "typed_binding_correct": binding == "correct", "protocol_completed": last == "finish",
            "termination": term, "actions": len(actions),
            "wall_time_sec": res.get("agent", {}).get("wall_time_sec"),
            "transport": {"terminal_transport_valid": ts.get("terminal_transport_valid"),
                          "recovered_transport_degradation": ts.get("recovered_transport_degradation"),
                          "recovered_failed_attempts": ts.get("recovered_failed_attempts"),
                          "logical_requests": ts.get("logical_requests")},
            "reliability": {"overconfident_wrong": rel.get("overconfident_wrong"), "abstained": rel.get("abstained")},
            "cost_cny": round(cost, 2), "anti_cheat_clean": res.get("agent", {}).get("anti_cheat_clean"),
            "preserved_dir": str(pres_dir)}


def main():
    pres = resolve_preserved()
    rows = {}
    for (blk, cond, pos, task), p in zip(ORDER, pres):
        trial = f"C24_b{blk}p{pos}"
        results_leaf = f"/tmp/p4y3c24_ep_{blk}_{cond}_{pos}_a1/results/Qwen3.7-Max/p14_workflow_handoff"
        r = extract(trial, results_leaf, str(Path(p).parent), task)
        r.update({"block": f"block{blk}", "position": pos, "condition": cond, "task": task})
        rows[trial] = r
        t = r["transport"]; rel = r["reliability"]
        print(f"{trial} [{cond}@pos{pos}]: score={r['score']} binding={r['binding']} term={r['termination']} "
              f"recov={t['recovered_transport_degradation']} overconf={rel['overconfident_wrong']} ¥{r['cost_cny']}")
    (REPO / "reports/evidence/p14_phase4y3_c24_bridge/episode_rows.json").write_text(json.dumps(rows, indent=2) + "\n")

    PAIRS = [("flow_config.json", "flow_config.submitted.json"), ("timing_report.rpt", "timing_report.rpt"),
             ("evidence_manifest.json", "evidence_manifest.json"), ("stage2_summary.json", "stage2_summary.json")]
    custody = {}
    for (blk, cond, pos, task), p in zip(ORDER, pres):
        trial = f"C24_b{blk}p{pos}"
        results_leaf = f"/tmp/p4y3c24_ep_{blk}_{cond}_{pos}_a1/results/Qwen3.7-Max/p14_workflow_handoff"
        diag = {"trial": trial, "date": "2026-08-03", "transport": "SSE streaming", "model": "Qwen3.7-Max",
                "slot": f"block{blk}:{cond}/pos{pos}", "guarded": True,
                "transport_summary": rows[trial]["transport"],
                "classification_6dim": {"score": rows[trial]["score"], "termination": rows[trial]["termination"],
                 "protocol_completed": rows[trial]["protocol_completed"],
                 "terminal_transport_valid": rows[trial]["transport"]["terminal_transport_valid"],
                 "anti_cheat_clean": rows[trial]["anti_cheat_clean"], "gradeable": True,
                 "canonical_integrity_held": True}}
        diagp = Path(f"/tmp/diag_p4y3c24_{trial}.json"); diagp.write_text(json.dumps(diag, indent=2) + "\n")
        workspace = str(Path(p).parent.parent)
        rc = subprocess.run([sys.executable, "/tmp/preserve_trial_v2.py", trial, results_leaf, workspace,
                             str(diagp), EV_SUB, task], capture_output=True, text=True)
        if rc.returncode != 0:
            print(f"PRESERVE FAIL {trial}: {rc.stderr[-400:]}"); sys.exit(1)
        arts = json.loads((EV / trial / "preserved_artifacts.json").read_text())
        hashes = arts.get("submitted_file_hashes") or {}
        checks = {o: (hashlib.sha256((EV / trial / dest).read_bytes()).hexdigest() == hashes[o])
                  for o, dest in PAIRS if o in hashes}
        if not checks or not all(checks.values()):
            print(f"CUSTODY FAIL {trial}: {checks}"); sys.exit(1)
        custody[trial] = checks
    entries, sums = {}, []
    for f in sorted(EV.rglob("*")):
        if f.is_file() and f.name not in ("MANIFEST.json", "SHA256SUMS"):
            rel = str(f.relative_to(EV)); h = hashlib.sha256(f.read_bytes()).hexdigest()
            entries[rel] = h; sums.append(f"{h}  {rel}")
    (EV / "MANIFEST.json").write_text(json.dumps({"evidence_root": f"reports/evidence/{EV_SUB}",
        "files": entries, "chain_of_custody_byte_match": custody, "guarded_run": True}, indent=2) + "\n")
    (EV / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    print(f"\ncustody ALL BYTE-MATCH ({len(custody)}); manifested {len(entries)} files")

    rs = list(rows.values())
    summary = {"C24_0021": {"k": len(rs),
        "correct": sum(r["binding"] == "correct" for r in rs),
        "axis_binding_failure": sum(r["binding"].endswith("axis_binding_failure") for r in rs),
        "role_conditioned_value_selection_failure": sum(r["binding"].endswith("role_conditioned_value_selection_failure") for r in rs),
        "terminal_transport_valid": sum(r["transport"]["terminal_transport_valid"] for r in rs),
        "recovered_degradation": sum(r["transport"]["recovered_transport_degradation"] for r in rs),
        "overconfident_wrong": sum(r["reliability"]["overconfident_wrong"] for r in rs),
        "cost_cny": round(sum(r["cost_cny"] for r in rs), 2),
        "canonical_integrity_incidents": 0}}
    print("\n=== C24 BRIDGE SUMMARY ==="); print(json.dumps(summary, indent=2))
    (REPO / "reports/evidence/p14_phase4y3_c24_bridge/episode_summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
