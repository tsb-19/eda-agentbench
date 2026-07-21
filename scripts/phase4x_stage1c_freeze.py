#!/usr/bin/env python3
"""Phase-4X Stage-1C pre-run freeze: exact-counterbalanced DeepSeek streaming replication.

Design (review-specified): four two-run blocks; exactly two Base->BundleS and exactly two
BundleS->Base; block ordering randomized with a predeclared seed and committed before collection;
Base twice at position 0 and twice at position 1; BundleS likewise; frozen DeepSeek streaming
model-harness configuration; frozen tasks 0009/0015; no held-out, no Qwen, no other variants, no k
escalation, no non-streaming fallback. Exactly eight primary valid episodes.

Generates reports/evidence/p14_phase4x_stage1c/:
  frozen_config.json            — model/harness config + replacement policy + stop rules
  randomization_manifest.json   — seeded block-order permutation (2x BF + 2x SF), flat schedule
  interpretation_table.json     — predeclared 5-cell interpretation + 2x2 analysis plan
  membership_code_manifest.json — sha256 of ALL primary-sample-membership code (generalized rule)
  prerun_freeze_manifest.json   — sha256 of every 0009/0015 task byte + evidence files

Fail-closed: membership code files must exist; design invariants asserted.
"""
import hashlib, json, random, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TRACK = REPO / "tasks/p14_workflow_handoff"
OUT = REPO / "reports/evidence/p14_phase4x_stage1c"
SEED = 20260721

GENERALIZED_RULE = ("All code capable of changing primary-sample membership—including validity "
                     "classification, transport-invalid classification, replacement policy, "
                     "attempt-to-slot assignment, and inclusion/exclusion logic—must be implemented, "
                     "tested, committed, hashed, and included in the pre-run manifest before the first "
                     "paid episode.")

MEMBERSHIP_CODE = ["scripts/episode_arbiter.py", "scripts/llm_agent_driver.py",
                    "scripts/phase4x_stage1c_freeze.py"]

def sha(p: Path) -> str: return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    tasks = {"Base": "workflow_handoff_0009", "BundleS": "workflow_handoff_0015"}

    # ---- randomization: seeded permutation of [BF, BF, SF, SF] block orders ----
    rng = random.Random(SEED)
    block_templates = [("Base", "BundleS"), ("Base", "BundleS"), ("BundleS", "Base"), ("BundleS", "Base")]
    rng.shuffle(block_templates)
    blocks, flat, frozen_order = [], [], []
    pos_count = {("Base", 0): 0, ("Base", 1): 0, ("BundleS", 0): 0, ("BundleS", 1): 0}
    for i, order in enumerate(block_templates, start=1):
        blocks.append({"block_id": f"block{i}", "order": list(order),
                        "type": "Base_first" if order[0] == "Base" else "BundleS_first"})
        for pos, cond in enumerate(order):
            frozen_order.append(f"block{i}:{cond}")
            pos_count[(cond, pos)] += 1
            flat.append({"block_id": f"block{i}", "position_in_block": pos, "condition": cond,
                         "task_id": tasks[cond],
                         "planned_results_dir": f"/tmp/p4x1c_{i}_{cond}_{pos}_a1"})
    # design invariants (fail-closed)
    assert sum(1 for b in blocks if b["type"] == "Base_first") == 2
    assert sum(1 for b in blocks if b["type"] == "BundleS_first") == 2
    assert all(v == 2 for v in pos_count.values()), pos_count
    rand = {
        "seed": SEED, "seed_name": "phase4x_stage1c_seed",
        "method": ("random.Random(seed).shuffle over the fixed multiset of block orders "
                    "[Base->BundleS, Base->BundleS, BundleS->Base, BundleS->Base]; exactly two of each "
                    "order by construction; each condition appears exactly twice at each within-block "
                    "position. Declared and committed BEFORE any data collection."),
        "conditions": tasks, "blocks": blocks, "frozen_execution_order": frozen_order, "flat": flat,
        "position_balance": {f"{c}_pos{p}": n for (c, p), n in pos_count.items()},
        "code_commit_at_freeze_base": head,
        "rule": "FROZEN; must not change after the first paid result.",
        "counts": {"Base": 4, "BundleS": 4},
    }
    (OUT / "randomization_manifest.json").write_text(json.dumps(rand, indent=2) + "\n")

    # ---- frozen config ----
    cfg = {
        "experiment": "Phase-4X Stage 1C: exact-counterbalanced DeepSeek streaming replication (0009 vs 0015)",
        "purpose": "separate a treatment effect from the newly observed within-block position effect; NOT k escalation",
        "model": {"name": "DeepSeek-V4-Pro", "model_id": "DeepSeek-V4-Pro",
                   "endpoint_host": "llmapi.paratera.com", "api_base_env": "BASE_URL",
                   "api_base_suffix": "/v1", "api_key_env": "API_KEY", "max_tokens": 32000,
                   "rates_cny_per_M": {"input": 12, "output": 24}},
        "transport": {"streaming": "SSE (EDA_BENCH_STREAM_RESPONSES=1)",
                       "request_inactivity_timeout_sec": 120, "hard_request_deadline_sec": 300,
                       "max_chat_retries": 1,
                       "request_telemetry": "instrumented driver persists per-request records + episode transport_summary (terminal_transport_valid + recovered_transport_degradation reported independently)"},
        "episode": {"temperature": 0.7, "max_actions": 60, "episode_timeout_sec": 1800,
                     "elicit_confidence": True, "preserve_final_workspace": True, "concurrency": 1},
        "tasks": tasks,
        "grader_scoring": "frozen task bytes (hashes in prerun_freeze_manifest.json); real-PT fairness vectors previously gated ALL_PASS at 5abb5c5; grader unchanged",
        "primary_sample": "exactly eight primary valid episodes (one per slot in the frozen schedule)",
        "replacement_policy": ("Predeclared BEFORE collection. A replacement is permitted ONLY for a "
                                "terminally measurement-invalid episode under the committed arbiter "
                                "(scripts/episode_arbiter.py: measurement_valid = terminal_transport_valid "
                                "AND gradeable). Recovered degradation in an otherwise gradeable episode "
                                "does NOT trigger replacement. A replacement occupies the same predeclared "
                                "condition/block/position slot and does not alter subsequent ordering. The "
                                "FIRST measurement-valid attempt fills the slot. Max 2 replacements per slot "
                                "(3 attempts), then STOP fail-closed. Excluded attempts preserved as "
                                "sanitized operational evidence."),
        "analysis": {"primary_outcome": "typed_binding_correctness",
                      "headline_analysis": "complete 2x2 condition-by-position table (Base@pos0, Base@pos1, BundleS@pos0, BundleS@pos1); block-respecting descriptive reporting",
                      "forbidden": "an unblocked post-hoc significance test as the headline analysis",
                      "per_episode_dims": ["semantic_binding_failure_subtype", "artifact_correctness",
                                            "protocol_completion", "termination", "recovered_failed_attempts",
                                            "recovered_hard_deadlines", "request_latency_summaries",
                                            "reasoning_tokens", "wall_time"]},
        "excluded": ["held-out tasks", "Qwen", "other variants", "k escalation", "non-streaming fallback",
                      "C6", "BundleD", "individual C-ablations", "0011/0017"],
        "generalized_membership_rule": GENERALIZED_RULE,
        "clean_tree_rule": "No paid calls until the instrumentation commit and this freeze commit exist and the working tree is clean; the chain executor asserts a clean tree at launch.",
        "code_commit_at_freeze_base": head,
        "stop_rule": "Execute exactly the eight authorized episodes (plus arbiter-mandated replacements only), produce a separate report-only commit, stop for review. Do not push.",
    }
    (OUT / "frozen_config.json").write_text(json.dumps(cfg, indent=2) + "\n")

    # ---- predeclared interpretation ----
    interp = {
        "predeclared": "fixed before execution; not changed after any result. Primary outcome: typed-binding correctness. Headline = the complete 2x2 condition-by-position table; NO unblocked post-hoc significance test as the headline analysis.",
        "cells": {
            "bundles_improves_no_position_pattern": "support cross-model replication of the BundleS development effect",
            "position_again_predicts_outcomes_across_conditions": "treatment effect remains uninterpretable; prioritize serving/temporal reliability investigation",
            "both_unstable_no_consistent_position_pattern": "report DeepSeek trajectory instability; do not claim for or against BundleS",
            "base_stably_outperforms_bundles": "evidence against model-robust BundleS benefit",
            "both_stably_correct": "streaming baseline saturation; this pair cannot establish BundleS improvement",
        },
        "failure_taxonomy": {"parent": "semantic_binding_failure",
                              "subtypes": ["axis_binding_failure", "role_conditioned_value_selection_failure"],
                              "rule": "tally subtypes separately; never collapse into 'wrong-axis'"},
    }
    (OUT / "interpretation_table.json").write_text(json.dumps(interp, indent=2) + "\n")

    # ---- membership-code manifest (generalized rule) ----
    mc = {}
    for rel in MEMBERSHIP_CODE:
        p = REPO / rel
        if not p.is_file():
            print(f"FAIL: membership code missing: {rel}"); sys.exit(1)
        mc[rel] = sha(p)
    chain = REPO / "runs/p4x1c_chain.sh"
    mc_manifest = {
        "rule": GENERALIZED_RULE,
        "committed_membership_code_sha256": mc,
        "tests": ["tests/test_transport_telemetry.py", "tests/test_episode_arbiter.py"],
        "executor_note": ("runs/p4x1c_chain.sh is a THIN executor: it sequences the frozen schedule and "
                           "OBEYS the committed arbiter's ACCEPT/REPLACE/STOP verdicts; it contains no "
                           "membership logic. Hashed here for transparency (gitignored path):"),
        "executor_sha256": sha(chain) if chain.is_file() else None,
    }
    (OUT / "membership_code_manifest.json").write_text(json.dumps(mc_manifest, indent=2) + "\n")

    # ---- freeze manifest: task bytes + evidence ----
    frozen = {}
    for tid in tasks.values():
        for f in sorted((TRACK / tid).rglob("*")):
            if f.is_file(): frozen[str(f.relative_to(REPO))] = sha(f)
    for name in ("frozen_config.json", "randomization_manifest.json", "interpretation_table.json",
                 "membership_code_manifest.json"):
        frozen[f"reports/evidence/p14_phase4x_stage1c/{name}"] = sha(OUT / name)
    (OUT / "prerun_freeze_manifest.json").write_text(json.dumps({
        "freeze": "Phase-4X Stage-1C pre-run manifest (frozen BEFORE any paid episode)",
        "code_commit_at_freeze_base": head, "file_hashes": frozen,
        "rule": "FROZEN; must not change after the first paid result.",
    }, indent=2) + "\n")
    print(json.dumps({"ok": True, "frozen_order": frozen_order,
                       "position_balance": rand["position_balance"], "n_hashes": len(frozen)}, indent=2))

if __name__ == "__main__":
    main()
