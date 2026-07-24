#!/usr/bin/env python3
"""Phase-4Y Stage-2 pre-run freeze: C1 (0020) vs C24 (0021), k=4 each, Qwen streaming.
4 EXACTLY-counterbalanced 2-run blocks (2 C1->C24 + 2 C24->C1); each condition 2x at each position.
Freezes task hashes, membership code, sentinel/retry policy, seeded order, predeclared interpretation."""
import hashlib, json, random, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TRACK = REPO / "tasks/p14_workflow_handoff"
OUT = REPO / "reports/evidence/p14_phase4y2"
SEED = 20260724
GENERALIZED_RULE = ("All code capable of changing primary-sample membership—including validity "
                     "classification, transport-invalid classification, replacement policy, attempt-to-slot "
                     "assignment, and inclusion/exclusion logic—must be implemented, tested, committed, hashed, "
                     "and included in the pre-run manifest before the first paid episode.")
MEMBERSHIP_CODE = ["scripts/episode_arbiter.py", "scripts/llm_agent_driver.py", "scripts/chain_executor.py",
                    "scripts/gen_phase4y2.py", "scripts/phase4y2_freeze.py", "scripts/fairness_retry.py",
                    "scripts/pt_health_sentinel.py"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    tasks = {"C1": "workflow_handoff_0020", "C24": "workflow_handoff_0021"}
    rng = random.Random(SEED)
    block_templates = [("C1", "C24"), ("C1", "C24"), ("C24", "C1"), ("C24", "C1")]
    rng.shuffle(block_templates)
    assert sum(1 for b in block_templates if b[0] == "C1") == 2 and sum(1 for b in block_templates if b[0] == "C24") == 2
    blocks, flat, frozen_order = [], [], []
    pos_count = {("C1", 0): 0, ("C1", 1): 0, ("C24", 0): 0, ("C24", 1): 0}
    for i, order in enumerate(block_templates, start=1):
        blocks.append({"block_id": f"block{i}", "order": list(order),
                        "type": "C1_first" if order[0] == "C1" else "C24_first"})
        for pos, cond in enumerate(order):
            frozen_order.append(f"block{i}:{cond}")
            pos_count[(cond, pos)] += 1
            flat.append({"block_id": f"block{i}", "position_in_block": pos, "condition": cond,
                         "task_id": tasks[cond], "planned_results_dir": f"/tmp/p4y2_{i}_{cond}_{pos}_a1"})
    assert all(v == 2 for v in pos_count.values()), pos_count  # exact counterbalance
    rand = {"seed": SEED, "seed_name": "phase4y2_seed",
            "method": "random.Random(seed).shuffle over [C1->C24, C1->C24, C24->C1, C24->C1]; exactly 2 of each order; each condition exactly 2x per position (exact counterbalance). Declared and committed BEFORE any data collection.",
            "conditions": tasks, "blocks": blocks, "frozen_execution_order": frozen_order, "flat": flat,
            "position_balance": {f"{c}_pos{p}": n for (c, p), n in pos_count.items()},
            "code_commit_at_freeze_base": head, "rule": "FROZEN; must not change after the first paid result.",
            "counts": {"C1": 4, "C24": 4}}
    (OUT / "randomization_manifest.json").write_text(json.dumps(rand, indent=2) + "\n")

    cfg = {"experiment": "Phase-4Y Stage-2: C1/Axis-schema (0020) vs C24/Value-schema (0021), k=4 each",
            "model": {"name": "Qwen3.7-Max", "rates_cny_per_M": {"input": 12, "output": 36}},
            "transport": {"streaming": "SSE", "request_inactivity_timeout_sec": 120, "hard_request_deadline_sec": 300,
                           "max_chat_retries": 1, "telemetry": "per-request + transport_summary (terminal_valid vs recovered)"},
            "episode": {"temperature": 0.7, "max_actions": 60, "episode_timeout_sec": 1800, "elicit_confidence": True, "concurrency": 1},
            "tasks": tasks, "primary_sample": "exactly 8 primary valid episodes (4 C1 + 4 C24)",
            "replacement_policy": "arbiter-driven (episode_arbiter + chain_executor); terminal-invalid only; recovered degradation never replaces; same-slot; max 2 then STOP",
            "primary_outcome": "typed_binding_correctness",
            "co_primary_mechanistic_diagnostic": "failure_subtype: axis_binding_failure vs role_conditioned_value_selection_failure",
            "secondary_outcomes": ["artifact_correctness", "evidence_generation", "protocol_completion", "termination",
                                    "actions", "reasoning_tokens", "confidence", "terminal_transport_validity",
                                    "recovered_degradation", "cost"],
            "excluded": ["Contract/C7", "full BundleS", "held-out", "DeepSeek", "C6", "k_escalation", "non_streaming"],
            "generalized_membership_rule": GENERALIZED_RULE,
            "pt_health_policy": "b04/PT sentinel runs before the fairness batch (sentinel.json, recorded separately); failure aborts the gate, never changes candidate membership/outcomes. Fairness retry is infra-only (valid wrong score = hard failure).",
            "code_commit_at_freeze_base": head,
            "stop_rule": "After exactly 8 authorized episodes, a report-only commit, stop for review. Do not push."}
    (OUT / "frozen_config.json").write_text(json.dumps(cfg, indent=2) + "\n")

    interp = {"predeclared": "fixed before execution; not changed after any result. Primary typed-binding + co-primary failure subtype; headline = the per-condition table, no unblocked post-hoc significance headline.",
              "cells": {"c1_stable_c24_weak": "axis-schema (C1) is the primary local sufficient route; next confirm C1 on frozen held-out",
                         "c1_weak_c24_stable": "value-schema (C24) is the primary local sufficient route; next confirm C24 on held-out",
                         "both_stable": "redundant schema routes; review before held-out",
                         "both_weak": "C1 x C2/C4 interaction required; do not attribute Schema to an individual subset",
                         "c1_eliminates_axis_only": "C1 specifically eliminates axis_binding_failure but leaves role-conditioned value-selection failures -> explicit axis schema targets axis binding, not complete value selection",
                         "substantial_instability": "report recurrence only and return for review"}}
    (OUT / "interpretation_table.json").write_text(json.dumps(interp, indent=2) + "\n")

    mc = {}
    for rel in MEMBERSHIP_CODE:
        p = REPO / rel
        if not p.is_file():
            print(f"FAIL: membership code missing: {rel}"); sys.exit(1)
        mc[rel] = sha(p)
    (OUT / "membership_code_manifest.json").write_text(json.dumps(
        {"rule": GENERALIZED_RULE, "committed_membership_code_sha256": mc,
         "tests": ["tests/test_transport_telemetry.py", "tests/test_episode_arbiter.py", "tests/test_chain_executor.py",
                   "tests/test_fairness_retry.py", "tests/test_pt_health_sentinel.py"]}, indent=2) + "\n")

    frozen = {}
    for tid in tasks.values():
        for f in sorted((TRACK / tid).rglob("*")):
            if f.is_file(): frozen[str(f.relative_to(REPO))] = sha(f)
    for name in ("component_classification.json", "disclosure_audit.json", "frozen_config.json",
                 "randomization_manifest.json", "interpretation_table.json", "membership_code_manifest.json"):
        frozen[f"reports/evidence/p14_phase4y2/{name}"] = sha(OUT / name)
    for name in ("fairness/fairness_verdict.json", "fairness/gate_results.json", "fairness/sentinel.json"):
        p = OUT / name
        if p.is_file(): frozen[f"reports/evidence/p14_phase4y2/{name}"] = sha(p)
    (OUT / "prerun_freeze_manifest.json").write_text(json.dumps(
        {"freeze": "Phase-4Y Stage-2 pre-run manifest (frozen BEFORE any paid episode)",
         "code_commit_at_freeze_base": head, "file_hashes": frozen,
         "rule": "FROZEN; must not change after the first paid result."}, indent=2) + "\n")
    print(json.dumps({"ok": True, "frozen_order": frozen_order, "position_balance": rand["position_balance"],
                       "n_hashes": len(frozen)}, indent=2))


if __name__ == "__main__":
    main()
