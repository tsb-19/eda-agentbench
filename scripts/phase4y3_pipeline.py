#!/usr/bin/env python3
"""Phase-4Y Stage-3 episode pipeline: extract C2-only (0022) vs C4-only (0023) rows with co-primary
failure subtype + both transport dimensions, preserve sanitized evidence, manifest + custody. Qwen 12/36.

Mirrors phase4y2_pipeline. Resolves each episode's preserved workspace by timestamp (frozen_order is
sequential, so the n-th preserved dir of today's run maps to the n-th slot). Classifies each submitted
binding: correct | axis_binding_failure | role_conditioned_value_selection_failure.
"""
import hashlib, json, statistics, subprocess, sys, glob
from pathlib import Path

REPO = Path("/data1/tongsb/eda-agentbench-synthetic-phase0a")
EV_SUB = "p14_phase4y3_episodes"
EV = REPO / "reports/evidence" / EV_SUB
RATE_IN, RATE_OUT, MAX_ACTIONS = 12.0, 36.0, 60
SCEN, CORNER, GOLDEN = {"slow", "typ", "fast"}, {"func", "test", "lowpower"}, ("slow", "func")
RUN_DATE = "20260731"

# frozen execution order -> (block, cond, pos, task)
ORDER = [(1, "C4", 0, "workflow_handoff_0023"), (1, "C2", 1, "workflow_handoff_0022"),
         (2, "C2", 0, "workflow_handoff_0022"), (2, "C4", 1, "workflow_handoff_0023"),
         (3, "C4", 0, "workflow_handoff_0023"), (3, "C2", 1, "workflow_handoff_0022"),
         (4, "C2", 0, "workflow_handoff_0022"), (4, "C4", 1, "workflow_handoff_0023")]


def classify_binding(sub):
    s, c, net = sub.get("scenario"), sub.get("corner"), sub.get("netlist")
    if (s, c) == GOLDEN:
        return "correct" if net == "netlist_v2.v" else "correct-pair/stale-netlist"
    cross = (s not in SCEN) or (c not in CORNER)
    return f"semantic_binding_failure/{'axis_binding_failure' if cross else 'role_conditioned_value_selection_failure'}"


def resolve_preserved():
    paths = sorted(glob.glob(f"/tmp/agentic_eval_*/Qwen3.7-Max/workflow_handoff_*/{RUN_DATE}_*/preserved/flow_config.json"),
                   key=lambda p: p.split("/")[-3])
    assert len(paths) == 8, f"expected 8 preserved dirs for {RUN_DATE}, got {len(paths)}"
    # verify task-id sequence matches ORDER
    for (blk, cond, pos, task), p in zip(ORDER, paths):
        pt = p.split("/")[-4]
        assert pt == task, f"preserved task {pt} != expected {task} at block{blk}:{cond}p{pos}"
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
    if last == "finish": term = "finish_action"
    elif timed_out: term = "task_wall_hard_kill"
    elif last == "deadline": term = "task_wall_limit"
    elif len(actions) >= MAX_ACTIONS: term = "action_cap"
    else: term = "other"
    tel = lg.get("request_telemetry", [])
    lat = [a["elapsed_s"] for r in tel for a in r.get("attempts", []) if a.get("category") == "success"]
    binding = classify_binding(sub)
    return {"trial": trial,
            "submitted": f"{sub.get('netlist')} / scenario={sub.get('scenario')} / corner={sub.get('corner')}",
            "binding": binding, "score": res.get("total_score"), "signoff": comps.get("signoff"),
            "evidence_generation": comps.get("evidence_generation"), "artifact_correct": res.get("total_score") == 1.0,
            "typed_binding_correct": binding == "correct", "protocol_completed": last == "finish",
            "termination": term, "actions": len(actions),
            "reasoning_tokens": (lg.get("usage") or {}).get("reasoning_tokens"),
            "confidence": lg.get("confidence") or "", "chat_retries": lg.get("retries"),
            "wall_time_sec": res.get("agent", {}).get("wall_time_sec"),
            "transport": {"terminal_transport_valid": ts.get("terminal_transport_valid"),
                          "recovered_transport_degradation": ts.get("recovered_transport_degradation"),
                          "recovered_failed_attempts": ts.get("recovered_failed_attempts"),
                          "recovered_hard_deadlines": ts.get("recovered_hard_deadlines"),
                          "cumulative_retry_wall_s": ts.get("cumulative_retry_wall_s"),
                          "logical_requests": ts.get("logical_requests"),
                          "request_latency_mean_s": round(statistics.mean(lat), 2) if lat else None},
            "reliability": {"confidence_decision": rel.get("confidence_decision"),
                            "overconfident_wrong": rel.get("overconfident_wrong"),
                            "underconfident_correct": rel.get("underconfident_correct"),
                            "abstained": rel.get("abstained"), "protocol_status": rel.get("protocol_status")},
            "cost_cny": round(cost, 2), "anti_cheat_clean": res.get("agent", {}).get("anti_cheat_clean"),
            "preserved_dir": str(pres_dir)}


def main():
    pres = resolve_preserved()
    rows = {}
    for (blk, cond, pos, task), p in zip(ORDER, pres):
        trial = f"{cond}_b{blk}p{pos}"
        results_leaf = f"/tmp/p4y3_ep_{blk}_{cond}_{pos}_a1/results/Qwen3.7-Max/p14_workflow_handoff"
        pres_dir = str(Path(p).parent)
        r = extract(trial, results_leaf, pres_dir, task)
        r.update({"block": f"block{blk}", "position": pos, "condition": cond, "task": task})
        rows[trial] = r
        t = r["transport"]; rel = r["reliability"]
        print(f"{trial} [{cond}@pos{pos}]: score={r['score']} binding={r['binding']} term={r['termination']} "
              f"conf={r['confidence']!r} recov_degrad={t['recovered_transport_degradation']} "
              f"overconf={rel['overconfident_wrong']} abstain={rel['abstained']} ¥{r['cost_cny']}")
    (REPO / "reports/evidence/p14_phase4y3/episode_rows.json").write_text(json.dumps(rows, indent=2) + "\n")

    PAIRS = [("flow_config.json", "flow_config.submitted.json"), ("timing_report.rpt", "timing_report.rpt"),
             ("evidence_manifest.json", "evidence_manifest.json"), ("stage2_summary.json", "stage2_summary.json")]
    custody = {}
    for (blk, cond, pos, task), p in zip(ORDER, pres):
        trial = f"{cond}_b{blk}p{pos}"
        results_leaf = f"/tmp/p4y3_ep_{blk}_{cond}_{pos}_a1/results/Qwen3.7-Max/p14_workflow_handoff"
        diag = {"trial": trial, "date": "2026-07-31", "transport": "SSE streaming", "model": "Qwen3.7-Max",
                "slot": f"block{blk}:{cond}/pos{pos}", "transport_summary": rows[trial]["transport"],
                "classification_6dim": {"score": rows[trial]["score"], "termination": rows[trial]["termination"],
                 "protocol_completed": rows[trial]["protocol_completed"],
                 "terminal_transport_valid": rows[trial]["transport"]["terminal_transport_valid"],
                 "anti_cheat_clean": rows[trial]["anti_cheat_clean"],
                 "gradeable": True}}
        diagp = Path(f"/tmp/diag_p4y3_{trial}.json"); diagp.write_text(json.dumps(diag, indent=2) + "\n")
        workspace = str(Path(p).parent.parent)  # preserve_trial reads workspace/preserved/...
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
        "files": entries, "chain_of_custody_byte_match": custody}, indent=2) + "\n")
    (EV / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    print(f"\ncustody ALL BYTE-MATCH ({len(custody)}); manifested {len(entries)} files")

    summary = {}
    for cond in ("C2", "C4"):
        rs = [r for r in rows.values() if r["condition"] == cond]
        summary[cond] = {"k": len(rs),
            "correct": sum(r["binding"] == "correct" for r in rs),
            "axis_binding_failure": sum(r["binding"].endswith("axis_binding_failure") for r in rs),
            "role_conditioned_value_selection_failure": sum(r["binding"].endswith("role_conditioned_value_selection_failure") for r in rs),
            "terminal_transport_valid": sum(r["transport"]["terminal_transport_valid"] for r in rs),
            "recovered_degradation": sum(r["transport"]["recovered_transport_degradation"] for r in rs),
            "overconfident_wrong": sum(r["reliability"]["overconfident_wrong"] for r in rs),
            "abstained": sum(r["reliability"]["abstained"] for r in rs),
            "cost_cny": round(sum(r["cost_cny"] for r in rs), 2)}
    print("\n=== PER-CONDITION SUMMARY ===")
    print(json.dumps(summary, indent=2))
    (REPO / "reports/evidence/p14_phase4y3/episode_summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
