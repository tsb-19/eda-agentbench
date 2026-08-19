#!/usr/bin/env python3
"""Phase-8A arm-2 COST PROBE — measures ¥/episode for DeepSeek. Reads no score, ever.

The preregistration (docs/phase8a_prereg.md §2.2) makes arm 2's k a function of one measured
quantity:

    remaining = 200 - spent_arm1 - 10        # ¥10 held back for replacements
    r         = ¥/episode, measured by a 6-episode DeepSeek cost probe
                                            # cost only: enters no analysis, spends <¥3
    k2        = largest k in {6, 4, 2} with 12 * 3 * k * r <= remaining
    none fits -> arm 2 is NOT RUN, and is reported as not run

This script measures r and computes k2. It is deliberately incapable of doing anything else: it
never reads total_score, never grades, and prints the k2 arithmetic in full so the decision can be
checked by hand.

Three properties that make it a probe rather than a small arm:

1. Custody goes to phase8a/evidence/cost_probe_arm2/ via PHASE8A_CUSTODY, which is OUTSIDE
   phase8a/evidence/episodes/. That tree's */episode.json glob is the grading and spend glob, so a
   probe written there would enter the analysis as if it were panel data -- the same hazard §5B.3
   addresses for aborted passes.
2. It runs the PILOT instances p15_eval_0001..0003, which §2 already excludes from the primary
   analysis. Even if a probe episode somehow reached the grader it could not become a panel point.
3. A hard ¥3 ceiling, checked after every block. §2.2 says the probe spends <¥3; a stated limit that
   the code does not enforce is not a limit.

The probe's own spend counts against the ¥200 cap like any other paid call -- money paid is money
paid (§5B.3 rule 3) -- so it is reported separately and subtracted in the affordability check.

Usage:
  python3 scripts/phase8a_cost_probe.py [--spent-arm1 122.8175] [--max-probe-cny 3.0] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
P8A = REPO / "phase8a" / "evidence"
# OUTSIDE evidence/episodes/ on purpose. See property 1 in the module docstring.
PROBE_CUSTODY = P8A / "cost_probe_arm2"
PROBE_SCHEDULES = P8A / "probe_blocks"
EXECUTOR = REPO / "scripts" / "chain_executor.py"
EPISODE_RUNNER = REPO / "scripts" / "phase8a_episode_runner.py"
MODELS = "phase8a/models_arm2.json"
TRACK = "p15_sta_handoff"
TOOL_ROOT = "/data1/tongsb/eda-remote-shim/EDA"
MODEL_TAG = "DeepSeek-V4-Pro-TR"
# Pilots, not panel instances. §2 excludes p15_eval_0001..0003 from the primary analysis.
PROBE_INSTANCES = ("p15_eval_0001", "p15_eval_0002")
CONDITIONS = (("Base", "base"), ("BundleS", "bundles"), ("TypedContract", "typedcontract"))
MAX_REPLACEMENTS = 2
MAX_ACTIONS = 60
EPISODE_TIMEOUT = 1800
TEMPERATURE = 0.7
RETRIES = "6"
HOLDBACK = 10.0
CAP = 200.0
N_INSTANCES, N_CONDITIONS = 12, 3


def _probe_spend() -> float:
    """Sum every probe episode's cost. Cost is the only field this script reads."""
    tot = 0.0
    for f in sorted(PROBE_CUSTODY.glob("*/episode.json")):
        try:
            tot += float(json.loads(f.read_text()).get("total_cost") or 0.0)
        except Exception:  # noqa: BLE001
            pass
    return round(tot, 4)


def _probe_episodes() -> int:
    return len(list(PROBE_CUSTODY.glob("*/episode.json")))


def k2_from(rate: float, spent_arm1: float, probe_spend: float = 0.0):
    """The frozen formula, verbatim, plus the §2.3 hard-cap cross-check.

    Returns (k2, remaining, detail). The formula in §2.2 subtracts arm 1 and the ¥10 holdback; it
    does not mention the probe, because when it was written the probe had not been paid for yet. The
    probe's money is nonetheless real, so affordability is checked BOTH ways and the stricter answer
    is the one that binds. Lowering the bar to fit a preferred k is exactly what a preregistration
    exists to prevent.
    """
    remaining = round(CAP - spent_arm1 - HOLDBACK, 4)
    detail = []
    chosen = None
    for k in (6, 4, 2):
        need = N_INSTANCES * N_CONDITIONS * k * rate
        by_formula = need <= remaining
        # total outlay if this k runs: arm 1 + the probe + arm 2, against the hard ¥200 cap
        total = spent_arm1 + probe_spend + need
        by_hard_cap = total <= CAP
        detail.append({"k": k, "episodes": N_INSTANCES * N_CONDITIONS * k,
                       "projected_arm2_cny": round(need, 4),
                       "fits_prereg_formula": by_formula,
                       "projected_total_cny": round(total, 4),
                       "fits_hard_200_cap": by_hard_cap,
                       "affordable": by_formula and by_hard_cap})
        if chosen is None and by_formula and by_hard_cap:
            chosen = k
    return chosen, remaining, detail


def _env(block_file: Path):
    e = dict(os.environ)
    envf = REPO / ".env"
    if envf.is_file():
        for line in envf.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                e.setdefault(k.strip(), v.strip().strip("'\""))
    if not e.get("TR_API_KEY"):
        raise SystemExit("phase8a_cost_probe: TR_API_KEY not provisioned (expected in .env)")
    e["API_KEY"] = e["TR_API_KEY"]
    e.update({
        "EDA_TOOL_ROOT": TOOL_ROOT,
        "B04_HOST": e.get("B04_HOST", "tsb@b04"),
        "EDA_PT_CMD": f"{TOOL_ROOT}/soft2/synopsys/prime/V-2023.12/bin/pt_shell",
        "EDA_HSPICE_CMD": f"{TOOL_ROOT}/soft2/synopsys/hspice/V-2023.12/hspice/bin/hspice",
        "EDA_BENCH_STREAM_RESPONSES": "1",
        "EDA_BENCH_PRESERVE_FINAL_WORKSPACE": "1",
        "EDA_BENCH_LLM_REQUEST_TIMEOUT_SEC": "120",
        "EDA_BENCH_LLM_REQUEST_DEADLINE_SEC": "300",
        "EDA_BENCH_MAX_CHAT_RETRIES": RETRIES,
        "PHASE8A_SCHEDULE": str(block_file),
        "PHASE8A_MODEL_NAME": "deepseek-v4-pro",
        # the whole point: custody outside the grading glob
        "PHASE8A_CUSTODY": str(PROBE_CUSTODY),
    })
    return e


def _probe_block(inst: str):
    """One pilot instance x all three conditions. Equal condition weight, because cost varies BY
    condition (arm 1 block 00: Base ¥1.272, BundleS ¥0.742, TypedContract ¥0.873) and arm 2 will run
    the three in equal proportion. A probe drawn from one condition would misestimate r."""
    return [{"block_id": f"8A_sta:{inst}:{MODEL_TAG}", "position_in_block": i,
             "condition": cond, "task_id": f"{inst}_{suffix}", "track": TRACK,
             "model": MODEL_TAG, "rep": 1, "arm": 2,
             "planned_results_dir": f"/tmp/p8a2probe_{inst}_{cond}_{i}_a1"}
            for i, (cond, suffix) in enumerate(CONDITIONS)]


def main() -> int:
    ap = argparse.ArgumentParser(description="Measure DeepSeek ¥/episode and compute arm 2's k2.")
    ap.add_argument("--spent-arm1", type=float, default=None,
                    help="arm 1 total incl. archived passes; read from the arm-1 report if omitted")
    ap.add_argument("--max-probe-cny", type=float, default=3.0,
                    help="hard ceiling on probe spend (prereg §2.2 says <¥3)")
    ap.add_argument("--dry-run", action="store_true", help="plan and show arithmetic; no model call")
    a = ap.parse_args()

    spent_arm1 = a.spent_arm1
    if spent_arm1 is None:
        rp = REPO / "phase8a" / "reports" / "phase8a_sta_report.json"
        if not rp.is_file():
            raise SystemExit("phase8a_cost_probe: run scripts/phase8a_report.py first, or pass "
                             "--spent-arm1")
        spent_arm1 = float(json.loads(rp.read_text())["spent_cny"])

    manifest = P8A / "prerun_manifest.json"
    if not manifest.is_file():
        raise SystemExit("phase8a_cost_probe: run scripts/phase8a_preflight.py first")

    blocks = [(inst, _probe_block(inst)) for inst in PROBE_INSTANCES]
    n_planned = sum(len(s) for _, s in blocks)
    print(json.dumps({"probe": "arm2_cost_only", "model": MODEL_TAG,
                      "instances": list(PROBE_INSTANCES), "episodes_planned": n_planned,
                      "custody": str(PROBE_CUSTODY.relative_to(REPO)),
                      "spent_arm1_cny": spent_arm1,
                      "probe_ceiling_cny": a.max_probe_cny,
                      "reads_scores": False,
                      "already_probed_episodes": _probe_episodes(),
                      "already_probed_cny": _probe_spend()}, indent=2), flush=True)
    if a.dry_run:
        k2, remaining, detail = k2_from(0.45, spent_arm1)
        print(json.dumps({"illustrative_only_rate": 0.45, "remaining_cny": remaining,
                          "k2": k2, "detail": detail}, indent=2))
        return 0

    PROBE_CUSTODY.mkdir(parents=True, exist_ok=True)
    PROBE_SCHEDULES.mkdir(parents=True, exist_ok=True)
    (REPO / "runs" / "phase8a").mkdir(parents=True, exist_ok=True)

    for i, (inst, slots) in enumerate(blocks):
        before = _probe_spend()
        if before >= a.max_probe_cny:
            print(json.dumps({"stopped": "probe_ceiling", "spent_cny": before}), flush=True)
            break
        bf = PROBE_SCHEDULES / f"arm2_probe_{inst}.json"
        bf.write_text(json.dumps({"schema": "phase8a_probe_block/v1", "arm": 2,
                                  "purpose": "cost measurement only; enters no analysis",
                                  "block_id": slots[0]["block_id"], "episodes": len(slots),
                                  "frozen_execution_order": slots, "flat": slots}, indent=2) + "\n")
        cmd = [sys.executable, str(EXECUTOR),
               "--schedule", str(bf), "--models", str(REPO / MODELS), "--track", TRACK,
               "--runner", str(EPISODE_RUNNER), "--model-name", "deepseek-v4-pro",
               "--results-prefix", str(REPO / "runs" / "phase8a" / "a2probe"),
               "--state", str(P8A / f"run_state_arm2_probe_{inst}.json"),
               "--log", str(REPO / "runs" / "phase8a" / f"chain_a2probe_{inst}.log"),
               "--max-replacements", str(MAX_REPLACEMENTS), "--max-actions", str(MAX_ACTIONS),
               "--timeout", str(EPISODE_TIMEOUT), "--temperature", str(TEMPERATURE),
               "--elicit-confidence", "--integrity-manifest", str(manifest)]
        t0 = time.time()
        print(f"[probe {i + 1}/{len(blocks)}] {inst}: {len(slots)} slots", flush=True)
        rc = subprocess.run(cmd, env=_env(bf), cwd=str(REPO)).returncode
        print(f"[probe {i + 1}/{len(blocks)}] rc={rc} in {round(time.time() - t0)}s "
              f"cumulative ¥{_probe_spend()}", flush=True)
        if rc == 3:
            print(json.dumps({"stopped": "FAILED_INTEGRITY",
                              "note": "canonical tree mutated mid-probe; find the writer first"}),
                  flush=True)
            return 3

    n = _probe_episodes()
    spend = _probe_spend()
    if n == 0:
        print(json.dumps({"result": "NO_PROBE_EPISODES",
                          "note": "no cost measured, so k2 is undefined; arm 2 stays unrun"}),
              indent=2)
        return 1
    rate = round(spend / n, 4)
    k2, remaining, detail = k2_from(rate, spent_arm1, spend)
    out = {"schema": "phase8a_arm2_cost_gate/v1",
           "preregistration": "docs/phase8a_prereg.md §2.2",
           "gate_reads": "cost only -- no score, rate, contrast or any analysis output",
           "probe": {"episodes": n, "spend_cny": spend, "measured_rate_cny_per_episode": rate,
                     "ceiling_cny": a.max_probe_cny,
                     "within_ceiling": spend < a.max_probe_cny,
                     "instances": list(PROBE_INSTANCES),
                     "excluded_from_all_analysis": True},
           "arithmetic": {"cap_cny": CAP, "spent_arm1_cny": spent_arm1,
                          "holdback_cny": HOLDBACK, "remaining_cny": remaining,
                          "formula": "k2 = max k in {6,4,2} with 12*3*k*r <= 200 - spent_arm1 - 10",
                          "candidates": detail},
           "k2": k2,
           "decision": ("RUN arm 2 at k=%d" % k2) if k2 else
                       "DO NOT RUN arm 2 -- no k in {6,4,2} is affordable; report as not run",
           "rate_denomination": ("frozen DeepSeek-V4-Pro rates, input 12 / output 24 CNY per 1M, "
                                 "as recorded in reports/evidence/*/frozen_config.json. This is a "
                                 "comparability unit, NOT the provider's bill -- see §5C.1"),
           }
    dest = REPO / "phase8a" / "reports" / "phase8a_arm2_cost_gate.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
