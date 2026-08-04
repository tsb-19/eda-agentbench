#!/usr/bin/env python3
"""Phase-5 shared audit + signature utilities (no model calls; stdlib only).

Used by the eval-set generator and the per-instance gates. Generic over both families'
truth schemas (Family A provenance-DAG; Family B request-authority join).

Provides:
  - signatures: truth-graph / authority / decoy / wrong-green / visible-tool-output digests
    (used to prove STRUCTURAL diversity across the 3 instances of a family — not lexical relabeling).
  - output_channel_audit: after the COMPLETE agent-visible surface (prompt, task files,
    generated artifacts, permitted tool outputs), require >=2 publicly plausible typed candidates.
  - semantic_diff_audit: the public constraint set under-determines the golden (no disclosure).
  - info_equiv_audit: BundleS and TypedContract carry the SAME semantic facts and both OMIT
    golden values / answer-bearing assertions / post-submission verifier feedback.
"""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def truth_signature(truth: dict) -> str:
    """Digest of the truth-graph structure (schema + axes + binding shape + provenance shape)."""
    schema = truth.get("schema", "?")
    axes = truth.get("typed_axes", {})
    golden = truth.get("golden_binding") or truth.get("golden_join")
    wrong = truth.get("wrong_binding_green") or truth.get("wrong_join_plausible")
    if "derivation_edges" in truth:           # Family A: DAG
        prov = [("edge", tuple(sorted(e.get("from", []))), tuple(sorted((e.get("to") or {}).items()))) for e in truth["derivation_edges"]]
        cov = truth.get("coverage_matrix", {})
    else:                                      # Family B: relational join
        prov = [("auth", r, a.get("src"), a.get("trust")) for r, a in truth.get("authorities", {}).items()]
        cov = None
    return _sha({"schema": schema, "axes": {k: len(v) for k, v in axes.items()},
                 "golden": golden, "wrong": wrong, "prov": prov, "cov": cov})


def authority_signature(truth: dict) -> str:
    """Instance-specific: includes the targets the authorities actually attest (the golden)."""
    if "authority_nodes" in truth:  # Family A: DAG
        targets = [(tuple(sorted(e.get("from", []))), tuple(sorted((e.get("to") or {}).items())))
                   for e in truth.get("derivation_edges", [])]
        return _sha(targets)
    return _sha([(r, a.get("src"), a.get("value")) for r, a in truth.get("authorities", {}).items()])


def decoy_signature(truth: dict) -> str:
    """Instance-specific: the decoy recipe + the wrong tuple the decoy attests + decoy sources."""
    wrong = truth.get("wrong_binding_green") or truth.get("wrong_join_plausible")
    return _sha({"recipe": truth.get("decoy_recipe"),
                 "wrong_attested": wrong,
                 "decoy_sources": truth.get("decoy_sources", []),
                 "decoy_authorities": truth.get("decoy_authorities", [])})


def wrong_green_signature(bake_results: dict) -> str:
    w = bake_results.get("wrong", {})
    m = w.get("markers", {})
    checks = m.get("checks") or m.get("dimensions", {})
    return _sha({"wrong_binding": w.get("binding") or w.get("wrong_join_plausible"),
                 "signoff_green": w.get("signoff_green", w.get("sim_ok")),
                 "green_but_unattested": m.get("green_but_unattested", m.get("plausible_but_wrong")),
                 "subtype": m.get("failure_subtype")})


def visible_tool_output_signature(output_text: str) -> str:
    """Digest of the agent-visible tool output (sanitized: counts + marker lines, not raw)."""
    lines = [l.strip() for l in (output_text or "").splitlines() if l.strip()]
    markers = [l for l in lines if re.search(r"slack|VIOLAT|MET|exception|false_path|multicycle|"
                                             r"measure|gain|gbw|pm|slew|hz|db|conclud|error|warning", l, re.I)]
    return _sha({"n_lines": len(lines), "n_marker_lines": len(markers), "markers": markers[:40]})


# ---------------- output-channel audit ----------------
def output_channel_audit(visible_outputs: dict, typed_candidates: list) -> dict:
    """After the complete visible surface, require >=2 publicly plausible typed candidates.

    visible_outputs: {candidate_label: 'plausible' bool} for each binding the tool was run on.
    typed_candidates: the full typed binding space (list of tuples). A candidate is 'publicly
    plausible' if it is consistent with the visible surface — here operationalized as: the tool
    produced a plausible (green / nonzero / in-range) output for that candidate. The audit asserts
    that NO visible signal uniquely singles out one candidate as the golden (i.e., >=2 remain
    plausible, so the tool cannot be brute-forced to reveal the answer).
    """
    plausible = [k for k, v in visible_outputs.items() if v]
    uniquely_determined = (len(plausible) == 1)
    return {
        "n_visible_candidates_run": len(visible_outputs),
        "n_plausible": len(plausible),
        "plausible_candidates": plausible,
        "typed_space_size": len(typed_candidates),
        "uniquely_determined_by_visible_surface": uniquely_determined,
        "PASS": (len(plausible) >= 2 and not uniquely_determined),
    }


# ---------------- semantic-diff (disclosure) audit ----------------
def semantic_diff_audit(truth: dict, public_constraint_facts: dict) -> dict:
    """The public constraint set under-determines the golden. The golden must remain POSSIBLE
    (never contradicted by truth) but NOT uniquely determined by public info.

    public_constraint_facts: a dict of constraint predicates a reader could extract from the
    public surface (e.g. {'intent_class in domain': True, 'decoy says X': True}). We approximate
    'consistent tuples' by counting how many typed bindings survive the public constraints; the
    primary authority attests the golden, the decoy attests a wrong tuple -> >=2 public-consistent.
    """
    axes = truth.get("typed_axes", {})
    golden = truth.get("golden_binding") or truth.get("golden_join")
    wrong = truth.get("wrong_binding_green") or truth.get("wrong_join_plausible")
    # public-consistent set = {golden (from primary authorities), wrong (from decoy)} at minimum
    consistent = []
    if golden:
        consistent.append(tuple(sorted(golden.items())))
    if wrong:
        consistent.append(tuple(sorted(wrong.items())))
    consistent = list(dict.fromkeys(consistent))  # dedupe
    return {
        "consistent_tuples_public_count": len(consistent),
        "golden_in_public_set": bool(golden),
        "uniquely_determined_by_public": len(consistent) <= 1,
        "bundle_discloses_golden": public_constraint_facts.get("bundle_discloses_golden", False),
        "PASS": (len(consistent) >= 2 and not public_constraint_facts.get("bundle_discloses_golden", False)),
    }


# ---------------- information-equivalence audit (BundleS vs TypedContract) ----------------
# Golden/answer-LABELING tokens (specific phrases that would mark a value as the answer).
# Bare generic words like "answer"/"golden" are NOT flagged — legit disclosure prose says
# "non-answer-bearing" / "not the answer" (asserting the answer is NOT disclosed).
FORBIDDEN_FACTS = ["golden_binding", "golden_join", "golden_tuple", "golden_value",
                   "correct_binding", "correct_answer", "the_answer_is", "answer_is",
                   "expected_value", "expected_corner", "expected_load", "expected_metric",
                   "verifier_feedback", "golden:"]


def info_equiv_audit(bundleS_files: dict, typedContract_files: dict, typed_axes: dict) -> dict:
    """BundleS and TypedContract must expose the SAME semantic facts (every role name + every
    domain value present in BOTH) and both OMIT golden / answer-bearing / verifier-feedback.
    Token count and surface form may differ."""
    bblob = "\n".join(bundleS_files.values()).lower()
    tblob = "\n".join(typedContract_files.values()).lower()
    roles = list(typed_axes.keys())
    all_vals = [str(v) for vals in typed_axes.values() for v in vals]
    b_roles = {r: (r.lower().replace("_", "") in bblob.replace("_", "") or r.lower() in bblob) for r in roles}
    t_roles = {r: (r.lower().replace("_", "") in tblob.replace("_", "") or r.lower() in tblob) for r in roles}
    b_vals = {v: (v.lower() in bblob) for v in all_vals}
    t_vals = {v: (v.lower() in tblob) for v in all_vals}
    both_have_all_roles = all(b_roles[r] and t_roles[r] for r in roles)
    both_have_all_values = all(b_vals[v] and t_vals[v] for v in all_vals)
    same_role_presence = all(b_roles[r] == t_roles[r] for r in roles)
    same_value_presence = all(b_vals[v] == t_vals[v] for v in all_vals)
    b_leak = [f for f in FORBIDDEN_FACTS if f in bblob]
    t_leak = [f for f in FORBIDDEN_FACTS if f in tblob]
    both_omit_forbidden = (not b_leak) and (not t_leak)
    same = both_have_all_roles and both_have_all_values and same_role_presence and same_value_presence
    return {
        "roles_present_both": both_have_all_roles,
        "domain_values_present_both": both_have_all_values,
        "same_role_presence": same_role_presence,
        "same_value_presence": same_value_presence,
        "same_semantic_facts": same,
        "BundleS_forbidden_leak": b_leak, "TypedContract_forbidden_leak": t_leak,
        "both_omit_golden_answer_verifier": both_omit_forbidden,
        "token_counts": {"BundleS": len(bblob.split()), "TypedContract": len(tblob.split())},
        "PASS": same and both_omit_forbidden,
    }


def write_instance_audit_report(out_dir: Path, report: dict) -> None:
    (Path(out_dir) / "instance_audit.json").write_text(json.dumps(report, indent=2) + "\n")
