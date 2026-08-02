#!/usr/bin/env python3
"""Phase-4Y C24 bridge pre-run freeze: one in-window C24/0021 k=4 remeasurement under the canonical-tree
integrity guard. Single condition (no counterbalancing); 4 slots of workflow_handoff_0021.

Purpose: Stage-3 compared singleton C2/C4 against a CROSS-RUN C24 result (Stage-2). This bridge
re-measures C24 (0021) in-window to test whether the bundle axis-stabilization pattern replicates
across run windows BEFORE any held-out-family-2 consumption.

Predeclared interpretation (frozen before any paid result):
  - C24 >= 3/4 typed-binding correct with 0/4 axis_binding_failure -> bundle pattern replicated across
    run windows; held-out-family-2 Base vs C24 may be proposed at the next review.
  - C24 <= 2/4, OR any axis_binding_failure recurs -> stable C24 interaction NOT established; do NOT
    consume held-out-family-2.
  - Artifact/protocol completion secondary to typed binding + failure subtype.

Emits the Stage-3-style manifests to reports/evidence/p14_phase4y3_c24_bridge/ PLUS a
canonical_integrity_manifest.json (consumed by chain_executor --integrity-manifest via run_chain_guarded).
"""
import hashlib, json, random, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TRACK = REPO / "tasks/p14_workflow_handoff"
OUT = REPO / "reports/evidence/p14_phase4y3_c24_bridge"
SEED = 20260801
GENERALIZED_RULE = ("All code capable of changing primary-sample membership—including validity "
                     "classification, transport-invalid classification, replacement policy, attempt-to-slot "
                     "assignment, and inclusion/exclusion logic—must be implemented, tested, committed, hashed, "
                     "and included in the pre-run manifest before the first paid episode.")
MEMBERSHIP_CODE = ["scripts/episode_arbiter.py", "scripts/llm_agent_driver.py", "scripts/chain_executor.py",
                    "scripts/run_agentic_baseline.py", "scripts/canonical_integrity.py",
                    "scripts/run_chain_guarded.py", "scripts/phase4y3_c24_bridge_freeze.py",
                    "scripts/fairness_retry.py", "scripts/pt_health_sentinel.py"]
FAIRNESS_CONTROL_CODE = ["scripts/fullpath_check.py", "scripts/measurement_control.py",
                          "scripts/phase4y3_fairness.py"]
GENERATOR_CODE = ["scripts/gen_phase4y2.py"]  # generated 0021 (C24 = 0009 + C2 + C4)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    tasks = {"C24": "workflow_handoff_0021"}
    # single condition, k=4: 4 slots, no counterbalancing
    blocks, flat, frozen_order = [], [], []
    for i in range(1, 5):
        blocks.append({"block_id": f"block{i}", "order": ["C24"], "type": "C24"})
        frozen_order.append(f"block{i}:C24")
        flat.append({"block_id": f"block{i}", "position_in_block": 0, "condition": "C24",
                     "task_id": tasks["C24"], "planned_results_dir": f"/tmp/p4y3c24_{i}_C24_0_a1"})
    rand = {"seed": SEED, "seed_name": "phase4y3_c24_bridge_seed",
            "method": "single condition C24/0021, k=4 (4 slots, no counterbalancing). Declared and committed BEFORE any data collection.",
            "conditions": tasks, "blocks": blocks, "frozen_execution_order": frozen_order, "flat": flat,
            "code_commit_at_freeze_base": head, "rule": "FROZEN; must not change after the first paid result.",
            "counts": {"C24": 4}}
    (OUT / "randomization_manifest.json").write_text(json.dumps(rand, indent=2) + "\n")

    cfg = {"experiment": "Phase-4Y C24 bridge: in-window C24/0021 k=4 remeasurement (under canonical-tree integrity guard)",
            "model": {"name": "Qwen3.7-Max", "rates_cny_per_M": {"input": 12, "output": 36}},
            "transport": {"streaming": "SSE", "request_inactivity_timeout_sec": 120, "hard_request_deadline_sec": 300,
                           "max_chat_retries": 1, "telemetry": "per-request + transport_summary (terminal_valid vs recovered)"},
            "episode": {"temperature": 0.7, "max_actions": 60, "episode_timeout_sec": 1800, "elicit_confidence": True, "concurrency": 1},
            "tasks": tasks, "primary_sample": "exactly 4 primary valid C24 episodes",
            "replacement_policy": "arbiter-driven (episode_arbiter + chain_executor); terminal-invalid only; recovered degradation never replaces; same-slot; max 2 then STOP",
            "integrity": "canonical-tree guard: run inside an exact-commit isolated git worktree; canonical task dirs non-writable; hashes verified pre-run, after every episode, post-chain; any mutation -> FAILED_INTEGRITY (exit 3), stop, no restore",
            "primary_outcome": "typed_binding_correctness",
            "co_primary_mechanistic_diagnostic": "failure_subtype: axis_binding_failure vs role_conditioned_value_selection_failure",
            "secondary_outcomes": ["artifact_correctness", "evidence_generation", "protocol_completion", "termination",
                                    "actions", "reasoning_tokens", "confidence", "terminal_transport_validity",
                                    "recovered_degradation", "cost"],
            "context_from_stage3": "Stage-3 found neither C2-only (1/4) nor C4-only (0/4) reproduced the C24 axis-stabilization pattern (candidate C2xC4 interaction, cross-stage directional). This bridge tests whether C24 itself replicates in-window (Stage-2's C24 3/4 + 0 axis was cross-run).",
            "excluded": ["C2", "C4", "C1", "full BundleS components other than 0021", "held-out (both families)", "DeepSeek", "C3/C5/C6/C7", "k_escalation", "non_streaming"],
            "generalized_membership_rule": GENERALIZED_RULE,
            "pt_health_policy": "b04/PT sentinel + Level-2 full-path check run before the gate (recorded separately); failure aborts, never changes membership. Fairness retry is infra-only (valid wrong score = hard failure).",
            "code_commit_at_freeze_base": head,
            "stop_rule": "After exactly 4 authorized episodes, a report-only commit, stop for review. Do not push."}
    (OUT / "frozen_config.json").write_text(json.dumps(cfg, indent=2) + "\n")

    interp = {"predeclared": "fixed before execution; not changed after any result. Primary typed-binding + co-primary failure subtype; headline = the C24 in-window result, no unblocked post-hoc significance.",
              "cells": {"replicated": "C24 >= 3/4 typed-binding correct with 0/4 axis_binding_failure -> bundle pattern replicated across run windows; held-out-family-2 Base vs C24 may be proposed at the next review",
                         "not_established": "C24 <= 2/4 correct, OR any axis_binding_failure recurs -> stable C24 interaction NOT established; do NOT consume held-out-family-2",
                         "artifact_protocol_secondary": "artifact completion and protocol completion remain secondary to typed binding and failure subtype"}}
    (OUT / "interpretation_table.json").write_text(json.dumps(interp, indent=2) + "\n")

    mc, fc = {}, {}
    for rel in MEMBERSHIP_CODE:
        p = REPO / rel
        if not p.is_file():
            print(f"FAIL: membership code missing: {rel}"); sys.exit(1)
        mc[rel] = sha(p)
    for rel in FAIRNESS_CONTROL_CODE + GENERATOR_CODE:
        p = REPO / rel
        if not p.is_file():
            print(f"FAIL: fairness/generator code missing: {rel}"); sys.exit(1)
        fc[rel] = sha(p)
    (OUT / "membership_code_manifest.json").write_text(json.dumps(
        {"rule": GENERALIZED_RULE, "committed_membership_code_sha256": mc,
         "fairness_generator_control_code_sha256": fc,
         "tests": ["tests/test_transport_telemetry.py", "tests/test_episode_arbiter.py", "tests/test_chain_executor.py",
                   "tests/test_fairness_retry.py", "tests/test_pt_health_sentinel.py",
                   "tests/test_fullpath_check.py", "tests/test_measurement_control.py",
                   "tests/test_canonical_integrity.py"]}, indent=2) + "\n")

    # canonical-tree integrity manifest (consumed by chain_executor --integrity-manifest)
    sys.path.insert(0, str(REPO / "scripts"))
    import canonical_integrity as cig  # noqa: E402
    evidence = [f"reports/evidence/p14_phase4y3_c24_bridge/{n}" for n in
                ("frozen_config.json", "randomization_manifest.json", "interpretation_table.json",
                 "membership_code_manifest.json")]
    ci = cig.freeze(REPO,
                    task_roots=[f"tasks/p14_workflow_handoff/{tasks['C24']}"],
                    code_files=MEMBERSHIP_CODE + FAIRNESS_CONTROL_CODE + GENERATOR_CODE,
                    evidence_files=evidence)
    (OUT / "canonical_integrity_manifest.json").write_text(json.dumps(ci, indent=2) + "\n")

    # pre-run freeze manifest (hashes of tasks + all manifests incl the integrity manifest)
    frozen = {}
    for tid in tasks.values():
        for f in sorted((TRACK / tid).rglob("*")):
            if f.is_file():
                frozen[str(f.relative_to(REPO))] = sha(f)
    for name in ("frozen_config.json", "randomization_manifest.json", "interpretation_table.json",
                 "membership_code_manifest.json", "canonical_integrity_manifest.json"):
        frozen[f"reports/evidence/p14_phase4y3_c24_bridge/{name}"] = sha(OUT / name)
    (OUT / "prerun_freeze_manifest.json").write_text(json.dumps(
        {"freeze": "Phase-4Y C24 bridge pre-run manifest (frozen BEFORE any paid episode)",
         "code_commit_at_freeze_base": head, "file_hashes": frozen,
         "rule": "FROZEN; must not change after the first paid result."}, indent=2) + "\n")
    print(json.dumps({"ok": True, "frozen_order": frozen_order,
                       "integrity_head": ci["head"][:12], "integrity_task_files": len(ci["task_hashes"]),
                       "n_hashes": len(frozen)}, indent=2))


if __name__ == "__main__":
    main()
