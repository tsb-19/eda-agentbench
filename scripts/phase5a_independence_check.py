#!/usr/bin/env python3
"""Phase-5 independence checker — OPERATIONAL structural independence under the five
preregistered criteria (NOT a proof). Also discloses shared generic infrastructure and
the family x tool confound. No model calls.

Five criteria checked (mechanically, fail-closed):
  C1 no p14 grader/generator import in the new generators/graders;
  C2 the new role vocabularies are disjoint from p14's (scenario/corner + PVT);
  C3 the new truth files contain none of p14's axis_schema/semantic_role_mapping/global_authority_tuple keys;
  C4 the new grader modules are distinct (no p14 master EVIDENCE_OK gate pattern);
  C5 the new decoy-recipe classes are distinct (authority-conflict / authority-substitution vs p14's intersection).
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]

P14_VOCAB = {"slow", "typ", "fast", "func", "test", "lowpower",
             "slow_1.0v_125c", "typ_1.0v_25c", "fast_0.8v_0c"}
P14_TRUTH_KEYS = {"axis_schema", "semantic_role_mapping", "global_authority_tuple"}
NEW_SOURCES = [
    "generators/p15_sta_handoff_gen.py", "generators/p15_sta_handoff/grade_sta_handoff.py",
    "generators/p16_spice_handoff_gen.py", "generators/p16_spice_handoff/grade_spice_handoff.py",
]
P14_SIG = ["grade_workflow", "p14_workflow_handoff_gen", "axis_schema", "semantic_role_mapping",
           "global_authority_tuple", "EVIDENCE_OK"]
P14_DECOY_FILES = ["report_a_role_swap", "report_b_role_stale", "report_c_role_pvt", "evidence_d_role_mismatch"]


def _strip_docstrings_and_comments(txt: str) -> str:
    """Remove triple-quoted strings and # comments so docstring MENTIONS of p14 symbols
    don't trip the structural check (we check actual CODE tokens/imports, not prose)."""
    txt = re.sub(r'"""[\s\S]*?"""', ' "" ', txt)
    txt = re.sub(r"'''[\s\S]*?'''", " '' ", txt)
    txt = re.sub(r"^\s*#.*$", "", txt, flags=re.M)
    txt = re.sub(r"(?<!['\"])\#[^\n]*", "", txt)  # inline comments (rough)
    return txt


def _imports(txt: str) -> list:
    lines = []
    for ln in txt.splitlines():
        s = ln.strip()
        if s.startswith("import ") or s.startswith("from "):
            lines.append(s)
    return lines


def _check_c1_no_p14_import() -> tuple[bool, list]:
    findings = []
    for src in NEW_SOURCES:
        txt = (REPO / src).read_text(errors="ignore")
        imps = _imports(txt)
        for sig in ("grade_workflow", "p14_workflow_handoff_gen"):
            if any(sig in line for line in imps):
                findings.append(f"{src}: imports p14 symbol '{sig}'")
    return (not findings), findings


def _check_c2_vocab_disjoint() -> tuple[bool, list]:
    # collect the new typed-axis domains from a generated truth file per family
    findings = []
    for track, tdir_pat in [("p15_sta_handoff", "p15_eval_0001_bundles"),
                            ("p16_spice_handoff", "p16_eval_0001_bundles")]:
        tdir = REPO / "tasks" / track / tdir_pat / "hidden"
        truth = None
        for name in ("signoff_intent_truth.json", "meas_request_truth.json"):
            p = tdir / name
            if p.is_file():
                truth = json.loads(p.read_text()); break
        if not truth:
            findings.append(f"{track}: no truth file"); continue
        vals = set()
        for dom in truth.get("typed_axes", {}).values():
            vals |= {str(v).lower() for v in dom}
        overlap = vals & P14_VOCAB
        if overlap:
            findings.append(f"{track}: vocabulary overlaps p14: {sorted(overlap)}")
    return (not findings), findings


def _check_c3_no_p14_truth_keys() -> tuple[bool, list]:
    findings = []
    for track in ("p15_sta_handoff", "p16_spice_handoff"):
        for tdir in (REPO / "tasks" / track).glob("*_bundles/hidden"):
            for name in ("signoff_intent_truth.json", "meas_request_truth.json"):
                p = tdir / name
                if p.is_file():
                    keys = set(json.loads(p.read_text()).keys())
                    hit = keys & P14_TRUTH_KEYS
                    if hit:
                        findings.append(f"{p}: p14 truth keys present {sorted(hit)}")
    return (not findings), findings


def _check_c4_distinct_grader() -> tuple[bool, list]:
    findings = []
    for src in NEW_SOURCES:
        if "grade_" in src:
            code = _strip_docstrings_and_comments((REPO / src).read_text(errors="ignore"))
            # EVIDENCE_OK as a CODE token (assignment/usage), not a docstring mention
            if re.search(r"\bEVIDENCE_OK\b\s*[=\(]", code) or re.search(r"require_evidence\s*=", code):
                findings.append(f"{src}: uses p14 master EVIDENCE_OK gate pattern in code")
    return (not findings), findings


def _check_c5_distinct_decoy_recipe() -> tuple[bool, list]:
    """Family A uses a provenance-DAG authority-CONFLICT structure (derivation_edges);
    Family B uses authority-SUBSTITUTION (decoy_authorities). Neither generates p14's
    value-swap intersection decoy files (report_A/B/C, evidence_D)."""
    findings = []
    a_truth = json.loads((REPO / "tasks/p15_sta_handoff/p15_eval_0001_bundles/hidden/signoff_intent_truth.json").read_text())
    b_truth = json.loads((REPO / "tasks/p16_spice_handoff/p16_eval_0001_bundles/hidden/meas_request_truth.json").read_text())
    if "derivation_edges" not in a_truth:
        findings.append("Family A: missing provenance-DAG derivation_edges (conflict structure)")
    if "decoy_authorities" not in b_truth:
        findings.append("Family B: missing decoy_authorities (substitution structure)")
    # the two decoy structures must differ
    if set(a_truth.keys()) & {"derivation_edges"} == set(b_truth.keys()) & {"derivation_edges"}:
        findings.append("Family A and B decoy structures not distinct")
    # no p14 value-swap decoy files generated
    for track in ("p15_sta_handoff", "p16_spice_handoff"):
        for tdir in (REPO / "tasks" / track).glob("*/files"):
            names = {p.name.lower() for p in tdir.iterdir()}
            hit = [f for f in P14_DECOY_FILES if any(f in n for n in names)]
            if hit:
                findings.append(f"{track}: generated p14-style decoy files {hit}")
    return (not findings), findings


def main():
    criteria = {
        "C1_no_p14_import": _check_c1_no_p14_import(),
        "C2_vocab_disjoint_from_p14": _check_c2_vocab_disjoint(),
        "C3_no_p14_truth_keys": _check_c3_no_p14_truth_keys(),
        "C4_distinct_grader_no_master_gate": _check_c4_distinct_grader(),
        "C5_distinct_decoy_recipe": _check_c5_distinct_decoy_recipe(),
    }
    verdict = {k: {"pass": v[0], "findings": v[1]} for k, v in criteria.items()}
    allpass = all(v[0] for v in criteria.values())
    report = {
        "schema": "phase5_independence_check/v1",
        "claim": "OPERATIONAL STRUCTURAL INDEPENDENCE under the five preregistered criteria (NOT a proof of independence)",
        "criteria": verdict,
        "all_pass": allpass,
        "shared_infrastructure_disclosed": [
            "PrimeTime shim (forwarder to b04)", "tiny.db / tiny.lib (shared 4-cell single-corner Liberty)",
            "read_db/link_design/read_sdc PT setup", "read_sdc/write_sdc laundering + [apply]-prefix anti-injection",
            "HSPICE shim (forwarder to b04)", ".measure/.lis run+parse pattern",
            "canonical-tree integrity guard, chain_executor, episode_arbiter, freeze/pipeline/launcher, custody",
        ],
        "family_tool_confound": "Family A (STA) runs on PrimeTime; Family B (SPICE) on HSPICE. Family and tool are CONFOUNDED: family-specific differences cannot be attributed to semantic domain vs tool environment. Inference is limited to the within-family, within-model Base-vs-BundleS contrast (tool held constant); cross-family comparison is descriptive only.",
    }
    out = REPO / "reports" / "synthetic_phase5_independence_check.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"all_pass": allpass, "claim": report["claim"]}, indent=2))
    for k, v in verdict.items():
        print(f"  {k}: {'PASS' if v['pass'] else 'FAIL'} {v['findings']}")
    return 0 if allpass else 1


if __name__ == "__main__":
    sys.exit(main())
