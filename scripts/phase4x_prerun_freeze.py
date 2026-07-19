#!/usr/bin/env python3
"""Phase-4X Stage 1 pre-run freeze: DeepSeek streaming cross-model confirmation on the frozen
development pair (0009 ambiguous baseline vs 0015 BundleS), k=3 valid episodes each.

Generates reports/evidence/p14_phase4x_dev/:
  preflight.json              — sanitized DeepSeek SSE preflight result (hygiene re-asserted)
  frozen_config.json          — model/endpoint, streaming config, timeouts, deadline, retries,
                                temperature, max actions, grader/scoring provenance, result dirs,
                                valid-episode replacement rule
  randomization_manifest.json — seeded 3-block restricted (balanced) order, one 0009 + one 0015/block
  interpretation_table.json   — predeclared 5-cell interpretation + outcome list + exclusions
  historical_reference.json   — Phase-4U non-streaming DeepSeek episodes: historical reference ONLY
  prerun_freeze_manifest.json — sha256 of every 0009/0015 task byte + gate scripts + evidence files

Fail-closed: preflight must be all-checks-pass; task hashes must match the frozen sources.
"""
import hashlib, json, random, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TRACK = REPO / "tasks/p14_workflow_handoff"
OUT = REPO / "reports/evidence/p14_phase4x_dev"
PREFLIGHT_SRC = Path("/tmp/p4x_preflight_out.json")
SEED = 20260720

def sha(p: Path) -> str: return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # 1. preflight (must be PASS; hygiene re-assert)
    pf = json.loads(PREFLIGHT_SRC.read_text())
    if not pf.get("all_checks_pass"):
        print("FAIL: preflight not all-checks-pass"); sys.exit(1)
    blob = json.dumps(pf)
    for bad in ("reasoning_content", "Bearer", "Authorization"):
        if bad in blob: print(f"FAIL: preflight output contains {bad}"); sys.exit(1)
    (OUT / "preflight.json").write_text(json.dumps(pf, indent=2) + "\n")

    # 2. frozen config
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    cfg = {
        "experiment": "Phase-4X Stage 1: DeepSeek streaming x frozen dev pair (0009 vs 0015)",
        "model": {"name": "DeepSeek-V4-Pro", "model_id": "DeepSeek-V4-Pro",
                   "endpoint_host": pf["endpoint_host"], "api_base_env": "BASE_URL",
                   "api_base_suffix": "/v1", "api_key_env": "API_KEY", "max_tokens": 32000,
                   "rates_cny_per_M": {"input": 12, "output": 24}},
        "transport": {"streaming": "SSE (EDA_BENCH_STREAM_RESPONSES=1)",
                       "request_inactivity_timeout_sec": 120,
                       "hard_request_deadline_sec": 300,
                       "max_chat_retries": 1,
                       "transport_homogeneous_with": "Qwen Phase-4V2/4W runs (identical env + driver args; only the model differs)"},
        "episode": {"temperature": 0.7, "max_actions": 60, "episode_timeout_sec": 1800,
                     "elicit_confidence": True, "preserve_final_workspace": True, "concurrency": 1},
        "tasks": {"Base": "workflow_handoff_0009", "BundleS": "workflow_handoff_0015"},
        "grader_scoring": "frozen task bytes at this commit (hashes in prerun_freeze_manifest.json); real-PT fairness vectors for 0009/0015 previously gated ALL_PASS at 5abb5c5 (golden 1.0 / wrong-axis 0.2 signoff-green evgen-0 / stale 0.1 signoff-red / mutant 0.1); grader unchanged since",
        "result_dirs": "/tmp/p4x_dev_{block}_{cond}_{pos}_a{attempt}/results (attempt starts at 1)",
        "valid_episode_rule": ("k=3 VALID episodes per condition. An episode with transport_valid=false "
                                "(any transport-failure marker / infra abort / runner timeout attributable to "
                                "transport) does NOT count; it is re-run at the same block position and "
                                "condition (attempt+1), max 2 replacements per slot (3 attempts total) — if "
                                "still invalid, STOP the chain and report. Grader-valid episodes count toward "
                                "k regardless of score. ALL attempts (valid and invalid) preserved + reported."),
        "excluded": ["0011/0017 with DeepSeek", "C1/C2/C4/C7 individual ablations", "C6", "BundleD",
                      "Qwen", "k=5", "non-streaming fallback", "DeepSeek held-out pair"],
        "code_commit_at_freeze_base": head,
        "stop_rule": "Stop after six valid development episodes and a report-only commit. Do not push. Held-out DeepSeek (0011 vs 0017) requires a NEW review authorization, only if the development comparison supports the same BundleS direction.",
    }
    (OUT / "frozen_config.json").write_text(json.dumps(cfg, indent=2) + "\n")

    # 3. randomization: seeded, 3 blocks, one 0009 + one 0015 per block, restricted (both orderings appear)
    rng = random.Random(SEED)
    attempt = 0
    while True:
        attempt += 1
        draws = [round(rng.random(), 6) for _ in range(3)]
        firsts = [("BundleS" if d < 0.5 else "Base") for d in draws]
        if len(set(firsts)) == 2:
            break
    blocks, flat, frozen_order = [], [], []
    tasks = {"Base": "workflow_handoff_0009", "BundleS": "workflow_handoff_0015"}
    for i, (draw, first) in enumerate(zip(draws, firsts), start=1):
        order = ["BundleS", "Base"] if first == "BundleS" else ["Base", "BundleS"]
        blocks.append({"block_id": f"block{i}", "order": order, "BundleS_first": first == "BundleS", "draw": draw})
        for pos, cond in enumerate(order):
            frozen_order.append(f"block{i}:{cond}")
            flat.append({"block_id": f"block{i}", "position_in_block": pos, "condition": cond,
                         "task_id": tasks[cond], "planned_results_dir": f"/tmp/p4x_dev_{i}_{cond}_{pos}_a1"})
    rand = {
        "seed": SEED, "seed_name": "phase4x_dev_seed",
        "method": ("RESTRICTED (balanced) randomization: random.Random(seed).random() triples; BundleS first "
                    "iff draw<0.5; accept the FIRST triple containing BOTH orderings. "
                    f"{attempt-1} triple(s) rejected before acceptance. Declared BEFORE commit and any paid call."),
        "rejected_triples": attempt - 1,
        "conditions": tasks, "blocks": blocks, "frozen_execution_order": frozen_order, "flat": flat,
        "code_commit_at_freeze_base": head,
        "rule": "FROZEN; must not change after the first paid result.",
        "counts": {"Base": 3, "BundleS": 3},
    }
    (OUT / "randomization_manifest.json").write_text(json.dumps(rand, indent=2) + "\n")

    # 4. predeclared interpretation
    interp = {
        "predeclared": "fixed before execution; not changed after any result. Primary outcome: typed-binding correctness.",
        "cells": {
            "baseline_recurrent_failures_AND_bundles_stable_correct": "support cross-model replication of the BundleS development effect",
            "both_succeed": "DeepSeek streaming baseline is saturated; no BundleS improvement can be established on this pair",
            "both_fail": "BundleS does not replicate for DeepSeek",
            "baseline_succeeds_bundles_degrades": "evidence against model-robust BundleS benefit",
            "high_within_condition_instability": "report recurrence only",
        },
        "primary_outcome": "typed_binding_correctness",
        "secondary_outcomes": ["semantic_failure_subtype", "artifact_correctness", "signoff",
                                "evidence_generation", "protocol_completion", "termination", "actions",
                                "reasoning_tokens", "confidence", "cost", "retries_and_transport_events"],
        "failure_taxonomy": {"parent": "semantic_binding_failure",
                              "subtypes": ["axis_binding_failure", "role_conditioned_value_selection_failure"],
                              "rule": "tally subtypes separately; never collapse into 'wrong-axis'"},
        "historical_baseline_rule": "Phase-4U non-streaming DeepSeek x 0009/0010 episodes are HISTORICAL REFERENCE ONLY — never the primary baseline for this transport-homogeneous comparison.",
        "next_gate": "Held-out DeepSeek (frozen 0011 vs 0017) only via a NEW review authorization, and only if this development comparison supports the same BundleS direction.",
    }
    (OUT / "interpretation_table.json").write_text(json.dumps(interp, indent=2) + "\n")

    # 5. historical reference
    hist = {
        "reference": "Phase-4U DeepSeek non-streaming episodes (historical only)",
        "cells": {"DeepSeek_0009_nonstream": "0/3 typed-binding (3 wrong-axis: func/typ, func/slow, func/slow)",
                   "DeepSeek_0010_nonstream": "3/3"},
        "transport_caveat": "3 of 6 episodes had late socket_timeout events under the non-streaming transport (gradeable but transport-contaminated); the Phase-4V finding established non-streaming censors thinking models. Hence: reference only, never a primary baseline.",
        "source_report": "reports/synthetic_p14_balanced_controlled_pair.{md,json}",
    }
    (OUT / "historical_reference.json").write_text(json.dumps(hist, indent=2) + "\n")

    # 6. freeze manifest: every 0009/0015 task byte + gate scripts + evidence files
    frozen = {}
    for tid in ("workflow_handoff_0009", "workflow_handoff_0015"):
        for f in sorted((TRACK / tid).rglob("*")):
            if f.is_file(): frozen[str(f.relative_to(REPO))] = sha(f)
    frozen["scripts/phase4x_prerun_freeze.py"] = sha(REPO / "scripts/phase4x_prerun_freeze.py")
    for name in ("preflight.json", "frozen_config.json", "randomization_manifest.json",
                 "interpretation_table.json", "historical_reference.json"):
        frozen[f"reports/evidence/p14_phase4x_dev/{name}"] = sha(OUT / name)
    (OUT / "prerun_freeze_manifest.json").write_text(json.dumps({
        "freeze": "Phase-4X Stage 1 pre-run manifest (frozen BEFORE any paid benchmark episode)",
        "code_commit_at_freeze_base": head,
        "file_hashes": frozen,
        "rule": "FROZEN; must not change after the first paid result.",
    }, indent=2) + "\n")
    print(json.dumps({"ok": True, "frozen_order": frozen_order, "rejected_triples": attempt - 1,
                       "n_hashes": len(frozen)}, indent=2))

if __name__ == "__main__":
    main()
