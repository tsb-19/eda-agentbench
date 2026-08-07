#!/usr/bin/env python3
"""Family A (STA constraint/exception handoff) grader — stdlib only.

Distinct from p14's grade_workflow.py: NO master EVIDENCE_OK gate; instead SEPARATED
checks. A binding can be pt_signoff_green yet fail provenance_attestation — that is the
core "tool success != semantic correctness" property of Family A.

Reads (cwd = staged task dir):
  - hidden/signoff_intent_truth.json   (provenance DAG + coverage matrix + golden)
  - exception_config.json              (the agent's submitted binding)
  - hidden/signoff_result.json         (written by run_hidden.sh: {signoff_green, slack, applied_sdc})
  - hidden/applied_hidden.sdc          (the laundered SDC actually applied to PT)

Emits a markers JSON on stdout that STAHandoffEvaluator maps to weighted components.

Truth-file schema (p15_signoff_intent_truth/v1):
  typed_axes: {axis: [legal values]}
  authority_nodes: [{id, artifact, clause, trust in {primary,derived,none}}]
  derivation_edges: [{from:[authority_ids], to:{axis:value}, rule}]
  coverage_matrix: {partition: {view: {intent: "requires_exception"|"<other>"}}}
  golden_binding: {intent_class, target_partition, check_mode}
  legal_views_for_intent: {intent: "setup"|"hold"|"both"}
  masking_keywords: [substrings that, if found applied as new exceptions, indicate masking]
"""
from __future__ import annotations
import json
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


def _rederive_golden(truth):
    """Defensive: re-derive the golden binding from the derivation edges, assert == golden_binding."""
    golden = dict(truth.get("golden_binding", {}))
    derived = {}
    for edge in truth.get("derivation_edges", []):
        frm = edge.get("from", [])
        # an edge counts only if ALL its source authorities are sufficiently trusted
        nodes = {n["id"]: n.get("trust") for n in truth.get("authority_nodes", [])}
        if all(nodes.get(a) in TRUST_OK for a in frm):
            for axis, val in (edge.get("to") or {}).items():
                derived[axis] = val
    tampered = {k: (golden.get(k), derived.get(k)) for k in golden if k in derived and golden.get(k) != derived.get(k)
                and golden.get(k) is not None and derived.get(k) is not None}
    return golden, derived, tampered


def grade(truth_path="signoff_intent_truth.json",
          submit_path="exception_config.json",
          signoff_path="signoff_result.json",
          sdc_path="applied_hidden.sdc"):
    truth = _load(truth_path)
    markers = {"schema": "p15_grade_markers/v1", "checks": {}, "tampered_truth": False}
    if not truth:
        markers["fatal"] = "truth_file_missing"
        return markers
    sub = _load(submit_path) or {}
    s_intent = sub.get("intent_class")
    s_part = sub.get("target_partition")
    s_view = sub.get("check_mode")
    typed = truth.get("typed_axes", {})

    golden, derived, tampered = _rederive_golden(truth)
    if tampered:
        markers["tampered_truth"] = True
        markers["tamper_detail"] = tampered

    # 1. pt_signoff_green  (from run_hidden.sh's signoff_result.json)
    sres = _load(signoff_path) or {}
    pt_green = bool(sres.get("signoff_green", False))

    # 2. semantic_binding  (submitted == golden)
    semantic_ok = (s_intent == golden.get("intent_class") and
                   s_part == golden.get("target_partition") and
                   s_view == golden.get("check_mode"))

    # 3. provenance_attested  (every submitted axis value is the target of an edge from
    #    sufficiently-trusted authorities; decoy-only support does not count)
    nodes = {n["id"]: n.get("trust") for n in truth.get("authority_nodes", [])}
    submitted = {"intent_class": s_intent, "target_partition": s_part, "check_mode": s_view}
    attested_axes = set()
    for axis, val in submitted.items():
        if val is None:
            continue
        for edge in truth.get("derivation_edges", []):
            to = edge.get("to") or {}
            if to.get(axis) == val:
                frm = edge.get("from", [])
                if all(nodes.get(a) in TRUST_OK for a in frm):
                    attested_axes.add(axis)
                    break
    provenance_attested = (len(attested_axes) == 3 and
                           all(a in attested_axes for a in ("intent_class", "target_partition", "check_mode")))

    # 4. coverage_cell_consistent  (the (partition, view) cell is a requires_exception cell for the intent)
    cov = truth.get("coverage_matrix", {})
    cell = ((cov.get(s_part) or {}).get(s_view) or {}).get(s_intent)
    coverage_ok = (cell == "requires_exception")

    # 5. check_view_legal  (submitted view is legal for the submitted intent)
    legal = truth.get("legal_views_for_intent", {})
    allowed = legal.get(s_intent)
    if allowed == "both":
        view_legal = s_view in ("setup", "hold", "both")
    elif allowed in ("setup", "hold"):
        view_legal = s_view in (allowed, "both")
    else:
        view_legal = s_view in typed.get("check_mode", [])

    # 6. not_masking  (applied SDC does not introduce extra weakening beyond the declared exception)
    sdc_text = ""
    if Path(sdc_path).is_file():
        sdc_text = Path(sdc_path).read_text(errors="ignore").lower()
    # masking = an applied exception line that is NOT the single expected golden exception.
    # Heuristic: count exception-declaring directives; >1 undeclared weakening => masking.
    directives = [k for k in truth.get("masking_keywords", [])
                  if k and k.lower() in sdc_text]
    # The golden applies exactly one exception; if the applied SDC carries weakening beyond
    # the laundered single exception, flag masking. run_hidden.sh records expected_exception_line.
    expected = sres.get("expected_exception_lines", 1)
    applied = sres.get("applied_exception_lines", len(directives))
    not_masking = (applied <= expected)

    # failure subtype (co-primary diagnostic, family A)
    subtype = None
    if not semantic_ok:
        if not provenance_attested and not coverage_ok:
            subtype = "authority_unattested_binding"
        elif not coverage_ok:
            subtype = "coverage_cell_mismatch"
        elif s_view not in (allowed or "") and allowed != "both":
            subtype = "check_view_inversion"
        elif s_part != golden.get("target_partition"):
            subtype = "scope_object_misbind"
        else:
            subtype = "role_conditioned_value_selection_failure"
    elif s_intent not in typed.get("intent_class", []) or s_part not in typed.get("target_partition", []) \
            or s_view not in typed.get("check_mode", []):
        subtype = "axis_binding_failure"

    markers["checks"] = {
        "pt_signoff_green": pt_green,
        "semantic_binding": semantic_ok,
        "provenance_attested": provenance_attested,
        "coverage_cell_consistent": coverage_ok,
        "check_view_legal": view_legal,
        "not_masking": not_masking,
    }
    markers["submitted"] = submitted
    markers["failure_subtype"] = subtype
    # provenance separation marker (the core property): green signoff but unattested
    markers["green_but_unattested"] = bool(pt_green and not provenance_attested)
    return markers


if __name__ == "__main__":
    args = sys.argv[1:]
    truth = args[0] if len(args) > 0 else "signoff_intent_truth.json"
    out = grade(truth_path=truth)
    print(json.dumps(out, indent=2))
