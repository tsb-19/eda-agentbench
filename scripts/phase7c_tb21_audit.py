#!/usr/bin/env python3
"""Phase-7 Study C — Terminal-Bench 2.0->2.1 static audit (NO model calls).

Retrospective application of the PREREGISTERED four-layer-plus-Other audit taxonomy
to the 26 officially documented repairs between Terminal-Bench 2.0 and 2.1 (PR #53
"Terminal-Bench 2.1" in harbor-framework/terminal-bench-2). This is a descriptive
taxonomy application; it does NOT claim our protocol predicted/prevented the repairs
or that TB validates our runtime implementation.

Frozen inputs (acquired + hashed before coding):
  A. 2.0 snapshot: harbor-framework/terminal-bench-2 @main, 89 tasks (tasklist sha256 5c7ed05c).
  B. 2.1 snapshot: harbor-framework/terminal-bench-2-1 @main, 89 tasks (same names; 26 modified).
  C. Manifest: PR #53 body (sha256 c7172fc6) + 57 changed files (file-list sha256 fccf2d61).
The 26 enumerated tasks are the FIXED audit universe (no later maintenance PRs added).
"""
import json
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
D = REPO / "reports" / "evidence" / "phase7c_terminalbench"

# Per the frozen rubric (phase7a_terminalbench_audit.py): L1 capability, L2 sampling,
# L3 execution, L4 artifact integrity, Other. repair_mechanism vocabulary per directive.
# coverage: direct / partial / not_covered -- would our protocol's layer detect/prevent THIS?
REPAIRS = [
 # (task, evidence(verbatim from PR#53 body), validity_threat[list], repair_mechanism[list], coverage, rationale)
 ("adaptive-rejection-sampler", "Update task description to specify the signature of the function the agent needs to implement (test code and oracle solution require a specific signature).",
  ["L1_capability"], ["instruction_clarification"], "partial", "Verifier enforced an unspecified signature (a correct solution could fail) = capability-validity; our L1 (tool-green/provenance) is semantic-handoff-specific, not generic verifier-over-specification."),
 ("build-pmars", "Update task description and test: remove ambiguity in build destination.",
  ["L1_capability"], ["instruction_clarification","verifier_test_tightening"], "partial", "Instruction/test misalignment (build destination) = capability-validity; partial overlap with L1 verifier-correctness."),
 ("caffe-cifar-10", "Increase timeout to accommodate oracle; accept make and cmake builds (test hardcoded make); specify solvers in instructions; add nproc wrapper (container CPU count); increase cpus to 4 and memory to 8GB.",
  ["L3_execution","L1_capability"], ["timeout_change","verifier_test_broadening","instruction_clarification","environment_dependency_repair","resource_increase"], "partial", "Mixed: resource/timeout/nproc = execution validity (L3); instruction/test = capability (L1). Our L3 tool-health/timeout conceptually relates but is PT/HSPICE-specific."),
 ("compile-compcert", "Add nproc wrapper. Workaround given that nproc inside a Docker container returns the host CPU count, not the container's limit.",
  ["L3_execution"], ["environment_dependency_repair"], "partial", "Container resource accounting (CPU) = execution reliability (L3); our L3 is agent-eval tool-health, not container resource caps."),
 ("configure-git-webserver", "Fix oracle solution: Task description promised to handle auth, but tests assumed a specific format (updated tests so it's now as promised).",
  ["L1_capability"], ["oracle_repair","verifier_test_tightening"], "partial", "Oracle/test assumed format not in description = capability-validity (verifier mis-measures); partial L1 overlap."),
 ("extract-moves-from-video", "Replace remote video fetch with local copy in environment. Removes runtime dependency on external video hosting, which users reported as unreliable.",
  ["L3_execution"], ["external_dependency_removal"], "partial", "Unreliable external runtime dependency = execution validity (L3); our L3 tool-health/transport partially relates."),
 ("filter-js-from-html", "Updated task description to mention normalization; Increased memory from 4GB to 8GB (agents that self-verify run Chrome alongside working state).",
  ["L1_capability","L3_execution"], ["instruction_clarification","resource_increase"], "partial", "Instruction (normalization) = L1; memory = L3. Partial overlap on both."),
 ("fix-git", "Delete the installation files after container is setup. Previously, they were left and agents could technically access them to cheat. Update tests with hardcoded md5 file hashes to account for the previous change.",
  ["L4_artifact_integrity"], ["hidden_artifact_removal","verifier_test_tightening"], "direct", "Install files left accessible for cheating = action-surface/reward-hacking threat; our L4 (action-surface isolation + forbidden files + canonical integrity) DIRECTLY addresses this."),
 ("hf-model-inference", "Change the tests to allow using either save_pretrained format or HuggingFace cache format for the model weights.",
  ["L1_capability"], ["verifier_test_broadening"], "partial", "Test over-specified to one format (legitimate solutions failed) = capability-validity; partial L1 overlap."),
 ("install-windows-3.11", "Update task description to explicitly specify that a QEMU monitor socket needs to be created at the path hardcoded in tests; Update tests to use pathlib.Path.is_socket() rather than hardcoded VGA flags.",
  ["L1_capability"], ["instruction_clarification","verifier_test_tightening"], "partial", "Instruction/test misalignment (socket path) = capability-validity; partial L1 overlap."),
 ("make-doom-for-mips", "Fixed oracle.sh: The package index inside the container was stale, so apt returned 404s and clang never installed.",
  ["L3_execution"], ["oracle_repair","environment_dependency_repair"], "partial", "Oracle could not run (stale apt index) = verifier execution reliability (L3); partial overlap."),
 ("mteb-leaderboard", "Add Pillow dependency (mteb==1.38.41 dropped it); Update task description (only models with results for all 28 tasks); Update memory from 4B to 8GB.",
  ["L3_execution","L1_capability"], ["environment_dependency_repair","instruction_clarification","resource_increase"], "partial", "Dependency + resource = L3; instruction = L1. Partial overlap."),
 ("mteb-retrieve", "Pin transformers==4.48.3 (rebuild pulls incompatible transformers 5.x); Update task description to say agents must use the installed mteb package.",
  ["L3_execution","L1_capability"], ["environment_dependency_repair","instruction_clarification"], "partial", "Dependency pin = L3; instruction = L1. Partial overlap."),
 ("polyglot-c-py", "Update tests to replace os.listdir == ['main.c'] with os.path.exists check (allows byproducts of compilation to exist in the target dir, allowed by the description).",
  ["L1_capability"], ["verifier_test_broadening"], "partial", "Test over-specified (rejected legitimate compilation byproducts) = capability-validity; partial L1 overlap."),
 ("polyglot-rust-c", "Update tests to replace os.listdir == ['main.rs'] with os.path.isfile check (allows byproducts of compilation).",
  ["L1_capability"], ["verifier_test_broadening"], "partial", "Test over-specified = capability-validity; partial L1 overlap."),
 ("protein-assembly", "Updated the oracle given that the API the verifier depended on had changed (rcsb.org fasta endpoint).",
  ["L1_capability"], ["oracle_repair"], "partial", "Oracle returned wrong results (external API changed) = capability-validity (verifier mis-measures); our provenance/authority oracle is static, not a live external API -> partial."),
 ("rstan-to-pystan", "Fix oracle: The oracle created Python 3.10 venv at /opt/py310 but then called python3 which resolved to system python (3.13).",
  ["L1_capability"], ["oracle_repair"], "partial", "Oracle used wrong interpreter (wrong results) = capability-validity; partial L1 overlap."),
 ("sam-cell-seg", "Update task description with -- prefixes for argument names (weights_path -> --weights_path); tests need them as required optional arguments.",
  ["L1_capability"], ["instruction_clarification"], "partial", "Instruction/test misalignment (positional vs --optional) = capability-validity; partial L1 overlap."),
 ("torch-tensor-parallelism", "Update task description to clarify RowParallelLinear.forward() receives a pre-scattered input slice; Increase memory from 4GB to 8GB.",
  ["L1_capability","L3_execution"], ["instruction_clarification","resource_increase"], "partial", "Instruction (shape semantics) = L1; memory = L3. Partial overlap."),
 ("torch-pipeline-parallelism", "Increase memory from 4GB to 8GB to avoid failures due to agent and verifier installation overhead.",
  ["L3_execution"], ["resource_increase"], "partial", "Memory cap caused spurious failures = execution validity (L3); partial overlap."),
 ("query-optimize", "Update task description to include 'Do not modify the database file in any way' (agents that touch and revert leave a file logically identical but not bit-identical; test checks SHA256 hash).",
  ["L1_capability"], ["instruction_clarification"], "partial", "Instruction/test misalignment (SHA256 check undisclosed) = capability-validity; partial L1 overlap."),
 ("train-fasttext", "Changed tests to evaluate from Python fasttext.load_model() to CLI fasttext test (more reliable); Made test.sh self-contained (builds fasttext from source to /usr/local/bin; removed dead deps).",
  ["L3_execution","L1_capability"], ["verifier_test_tightening","environment_dependency_repair"], "partial", "Verifier reliability (CLI vs bindings) + self-contained verifier = execution (L3) + capability (L1); partial overlap."),
 ("build-pov-ray", "Removed apt or package pin.",
  ["Other"], ["environment_dependency_repair"], "not_covered", "Package-pin removal is benchmark-environment maintenance; not an evaluation-validity layer our protocol addresses."),
 ("financial-document-processor", "Removed apt or package pin.",
  ["Other"], ["environment_dependency_repair"], "not_covered", "Package-pin removal = environment maintenance; outside our four-layer protocol."),
 ("mcmc-sampling-stan", "Removed apt or package pin.",
  ["Other"], ["environment_dependency_repair"], "not_covered", "Package-pin removal = environment maintenance; outside our four-layer protocol."),
 ("overfull-hbox", "Removed apt or package pin.",
  ["Other"], ["environment_dependency_repair"], "not_covered", "Package-pin removal = environment maintenance; outside our four-layer protocol."),
]


def main():
    rows = []
    for task, evidence, threat, mech, cov, rat in REPAIRS:
        rows.append({"task": task, "exact_source_evidence": evidence,
                     "validity_threat": threat, "repair_mechanism": mech,
                     "coverage": cov, "rationale": rat})
    assert len(rows) == 26, len(rows)
    # aggregates
    from collections import Counter
    cov_dist = Counter(r["coverage"] for r in rows)
    layer_dist = Counter(t for r in rows for t in r["validity_threat"])
    mech_dist = Counter(m for r in rows for m in r["repair_mechanism"])
    multi_layer = [r["task"] for r in rows if len(r["validity_threat"]) > 1]
    ambiguous = [r["task"] for r in rows if r["coverage"] == "not_covered"] + \
                ["protein-assembly (L1 oracle-correctness vs L3 external-API dependency)",
                 "train-fasttext (L3 verifier-reliability vs L1 capability)"]
    audit = {
        "schema": "phase7c_terminalbench_audit/v1",
        "framing": "Retrospective application of a preregistered audit taxonomy to the 26 officially documented repairs between Terminal-Bench 2.0 and 2.1.",
        "disclaimers": ["does NOT claim our protocol predicted the repairs",
                        "does NOT claim it would necessarily have prevented all repairs",
                        "does NOT claim Terminal-Bench validates the full runtime implementation of our protocol"],
        "frozen_inputs": {
            "A_2_0_snapshot": "harbor-framework/terminal-bench-2 @main; 89 tasks; tasklist sha256 5c7ed05c",
            "B_2_1_snapshot": "harbor-framework/terminal-bench-2-1 @main; 89 tasks (same names; 26 content-modified)",
            "C_manifest": "PR #53 'Terminal-Bench 2.1' in harbor-framework/terminal-bench-2; body sha256 c7172fc6; 57 changed files sha256 fccf2d61",
            "audit_universe": "the 26 tasks enumerated in PR #53 (fixed; no later maintenance PRs added)",
        },
        "source_resolution_discrepancy": "An earlier PR #53 inspected in the legacy laude-institute/terminal-bench (= harbor-framework/terminal-bench-1) repo is 'Share envs across instances' (a harness refactor, 0 task files) and is NOT the Study-C manifest; recorded here, not used as data. The authoritative manifest is PR #53 in harbor-framework/terminal-bench-2.",
        "n_repairs": 26,
        "coverage_distribution": dict(cov_dist),
        "validity_threat_layer_distribution": dict(layer_dist),
        "repair_mechanism_distribution": dict(mech_dist),
        "multi_layer_cases": multi_layer,
        "ambiguous_or_disagreement_cases": ambiguous,
        "repairs": rows,
    }
    (D / "audit_26.json").write_text(json.dumps(audit, indent=2) + "\n")
    # markdown
    md = ["# Phase-7 Study C — Terminal-Bench 2.0→2.1 Static Audit (26 officially documented repairs)",
          "",
          "**Framing:** *Retrospective application of a preregistered audit taxonomy to the 26 "
          "officially documented repairs between Terminal-Bench 2.0 and 2.1.*",
          "This does NOT claim our protocol predicted/prevented the repairs, nor that Terminal-Bench "
          "validates our runtime implementation. No model calls.",
          "",
          "## Frozen inputs (acquired + hashed before coding)",
          "- **A. 2.0 snapshot:** `harbor-framework/terminal-bench-2` @main, 89 tasks (tasklist sha256 `5c7ed05c`).",
          "- **B. 2.1 snapshot:** `harbor-framework/terminal-bench-2-1` @main, 89 tasks (same names; 26 content-modified).",
          "- **C. Manifest:** PR #53 'Terminal-Bench 2.1' in `terminal-bench-2` (body sha256 `c7172fc6`; 57 files sha256 `fccf2d61`). Audit universe = the 26 enumerated tasks.",
          "- **Provenance note:** an earlier PR #53 in the legacy `terminal-bench-1` repo ('Share envs across instances') is unrelated; recorded, not used.",
          "",
          "## Coverage distribution",
          f"- **Direct:** {cov_dist.get('direct',0)}  | **Partial:** {cov_dist.get('partial',0)}  | **Not-covered/Other:** {cov_dist.get('not_covered',0)}  (of 26)",
          "",
          "## Validity-threat layer distribution (multi-layer allowed)",
          "\n".join(f"- {k}: {v}" for k, v in sorted(layer_dist.items())),
          "",
          "## Repair-mechanism distribution",
          "\n".join(f"- {k}: {v}" for k, v in sorted(mech_dist.items(), key=lambda x: -x[1])),
          "",
          f"## Multi-layer cases ({len(multi_layer)})", ", ".join(multi_layer) or "none",
          "",
          "## Ambiguous / disagreement cases",
          "\n".join(f"- {a}" for a in ambiguous),
          "",
          "## Primary descriptive result",
          "Our protocol **directly** addresses only the action-surface/cheat repair (`fix-git`, L4). "
          "Most repairs **partially** overlap our layers: instruction/test misalignment and oracle-correctness "
          "map conceptually to capability validity (L1), and resource/timeout/dependency/oracle-execability "
          "map to execution validity (L3) — but our specific controls are EDA semantic-handoff / PT-HSPICE "
          "tool-health oriented, not generic verifier-over-specification or container-resource hygiene. "
          "Four package-pin removals are **not covered** (environment maintenance, outside the four layers). "
          "No repair mapped to sampling validity (L2). This is the honest external-taxonomy-application "
          "outcome: partial conceptual overlap, limited direct coverage — **not** a claim of prediction or prevention.",
          "",
          "## Per-repair coding (26)",
          "| task | validity_threat | repair_mechanism | coverage |",
          "|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['task']} | {', '.join(r['validity_threat'])} | {', '.join(r['repair_mechanism'])} | {r['coverage']} |")
    (REPO / "reports" / "synthetic_phase7c_terminalbench_audit.md").write_text("\n".join(md) + "\n")
    print(json.dumps({"n": 26, "coverage": dict(cov_dist), "layers": dict(layer_dist),
                      "multi_layer": len(multi_layer)}, indent=2))


if __name__ == "__main__":
    main()
