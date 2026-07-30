#!/usr/bin/env python3
"""Phase-4Y Stage-3 pre-run freeze: C2-only (0022) vs C4-only (0023), k=4 each, Qwen streaming.
4 EXACTLY-counterbalanced 2-run blocks (2 C2->C4 + 2 C4->C2); each condition 2x at each position.
Freezes task hashes, membership code, sentinel/retry policy, seeded order, predeclared interpretation.

DRAFT (not run / not committed): executed only AFTER the Stage-3 fairness gate returns ALL_PASS under
block measurement-control. The variants 0022/0023 remain frozen (do not regenerate). Measurement-control
infrastructure (fullpath_check.py, measurement_control.py, phase4y3_fairness.py) is committed separately
(f6a716e, 95aa33c) from this pre-run gate.
"""
import hashlib, json, random, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TRACK = REPO / "tasks/p14_workflow_handoff"
OUT = REPO / "reports/evidence/p14_phase4y3"
SEED = 20260730
GENERALIZED_RULE = ("All code capable of changing primary-sample membership—including validity "
                     "classification, transport-invalid classification, replacement policy, attempt-to-slot "
                     "assignment, and inclusion/exclusion logic—must be implemented, tested, committed, hashed, "
                     "and included in the pre-run manifest before the first paid episode.")
# paid-episode membership code (mirrors Stage-2, with Stage-3 generator/freeze). Fairness block-control
# code (fullpath_check.py, measurement_control.py, phase4y3_fairness.py) gates whether the run STARTS but
# does not change paid-episode membership; it is recorded separately as fairness_control_code below.
MEMBERSHIP_CODE = ["scripts/episode_arbiter.py", "scripts/llm_agent_driver.py", "scripts/chain_executor.py",
                    "scripts/gen_phase4y3.py", "scripts/phase4y3_freeze.py", "scripts/fairness_retry.py",
                    "scripts/pt_health_sentinel.py"]
FAIRNESS_CONTROL_CODE = ["scripts/fullpath_check.py", "scripts/measurement_control.py",
                          "scripts/phase4y3_fairness.py"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    tasks = {"C2": "workflow_handoff_0022", "C4": "workflow_handoff_0023"}
    rng = random.Random(SEED)
    block_templates = [("C2", "C4"), ("C2", "C4"), ("C4", "C2"), ("C4", "C2")]
    rng.shuffle(block_templates)
    assert sum(1 for b in block_templates if b[0] == "C2") == 2 and sum(1 for b in block_templates if b[0] == "C4") == 2
    blocks, flat, frozen_order = [], [], []
    pos_count = {("C2", 0): 0, ("C2", 1): 0, ("C4", 0): 0, ("C4", 1): 0}
    for i, order in enumerate(block_templates, start=1):
        blocks.append({"block_id": f"block{i}", "order": list(order),
                        "type": "C2_first" if order[0] == "C2" else "C4_first"})
        for pos, cond in enumerate(order):
            frozen_order.append(f"block{i}:{cond}")
            pos_count[(cond, pos)] += 1
            flat.append({"block_id": f"block{i}", "position_in_block": pos, "condition": cond,
                         "task_id": tasks[cond], "planned_results_dir": f"/tmp/p4y3_{i}_{cond}_{pos}_a1"})
    assert all(v == 2 for v in pos_count.values()), pos_count  # exact counterbalance
    rand = {"seed": SEED, "seed_name": "phase4y3_seed",
            "method": "random.Random(seed).shuffle over [C2->C4, C2->C4, C4->C2, C4->C2]; exactly 2 of each order; each condition exactly 2x per position (exact counterbalance). Declared and committed BEFORE any data collection.",
            "conditions": tasks, "blocks": blocks, "frozen_execution_order": frozen_order, "flat": flat,
            "position_balance": {f"{c}_pos{p}": n for (c, p), n in pos_count.items()},
            "code_commit_at_freeze_base": head, "rule": "FROZEN; must not change after the first paid result.",
            "counts": {"C2": 4, "C4": 4}}
    (OUT / "randomization_manifest.json").write_text(json.dumps(rand, indent=2) + "\n")

    cfg = {"experiment": "Phase-4Y Stage-3: C2-only/PVT-def (0022) vs C4-only/glossary+refs (0023), k=4 each",
            "model": {"name": "Qwen3.7-Max", "rates_cny_per_M": {"input": 12, "output": 36}},
            "transport": {"streaming": "SSE", "request_inactivity_timeout_sec": 120, "hard_request_deadline_sec": 300,
                           "max_chat_retries": 1, "telemetry": "per-request + transport_summary (terminal_valid vs recovered)"},
            "episode": {"temperature": 0.7, "max_actions": 60, "episode_timeout_sec": 1800, "elicit_confidence": True, "concurrency": 1},
            "tasks": tasks, "primary_sample": "exactly 8 primary valid episodes (4 C2 + 4 C4)",
            "replacement_policy": "arbiter-driven (episode_arbiter + chain_executor); terminal-invalid only; recovered degradation never replaces; same-slot; max 2 then STOP",
            "primary_outcome": "typed_binding_correctness",
            "co_primary_mechanistic_diagnostic": "failure_subtype: axis_binding_failure vs role_conditioned_value_selection_failure",
            "secondary_outcomes": ["artifact_correctness", "evidence_generation", "protocol_completion", "termination",
                                    "actions", "reasoning_tokens", "confidence", "terminal_transport_validity",
                                    "recovered_degradation", "cost"],
            "context_from_stage2": "Stage-2 localized the strongest axis-stabilization signal to the C2+C4 value-schema bundle (C24), not C1. Stage-3 decomposes C24 into its two components to attribute the signal.",
            "excluded": ["C1", "full BundleS", "held-out (both families)", "DeepSeek", "C3/C5/C6/C7", "k_escalation", "non_streaming"],
            "generalized_membership_rule": GENERALIZED_RULE,
            "fairness_control_code_committed_separately": "fullpath_check.py + measurement_control.py + phase4y3_fairness.py (block measurement-control; score-independent; commits f6a716e, 95aa33c). NOT part of this pre-run gate commit.",
            "measurement_control_policy": "Stage-3 fairness ran under block measurement-control (full-path L2 check -> candidate subset -> full-path L2 check); a block is admissible only if both bookends healthy; a valid unexpected score in an admissible block is a HARD fairness fail (no retry); inadmissible blocks are diagnostic-only and rerun unchanged.",
            "pt_health_policy": "b04/PT sentinel runs before the fairness batch (sentinel.json, recorded separately); failure aborts the gate, never changes candidate membership/outcomes. Fairness retry is infra-only (valid wrong score = hard failure).",
            "code_commit_at_freeze_base": head,
            "stop_rule": "After exactly 8 authorized episodes, a report-only commit, stop for review. Do not push."}
    (OUT / "frozen_config.json").write_text(json.dumps(cfg, indent=2) + "\n")

    interp = {"predeclared": "fixed before execution; not changed after any result. Primary typed-binding + co-primary failure subtype; headline = the per-condition table, no unblocked post-hoc significance headline. Decomposes the Stage-2 C24 (C2+C4) signal.",
              "cells": {"c2_stable_c4_weak": "C2 (PVT-def value-schema) is the primary local sufficient route for axis stabilization; next confirm C2 on frozen held-out-2",
                         "c2_weak_c4_stable": "C4 (glossary+refs) is the primary local sufficient route; next confirm C4 on held-out-2",
                         "both_stable": "C2 and C4 each independently sufficient (redundant value-schema routes); review before held-out",
                         "both_weak": "axis stabilization requires the C2+C4 bundle jointly (interaction); do not attribute the Stage-2 C24 signal to C2 or C4 individually",
                         "c2_eliminates_axis_only": "C2 specifically eliminates axis_binding_failure but leaves role-conditioned value-selection failures",
                         "c4_eliminates_axis_only": "C4 specifically eliminates axis_binding_failure but leaves role-conditioned value-selection failures",
                         "substantial_instability": "report recurrence only and return for review"}}
    (OUT / "interpretation_table.json").write_text(json.dumps(interp, indent=2) + "\n")

    mc = {}
    for rel in MEMBERSHIP_CODE:
        p = REPO / rel
        if not p.is_file():
            print(f"FAIL: membership code missing: {rel}"); sys.exit(1)
        mc[rel] = sha(p)
    fc = {}
    for rel in FAIRNESS_CONTROL_CODE:
        p = REPO / rel
        if not p.is_file():
            print(f"FAIL: fairness-control code missing: {rel}"); sys.exit(1)
        fc[rel] = sha(p)
    (OUT / "membership_code_manifest.json").write_text(json.dumps(
        {"rule": GENERALIZED_RULE, "committed_membership_code_sha256": mc,
         "fairness_control_code_sha256": fc,
         "fairness_control_note": "gates run-start admissibility (block measurement-control); committed separately from this pre-run gate",
         "tests": ["tests/test_transport_telemetry.py", "tests/test_episode_arbiter.py", "tests/test_chain_executor.py",
                   "tests/test_fairness_retry.py", "tests/test_pt_health_sentinel.py",
                   "tests/test_fullpath_check.py", "tests/test_measurement_control.py"]}, indent=2) + "\n")

    frozen = {}
    for tid in tasks.values():
        for f in sorted((TRACK / tid).rglob("*")):
            if f.is_file(): frozen[str(f.relative_to(REPO))] = sha(f)
    for name in ("component_classification.json", "disclosure_audit.json", "frozen_config.json",
                 "randomization_manifest.json", "interpretation_table.json", "membership_code_manifest.json"):
        frozen[f"reports/evidence/p14_phase4y3/{name}"] = sha(OUT / name)
    for name in ("fairness/fairness_verdict.json", "fairness/gate_results.json", "fairness/sentinel.json"):
        p = OUT / name
        if p.is_file(): frozen[f"reports/evidence/p14_phase4y3/{name}"] = sha(p)
    (OUT / "prerun_freeze_manifest.json").write_text(json.dumps(
        {"freeze": "Phase-4Y Stage-3 pre-run manifest (frozen BEFORE any paid episode)",
         "code_commit_at_freeze_base": head, "file_hashes": frozen,
         "rule": "FROZEN; must not change after the first paid result."}, indent=2) + "\n")
    print(json.dumps({"ok": True, "frozen_order": frozen_order, "position_balance": rand["position_balance"],
                       "n_hashes": len(frozen)}, indent=2))


if __name__ == "__main__":
    main()
