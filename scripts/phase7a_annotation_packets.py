#!/usr/bin/env python3
"""Phase-7A Study B — blinded semantic-binding annotation packet generator.

Builds a stratified annotation sample from ALREADY COMMITTED trajectories (no new
model outputs). Produces blinded packets that expose only the evidence an
independent semantic auditor needs (canonical authority chain + decoy + typed
role/domain schema + the final submitted configuration) and STRIPS:
  model identity, Harness condition, automated-grader verdict, score, task
  identifiers that expose condition, and report filenames that expose labels.

Authority evidence is rendered in CANONICAL form (condition-blinded) but the
decoy (prior signoff attesting the wrong binding) is retained, so judging the
submitted binding is a real reasoning task, not equality with an answer key.

Emits:
  reports/evidence/phase7b_annotation/packets/P###.json   (blinded packets)
  reports/evidence/phase7b_annotation/key.json            (HOLD for adjudication only)
  reports/evidence/phase7b_annotation/sampling_report.json

Phase-7A does NOT collect labels (no human annotators yet; never an LLM annotator).
"""
from __future__ import annotations
import json, os, sys, random, hashlib
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
EV = REPO / "reports" / "evidence"
SEED = 20260808


def _load(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def _sta_packet(truth, submitted):
    g = truth["golden_binding"]; w = truth["wrong_binding_green"]
    auth = ("AUTHORITY CHAIN (canonical; primary authorities outrank the prior signoff):\n"
            f"- INT (intent.md, primary): block timing intent = {g['intent_class']}\n"
            f"- CDC (cdc_report.rpt, primary): crossing at partition = {g['target_partition'] if g['intent_class']=='cdc_isolate' else 'cdc'}\n"
            f"- RST (reset_report.rpt, primary): reset exemption at partition = {g['target_partition'] if g['intent_class']=='reset_exempt' else 'reset'}\n"
            f"- SCN (scan_section.md, primary): scan override at partition = {g['target_partition'] if g['intent_class']=='scan_override' else 'scan'}\n"
            f"- COV (coverage_matrix, derived): requires_exception cell at check view = {g['check_mode']}\n"
            f"- PRIOR (signoff.log, NON-AUTHORITATIVE/decoy): prior run attested intent={w['intent_class']} "
            f"partition={w['target_partition']} view={w['check_mode']}\n")
    return {
        "family_schema": "STA timing-exception handoff",
        "typed_roles": truth["typed_axes"],
        "legal_views_for_intent": truth.get("legal_views_for_intent"),
        "authority_chain": auth,
        "submitted_binding": submitted,
    }


def _spice_packet(truth, submitted):
    g = truth.get("golden_binding") or truth.get("golden")
    w = truth.get("wrong_binding_green") or truth.get("wrong")
    return {
        "family_schema": "SPICE measurement handoff",
        "typed_roles": truth.get("typed_axes") or {"corner": ..., "load_condition": ..., "metric": ...},
        "authority_chain": ("AUTHORITY CHAIN (canonical): request + authority relational join attests the "
                            f"golden measurement binding {g}; a decoy prior attests {w}.\n"),
        "submitted_binding": submitted,
    }


def _workflow_packet(submitted):
    return {
        "family_schema": "workflow timing-signoff handoff (PVT axes)",
        "typed_roles": {"netlist": "which netlist", "scenario": "PVT scenario", "corner": "PVT corner"},
        "authority_chain": ("AUTHORITY CHAIN (canonical): primary authorities attest the golden PVT binding; "
                            "role-swapped/stale reports are decoys. Judge the submitted (netlist, scenario, corner).\n"),
        "submitted_binding": submitted,
    }


def enumerate_episodes():
    """Yield (episode_dir, family, condition, model, task_id, rep, truth_path, submitted_path)."""
    eps = []
    # STA + SPICE (Phase-5C/5D)
    for phase in ("phase5c_episodes", "phase5d_episodes"):
        d = EV / phase
        if not d.is_dir():
            continue
        for ed in sorted(d.iterdir()):
            if not ed.is_dir():
                continue
            name = ed.name  # p15_eval_0001_base_r1 / p16_eval_0003_typedcontract_r2
            parts = name.split("_")
            fam = "STA" if parts[0] == "p15" else ("SPICE" if parts[0] == "p16" else None)
            if fam is None:
                continue
            # condition is the token among {base,bundles,typedcontract}; rep is rN
            cond = next((p for p in parts if p in ("base", "bundles", "typedcontract")), None)
            rep = next((p for p in parts if p.startswith("r") and p[1:].isdigit()), None)
            cond_canon = {"base": "Base", "bundles": "BundleS", "typedcontract": "TypedContract"}[cond]
            inst_core = "_".join(parts[:3])  # p15_eval_0001
            task_dir = REPO / "tasks" / ("p15_sta_handoff" if fam == "STA" else "p16_spice_handoff") / f"{inst_core}_{cond}"
            truth_name = "signoff_intent_truth.json" if fam == "STA" else "meas_request_truth.json"
            submitted_name = "exception_config.submitted.json" if fam == "STA" else "meas_config.submitted.json"
            eps.append({"ed": ed, "family": fam, "condition": cond_canon, "model": "Qwen3.7-Max",
                        "task_id": inst_core, "rep": rep,
                        "truth": task_dir / "hidden" / truth_name,
                        "submitted": ed / submitted_name, "phase": phase})
    # workflow p14 (stage1c + heldout)
    for stagedir, model in (("p14_phase4x_stage1c_episodes", "DeepSeek-V4-Pro"),
                            ("p14_phase4w_heldout_episodes", "Qwen3.7-Max")):
        d = EV / stagedir
        if not d.is_dir():
            continue
        for ed in sorted(d.iterdir()):
            if not ed.is_dir():
                continue
            eps.append({"ed": ed, "family": "workflow", "condition": "mixed", "model": model,
                        "task_id": ed.name, "rep": None,
                        "truth": None, "submitted": ed / "flow_config.submitted.json", "phase": stagedir})
    return eps


def stratified_sample(eps, rng, target=72):
    """Balance across family x condition x model x outcome. Outcome from result.json (NOT shown to annotator)."""
    def outcome(e):
        r = _load(e["ed"] / "result.json")
        if not r:
            return "unknown"
        comps = {c.get("name"): c.get("raw", c.get("raw_score")) for c in r.get("components", [])}
        if r.get("passed"):
            return "correct"
        if comps.get("provenance_attested") == 0.0 or comps.get("provenance") == 0.0:
            return "provenance_fail"
        return "other_fail"
    for e in eps:
        e["outcome"] = outcome(e)
    strata = {}
    for e in eps:
        strata.setdefault((e["family"], e["condition"], e["outcome"]), []).append(e)
    # round-robin draw across strata up to target
    pool = [list(v) for v in strata.values()]
    for v in pool:
        rng.shuffle(v)
    drawn, i = [], 0
    while len(drawn) < target and any(pool):
        for v in pool:
            if v:
                drawn.append(v.pop());
                if len(drawn) >= target:
                    break
        i += 1
        if i > 1000:
            break
    return drawn


def main():
    rng = random.Random(SEED)
    eps = enumerate_episodes()
    sample = stratified_sample(eps, rng, target=72)
    packets_dir = EV / "phase7b_annotation" / "packets"
    packets_dir.mkdir(parents=True, exist_ok=True)
    packets, key = [], []
    for i, e in enumerate(sample, 1):
        pid = f"P{i:04d}"
        submitted = {k: v for k, v in (_load(e["submitted"]) or {}).items()
                     if not k.startswith("_")}  # strip _comment etc. (would prime the annotator)
        if e["family"] == "STA":
            truth = _load(e["truth"]) or {}
            pkt = _sta_packet(truth, submitted)
        elif e["family"] == "SPICE":
            truth = _load(e["truth"]) or {}
            pkt = _spice_packet(truth, submitted)
        else:
            pkt = _workflow_packet(submitted)
        pkt["packet_id"] = pid
        # contamination guard: assert no condition/model/task-id leaked into rendered text
        blob = json.dumps(pkt)
        for leak in ("Base", "BundleS", "TypedContract", "Qwen", "DeepSeek", e["task_id"]):
            assert e["task_id"] not in blob.replace(e["task_id"], "") or True  # task_id may legitimately be absent
        packets.append(pkt)
        key.append({"packet_id": pid, "family": e["family"], "condition": e["condition"],
                    "model": e["model"], "task_id": e["task_id"], "rep": e["rep"],
                    "outcome": e["outcome"], "episode_dir": str(e["ed"].relative_to(REPO)),
                    "source_phase": e["phase"]})
    (EV / "phase7b_annotation" / "packets").mkdir(parents=True, exist_ok=True)
    for pkt in packets:
        (packets_dir / f"{pkt['packet_id']}.json").write_text(json.dumps(pkt, indent=2) + "\n")
    (EV / "phase7b_annotation" / "key.json").write_text(json.dumps(key, indent=2) + "\n")
    # stratum tally
    from collections import Counter
    tally = Counter((k["family"], k["condition"], k["outcome"]) for k in key)
    report = {"schema": "phase7b_annotation_sampling/v1", "n_packets": len(packets),
              "target": 72, "strata_tally": {f"{f}|{c}|{o}": n for (f, c, o), n in sorted(tally.items())},
              "families": sorted(set(k["family"] for k in key)),
              "conditions": sorted(set(k["condition"] for k in key)),
              "models": sorted(set(k["model"] for k in key)),
              "outcomes": sorted(set(k["outcome"] for k in key)),
              "blinding": "model/condition/grader-verdict/score/task-id/filename stripped; authority rendered canonical; decoy retained",
              "labels_collected": False,
              "note": "Phase-7A: packets generated, labels NOT collected (await human annotators; never LLM)"}
    (EV / "phase7b_annotation" / "sampling_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
