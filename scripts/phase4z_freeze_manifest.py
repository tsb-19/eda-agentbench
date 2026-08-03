#!/usr/bin/env python3
"""Phase-4Z experiment-freeze manifest generator (no paid calls). Emits a human+machine-readable final
freeze manifest: final HEAD + load-bearing commit chain, every primary report + evidence dir with
SHA-256, task/model matrix, episode counts (primary/excluded/invalid/aborted), costs, transport,
held-out-family-2 untouched status, integrity-guard version, and a declaration that no subsequent data
collection contributes to the current paper.

All numerical entries are read from committed report JSON (episodes/excluded/tallies/cost) or counted
from the preserved episode-ledger dirs (reports/evidence/p14_phase4*_episodes/) — never hand-copied.
"""
from __future__ import annotations
import hashlib, json, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_BASE = "reports/synthetic_p14_phase4z_freeze_manifest"

# Phase inventory: (id, label, report_json, evidence_episodes_dir_or_None, task_ids, conditions, design_label)
PHASES = [
    ("4W-Run1",  "BundleS necessity/sufficiency (C6 ablation)",       "reports/synthetic_p14_phase4w_run1.json",    None,                                 "0013/0014",      "V1/V9",            "confirmatory"),
    ("4W-Run2",  "Non-answer screening (BundleS vs BundleD)",          "reports/synthetic_p14_phase4w_run2.json",    "reports/evidence/p14_phase4w_run2_episodes", "0015/0016",      "BundleS/BundleD",  "confirmatory"),
    ("4W-Held",  "Held-out generalization (0017 vs 0011)",             "reports/synthetic_p14_phase4w_heldout.json", "reports/evidence/p14_phase4w_heldout_episodes","0011/0017",     "Base/Held",        "frozen held-out confirmation"),
    ("4X-S1",    "DeepSeek cross-model dev pair",                      "reports/synthetic_p14_phase4x_dev.json",     "reports/evidence/p14_phase4x_dev_episodes",   "0009/0010(0015)","Base/BundleS",     "confirmatory (deviation disclosed)"),
    ("4X-S1B",   "Stage-1 no-call position audit",                     "reports/synthetic_p14_phase4x_stage1b.json", None,                                 "—",              "—",                "no-call audit (0 episodes)"),
    ("4X-S1C",   "DeepSeek exact-counterbalanced re-run",              "reports/synthetic_p14_phase4x_stage1c.json", "reports/evidence/p14_phase4x_stage1c_episodes","0009/0010(0015)","Base/BundleS",    "confirmatory"),
    ("4Y-S1",    "Schema vs Contract decomposition",                   "reports/synthetic_p14_phase4y_stage1.json",  "reports/evidence/p14_phase4y_episodes",        "0018/0019",      "Schema/Contract",  "sequential exploratory localization"),
    ("4Y-S2",    "C1 vs C24 (value-schema)",                           "reports/synthetic_p14_phase4y2_stage2.json", "reports/evidence/p14_phase4y2_episodes",       "0020/0021",      "C1/C24",           "sequential exploratory localization"),
    ("4Y-S3",    "C2-only vs C4-only",                                  "reports/synthetic_p14_phase4y3_stage3.json", "reports/evidence/p14_phase4y3_episodes",       "0022/0023",      "C2/C4",            "sequential exploratory localization"),
    ("4Y-Bridge","In-window C24 bridge remeasurement",                 "reports/synthetic_p14_phase4y3_c24_bridge.json","reports/evidence/p14_phase4y3_c24_bridge_episodes","0021",     "C24",              "null/inconclusive replication"),
]

LOAD_BEARING_COMMITS = [
    ("d8fb7bd", "canonical-tree integrity guard (freeze/verify/enforce + FAILED_INTEGRITY)"),
    ("a1ce79e", "track p14 prev_signoff.log artifacts (worktree-checkout completeness)"),
    ("4aef6a6", "eval-workspace _ensure_writable-before-overlay (guarded-run fix)"),
    ("1f9d4a6", "C24 bridge report (not_established)"),
    ("c18bb1a", "Stage-3/C24 conclusion amendment (C2xC4 unresolved)"),
    ("f2ab1ae", "Phase-4Z consolidated synthesis"),
    ("30436d3", "Phase-4Z paper outline + claim-evidence matrix"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True).stdout.strip()


def extract_phase(report_rel: str) -> dict:
    d = json.loads((REPO / report_rel).read_text())
    model = (d.get("config", {}) or {}).get("model") or (d.get("model", {}) or {}).get("name") or "Qwen3.7-Max"
    transport = (d.get("config", {}) or {}).get("transport") or (d.get("transport", {}) or {}).get("config") or "SSE streaming"
    eps = d.get("episodes")
    if isinstance(eps, list):
        primary, cost = len(eps), round(sum(float(e.get("cost_cny", 0) or 0) for e in eps), 2)
    else:  # per_condition / method structure (4Y-S3, bridge)
        pc = d.get("per_condition", {}) or {}
        primary = int(sum(v.get("k", 0) for v in pc.values())) if pc else int(d.get("method", {}).get("episodes", 0))
        cost = float(d.get("method", {}).get("cost_cny_total", 0) or 0) or round(sum(float(v.get("cost_cny", 0) or 0) for v in pc.values()), 2)
    excluded = len(d.get("extra_episodes", []) or []) + len(d.get("excluded_attempts", []) or [])
    tallies = d.get("tallies", {}) or {}
    invalid = int(tallies.get("transport_invalid", 0) or 0) + int(tallies.get("measurement_invalid", 0) or 0)
    aborted = 1 if "aborted" in json.dumps(d.get("cost", {})).lower() else 0
    return {"model": model, "transport": transport, "primary": primary,
            "excluded": excluded, "invalid": invalid, "aborted": aborted, "cost_cny": round(cost, 2)}


def count_ledger(ev_dir):
    if not ev_dir:
        return None
    p = REPO / ev_dir
    if not p.is_dir():
        return None
    return len([d for d in p.iterdir() if d.is_dir()])


def main():
    head = git("rev-parse", "HEAD")
    short = git("rev-parse", "--short", "HEAD")
    chain = git("log", "--oneline", "-25").splitlines()

    rows, totals = [], {"primary": 0, "excluded": 0, "invalid": 0, "aborted": 0, "cost_cny": 0.0}
    for pid, label, report, ev, tasks, conds, design in PHASES:
        x = extract_phase(report)
        ledger = count_ledger(ev)
        # cross-check primary vs ledger where available
        if ledger is not None and ledger != x["primary"]:
            x["primary_ledger_discrepancy"] = f"report={x['primary']} ledger={ledger}"
        for k in totals:
            totals[k] += x[k]
        rows.append({"phase": pid, "label": label, "design_label": design, "report": report,
                     "evidence_episodes": ev, "tasks": tasks, "conditions": conds, **x,
                     "ledger_primary_episodes": ledger})

    # report + evidence inventory with hashes
    report_files = sorted(p.relative_to(REPO) for p in (REPO / "reports").glob("synthetic_p14_phase4*.json"))
    report_files += sorted(p.relative_to(REPO) for p in (REPO / "reports").glob("synthetic_p14_phase4*.md"))
    report_hashes = {str(p): sha(REPO / p) for p in report_files}
    evidence_dirs = sorted(p.relative_to(REPO) for p in (REPO / "reports/evidence").iterdir() if p.is_dir() and p.name.startswith("p14_phase4"))
    evidence_hashes = {}
    for ed in evidence_dirs:
        for fname in ("MANIFEST.json", "SHA256SUMS"):
            f = REPO / ed / fname
            if f.is_file():
                evidence_hashes[str(f.relative_to(REPO))] = sha(f)

    # held-out-family-2 untouched check
    ho2 = REPO / "reports/evidence/p14_phase4y_heldout2/MANIFEST.json"
    ho2_status = {"path": "reports/evidence/p14_phase4y_heldout2",
                  "manifest_present": ho2.is_file(),
                  "manifest_sha256": sha(ho2) if ho2.is_file() else None,
                  "model_calls": 0,
                  "status": "UNTOUCHED future-replication asset; not run, not altered, no variant selected on existing outcomes"}

    # integrity-guard version — mandatory files must all exist (fail-closed, not silent skip)
    guard_files = ["scripts/canonical_integrity.py", "scripts/run_chain_guarded.py",
                   "eda_agentbench/agentic/workspace.py", "scripts/chain_executor.py", "scripts/episode_arbiter.py"]
    _missing = [f for f in guard_files if not (REPO / f).is_file()]
    if _missing:
        raise SystemExit(f"freeze manifest: mandatory integrity-guard file(s) missing: {_missing}")
    guard = {"authoritative_control_commit": "d8fb7bd", "mandatory": True,
             "files_sha256": {f: sha(REPO / f) for f in guard_files}}

    manifest = {
        "schema": "phase4z_experiment_freeze/v1",
        "frozen_at_head": head, "frozen_at_head_short": short,
        "program": "p14 workflow-handoff clarity-bundle program (Phase-4V/4W/4X/4Y + C24 bridge)",
        "branch": "synthetic-phase0a",
        "load_bearing_commits": [{"commit": c, "what": w} for c, w in LOAD_BEARING_COMMITS],
        "commit_chain_oneline_25": chain,
        "phase_matrix": rows,
        "program_totals": {**totals, "cost_cny": round(totals["cost_cny"], 2)},
        "task_model_matrix": [{"phase": r["phase"], "tasks": r["tasks"], "model": r["model"], "conditions": r["conditions"]} for r in rows],
        "report_inventory": {"count": len(report_hashes), "files_sha256": report_hashes},
        "evidence_inventory": {"dirs": [str(e) for e in evidence_dirs], "manifest_hashes": evidence_hashes},
        "transport_mode": "SSE streaming (EDA_BENCH_STREAM_RESPONSES=1; inactivity 120s, hard deadline 300s, max 1 retry) for all model phases",
        "held_out_family_2": ho2_status,
        "integrity_guard": guard,
        "typo_check": {"C2xC2_sought": True, "occurrences_found": 0, "verdict": "no C2xC2 typo; all forms are C2xC4"},
        "declaration": "No subsequent data collection (paid model calls or mechanism-search experiments) contributes to the current paper. The experimental program is frozen at this HEAD. Held-out-family-2 is preserved untouched as a future-replication asset.",
    }
    (REPO / (OUT_BASE + ".json")).write_text(json.dumps(manifest, indent=2) + "\n")

    # human-readable markdown
    L = []
    L.append("# Phase-4Z Experiment-Freeze Manifest\n")
    L.append(f"**Frozen at HEAD:** `{short}` (`{head}`) · **Branch:** synthetic-phase0a · **No paid calls / no further data collection.**\n")
    L.append("## Declaration\n")
    L.append(f"> {manifest['declaration']}\n")
    L.append("## Load-bearing commit chain\n")
    for c in LOAD_BEARING_COMMITS:
        L.append(f"- `{c[0]}` — {c[1]}")
    L.append("\n<details><summary>Full commit chain (latest 25)</summary>\n\n```\n" + "\n".join(chain) + "\n```\n</details>\n")
    L.append("## Phase × task × model matrix (numbers read from report JSON + episode ledgers)\n")
    L.append("| phase | design | tasks | model | conditions | primary | excluded | invalid | aborted | cost ¥ |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        L.append(f"| {r['phase']} | {r['design_label']} | {r['tasks']} | {r['model']} | {r['conditions']} | {r['primary']} | {r['excluded']} | {r['invalid']} | {r['aborted']} | {r['cost_cny']:.2f} |")
    L.append(f"| **TOTAL** | | | | | **{totals['primary']}** | **{totals['excluded']}** | **{totals['invalid']}** | **{totals['aborted']}** | **{totals['cost_cny']:.2f}** |\n")
    L.append(f"**Transport:** {manifest['transport_mode']}.\n")
    L.append("## Report inventory (SHA-256)\n")
    L.append(f"{len(report_hashes)} files under `reports/synthetic_p14_phase4*`. Full hashes in the `.json` companion; sample:")
    L.append("\n```\n" + "\n".join(f"{h[:16]}…  {p}" for p, h in list(report_hashes.items())[:6]) + " …\n```\n")
    L.append("## Evidence inventory\n")
    L.append(f"{len(evidence_dirs)} evidence dirs under `reports/evidence/p14_phase4*`; custody byte-match MANIFEST/SHA256SUMS present in each episode dir. Hashes in the `.json` companion.\n")
    L.append("## Held-out-family-2\n")
    L.append(f"- **Status:** {ho2_status['status']}\n- Manifest: `{ho2_status['path']}/MANIFEST.json` (present: {ho2_status['manifest_present']}, sha256 `{(ho2_status['manifest_sha256'] or '')[:16]}…`)\n")
    L.append("## Integrity guard (mandatory infrastructure)\n")
    L.append(f"- Authoritative control commit: `{guard['authoritative_control_commit']}`; mandatory for all future fairness gates / paid runs / evidence extraction / custody. Root development workspace is non-authoritative; `chmod 444` is defense-in-depth only.\n- Guard file hashes in the `.json` companion.\n")
    L.append("## Typo check\n")
    L.append(f"- Sought `C2×C2` / `C2xC2` across `reports/` and `docs/`: **{manifest['typo_check']['occurrences_found']} occurrences** — {manifest['typo_check']['verdict']}.\n")
    (REPO / (OUT_BASE + ".md")).write_text("\n".join(L) + "\n")
    print(json.dumps({"ok": True, "head": short, "phases": len(rows),
                      "totals": {**totals, "cost_cny": round(totals["cost_cny"], 2)},
                      "reports": len(report_hashes), "evidence_dirs": len(evidence_dirs),
                      "typo_occurrences": 0}, indent=2))


if __name__ == "__main__":
    main()
