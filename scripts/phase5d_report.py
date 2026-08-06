#!/usr/bin/env python3
"""Phase-5D collection report generator (NO model calls). 3-condition TypedContract extension
(Base, BundleS, TypedContract) on STA + protocol-repaired SPICE. Re-grades each episode from its
preserved submitted config + instance truth (semantic_binding + family subtype); instance = unit;
reps nested; no pooled-trajectory headline. Three predeclared contrasts:
  (1) TypedContract vs Base; (2) TypedContract vs BundleS; (3) BundleS vs Base (same-window replication).
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
STATE = REPO / "reports/evidence/phase5d_state.json"
EVIDENCE = REPO / "reports/evidence/phase5d_episodes"
CONDITIONS = ["Base", "BundleS", "TypedContract"]
_SAFE = re.compile(r"^[A-Za-z0-9_]+$")


def _safe(v, f):
    if not isinstance(v, str) or not _SAFE.match(v):
        raise ValueError(f"unsafe {f}: {v!r}")
    return v


def _under(p, root):
    p = Path(p).resolve(); r = Path(root).resolve()
    if not str(p).startswith(str(r) + "/") and p != r:
        raise ValueError("path escapes root")
    return p


def _j(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return {}


def _sem_subtype(family, submitted, truth):
    if family == "A_sta":
        g = truth.get("golden_binding", {}); axes = ("intent_class", "target_partition", "check_mode")
    else:
        g = truth.get("golden_join", {}); axes = ("corner", "load_condition", "metric")
    sub = {a: submitted.get(a) for a in axes}
    correct = all(sub.get(a) == g.get(a) for a in axes)
    subtype = None
    if not correct:
        subtype = ("coverage_cell_mismatch" if family == "A_sta" and sub.get("target_partition") != g.get("target_partition")
                   else "authority_unattested_binding" if family == "A_sta" else
                   "corner_authority_misbind" if sub.get("corner") != g.get("corner") else
                   "load_authority_misbind" if sub.get("load_condition") != g.get("load_condition") else
                   "metric_role_misbind" if sub.get("metric") != g.get("metric") else "role_conditioned_value_selection_failure")
    return correct, subtype


def _truth_for(family, task_id):
    track = "p15_sta_handoff" if family == "A_sta" else "p16_spice_handoff"
    base_id = task_id.rsplit("_", 1)[0] if task_id.endswith(("_base", "_bundles", "_typedcontract")) else task_id
    tn = "signoff_intent_truth.json" if family == "A_sta" else "meas_request_truth.json"
    for cond in ("_bundles", "_base", "_typedcontract"):
        p = _under(REPO / "tasks" / track / f"{_safe(base_id,'base_id')}{cond}" / "hidden" / tn, REPO)
        if p.is_file():
            return _j(p)
    return {}


def _edit(family):
    return "exception_config" if family == "A_sta" else "meas_config"


def build():
    st = _j(STATE)
    eps = []
    for rec in st.get("episodes", []):
        tid = _safe(rec["task_id"], "task_id"); fam = _safe(rec["family"], "family"); trial = _safe(rec["trial"], "trial")
        truth = _truth_for(fam, tid)
        ef = _edit(fam)
        sub = _j(_under(EVIDENCE / trial / f"{ef}.submitted.json", EVIDENCE))
        sem, subtype = _sem_subtype(fam, sub, truth) if sub else (None, "no_submitted_config")
        sc = _j(_under(EVIDENCE / trial / "result.json", EVIDENCE))
        ag = _j(_under(EVIDENCE / trial / "agentlog.sanitized.json", EVIDENCE))
        comps = {c["name"]: c["raw_score"] for c in sc.get("components", [])}
        ts = ag.get("transport_summary") or {}; u = ag.get("usage") or {}
        ac = sc.get("anti_cheat", {})
        eps.append({"trial": trial, "family": fam, "instance": tid.rsplit("_", 1)[0], "condition": rec["condition"],
                    "rep": rec["rep"], "position_in_block": rec["position_in_block"],
                    "semantic_binding": sem, "failure_subtype": subtype,
                    "artifact_total_score": sc.get("total_score"), "anti_cheat_forbidden_mod": ac.get("forbidden_files_modified"),
                    "provenance": comps.get("provenance_attested", comps.get("evidence_provenance")),
                    "protocol_completion": comps.get("protocol_completion"),
                    "termination": "timed_out" if rec.get("final", {}).get("timed_out") else ("finish" if comps.get("protocol_completion") else "other"),
                    "terminal_transport_valid": ts.get("terminal_transport_valid"),
                    "recovered_degradation": ts.get("recovered_transport_degradation"),
                    "tokens_in": u.get("prompt_tokens") or u.get("tokens_in"),
                    "cost_cny": rec.get("total_cost")})
    # instance x condition rates
    by = {}
    for e in eps:
        d = by.setdefault((e["family"], e["instance"]), {c: [] for c in CONDITIONS})
        d[e["condition"]].append(e)
    instances = []
    for (fam, inst), d in sorted(by.items()):
        rates = {c: (sum(1 for x in d[c] if x["semantic_binding"]) / len(d[c]) if d[c] else None) for c in CONDITIONS}
        instances.append({"family": fam, "instance": inst, "rates": rates, "n_per_cond": {c: len(d[c]) for c in CONDITIONS}})
    # family mean rates
    fam_rates = {}
    for fam in ("A_sta", "B_spice"):
        fi = [i for i in instances if i["family"] == fam]
        fam_rates[fam] = {c: round(sum(i["rates"][c] or 0 for i in fi) / len(fi), 3) if fi else None for c in CONDITIONS}
    # contrasts (descriptive, instance-level direction counts; NOT a pooled headline test)
    def contrast(c1, c2):
        improve = decline = tie = 0
        for i in instances:
            r1, r2 = i["rates"][c1], i["rates"][c2]
            if r1 is None or r2 is None: continue
            improve += int(r1 > r2); decline += int(r1 < r2); tie += int(r1 == r2)
        return {"improve": improve, "decline": decline, "tie": tie, "n_instances": len(instances)}
    contrasts = {"TypedContract_vs_Base": contrast("TypedContract", "Base"),
                 "TypedContract_vs_BundleS": contrast("TypedContract", "BundleS"),
                 "BundleS_vs_Base_same_window": contrast("BundleS", "Base")}
    return {"schema": "phase5d_collection_report/v1",
            "label": "pre-specified secondary TypedContract extension with a protocol-repaired SPICE replication",
            "phase5c_remains_frozen_primary": True,
            "collection_status": {"status": st.get("status"), "primary": st.get("primary"), "invalid": st.get("invalid"),
                                  "replaced": st.get("replaced"), "aborted": st.get("aborted"), "target": 36,
                                  "total_cost_cny": st.get("spent"), "remaining_ledger_cny": st.get("remaining_ledger_balance")},
            "family_mean_rates": fam_rates, "instance_level": instances,
            "predeclared_contrasts_descriptive": contrasts,
            "analysis_note": "instance is the primary unit; reps nested; descriptive contrast directions only; NO pooled-trajectory headline test",
            "per_episode": eps}


if __name__ == "__main__":
    r = build()
    (REPO / "reports/synthetic_phase5d_collection_report.json").write_text(json.dumps(r, indent=2) + "\n")
    print(json.dumps({"collection": r["collection_status"], "family_mean_rates": r["family_mean_rates"],
                      "contrasts": r["predeclared_contrasts_descriptive"]}, indent=2))
