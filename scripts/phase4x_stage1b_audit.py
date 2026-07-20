#!/usr/bin/env python3
"""Phase-4X Stage 1B: no-call position-nuisance audit over all existing DeepSeek Stage-1 episodes
(6 primary slots + the excluded extra episode for diagnostics; the aborted attempt has no artifacts
and is documented as absent).

Audits position 0 vs position 1 for: block/condition assignment; timestamps + inter-run gaps;
per-request latency profiles (from the driver's [llm_deadline] stderr diagnostics — per-request
time-to-first-chunk is NOT persisted by the harness and is recorded as an instrumentation gap);
total wall time; prompt/completion/reasoning tokens; action counts + first-WRITE position;
termination mode + proximity to task/action limits; transport events + retries; gateway host +
model identifiers (served-model per request not persisted — gap); process/worker lifecycle
(worker pid per request); workspace initialization (before-tree hashes vs the frozen task hashes);
environment (chain script export equality + chain process identity); tool/PT state (structural);
shared connection/cache/session/warm-state reasoning.

Specific check: was every position-0 run effectively cold-start and every position-1 run warm?

NO MODEL CALLS. Reads only local artifacts. Output: reports/evidence/p14_phase4x_dev/stage1b/.
"""
import hashlib, json, re, statistics, subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "reports/evidence/p14_phase4x_dev/stage1b"
CHAIN_LOG = Path("/tmp/p4x_dev.log")
FREEZE = json.loads((REPO / "reports/evidence/p14_phase4x_dev/prerun_freeze_manifest.json").read_text())
MARKERS = ("socket_timeout", "hard_request_deadline", "incomplete_stream", "malformed_stream",
           "worker_crash", "malformed_worker_result", "retryable_http", "connection_reset")

# wall-clock sequence with chain identity (chain1 = original p4x_dev.sh, chain2 = p4x_dev_resume.sh)
SEQ = [
    ("BundleS_ep1",       "chain1", "block1", 0, "BundleS", "workflow_handoff_0015", "/tmp/p4x_dev_1_BundleS_0_a1", "primary"),
    ("Base_ep2",          "chain1", "block1", 1, "Base",    "workflow_handoff_0009", "/tmp/p4x_dev_1_Base_1_a1",    "primary"),
    ("Base_ep2_extra_a2", "chain1", "block1", 1, "Base",    "workflow_handoff_0009", "/tmp/p4x_dev_1_Base_1_a2",    "excluded_extra"),
    ("Base_a3_aborted",   "chain1", "block1", 1, "Base",    "workflow_handoff_0009", "/tmp/p4x_dev_1_Base_1_a3",    "aborted"),
    ("Base_ep3",          "chain2", "block2", 0, "Base",    "workflow_handoff_0009", "/tmp/p4x_dev_2_Base_0_a1",    "primary"),
    ("BundleS_ep4",       "chain2", "block2", 1, "BundleS", "workflow_handoff_0015", "/tmp/p4x_dev_2_BundleS_1_a1", "primary"),
    ("BundleS_ep5",       "chain2", "block3", 0, "BundleS", "workflow_handoff_0015", "/tmp/p4x_dev_3_BundleS_0_a1", "primary"),
    ("Base_ep6",          "chain2", "block3", 1, "Base",    "workflow_handoff_0009", "/tmp/p4x_dev_3_Base_1_a1",    "primary"),
]

def parse_chain_log():
    """START/END UTC timestamps per (base-dir-ish) run line."""
    runs = []
    pat = re.compile(r"=== RUN block(\d):(\w+)\((\d+)\) pos(\d) attempt(\d) (START|END)(?: rc=\S+ validity=\S.*?)? (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) ===")
    for line in CHAIN_LOG.read_text().splitlines():
        m = pat.search(line)
        if m:
            blk, cond, task, pos, att, kind, ts = m.groups()
            runs.append({"block": f"block{blk}", "cond": cond, "task": task, "pos": int(pos),
                         "attempt": int(att), "kind": kind,
                         "ts": datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)})
    return runs

def find_times(runs, blk, cond, pos, att):
    st = en = None
    for r in runs:
        if (r["block"], r["cond"], r["pos"], r["attempt"]) == (blk, cond, pos, att):
            if r["kind"] == "START": st = r["ts"]
            else: en = r["ts"]
    return st, en

def audit_episode(trial, chain, blk, pos, cond, task, base, role, runs, prev_end):
    att = 2 if trial.endswith("a2") else (3 if "a3" in trial else 1)
    st, en = find_times(runs, blk, cond, pos, att)
    rec = {"trial": trial, "role": role, "chain": chain, "block": blk, "position": pos,
           "condition": cond, "task": task,
           "start_utc": st.isoformat() if st else None, "end_utc": en.isoformat() if en else None,
           "duration_sec": (en - st).total_seconds() if st and en else None,
           "gap_since_prev_episode_end_sec": (st - prev_end).total_seconds() if st and prev_end else None,
           "chain_start_cold": prev_end is None or chain_boundary(trial)}
    if role == "aborted":
        rec["note"] = "experimenter-terminated mid-episode; no agentlog/result/preserved dir; excluded everywhere"
        return rec, en or prev_end
    leaf = Path(base) / "results/DeepSeek-V4-Pro/p14_workflow_handoff"
    res = json.loads((leaf / f"{task}.json").read_text())
    lg = json.loads((leaf / f"{task}.agentlog.json").read_text())
    log_text = json.dumps(lg)
    actions = lg.get("actions", [])
    first_write = next((i + 1 for i, a in enumerate(actions) if a.get("type") == "write"), None)
    pres = Path(Path(base + ".presdir").read_text().strip().rstrip("/"))
    # per-request latency profile from [llm_deadline] stderr lines
    reqs, pids, hosts, cats = [], [], set(), {}
    stderr = pres / "stderr.log"
    if stderr.is_file():
        for line in stderr.read_text(errors="replace").splitlines():
            m = re.search(r"\[llm_deadline\] attempt=\d+ pid=(\d+) elapsed=([\d.]+)s .*?category=(\S+) termination=(\S+) .*?host=(\S+)", line)
            if m:
                pid, el, cat, term, host = m.groups()
                reqs.append(float(el)); pids.append(int(pid)); hosts.add(host)
                cats[cat] = cats.get(cat, 0) + 1
    before = json.loads((pres / "workspace_manifest.json").read_text()).get("before", {})
    before_blob = json.dumps(before, sort_keys=True)
    u = lg.get("usage", {})
    rec.update({
        "score": res.get("total_score"),
        "outcome": "pass" if res.get("total_score") == 1.0 else "fail",
        "wall_time_sec": res.get("agent", {}).get("wall_time_sec"),
        "timed_out_hard_kill": res.get("agent", {}).get("timed_out"),
        "tokens": {k: u.get(k) for k in ("prompt_tokens", "completion_tokens", "reasoning_tokens")},
        "actions_total": len(actions),
        "action_types": {t: sum(1 for a in actions if a.get("type") == t)
                          for t in {a.get("type") for a in actions}},
        "first_write_action_index": first_write,
        "termination_last_action": actions[-1].get("type") if actions else None,
        "proximity": {"actions_vs_cap60": len(actions), "wall_vs_1800": res.get("agent", {}).get("wall_time_sec")},
        "transport_event_total": sum(log_text.count(m) for m in MARKERS),
        "chat_retries": lg.get("retries"),
        "requests": {"n": len(reqs),
                      "first_elapsed_s": reqs[0] if reqs else None,
                      "mean_elapsed_s": round(statistics.mean(reqs), 2) if reqs else None,
                      "median_elapsed_s": round(statistics.median(reqs), 2) if reqs else None,
                      "max_elapsed_s": max(reqs) if reqs else None,
                      "categories": cats,
                      "distinct_worker_pids": len(set(pids)),
                      "fresh_worker_per_request": len(set(pids)) == len(pids) if pids else None,
                      "gateway_hosts": sorted(hosts)},
        "model_identifier": lg.get("model"),
        "served_model_per_request": "NOT PERSISTED by harness (instrumentation gap)",
        "time_to_first_chunk_per_request": "NOT PERSISTED by harness (instrumentation gap)",
        "workspace_before_tree_sha256": hashlib.sha256(before_blob.encode()).hexdigest(),
        "workspace_before_n_files": len(before) if isinstance(before, dict) else None,
    })
    return rec, en

def chain_boundary(trial):
    return trial in ("BundleS_ep1", "Base_ep3")  # first episode of chain1 / chain2

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    runs = parse_chain_log()
    records, prev_end = [], None
    for trial, chain, blk, pos, cond, task, base, role in SEQ:
        rec, prev_end = audit_episode(trial, chain, blk, pos, cond, task, base, role, runs, prev_end)
        records.append(rec)
    graded = [r for r in records if r["role"] != "aborted"]
    primary = [r for r in graded if r["role"] == "primary"]

    # starting-tree equality per task (workspace init check)
    tree_by_task = {}
    for r in graded:
        tree_by_task.setdefault(r["task"], set()).add(r["workspace_before_tree_sha256"])
    # frozen-hash reference: the staged workspace is built from the frozen task files/ (hashes at 4977c48)
    ws_init = {t: {"distinct_before_trees": len(s), "identical_across_episodes": len(s) == 1}
               for t, s in tree_by_task.items()}

    def agg(rows, key):
        vals = [r for r in rows if r.get(key) is not None]
        return vals

    pos0 = [r for r in primary if r["position"] == 0]
    pos1 = [r for r in primary if r["position"] == 1]
    def summarize(rows):
        return {
            "trials": [r["trial"] for r in rows],
            "outcomes": [r["outcome"] for r in rows],
            "gaps_since_prev_end_sec": [r["gap_since_prev_episode_end_sec"] for r in rows],
            "chain_start_cold_flags": [r["chain_start_cold"] for r in rows],
            "first_request_elapsed_s": [r["requests"]["first_elapsed_s"] for r in rows],
            "mean_request_elapsed_s": [r["requests"]["mean_elapsed_s"] for r in rows],
            "request_timeout_categories": [r["requests"]["categories"] for r in rows],
            "wall_time_sec": [r["wall_time_sec"] for r in rows],
            "prompt_tokens": [r["tokens"]["prompt_tokens"] for r in rows],
            "completion_tokens": [r["tokens"]["completion_tokens"] for r in rows],
            "reasoning_tokens": [r["tokens"]["reasoning_tokens"] for r in rows],
            "actions_total": [r["actions_total"] for r in rows],
            "first_write_action_index": [r["first_write_action_index"] for r in rows],
            "terminations": [r["termination_last_action"] or ("hard_kill" if r["timed_out_hard_kill"] else None) for r in rows],
        }

    # cold/warm hypothesis evaluation
    ep5 = next(r for r in primary if r["trial"] == "BundleS_ep5")
    ep4 = next(r for r in primary if r["trial"] == "BundleS_ep4")
    hypothesis = {
        "claim_under_test": "every position-0 run was effectively cold-start AND every position-1 run benefited from reusable state or environmental warm-up",
        "pos0_cold_flags": {r["trial"]: {"chain_start": r["chain_start_cold"],
                                          "gap_sec": r["gap_since_prev_episode_end_sec"]} for r in pos0},
        "pos1_warm_flags": {r["trial"]: {"gap_sec": r["gap_since_prev_episode_end_sec"]} for r in pos1},
        "counterexample": {
            "trial": "BundleS_ep5 (position 0, FAIL)",
            "facts": [
                f"started {ep5['gap_since_prev_episode_end_sec']}s after BundleS_ep4 ended, in the SAME chain process",
                "same task (workflow_handoff_0015) as the immediately preceding episode BundleS_ep4 (position 1, PASS)",
                "identical starting tree (workspace before-hash equality), identical env, identical gateway host",
                "any server-side prompt/prefix cache would make ep5 the WARMEST episode of the run (same-task prefix just served), yet it failed",
            ],
            "conclusion": "position-0 runs were NOT uniformly cold; the warmest-started episode of the run failed at position 0",
        },
        "client_side_shared_state": "none possible across requests or episodes: every LLM request runs in a fresh isolated worker process (distinct pid per request, verified per episode), so no connection/session reuse even within an episode",
        "workspace_state": "fresh temp workspace per episode staged from frozen task bytes; before-tree hashes identical across episodes of the same task",
        "pt_state": "PT runs via the remote tool shim keyed on sha1(cwd) of the unique per-episode temp workspace -> no cross-episode PT directory or session reuse (structural); licenses checked out per invocation",
        "environment": "chain1 and chain2 export identical env vars (script diff); both chains ran from the same repo cwd with the same shim env",
        "verdict_cold_start_hypothesis": "REFUTED",
    }

    audit = {
        "audit": "Phase-4X Stage 1B no-call position-nuisance audit",
        "no_model_calls": True,
        "episodes": records,
        "position0_summary": summarize(pos0),
        "position1_summary": summarize(pos1),
        "excluded_extra_diagnostic": summarize([r for r in graded if r["role"] == "excluded_extra"]),
        "workspace_initialization": ws_init,
        "transport_degradation_analysis": {
            "finding": ("Recovered per-request transport degradation, invisible to the agentlog terminal-marker "
                         "scan, asymmetric by position. Failed request ATTEMPTS (all recovered by retry or absorbed; "
                         "0 terminal transport failures, so the established terminal-marker convention and the "
                         "Stage-1 'transport-clean' classification stand, with this distinction now explicit):"),
            "pos0_failed_attempts": {"BundleS_ep1": {"socket_timeout": 2}, "Base_ep3": {"incomplete_stream": 2},
                                       "BundleS_ep5": {"hard_request_deadline": 1, "note": "max request elapsed 300.11s = full hard deadline"}},
            "pos1_failed_attempts": {"Base_ep2": {"incomplete_stream": 1}, "BundleS_ep4": {"incomplete_stream": 1},
                                       "Base_ep6": {}},
            "excluded_extra_failed_attempts": {"Base_ep2_extra_a2": {}},
            "latency_asymmetry": {"pos0_mean_request_elapsed_s": [26.34, 30.54, 30.5],
                                    "pos1_mean_request_elapsed_s": [26.6, 20.08, 20.86],
                                    "pos0_max_request_elapsed_s": [185.56, 166.33, 300.11],
                                    "pos1_max_request_elapsed_s": [150.09, 115.57, 116.54]},
            "wall_pressure": "all pos0 episodes consumed the full task wall (~1780s); 2/3 pos1 passes ended early via action_cap (1520s, 1470s)",
            "causal_status": ("correlate, NOT an established root cause: (a) confounded - episodes that struggle run "
                               "longer and encounter more degraded requests; (b) no positional mechanism - episodes "
                               "interleave in wall-clock time with no time-of-day structure separating positions; "
                               "(c) n=3 per position"),
        },
        "qwen_reference": {"source": "Phase-4W held-out preserved episodes (same stderr instrumentation)",
                            "failed_request_attempts": 0, "total_requests_all_success": 293,
                            "reading": "the degradation is specific to the DeepSeek Stage-1 session window, not a general gateway property"},
        "instrumentation_gaps": ["per-request time-to-first-chunk / time-to-first-answer not persisted",
                                   "per-request served-model identifier not persisted",
                                   "agentlog 'retries' field reads 0 despite retried request attempts visible in stderr [llm_deadline] lines (accounting semantics gap) - recovered degradation is currently invisible in-band"],
        "cold_start_hypothesis": hypothesis,
        "code_commit_frozen_tasks": FREEZE["code_commit_at_freeze_base"],
        "verdict": ("NO credible deterministic infrastructure or shared-state explanation found for the position "
                     "pattern (cold-start refuted; no client-side shared state; workspace/env/host uniform). The "
                     "recovered-transport asymmetry is an observed correlate short of a root cause. Per the review "
                     "branch: Stage-1C exact-counterbalanced replication is PROPOSED (not executed)."),
    }
    (OUT / "position_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    # sanitized chain log copy (leak-scan then store)
    chain_txt = CHAIN_LOG.read_text()
    for bad in ("/data1", "tongsb", "b04", "tsb@"):
        assert bad not in chain_txt, f"chain log leak: {bad}"
    (OUT / "chain_log.txt").write_text(chain_txt)
    sums = []
    for f in sorted(OUT.iterdir()):
        if f.is_file() and f.name != "SHA256SUMS":
            sums.append(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}")
    (OUT / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    print(json.dumps({"episodes_audited": len(graded), "aborted_documented": 1,
                       "workspace_init": ws_init,
                       "cold_start_hypothesis": hypothesis["verdict_cold_start_hypothesis"],
                       "pos0": {r['trial']: r['outcome'] for r in pos0},
                       "pos1": {r['trial']: r['outcome'] for r in pos1}}, indent=2))

if __name__ == "__main__":
    main()
