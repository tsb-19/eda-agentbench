#!/usr/bin/env python3
"""Phase-7D: what does the typed semantic oracle discriminate that the tool signal does not?

No paid calls, no EDA tool, no new episode. Every value is re-derived from records committed at
or before the experiment freeze. This script answers one question and refuses to answer more:

    On the frozen trajectories, how often does a family's own tool-success signal accept a
    submission that the typed provenance/authority oracle rejects?

WHAT IS COMPARED
----------------
Two verdicts per episode, both read from pre-existing frozen fields. No proxy rule is invented
here; if a family did not already record a tool-success field, its episodes are EXCLUDED rather
than imputed.

  family      semantic verdict (oracle)             tool-success signal (frozen field)
  ---------   -----------------------------------   -----------------------------------------
  workflow    flow_config.submitted.json compared   stage2_summary.json:
              to the hidden golden tuple by the       tool == "pt_shell" and tool_exit == 0
              FROZEN classifier imported from         and signoff == "OK"
              phase7c_study1_ledger.classify()
  STA (p15)   semantic_binding (submitted tuple     result.json component pt_signoff_green,
              == golden), from the frozen phase       which grade_sta_handoff.py reads from
              report / collection report             run_hidden.sh's signoff_result.json
  SPICE(p16)  semantic_binding component            result.json component simulation_success

PAIRING --- the reason this script is not a one-liner
-----------------------------------------------------
A semantic verdict and a tool verdict may only be compared when both describe the SAME final
submission. The two families differ in whether that holds:

  * STA / SPICE: it holds BY CONSTRUCTION. The tool signal is produced at grading time --- the
    hidden runner launders the agent's submitted binding into an SDC/deck and runs the real tool
    on it. There is no window in which the submission can drift from the verdict.

  * workflow: it does NOT hold automatically. The agent runs a two-stage evidence chain DURING
    the episode and may edit flow_config.json afterwards, leaving stage2_summary.json describing
    a configuration that was later replaced. stage2_summary.json records
    input_hashes["flow_config.json"], so this is decidable: an episode is paired only when that
    hash equals sha256(flow_config.submitted.json). 9 of 58 fail, and comparing tuples instead of
    hashes catches only 2 of the 9 --- the other 7 agree on (scenario, corner, netlist) while the
    consumed file differs. The frozen grader independently flags these (stage_chain == 0.0); this
    gate exists so the derived statistic agrees with the grader rather than contradicting it.

  The strict hash rule is PRIMARY. Two looser rules are reported as sensitivity only.

WHAT THE RESULT IS AND IS NOT
-----------------------------
The tool-success signal is CONSTANT (accept) on every retained episode, so it carries zero
discrimination for semantic correctness, and

    Delta = S_tool - S_semantic  ==  1 - S_semantic

identically. Delta is therefore NOT independent information and is emitted for the appendix only.
The reportable finding is the degeneracy plus its numerator/denominator.

This is a property of these frozen trajectories under a task construction that DELIBERATELY makes
a wrong binding tool-green --- it is the construction working as specified, quantified. It is not
an estimate of false-accept prevalence in agent benchmarks generally, and the emitted JSON says so
in `scope_limitation`. Strata are never pooled into a single population rate: the trajectories span
stages, conditions, models and run windows and are not one sampling frame.

Usage:  python3 scripts/phase7d_semantic_proxy_gap.py [--check]
        --check  recompute and diff against the committed JSON; non-zero exit on drift.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase7c_study1_ledger as LEDGER  # frozen classifier + goldens; imported, never re-implemented

REPO = Path(__file__).resolve().parents[1]
EV = REPO / "reports/evidence"
OUT_JSON = REPO / "reports/synthetic_phase7d_semantic_proxy_gap.json"

STA72 = REPO / "reports/synthetic_phase7a_sta72_report.json"
P5C = REPO / "reports/synthetic_phase5c_collection_report.json"
P5D = REPO / "reports/synthetic_phase5d_collection_report.json"
RUN1 = REPO / "reports/synthetic_p14_phase4w_run1.json"
PAIR2X2 = REPO / "reports/synthetic_p14_balanced_controlled_pair.json"

BY_CONSTRUCTION = "by_construction:tool_signal_generated_at_grading_time_from_submission"


class Excluded(Exception):
    """Raised when an episode cannot be paired or a required frozen field is absent."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _component(result: dict, name: str):
    """Return a component's raw score, or None. Never defaults a missing component."""
    for c in result.get("components", []):
        if c.get("name") == name:
            # two frozen schemas: p14 uses "raw", p15/p16 use "raw_score"
            v = c.get("raw_score", c.get("raw"))
            return None if v is None else float(v)
    return None


def _require(value, what: str):
    if value is None:
        raise Excluded(f"missing_frozen_field:{what}")
    return value


# --------------------------------------------------------------------------- workflow (p14)

def _workflow_episode_dirs():
    """(stage, condition, model, task, evidence_dir, path) for the 58 program-primary episodes."""
    out = []
    for stage, ldir, pfx, task, model, cond in LEDGER.LEDGER_CELLS:
        for t in sorted(p for p in (EV / ldir).iterdir() if p.is_dir()):
            if t.name.startswith(pfx + "_") and t.name not in LEDGER.EXCLUDED_TRIALS:
                out.append((stage, cond, model, task, ldir, t))
    run1 = {e["trial"]: e for e in json.loads(RUN1.read_text())["episodes"]}
    for t in sorted(p for p in (EV / "p14_phase4w_run1").iterdir() if p.is_dir()):
        ep = _require(run1.get(t.name), f"run1_report_entry:{t.name}")
        out.append(("4W-Run1", ep["variant"], "Qwen", ep["task"][-4:], "p14_phase4w_run1", t))
    return out


def _workflow_records():
    records = []
    for stage, cond, model, task, ldir, t in _workflow_episode_dirs():
        rec = {
            "episode_id": f"{ldir}/{t.name}", "family": "workflow", "stage": stage,
            "condition": cond, "model": model, "task": task,
            "semantic_source": "flow_config.submitted.json+phase7c_study1_ledger.classify",
            "tool_proxy_source": "stage2_summary.json:tool_exit,signoff",
            "semantic_correct": None, "tool_proxy_accept": None,
            "pairing_verified": False, "pairing_rule": "stage2_input_hash==sha256(submitted)",
            "exclusion_reason": None,
        }
        try:
            sub_path = t / "flow_config.submitted.json"
            s2_path = t / "stage2_summary.json"
            if not sub_path.is_file():
                raise Excluded("missing_frozen_field:flow_config.submitted.json")
            if not s2_path.is_file():
                raise Excluded("missing_frozen_field:stage2_summary.json")
            sub = json.loads(sub_path.read_text())
            s2 = json.loads(s2_path.read_text())

            # the stored submission must be the one the custody manifest declares
            pa = t / "preserved_artifacts.json"
            sub_sha = _sha256(sub_path)
            if pa.is_file():
                declared = json.loads(pa.read_text()).get("submitted_file_hashes", {}).get("flow_config.json")
                if declared is not None and declared != sub_sha:
                    raise Excluded("stored_submission_hash_disagrees_with_custody_manifest")

            golden = LEDGER.TASK_GOLDEN.get(task, LEDGER.DEV_GOLDEN)
            verdict = LEDGER.classify(sub.get("scenario"), sub.get("corner"),
                                      sub.get("netlist"), golden)
            rec["semantic_verdict"] = verdict
            rec["semantic_correct"] = (verdict == "correct")

            s2_cfg = s2.get("input_hashes", {}).get("flow_config.json")
            rec["pairing_verified"] = (_require(s2_cfg, "stage2_input_hashes.flow_config.json") == sub_sha)
            rec["binding_paired"] = (
                (sub.get("scenario"), sub.get("corner"), sub.get("netlist"))
                == (s2.get("scenario"), s2.get("corner"), s2.get("selected_netlist")))

            tool_exit = _require(s2.get("tool_exit"), "stage2_summary.tool_exit")
            signoff = _require(s2.get("signoff"), "stage2_summary.signoff")
            rec["tool_proxy_accept"] = (s2.get("tool") == "pt_shell" and tool_exit == 0
                                        and signoff == "OK")
            if not rec["pairing_verified"]:
                rec["exclusion_reason"] = "stale_stage2_evidence:tool_verdict_on_superseded_config"
        except Excluded as e:
            rec["exclusion_reason"] = str(e)
        records.append(rec)

    # controlled pair: frozen 2x2 reports per-cell counts only; no per-episode tool field exists
    matrix = json.loads(PAIR2X2.read_text())["matrix_2x2_k3"]
    for key, m in matrix.items():
        model, task = key.split("_")
        for i in range(m["k"]):
            records.append({
                "episode_id": f"controlled_pair/{key}/ep{i + 1}", "family": "workflow",
                "stage": "4V-pair", "condition": ("Base" if task == "0009" else "Full bundle"),
                "model": model, "task": task,
                "semantic_source": "synthetic_p14_balanced_controlled_pair.json:cell_counts_only",
                "tool_proxy_source": None, "semantic_correct": None, "tool_proxy_accept": None,
                "pairing_verified": False, "pairing_rule": None,
                "exclusion_reason": "aggregate_only:no_per_episode_record_and_no_tool_field",
            })
    return records


# --------------------------------------------------------------------------- STA / SPICE

def _graded_record(ep_dir: Path, field: str):
    """Read one frozen tool component from a per-episode result.json."""
    rj = ep_dir / "result.json"
    if not rj.is_file():
        raise Excluded("missing_frozen_field:result.json")
    d = json.loads(rj.read_text())
    v = _component(d, field)
    if v is None:
        raise Excluded(f"missing_frozen_field:component.{field}")
    return v == 1.0


def _sta_prospective_records():
    """Phase-7A: semantic per-rep booleans from the frozen report; tool from result.json."""
    rep = json.loads(STA72.read_text())
    conds = [("Base", "base"), ("BundleS", "bundles"), ("TypedContract", "typedcontract")]
    out = []
    for inst in rep["instances"]:
        iid = inst["instance"]
        for cond, tag in conds:
            for i, sem in enumerate(_require(inst.get(f"{cond}_reps"), f"{iid}.{cond}_reps"), start=1):
                trial = f"{iid}_{tag}_r{i}"
                rec = {
                    "episode_id": f"phase7a_episodes/{trial}", "family": "sta",
                    "stage": "7A-prospective", "condition": cond, "model": "Qwen3.7-Max",
                    "task": iid,
                    "semantic_source": "synthetic_phase7a_sta72_report.json:instances[].{cond}_reps",
                    "tool_proxy_source": "result.json:component.pt_signoff_green",
                    "semantic_correct": bool(sem), "tool_proxy_accept": None,
                    "pairing_verified": True, "pairing_rule": BY_CONSTRUCTION,
                    "exclusion_reason": None,
                }
                try:
                    rec["tool_proxy_accept"] = _graded_record(EV / "phase7a_episodes" / trial,
                                                              "pt_signoff_green")
                except Excluded as e:
                    rec["exclusion_reason"] = str(e)
                    rec["pairing_verified"] = False
                out.append(rec)
    return out


def _collection_records(report: Path, ev_dir: str, stage: str):
    """phase5c / phase5d: semantic_binding per episode from the collection report."""
    cr = json.loads(report.read_text())
    fam_field = {"A_sta": ("sta", "pt_signoff_green"), "B_spice": ("spice", "simulation_success")}
    out = []
    for e in cr["per_episode"]:
        family, field = fam_field[e["family"]]
        rec = {
            "episode_id": f"{ev_dir}/{e['trial']}", "family": family, "stage": stage,
            "condition": e["condition"], "model": "Qwen3.7-Max", "task": e["instance"],
            "semantic_source": f"{report.name}:per_episode[].semantic_binding",
            "tool_proxy_source": f"result.json:component.{field}",
            "semantic_correct": None,
            "tool_proxy_accept": None, "pairing_verified": True,
            "pairing_rule": BY_CONSTRUCTION, "exclusion_reason": None,
        }
        # semantic_binding is a required frozen boolean; absence is an exclusion, not a False
        if e.get("semantic_binding") is None:
            rec["semantic_correct"] = None
            rec["exclusion_reason"] = "missing_frozen_field:semantic_binding"
            rec["pairing_verified"] = False
            out.append(rec)
            continue
        rec["semantic_correct"] = bool(e["semantic_binding"])
        try:
            rec["tool_proxy_accept"] = _graded_record(EV / ev_dir / e["trial"], field)
        except Excluded as ex:
            rec["exclusion_reason"] = str(ex)
            rec["pairing_verified"] = False
        out.append(rec)
    return out


# --------------------------------------------------------------------------- aggregation

def _confusion(rows):
    """2x2 of tool-proxy prediction against the semantic verdict."""
    return {
        "tool_accept_semantic_correct": sum(1 for r in rows if r["tool_proxy_accept"] and r["semantic_correct"]),
        "tool_accept_semantic_wrong": sum(1 for r in rows if r["tool_proxy_accept"] and not r["semantic_correct"]),
        "tool_reject_semantic_correct": sum(1 for r in rows if not r["tool_proxy_accept"] and r["semantic_correct"]),
        "tool_reject_semantic_wrong": sum(1 for r in rows if not r["tool_proxy_accept"] and not r["semantic_correct"]),
    }


def _stratum_stats(rows):
    n = len(rows)
    if n == 0:
        return {"n": 0}
    correct = sum(1 for r in rows if r["semantic_correct"])
    accept = sum(1 for r in rows if r["tool_proxy_accept"])
    wrong = n - correct
    wrong_accepted = sum(1 for r in rows if (not r["semantic_correct"]) and r["tool_proxy_accept"])
    uniq = sorted({bool(r["tool_proxy_accept"]) for r in rows})
    out = {
        "n": n,
        "semantic_correct": correct,
        "semantic_wrong": wrong,
        "tool_proxy_accept": accept,
        "tool_proxy_unique_values": len(uniq),
        "tool_proxy_is_constant": len(uniq) == 1,
        "confusion_matrix": _confusion(rows),
        "observed_tool_false_accept_numerator": wrong_accepted,
        "observed_tool_false_accept_denominator": wrong,
        "observed_tool_false_accept_rate": (round(wrong_accepted / wrong, 4) if wrong else None),
        "S_tool": round(accept / n, 4),
        "S_semantic": round(correct / n, 4),
        "delta_appendix_only_pp": round((accept - correct) / n * 100, 1),
    }
    return out


def collect():
    records = (_workflow_records()
               + _sta_prospective_records()
               + _collection_records(P5C, "phase5c_episodes", "5C")
               + _collection_records(P5D, "phase5d_episodes", "5D"))

    included = [r for r in records if r["exclusion_reason"] is None]
    excluded = [r for r in records if r["exclusion_reason"] is not None]

    strata = {}
    for key, sel in [
        ("workflow_program_primary", lambda r: r["family"] == "workflow"),
        ("sta_prospective_7A", lambda r: r["family"] == "sta" and r["stage"] == "7A-prospective"),
        ("sta_phase5C", lambda r: r["family"] == "sta" and r["stage"] == "5C"),
        ("sta_phase5D", lambda r: r["family"] == "sta" and r["stage"] == "5D"),
        ("spice_phase5D", lambda r: r["family"] == "spice" and r["stage"] == "5D"),
    ]:
        strata[key] = _stratum_stats([r for r in included if sel(r)])

    # sensitivity: the two looser workflow pairing rules (reported, never headline)
    wf = [r for r in records if r["family"] == "workflow" and r.get("semantic_correct") is not None
          and r.get("tool_proxy_accept") is not None]
    sens = {
        "workflow_binding_paired": _stratum_stats([r for r in wf if r.get("binding_paired")]),
        "workflow_pairing_not_enforced": _stratum_stats(wf),
    }

    exclusion_tally = {}
    for r in excluded:
        exclusion_tally[r["exclusion_reason"]] = exclusion_tally.get(r["exclusion_reason"], 0) + 1

    overall = _stratum_stats(included)
    return {
        "schema": "phase7d_semantic_proxy_gap/v1",
        "question": ("On the frozen trajectories, how often does a family's own tool-success "
                     "signal accept a submission the typed oracle rejects?"),
        "no_new_measurement": ("Re-derived from records committed at or before the experiment "
                               "freeze. No model call, no EDA tool run, no new episode."),
        "scope_limitation": (
            "These families are CONSTRUCTED so that a wrong binding is still tool-green. A "
            "false-accept rate of 1.0 therefore shows the construction working as specified and "
            "quantifies its consequence for measurement; it is NOT an estimate of false-accept "
            "prevalence in agent benchmarks generally. Strata are reported separately and never "
            "pooled into a population rate: they span stages, conditions, models and run windows "
            "and do not form one sampling frame."),
        "delta_is_not_independent": (
            "The tool signal is constant (accept) on every retained episode, so "
            "delta = S_tool - S_semantic == 1 - S_semantic identically. Delta is emitted for the "
            "appendix and is not a second finding."),
        "universe": {
            "considered": len(records),
            "included": len(included),
            "excluded": len(excluded),
            "exclusion_reasons": exclusion_tally,
        },
        "overall_included": overall,
        "strata": strata,
        "workflow_pairing_sensitivity": sens,
        "per_episode": sorted(records, key=lambda r: r["episode_id"]),
    }


# --------------------------------------------------------------------------- fail-closed checks

def assertions(payload):
    """Fail-closed source assertions. Returns a list of problems; empty means pass."""
    p = []
    recs = payload["per_episode"]
    inc = [r for r in recs if r["exclusion_reason"] is None]
    exc = [r for r in recs if r["exclusion_reason"] is not None]

    # 1. frozen universe reconciles with the source manifests
    n_pair = sum(v["k"] for v in json.loads(PAIR2X2.read_text())["matrix_2x2_k3"].values())
    n_run1 = len(json.loads(RUN1.read_text())["episodes"])
    n_7a = json.loads(STA72.read_text())["n_episodes"]
    n_5c = len(json.loads(P5C.read_text())["per_episode"])
    n_5d = len(json.loads(P5D.read_text())["per_episode"])
    n_wf = len([r for r in recs if r["family"] == "workflow"])
    if n_wf != 58 + n_pair:
        p.append(f"workflow universe {n_wf} != 58 + {n_pair} controlled-pair")
    if len([r for r in recs if r["stage"] == "7A-prospective"]) != n_7a:
        p.append(f"7A universe != report n_episodes ({n_7a})")
    if len([r for r in recs if r["stage"] == "5C"]) != n_5c:
        p.append(f"5C universe != collection per_episode ({n_5c})")
    if len([r for r in recs if r["stage"] == "5D"]) != n_5d:
        p.append(f"5D universe != collection per_episode ({n_5d})")
    if len(recs) != 58 + n_pair + n_7a + n_5c + n_5d:
        p.append("universe total does not reconcile with source manifests")
    if payload["universe"]["considered"] != len(recs):
        p.append("universe.considered != len(per_episode)")

    # 2. every included episode carries all three provenance fields
    for r in inc:
        for f in ("semantic_source", "tool_proxy_source", "pairing_rule"):
            if not r.get(f):
                p.append(f"{r['episode_id']}: included without {f}")
        if r["pairing_verified"] is not True:
            p.append(f"{r['episode_id']}: included without pairing_verified")
        # 3. no field silently defaulted
        if r["semantic_correct"] is None or r["tool_proxy_accept"] is None:
            p.append(f"{r['episode_id']}: included with a null verdict")
    for r in exc:
        if r["semantic_correct"] is not None and r["tool_proxy_accept"] is not None \
                and r["pairing_verified"] is True:
            p.append(f"{r['episode_id']}: excluded but fully identifiable")

    # 4/5. the two structurally unidentifiable groups must stay excluded
    cp = [r for r in recs if r["stage"] == "4V-pair"]
    if len(cp) != n_pair or any(r["exclusion_reason"] is None for r in cp):
        p.append("controlled-pair episodes must all be excluded")
    sp5c = [r for r in recs if r["family"] == "spice" and r["stage"] == "5C"]
    if not sp5c or any(r["exclusion_reason"] is None for r in sp5c):
        p.append("SPICE phase-5C episodes must all be excluded (no frozen tool component)")

    # 6/7/8/9. arithmetic integrity of every emitted stratum
    for name, s in list(payload["strata"].items()) + list(payload["workflow_pairing_sensitivity"].items()) \
            + [("overall_included", payload["overall_included"])]:
        if s.get("n", 0) == 0:
            continue
        if s["semantic_correct"] + s["semantic_wrong"] != s["n"]:
            p.append(f"{name}: correct + wrong != n")
        if s["tool_proxy_accept"] > s["n"]:
            p.append(f"{name}: tool accepts exceed n")
        cm = s["confusion_matrix"]
        if sum(cm.values()) != s["n"]:
            p.append(f"{name}: confusion matrix does not sum to n")
        num, den = (s["observed_tool_false_accept_numerator"],
                    s["observed_tool_false_accept_denominator"])
        if num > den:
            p.append(f"{name}: false-accept numerator {num} > denominator {den}")
        if den != s["semantic_wrong"]:
            p.append(f"{name}: false-accept denominator != semantic_wrong")
    if sum(s["n"] for s in payload["strata"].values()) != len(inc):
        p.append("stratum sizes do not sum to the included count")
    if payload["universe"]["included"] != len(inc):
        p.append("universe.included != included records")
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="recompute, assert, and diff against the committed JSON")
    args = ap.parse_args()

    payload = collect()
    problems = assertions(payload)
    if problems:
        print("PHASE-7D SOURCE ASSERTIONS FAILED:", file=sys.stderr)
        for q in problems:
            print(f"  - {q}", file=sys.stderr)
        return 2

    if args.check:
        if not OUT_JSON.is_file():
            print(f"PHASE-7D: {OUT_JSON.relative_to(REPO)} missing; run without --check first",
                  file=sys.stderr)
            return 1
        if json.loads(OUT_JSON.read_text()) != payload:
            print("PHASE-7D DRIFT: recomputed result differs from the committed JSON",
                  file=sys.stderr)
            return 1
        print("phase7d: assertions pass; committed JSON reproduces exactly")
    else:
        OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"wrote {OUT_JSON.relative_to(REPO)}")

    u = payload["universe"]
    o = payload["overall_included"]
    print(f"\nuniverse: {u['considered']} considered, {u['included']} included, "
          f"{u['excluded']} excluded (never imputed)")
    for reason, k in sorted(u["exclusion_reasons"].items()):
        print(f"    {k:>3}  {reason}")
    print(f"\n{'stratum':<28}{'n':>5}{'correct':>9}{'wrong':>7}{'accept':>8}"
          f"{'false-accept':>14}{'const?':>8}")
    for name, s in payload["strata"].items():
        far = (f"{s['observed_tool_false_accept_numerator']}/"
               f"{s['observed_tool_false_accept_denominator']}"
               if s["semantic_wrong"] else "0/0 n/a")
        print(f"{name:<28}{s['n']:>5}{s['semantic_correct']:>9}{s['semantic_wrong']:>7}"
              f"{s['tool_proxy_accept']:>8}{far:>14}{str(s['tool_proxy_is_constant']):>8}")
    print(f"\noverall (included, NOT a population rate): "
          f"tool accepted {o['tool_proxy_accept']}/{o['n']}, including "
          f"{o['observed_tool_false_accept_numerator']}/"
          f"{o['observed_tool_false_accept_denominator']} semantically wrong bindings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
