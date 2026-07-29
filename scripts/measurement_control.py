#!/usr/bin/env python3
"""Score-independent block measurement-control protocol for heavy fairness gates.

Restructures a fairness batch into small measurement blocks of the form:
    full-path check (Level-2) -> fixed candidate subset -> full-path check (Level-2)
A block is ADMISSIBLE only if BOTH surrounding full-path checks are healthy. The admissibility
decision uses ONLY the predeclared control evidence (the full-path reference invariants) and NEVER
inspects any candidate's score.

If either bookend fails:
  - the ENTIRE enclosed block is measurement-invalid;
  - candidate outcomes are NOT selectively discarded (neither bad nor good) -- all are preserved as
    diagnostic evidence and marked measurement_invalid (a 1.0 inside an out-of-control block is invalid
    just as a 0.1/0.2 is -- SYMMETRIC);
  - the block is rerun unchanged in a later healthy b04 window.

If both bookends pass:
  - every candidate result is AUTHORITATIVE;
  - a valid candidate score that differs from the expected fairness result is a HARD FAIRNESS FAIL
    (no retry merely because the score is unfavorable).
"""
from __future__ import annotations
import json, tempfile, shutil
from pathlib import Path
import phase4w_fairness_gate as G
import fairness_retry as FR
import fullpath_check as L2


def grade_candidate_subset(task, tid, candidates, env, runs, max_replacements=2):
    """Grade a fixed candidate subset with the validity-only (infra-only) retry policy. Returns
    {candidate: [attempts...]}. Does NOT inspect expected scores and does NOT retry on unfavorable
    scores (a gradeable wrong score is final -> hard fairness fail at the gate level)."""
    out = {}
    for cand in candidates:
        fc = G.build_candidate_fc(task, cand)
        attempts = []
        a = 0
        while True:
            a += 1
            work = Path(tempfile.mkdtemp(prefix=f"mc_ev_{tid}_{cand}_a{a}_"))
            shutil.copytree(task / "files", work, dirs_exist_ok=True)
            shutil.copytree(task / "hidden", work, dirs_exist_ok=True)
            (work / "flow_config.json").write_text(json.dumps(fc, indent=2) + "\n")
            try:
                G.regen_evidence(work, env, 600)
                sub = Path(tempfile.mkdtemp(prefix=f"mc_sub_{tid}_{cand}_a{a}_"))
                for ef in G.EDITABLE:
                    if (work / ef).exists():
                        shutil.copy2(work / ef, sub / ef)
                res = G._grade_one(task, sub, runs / tid)
            except Exception as e:  # noqa: BLE001
                res = {"ok": False, "total_score": None, "error": f"{type(e).__name__}: {e}"}
            res["submitted"] = {k: fc.get(k) for k in ("netlist", "scenario", "corner")}
            res["candidate"] = cand
            res["attempt"] = a
            attempts.append(res)
            if not FR.should_retry(res, None, a, max_replacements):  # infra-only; valid score -> stop
                break
        out[cand] = attempts
    return out


def run_block(task, tid, candidates, env, runs, max_replacements=2):
    """full-path check -> candidate subset -> full-path check. Returns a block record with
    admissibility decided SOLELY by the two control measurements (score-independent)."""
    before = L2.check(env)
    candidate_attempts = grade_candidate_subset(task, tid, candidates, env, runs, max_replacements)
    after = L2.check(env)
    admissible = bool(before["healthy"] and after["healthy"])
    # mark every candidate outcome by block admissibility (SYMMETRIC: score-independent)
    results = {}
    for cand, attempts in candidate_attempts.items():
        res = attempts[-1]
        res["all_attempts"] = ([{"attempt": x["attempt"], "score": x.get("total_score"),
                                 "error": x.get("error"), "infra_retry": FR.is_measurement_infra_failure(x)}
                                for x in attempts] if len(attempts) > 1 else None)
        res["block_admissible"] = admissible
        res["measurement_valid"] = admissible  # invalid (diagnostic-only) when a bookend failed
        results[cand] = res
    return {"task": tid, "before": before, "after": after, "admissible": admissible,
            "candidates": results,
            "invalid_reason": (None if admissible else
                               ("before-check unhealthy" if not before["healthy"] else "after-check unhealthy"))}


# expected fairness results (for the gate-level HARD-FAIL decision, ONLY applied to ADMISSIBLE blocks)
EXPECTED = {"golden": 1.0, "wrong_axis": 0.2, "stale_decoy": 0.1, "unchanged_mutant": 0.1}


def block_hard_fail(block):
    """For an ADMISSIBLE block, return the list of candidates whose authoritative valid score differs
    from the expected fairness result (a HARD FAIRNESS FAIL -- real, not infrastructure). Returns []
    for inadmissible blocks (their outcomes are diagnostic-only, not authoritative)."""
    if not block["admissible"]:
        return []
    fails = []
    for cand, res in block["candidates"].items():
        if not FR.is_measurement_infra_failure(res) and res.get("total_score") != EXPECTED.get(cand):
            fails.append({"candidate": cand, "score": res.get("total_score"), "expected": EXPECTED.get(cand)})
    return fails
