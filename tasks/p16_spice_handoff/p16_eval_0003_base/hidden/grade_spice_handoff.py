#!/usr/bin/env python3
"""Family B (SPICE model/measurement handoff) grader — stdlib only.

Six SEPARATED dimensions (per directive) — no master gate. A wrong tuple can be
simulation_success + numeric_validity yet fail semantic_binding: that is the core
"simulation success + plausible number != semantic correctness" property of Family B.

Reads (cwd = staged task dir):
  - hidden/meas_request_truth.json     (request-authority relational join + golden)
  - meas_config.json                   (the agent's submitted binding: corner/load_condition/metric)
  - provenance_attestation.json        (the agent's cited authority sources per role)
  - hidden/measure_result.json         (written by run_hidden.sh: {sim_ok, value, analysis})
  - measurement_report.md              (artifact-completion check; presence)

Emits markers JSON on stdout that SPICEHandoffEvaluator maps to weighted components.

Truth-file schema (p16_meas_request_truth/v1):
  typed_axes: {axis: [legal values]}
  authorities: {role: {src, value, trust}}            # the golden authorities
  decoy_authorities: [{role, src, value, trust}]
  golden_join: {corner, load_condition, metric}
  wrong_join_plausible: {corner, load_condition, metric}
  plausible_range: {min, max}
  analysis_for_metric: {metric: "dc"|"tran"|"ac"}
"""
from __future__ import annotations
import json
import math
import sys
from pathlib import Path

TRUST_OK = {"primary", "derived"}


def _load(p):
    p = Path(p)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def grade(truth_path="meas_request_truth.json",
          submit_path="meas_config.json",
          attestation_path="provenance_attestation.json",
          measure_path="measure_result.json",
          report_path="measurement_report.md"):
    truth = _load(truth_path) or {}
    markers = {"schema": "p16_grade_markers/v1", "dimensions": {}, "tampered_truth": False}
    sub = _load(submit_path) or {}
    s_corner = sub.get("corner")
    s_load = sub.get("load_condition")
    s_metric = sub.get("metric")

    golden = truth.get("golden_join", {})
    authorities = truth.get("authorities", {})

    # defensive: re-derive golden join from authorities; assert consistent
    derived = {role: a.get("value") for role, a in authorities.items()
               if a.get("trust") in TRUST_OK}
    tampered = {k: (golden.get(k), derived.get(k)) for k in golden
                if k in derived and golden.get(k) != derived.get(k)
                and golden.get(k) is not None and derived.get(k) is not None}
    if tampered:
        markers["tampered_truth"] = True
        markers["tamper_detail"] = tampered

    # 1. simulation_success — HSPICE ran and produced a measurement
    mres = _load(measure_path) or {}
    sim_ok = bool(mres.get("sim_ok", False))

    # 2. numeric_validity — measured value is finite and inside plausible_range[metric]
    val = mres.get("value")
    rng = (truth.get("plausible_range") or {}).get(s_metric, {})
    try:
        val_f = float(val) if val is not None else None
    except (TypeError, ValueError):
        val_f = None
    numeric_ok = (val_f is not None and math.isfinite(val_f)
                  and val_f >= float(rng.get("min", -math.inf))
                  and val_f <= float(rng.get("max", math.inf)))

    # 3. semantic_binding — submitted join == golden join
    semantic_ok = (s_corner == golden.get("corner") and
                   s_load == golden.get("load_condition") and
                   s_metric == golden.get("metric"))

    # 4. evidence_provenance — the agent's cited source per role == the golden authority source
    att = _load(attestation_path) or {}
    cited = att.get("roles") or att  # accept {roles:{...}} or a flat map
    prov_ok = True
    for role in ("corner", "load_condition", "metric"):
        gold_src = (authorities.get(role) or {}).get("src")
        cit = cited.get(role) if isinstance(cited, dict) else None
        if isinstance(cit, dict):
            cit = cit.get("src")
        if cit != gold_src:
            prov_ok = False
            break

    # 5. artifact_completion — measurement report present and non-trivial
    rep = Path(report_path)
    artifact_ok = rep.is_file() and len(rep.read_text(errors="ignore").strip()) > 0

    # 6. protocol_completion — voluntary FINISH recorded by the harness in the attestation/report meta
    proto_ok = bool(att.get("protocol_completed") or mres.get("protocol_completed") or
                    (rep.is_file() and "FINISH" in rep.read_text(errors="ignore")))

    markers["dimensions"] = {
        "simulation_success": sim_ok,
        "numeric_validity": numeric_ok,
        "semantic_binding": semantic_ok,
        "evidence_provenance": prov_ok,
        "artifact_completion": artifact_ok,
        "protocol_completion": proto_ok,
    }
    markers["submitted"] = {"corner": s_corner, "load_condition": s_load, "metric": s_metric}

    # failure subtype (co-primary diagnostic, family B)
    subtype = None
    if not semantic_ok:
        if s_corner != golden.get("corner"):
            subtype = "corner_authority_misbind"
        elif s_load != golden.get("load_condition"):
            subtype = "load_authority_misbind"
        elif s_metric != golden.get("metric"):
            subtype = "metric_role_misbind"
        else:
            subtype = "role_conditioned_value_selection_failure"
    typed = truth.get("typed_axes", {})
    if (s_corner not in typed.get("corner", []) or s_load not in typed.get("load_condition", [])
            or s_metric not in typed.get("metric", [])):
        subtype = "axis_binding_failure"
    # analysis-implied mismatch (the analysis type run was inconsistent with the metric)
    expected_analysis = (truth.get("analysis_for_metric") or {}).get(s_metric)
    if expected_analysis and mres.get("analysis") and mres.get("analysis") != expected_analysis:
        subtype = "analysis_implied_mismatch"

    # core-property marker: sim ok + number plausible but semantically wrong
    markers["plausible_but_wrong"] = bool(sim_ok and numeric_ok and not semantic_ok)
    markers["failure_subtype"] = subtype
    return markers


if __name__ == "__main__":
    args = sys.argv[1:]
    truth = args[0] if len(args) > 0 else "meas_request_truth.json"
    print(json.dumps(grade(truth_path=truth), indent=2))
