#!/usr/bin/env python3
"""Phase-5C NO-MODEL execution-path dry-run (validates the full agent->workspace->grade->result
pipeline for p15/p16 WITHOUT any paid Qwen call). A MOCK agent edits the editable config to a
chosen binding; the real two-phase runner then creates the evaluator workspace, runs run_public.sh +
run_hidden.sh on REAL PT/HSPICE (b04), and grades via STAHandoffEvaluator/SPICEHandoffEvaluator.

Must produce: golden-binding mock -> semantic_binding True + high total_score; wrong-binding mock
-> semantic_binding False + lower total_score. If this fails, the paid run MUST NOT proceed.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from eda_agentbench.task.loader import TaskLoader  # noqa: E402
from eda_agentbench.agentic.runner import run_single_agentic  # noqa: E402

os.environ.setdefault("EDA_TOOL_ROOT", "/data1/tongsb/eda-remote-shim/EDA")
os.environ.setdefault("B04_HOST", "tsb@b04")
RUNS = REPO / "runs" / "phase5c_dryrun"


def _mock_agent_cmd(edit_file: str, binding: dict) -> str:
    b = json.dumps(binding)
    return f"python3 -c 'import json; json.dump({b}, open(\"{edit_file}\",\"w\")); print(\"mock agent set\", \"{edit_file}\")'"


def run_one(track, tid, edit_file, truth_name, golden_key, wrong_key):
    task_path = REPO / "tasks" / track / tid
    meta = json.loads((task_path / "metadata.json").read_text())
    truth = json.loads((task_path / "hidden" / truth_name).read_text())
    out = []
    for label, key in (("golden", golden_key), ("wrong", wrong_key)):
        binding = truth[key]
        runs_dir, score, ag = run_single_agentic(task_path, _mock_agent_cmd(edit_file, binding),
                                                 meta, timeout=300, runs_root=RUNS)
        sem = None
        for c in (score.components if score else []):
            if c.name == "semantic_binding":
                sem = c.raw_score
        out.append({"label": label, "total_score": round(score.total_score, 3) if score else None,
                    "semantic_binding": sem, "passed": score.passed if score else None,
                    "timed_out": getattr(ag, "timed_out", None)})
    return out


def main():
    results = {}
    # Family A (STA): p15_eval_0001_bundles
    results["p15_eval_0001_bundles"] = run_one(
        "p15_sta_handoff", "p15_eval_0001_bundles", "exception_config.json",
        "signoff_intent_truth.json", "golden_binding", "wrong_binding_green")
    # Family B (SPICE): p16_eval_0001_bundles
    results["p16_eval_0001_bundles"] = run_one(
        "p16_spice_handoff", "p16_eval_0001_bundles", "meas_config.json",
        "meas_request_truth.json", "golden_join", "wrong_join_plausible")
    print(json.dumps(results, indent=2))
    ok = True
    for tid, eps in results.items():
        g, w = eps[0], eps[1]
        is_spice = tid.startswith("p16")
        if is_spice:
            # SPICE: semantic_binding is a weighted component; golden must be True, wrong False
            golden_correct = (g["semantic_binding"] == 1.0)
            wrong_rejected = (w["semantic_binding"] == 0.0)
        else:
            # STA: semantic_binding is not a weighted component (the 5 provenance/coverage checks are);
            # golden passes all -> total_score 1.0, wrong fails some -> lower. Distinguish by total_score.
            golden_correct = (g["total_score"] == 1.0)
            wrong_rejected = (w["total_score"] is not None and w["total_score"] < g["total_score"])
        print(f"{tid}: golden_sem={g['semantic_binding']} score={g['total_score']} | wrong_sem={w['semantic_binding']} score={w['total_score']} -> {'OK' if (golden_correct and wrong_rejected) else 'FAIL'}")
        ok = ok and golden_correct and wrong_rejected
    print("DRY-RUN PASS (full agent->workspace->grade->result pipeline, real tools, mock agent, no paid call):", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
