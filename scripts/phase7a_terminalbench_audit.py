#!/usr/bin/env python3
"""Phase-7A Study C — Terminal-Bench 2.1 external protocol audit (ZERO MODEL CALLS).

A retrospective, zero-model-call audit of an INDEPENDENTLY DEVELOPED public
benchmark (Terminal-Bench 2.1) against the four-layer Harness Effect Audit
Protocol. This is an external validation/audit of the protocol, NOT a claim that
our protocol caused or predicted Terminal-Bench's fixes.

The 4-layer + Other rubric is FROZEN HERE before any inspection of the Terminal-Bench
2.0->2.1 modifications. Each of the 26 changed tasks is coded without forcing it
into our taxonomy (an explicit 'Other / not covered' bucket exists).

Terminal-Bench 2.0->2.1 modification data is NOT bundled (web retrieval was
rate-limited during Phase-7A). This script emits the FROZEN rubric + an empty
coding template + the retrieval plan. When the 26 modifications are supplied
(via reports/evidence/phase7c_terminalbench/tb21_modifications.json), re-run to
emit the coded sheet. No model calls at any stage.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "reports" / "evidence" / "phase7c_terminalbench"

# ---------- FROZEN rubric (frozen before inspecting any modification) ----------
RUBRIC = {
    "L1_capability_validity": {
        "definition": "Does the issue concern whether the task measures the intended capability "
                      "(vs a tool-green/shortcut/rubric-correctable wrong answer; semantic correctness; failure taxonomy)?",
        "detect_prevent": "would our protocol's L1 (tool-green alternatives + provenance/authority oracle + failure taxonomy) detect or prevent this?",
    },
    "L2_sampling_validity": {
        "definition": "Does the issue concern sampling (repeated trajectories, blocking/counterbalancing, sample-membership)?",
        "detect_prevent": "would our protocol's L2 (reps + counterbalancing + membership arbiter) detect or prevent this?",
    },
    "L3_execution_validity": {
        "definition": "Does the issue concern execution (transport/timeout, terminal-vs-recovered, tool health, protocol completion)?",
        "detect_prevent": "would our protocol's L3 (streaming transport + terminal-vs-recovered + tool-health bookends + protocol completion) detect or prevent this?",
    },
    "L4_artifact_integrity": {
        "definition": "Does the issue concern artifact integrity (action-surface tampering, reward hacking via file edits, canonical-source integrity)?",
        "detect_prevent": "would our protocol's L4 (action-surface isolation + canonical-hash guard + custody) detect or prevent this?",
    },
    "Other_not_covered": {
        "definition": "The issue lies outside the four layers (e.g., task-content correctness unrelated to evaluation validity, licensing, dataset curation).",
        "detect_prevent": "not covered by our protocol; record explicitly.",
    },
}

# per-task coding record (one per changed task; filled without forcing taxonomy)
CODING_FIELDS = {
    "task_id": "Terminal-Bench task identifier",
    "nature_of_repair": "free-text: what 2.0->2.1 changed (bug / timeout-resource / reward-hacking-robustness / other)",
    "affected_layer": "exactly one of the 5 rubric keys; choose 'Other_not_covered' if it does not fit L1-L4",
    "our_protocol_would_detect_or_prevent": "yes / no / partial (one sentence)",
    "abc_or_protocol_validity_prior_covers": "yes / no / unknown (prior work on benchmark setup / shortcut / reward validity)",
    "outside_our_protocol": "true if affected_layer == Other_not_covered",
    "notes": "optional",
}


def emit_template():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "frozen_rubric.json").write_text(json.dumps({
        "schema": "phase7c_terminalbench_rubric/v1",
        "frozen_before": "inspection of any Terminal-Bench 2.0->2.1 modification",
        "rubric": RUBRIC,
        "coding_fields": CODING_FIELDS,
        "claim_scope": "external audit of our protocol against an independent benchmark; NOT a claim that our protocol caused/predicted Terminal-Bench fixes",
        "n_modifications_expected": 26,
        "retrieval_plan": "obtain the Terminal-Bench 2.0->2.1 changelog (26 tasks modified for bugs/timeout-resource/reward-hacking robustness); "
                          "place at reports/evidence/phase7c_terminalbench/tb21_modifications.json then re-run --code",
        "retrieval_blocked_in_phase7a": "web tools rate-limited (reset 2026-08-14); retrieval deferred",
    }, indent=2) + "\n")
    (OUT / "coding_template.json").write_text(json.dumps({
        "schema": "phase7c_terminalbench_coding/v1", "coded": False,
        "tasks": [{"task_id": f"<tb_task_{i}>", **{k: "" for k in CODING_FIELDS if k != "task_id"}}
                  for i in range(1, 27)]}, indent=2) + "\n")
    print(f"frozen rubric + coding template emitted at {OUT}/")
    print("To code: supply tb21_modifications.json and re-run with --code (still zero model calls).")


def code():
    src = OUT / "tb21_modifications.json"
    if not src.is_file():
        print("tb21_modifications.json not present; emitting template only.", file=sys.stderr)
        emit_template(); return
    mods = json.loads(src.read_text())
    sheet = {"schema": "phase7c_terminalbench_coding/v1", "coded": True,
             "rubric_frozen_at": "before inspection", "tasks": []}
    for m in mods:
        # coder fills these by hand from the frozen rubric (no auto-forcing)
        sheet["tasks"].append({"task_id": m.get("task_id"), "nature_of_repair": m.get("nature"),
                               "affected_layer": "<code: L1|L2|L3|L4|Other_not_covered>",
                               "our_protocol_would_detect_or_prevent": "<yes/no/partial>",
                               "abc_or_protocol_validity_prior_covers": "<yes/no/unknown>",
                               "outside_our_protocol": "<true/false>"})
    (OUT / "coded_sheet.json").write_text(json.dumps(sheet, indent=2) + "\n")
    print(f"coded sheet scaffold emitted at {OUT}/coded_sheet.json (hand-complete per frozen rubric)")


def main():
    if "--code" in sys.argv:
        code()
    else:
        emit_template()


if __name__ == "__main__":
    main()
