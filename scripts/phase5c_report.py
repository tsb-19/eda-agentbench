#!/usr/bin/env python3
"""Phase-5C collection report generator. Consumes the durable run-state + per-episode evidence,
re-grades each episode from its preserved submitted config + the instance truth (authoritative
semantic_binding + family-specific failure subtype, uniform across families), and applies the
FROZEN external-validity interpretation rules. No model calls.

External-validity outcomes (frozen interpretation):
  - cross_family_support    : BundleS improves over Base in BOTH families (>=2/3 instances each)
  - family_contingent       : improves in one family, not the other
  - null_no_transfer        : no consistent improvement in either family
  - ceiling                 : Base already near-perfect (mean >= 0.9) -> no room to show improvement
  - excessive_difficulty    : both Base and BundleS near-zero (mean <= 0.1) in a family
  - incomplete_collection   : budget-stopped before all 24 primary slots
Repetitions are nested observations; instance is the unit; NO pooled-trajectory headline test.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
STATE = REPO / "reports/evidence/phase5c_state.json"
EVIDENCE = REPO / "reports/evidence/phase5c_episodes"


def _load_json(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return {}


def _sem_subtype(family, submitted, truth):
    """Re-grade: semantic_binding (submitted==golden on the typed axes) + family-specific subtype."""
    if family == "A_sta":
        g = truth.get("golden_binding", {}); axes = ("intent_class", "target_partition", "check_mode")
    else:
        g = truth.get("golden_join", {}); axes = ("corner", "load_condition", "metric")
    sub = {a: submitted.get(a) for a in axes}
    correct = all(sub.get(a) == g.get(a) for a in axes)
    subtype = None
    if not correct:
        if family == "A_sta":
            cov = truth.get("coverage_matrix", {})
            cell = ((cov.get(sub.get("target_partition")) or {}).get(sub.get("check_mode")) or {}).get(sub.get("intent_class"))
            if sub.get("intent_class") != g.get("intent_class") and sub.get("target_partition") != g.get("target_partition"):
                subtype = "authority_unattested_binding"
            elif cell != "requires_exception":
                subtype = "coverage_cell_mismatch"
            elif sub.get("target_partition") != g.get("target_partition"):
                subtype = "scope_object_misbind"
            else:
                subtype = "role_conditioned_value_selection_failure"
        else:
            if sub.get("corner") != g.get("corner"):
                subtype = "corner_authority_misbind"
            elif sub.get("load_condition") != g.get("load_condition"):
                subtype = "load_authority_misbind"
            elif sub.get("metric") != g.get("metric"):
                subtype = "metric_role_misbind"
            else:
                subtype = "role_conditioned_value_selection_failure"
    return correct, subtype


def _truth_for(family, task_id):
    track = "p15_sta_handoff" if family == "A_sta" else "p16_spice_handoff"
    base_id = task_id.rsplit("_", 1)[0] if task_id.endswith(("_base", "_bundles", "_typedcontract")) else task_id
    tn = "signoff_intent_truth.json" if family == "A_sta" else "meas_request_truth.json"
    for cond in ("_bundles", "_base"):
        p = REPO / "tasks" / track / f"{base_id}{cond}" / "hidden" / tn
        if p.is_file():
            return _load_json(p)
    return {}


def _edit_name(family):
    return "exception_config" if family == "A_sta" else "meas_config"


def build():
    st = _load_json(STATE)
    episodes = []
    for rec in st.get("episodes", []):
        tid = rec["task_id"]; fam = rec["family"]; trial = rec["trial"]
        truth = _truth_for(fam, tid)
        ef = _edit_name(fam)
        sub = _load_json(EVIDENCE / trial / f"{ef}.submitted.json")
        sem, subtype = _sem_subtype(fam, sub, truth) if sub else (None, "no_submitted_config")
        sc = _load_json(EVIDENCE / trial / "result.json")
        ag = _load_json(EVIDENCE / trial / "agentlog.sanitized.json")
        comps = sc.get("component_scores", {}) or {}
        ts = ag.get("transport_summary") or {}
        usage = ag.get("usage") or {}
        episodes.append({
            "trial": trial, "family": fam, "instance": tid.rsplit("_", 1)[0], "condition": rec["condition"],
            "rep": rec["rep"], "position_in_block": rec["position_in_block"], "block_id": rec["block_id"],
            "semantic_binding": sem, "failure_subtype": subtype,
            "tool_artifact_total_score": sc.get("total_score"),
            "provenance_authority": comps.get("provenance_attested", comps.get("evidence_provenance")),
            "protocol_completion": comps.get("protocol_completion"),
            "termination": ("timed_out" if rec.get("final", {}).get("timed_out") else ("finish" if comps.get("protocol_completion") else "other")),
            "terminal_transport_valid": ts.get("terminal_transport_valid"),
            "recovered_degradation": ts.get("recovered_transport_degradation"),
            "actions": ag.get("n_actions") or len(ag.get("actions", [])),
            "tokens_in": usage.get("prompt_tokens") or usage.get("tokens_in"),
            "tokens_out": usage.get("completion_tokens") or usage.get("tokens_out"),
            "cost_cny": rec.get("total_cost"),
        })
    # instance-level paired (2 Base + 2 BundleS per instance)
    by_inst = {}
    for e in episodes:
        by_inst.setdefault(e["instance"], {"family": e["family"], "Base": [], "BundleS": []})[e["condition"]].append(e)
    instances = []
    for inst, d in by_inst.items():
        b = d["Base"]; s = d["BundleS"]
        b_rate = sum(1 for x in b if x["semantic_binding"]) / len(b) if b else None
        s_rate = sum(1 for x in s if x["semantic_binding"]) / len(s) if s else None
        direction = "improve" if (s_rate is not None and b_rate is not None and s_rate > b_rate) else (
            "decline" if (s_rate is not None and b_rate is not None and s_rate < b_rate) else "tie")
        instances.append({"instance": inst, "family": d["family"], "n_Base": len(b), "n_BundleS": len(s),
                          "Base_rate": b_rate, "BundleS_rate": s_rate, "direction": direction})
    fam_summary = {}
    for fam in ("A_sta", "B_spice"):
        fi = [i for i in instances if i["family"] == fam]
        fam_summary[fam] = {"n_instances": len(fi), "instances_improve": sum(1 for i in fi if i["direction"] == "improve"),
                            "Base_mean_rate": round(sum(i["Base_rate"] or 0 for i in fi) / len(fi), 3) if fi else None,
                            "BundleS_mean_rate": round(sum(i["BundleS_rate"] or 0 for i in fi) / len(fi), 3) if fi else None}
    conclusion = _conclusion(st, fam_summary)
    return {"schema": "phase5c_collection_report/v1", "collection_status": {
                "status": st.get("status"), "primary": st.get("primary"), "invalid": st.get("invalid"),
                "excluded": st.get("excluded"), "replaced": st.get("replaced"), "aborted": st.get("aborted"),
                "target": 24, "total_cost_cny": st.get("spent"), "remaining_ledger_balance_cny": st.get("remaining_ledger_balance")},
            "per_episode": episodes, "instance_level": instances, "family_summary": fam_summary,
            "external_validity_conclusion": conclusion,
            "analysis_note": "instance is the primary unit; reps nested; descriptive only; no pooled-trajectory headline test",
            "phase5c_paid_model_episodes": len(episodes)}


def _conclusion(st, fam_summary):
    if st.get("status") == "incomplete_collection_budget_stop":
        return "incomplete_collection"
    a = fam_summary.get("A_sta", {}); b = fam_summary.get("B_spice", {})
    def ceiling(f): return (f.get("Base_mean_rate") or 0) >= 0.9
    def toohard(f): return (f.get("Base_mean_rate") or 0) <= 0.1 and (f.get("BundleS_mean_rate") or 0) <= 0.1
    def support(f): return (f.get("instances_improve") or 0) >= 2
    a_sup, b_sup = support(a), support(b)
    a_state = "ceiling" if ceiling(a) else ("excessive_difficulty" if toohard(a) else ("support" if a_sup else "null"))
    b_state = "ceiling" if ceiling(b) else ("excessive_difficulty" if toohard(b) else ("support" if b_sup else "null"))
    if a_state == "support" and b_state == "support":
        return "cross_family_support"
    if a_state == "support" or b_state == "support":
        return "family_contingent"
    if "ceiling" in (a_state, b_state):
        return "ceiling"
    if "excessive_difficulty" in (a_state, b_state):
        return "excessive_difficulty"
    return "null_no_transfer"


if __name__ == "__main__":
    r = build()
    (REPO / "reports/synthetic_phase5c_collection_report.json").write_text(json.dumps(r, indent=2) + "\n")
    print(json.dumps({"collection_status": r["collection_status"], "family_summary": r["family_summary"],
                      "conclusion": r["external_validity_conclusion"], "episodes": len(r["per_episode"])}, indent=2))
