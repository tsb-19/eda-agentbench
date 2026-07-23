#!/usr/bin/env python3
"""Phase-4Y Stage-1 pre-run freeze: Schema (0018) vs Contract (0019), k=3 each, Qwen streaming.

Freezes: task hashes, membership-code hashes (arbiter + instrumented driver + executor + freeze/gen
scripts per the generalized rule), seeded 3-block-pair randomized order, predeclared 5-cell
interpretation, and the gate verdicts (semantic-diff + disclosure + fairness). No paid calls here.
"""
import hashlib, json, random, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TRACK = REPO / "tasks/p14_workflow_handoff"
OUT = REPO / "reports/evidence/p14_phase4y"
SEED = 20260723
GENERALIZED_RULE = ("All code capable of changing primary-sample membership—including validity "
                     "classification, transport-invalid classification, replacement policy, attempt-to-slot "
                     "assignment, and inclusion/exclusion logic—must be implemented, tested, committed, hashed, "
                     "and included in the pre-run manifest before the first paid episode.")
MEMBERSHIP_CODE = ["scripts/episode_arbiter.py", "scripts/llm_agent_driver.py",
                    "scripts/chain_executor.py", "scripts/gen_phase4y.py", "scripts/phase4y_freeze.py"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    tasks = {"Schema": "workflow_handoff_0018", "Contract": "workflow_handoff_0019"}
    # seeded 3 blocked pairs: each pair one Schema + one Contract; order within pair randomized
    rng = random.Random(SEED)
    blocks, flat, frozen_order = [], [], []
    pos_count = {("Schema", 0): 0, ("Schema", 1): 0, ("Contract", 0): 0, ("Contract", 1): 0}
    for i in range(1, 4):
        schema_first = rng.random() < 0.5
        order = ["Schema", "Contract"] if schema_first else ["Contract", "Schema"]
        blocks.append({"block_id": f"block{i}", "order": order, "Schema_first": schema_first,
                        "draw": round(rng.random() if False else rng.random(), 6)})
        for pos, cond in enumerate(order):
            frozen_order.append(f"block{i}:{cond}")
            pos_count[(cond, pos)] += 1
            flat.append({"block_id": f"block{i}", "position_in_block": pos, "condition": cond,
                         "task_id": tasks[cond],
                         "planned_results_dir": f"/tmp/p4y_{i}_{cond}_{pos}_a1"})
    rand = {"seed": SEED, "seed_name": "phase4y_seed",
            "method": "random.Random(seed).random()<0.5 per block; 3 blocked pairs (one Schema + one Contract each)",
            "conditions": tasks, "blocks": blocks, "frozen_execution_order": frozen_order, "flat": flat,
            "position_balance": {f"{c}_pos{p}": n for (c, p), n in pos_count.items()},
            "code_commit_at_freeze_base": head,
            "rule": "FROZEN; must not change after the first paid result.", "counts": {"Schema": 3, "Contract": 3}}
    (OUT / "randomization_manifest.json").write_text(json.dumps(rand, indent=2) + "\n")

    cfg = {"experiment": "Phase-4Y Stage-1: Schema (C1+C2+C4) vs Contract (C7), from frozen 0009",
            "model": {"name": "Qwen3.7-Max", "model_id": "Qwen3.7-Max", "endpoint_host": "llmapi.paratera.com",
                       "api_base_env": "BASE_URL", "api_base_suffix": "/v1", "api_key_env": "API_KEY",
                       "max_tokens": 32000, "rates_cny_per_M": {"input": 12, "output": 36}},
            "transport": {"streaming": "SSE (EDA_BENCH_STREAM_RESPONSES=1)", "request_inactivity_timeout_sec": 120,
                           "hard_request_deadline_sec": 300, "max_chat_retries": 1,
                           "telemetry": "per-request records + transport_summary (terminal_transport_valid + recovered_transport_degradation)"},
            "episode": {"temperature": 0.7, "max_actions": 60, "episode_timeout_sec": 1800,
                         "elicit_confidence": True, "concurrency": 1},
            "tasks": tasks,
            "primary_sample": "exactly 6 primary valid episodes (3 Schema + 3 Contract)",
            "replacement_policy": "arbiter-driven (scripts/episode_arbiter.py + scripts/chain_executor.py); "
                                   "terminal-invalid only; recovered degradation never replaces; same-slot; "
                                   "ordering unaltered; max 2 replacements then STOP; excluded attempts preserved",
            "primary_outcome": "typed_binding_correctness",
            "secondary_outcomes": ["artifact_completion", "semantic_binding_failure_subtype", "signoff",
                                    "evidence_regeneration", "protocol_completion", "termination", "actions",
                                    "reasoning_tokens", "confidence", "terminal_transport_validity",
                                    "recovered_degradation", "cost"],
            "excluded": ["DeepSeek", "held-out calls", "C6", "BundleD", "individual C1/C2/C4 decomposition",
                          "k=5", "non-streaming fallback"],
            "generalized_membership_rule": GENERALIZED_RULE,
            "clean_tree_rule": "no paid calls until the pre-run freeze commit exists and the tree is clean; "
                                "the executor (chain_executor.py) asserts a clean tree at launch",
            "code_commit_at_freeze_base": head,
            "stop_rule": "After exactly 6 authorized episodes, a separate report-only commit, stop for review. Do not push."}
    (OUT / "frozen_config.json").write_text(json.dumps(cfg, indent=2) + "\n")

    interp = {"predeclared": "fixed before execution; not changed after any result. Primary: typed-binding. Headline = Schema-vs-Contract contrast; no unblocked post-hoc significance test as headline.",
              "cells": {"schema_succeeds_contract_fails": "prioritize decomposition of C1/C2/C4",
                         "schema_fails_contract_succeeds": "C7 is the primary local sufficient route; next test C7 on frozen held-out 0011",
                         "both_succeed": "two redundant non-answer-bearing sufficient routes; test both independently on held-out before further decomposition",
                         "both_fail": "BundleS requires Schema x Contract interaction; do not interpret any individual component as sufficient",
                         "high_instability": "report recurrence only and return for review"},
              "failure_taxonomy": {"parent": "semantic_binding_failure",
                                    "subtypes": ["axis_binding_failure", "role_conditioned_value_selection_failure"]}}
    (OUT / "interpretation_table.json").write_text(json.dumps(interp, indent=2) + "\n")

    # membership-code manifest (generalized rule)
    mc = {}
    for rel in MEMBERSHIP_CODE:
        p = REPO / rel
        if not p.is_file():
            print(f"FAIL: membership code missing: {rel}"); sys.exit(1)
        mc[rel] = sha(p)
    (OUT / "membership_code_manifest.json").write_text(json.dumps(
        {"rule": GENERALIZED_RULE, "committed_membership_code_sha256": mc,
         "tests": ["tests/test_transport_telemetry.py", "tests/test_episode_arbiter.py", "tests/test_chain_executor.py"]},
        indent=2) + "\n")

    # freeze manifest: task bytes + gate evidence
    frozen = {}
    for tid in tasks.values():
        for f in sorted((TRACK / tid).rglob("*")):
            if f.is_file(): frozen[str(f.relative_to(REPO))] = sha(f)
    for name in ("component_classification.json", "disclosure_audit.json", "frozen_config.json",
                 "randomization_manifest.json", "interpretation_table.json", "membership_code_manifest.json"):
        frozen[f"reports/evidence/p14_phase4y/{name}"] = sha(OUT / name)
    for name in ("fairness/fairness_verdict.json", "fairness/gate_results.json"):
        p = OUT / name
        if p.is_file():
            frozen[f"reports/evidence/p14_phase4y/{name}"] = sha(p)
    frozen["_fairness_note"] = ("ALL_PASS on the committed retry-robust gate. b04 PT degrades under the "
                                 "sustained ~60-op full gate, flaking the mid-gate golden cell (0018); the gate retries a "
                                 "non-1.0 golden once (a real variant defect fails every attempt). 0018 golden is "
                                 "independently proven fair by an isolated full-grade (scripts/phase4y_debug_grade.py: 1.0).")
    (OUT / "prerun_freeze_manifest.json").write_text(json.dumps(
        {"freeze": "Phase-4Y Stage-1 pre-run manifest (frozen BEFORE any paid episode)",
         "code_commit_at_freeze_base": head, "file_hashes": frozen,
         "rule": "FROZEN; must not change after the first paid result."}, indent=2) + "\n")
    print(json.dumps({"ok": True, "frozen_order": frozen_order, "position_balance": rand["position_balance"],
                       "n_hashes": len(frozen)}, indent=2))


if __name__ == "__main__":
    main()
