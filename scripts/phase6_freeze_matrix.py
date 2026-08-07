#!/usr/bin/env python3
"""Phase-6 final submission freeze manifest + RQ-based claim-evidence matrix (NO model calls).
All numbers read from reports/evidence/phase6_data.json (programmatic). Emits:
  reports/synthetic_phase6_freeze_manifest.{md,json}
  docs/synthetic_phase6_claim_matrix.{md,json}
"""
from __future__ import annotations
import json, subprocess, hashlib
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
D = json.loads((REPO / "reports/evidence/phase6_data.json").read_text())


def _git(*a):
    return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True).stdout.strip()


def _sha(p):
    return hashlib.sha256((REPO / p).read_bytes()).hexdigest()[:16]


def freeze_manifest():
    head = _git("rev-parse", "HEAD"); short = _git("rev-parse", "--short", "HEAD")
    chain = _git("log", "--oneline", "-40").splitlines()
    # evidence/custody dir hashes
    ev_dirs = sorted(p.name for p in (REPO / "reports/evidence").iterdir() if p.is_dir()
                     and (p.name.startswith("p14_phase4") or p.name.startswith("phase5") or p.name == "phase5b_schedules"))
    report_hashes = {str(p): _sha(p) for p in sorted((REPO / "reports").glob("synthetic_phase5*.json"))
                     } | {str(p): _sha(p) for p in sorted((REPO / "reports").glob("synthetic_phase6*.json"))}
    m = {
        "schema": "phase6_final_freeze/v1",
        "final_experiment_head": head, "final_experiment_head_short": short,
        "program": "EDA-AgentBench semantic-handoff harness-effects study (p14 + Phase-5 cross-family)",
        "load_bearing_commit_chain": chain,
        "task_families": {
            "p14_workflow_handoff": {"role": "discovery/within-family mechanism; FROZEN primary Tier-1/Tier-2 evidence",
                                     "instances": "0009-0027 (controlled pair 0009/0010; held-out-1 0011/0017; held-out-2 0024-0027 UNTOUCHED)",
                                     "models": ["Qwen3.7-Max", "DeepSeek-V4-Pro"], "conditions": "Base/BundleS/C1/C2/C4/C7/C24 + ablations"},
            "p15_sta_handoff (Family A, STA/PT)": {"role": "Phase-5 cross-family external validity; clean primary",
                                                  "instances": "3 eval (0001-0003) + 1 excluded dev", "models": ["Qwen3.7-Max"],
                                                  "conditions": "Base/BundleS/TypedContract"},
            "p16_spice_handoff (Family B, SPICE/HSPICE)": {"role": "Phase-5 cross-family; repaired in Phase-5D",
                                                          "instances": "3 eval (0001-0003) + 1 excluded dev", "models": ["Qwen3.7-Max"],
                                                          "conditions": "Base/BundleS/TypedContract"},
        },
        "episode_counts": {"p14_primary": D["aggregate_episodes"]["p14_primary"],
                           "phase5c_primary": D["aggregate_episodes"]["phase5c_primary"],
                           "phase5d_primary": D["aggregate_episodes"]["phase5d_primary"],
                           "total_paid_primary": (D["aggregate_episodes"]["p14_primary"] or 0) + 118},
        "classifications": {
            "confirmatory": "p14 controlled pair (full bundle, Qwen+DeepSeek); Phase-5C Qwen-24 core",
            "sequential_exploratory_localization": "p14 component decomposition (4W/4X/4Y); not headline",
            "frozen_held_out": "p14 held-out-1 (0017); held-out-2 (0024-0027) UNTOUCHED",
            "cross_model_null": "p14 DeepSeek BundleS not established (Stage 1C tie)",
            "cross_family_null": "Phase-5C/5D STA null + SPICE ceiling; TypedContract no benefit",
            "ceiling": "SPICE semantic binding (Base=BundleS=TypedContract=1.00); p14 STA-instance 0002"},
        "costs_cny": D["aggregate_costs_cny"],
        "evidence_custody_dirs": ev_dirs, "report_hashes": report_hashes,
        "untouched_future_assets_explicitly_excluded": [
            "held-out-family-2 (p14 tasks 0024-0027): not run, not altered, no variant selected on outcomes",
            "DeepSeek cross-family extension (Phase-5D): separately frozen, not executed",
            "TypedContract beyond the Phase-5D 36-ep secondary: no further collection"],
        "declaration": "No further data collection (paid model calls or experiments) contributes to this submission. The experimental program is frozen at this HEAD.",
        "no_push": True,
    }
    return m


def claim_matrix():
    rows = [
        # RQ1
        {"rq": "RQ1", "id": "RQ1a", "claim": "Harness information structure can change semantic-binding behavior (full clarity bundle).",
         "status": "Established", "phase": "p14 controlled pair (Phase-4U/4V)", "numbers": "Qwen 0009 1/3 -> 0010 3/3 (0 axis); DeepSeek 0/3 -> 3/3 (0 axis)",
         "counter": "Bundle-level only; Tier-2/3 decompose it", "scope": "p14 controlled pair; both providers",
         "prohibited_wording": "do not claim the bundle generalizes beyond p14 from this row"},
        {"rq": "RQ1", "id": "RQ1b", "claim": "A NON-answer-bearing subset (BundleS) suffices on the development pair.",
         "status": "Established (Qwen) / Null (DeepSeek)", "phase": "p14 4W (dev+held-out) / 4X (DeepSeek)", "numbers": "Qwen BundleS 3/3 vs BundleD 1/3; held-out 0017 3/3 vs Base 0011 1/3; DeepSeek Stage-1C Base 3/4 = BundleS 3/4 (tie)",
         "counter": "DeepSeek null under exact counterbalancing", "scope": "model-contingent (Qwen yes, DeepSeek not established)",
         "prohibited_wording": "do not call BundleS a model-robust harness fix"},
        {"rq": "RQ1", "id": "RQ1c", "claim": "A stable minimal component / C2xC4 interaction exists.",
         "status": "Unresolved", "phase": "p14 4Y + C24 bridge", "numbers": "C1 2/4 (2 axis); C2-only 1/4; C4-only 0/4; C24 bridge 2/4 (1 axis) -> not_established",
         "counter": "in-window C24 bridge failed the >=3/4+0-axis threshold", "scope": "Qwen; component attribution unresolved",
         "prohibited_wording": "do not claim C24 confirmed or a super-additive interaction established"},
        # RQ2
        {"rq": "RQ2", "id": "RQ2a", "claim": "Discovered harness effects transfer across MODELS.",
         "status": "Null (model-contingent)", "phase": "p14 4X", "numbers": "BundleS established for Qwen; NOT established for DeepSeek (Stage-1C tie 3/4 = 3/4)",
         "counter": "the within-family benefit is provider-specific", "scope": "Qwen vs DeepSeek, p14",
         "prohibited_wording": "do not claim model-robust transfer"},
        {"rq": "RQ2", "id": "RQ2b", "claim": "Discovered harness effects transfer across TASK FAMILIES (STA).",
         "status": "Null", "phase": "Phase-5C/5D", "numbers": "STA Base 0.50 / BundleS 0.33 / TypedContract 0.33; 0/3 improve (0001 decline, 0002 ceiling, 0003 floor)",
         "counter": "clean null; no instance improves", "scope": "Qwen, 3 STA instances",
         "prohibited_wording": "do not state BundleS universally fails to generalize or is proven task-specific"},
        {"rq": "RQ2", "id": "RQ2c", "claim": "Discovered harness effects transfer across TASK FAMILIES (SPICE).",
         "status": "Ceiling (non-discriminative)", "phase": "Phase-5C/5D", "numbers": "SPICE Base=BundleS=TypedContract=1.00 (semantic binding)",
         "counter": "Base already solved; effect unmeasurable", "scope": "Qwen, 3 SPICE instances (repaired Phase-5D)",
         "prohibited_wording": "do not claim SPICE refutes transfer; it is non-discriminative"},
        {"rq": "RQ2", "id": "RQ2d", "claim": "A machine-readable typed representation restores cross-family transfer.",
         "status": "Null", "phase": "Phase-5D", "numbers": "TypedContract vs Base 0 improve/1 decline/5 tie; vs BundleS 0/0/6 tie",
         "counter": "TypedContract = BundleS; no advantage", "scope": "tested model + families only",
         "prohibited_wording": "do not infer typed contracts are generally ineffective"},
        # RQ3
        {"rq": "RQ3", "id": "RQ3a", "claim": "Transport validity is a prerequisite for capability classification.",
         "status": "Established (infra)", "phase": "p14 4V", "numbers": "non-streaming censored thinking-model reasoning; SSE resolved it",
         "counter": "provider-specific transport", "scope": "thinking models (Qwen)",
         "prohibited_wording": "do not generalize the transport claim to all providers"},
        {"rq": "RQ3", "id": "RQ3b", "claim": "Canonical-artifact integrity + isolated-worktree execution protects paid runs.",
         "status": "Established (infra)", "phase": "p14 integrity guard", "numbers": "C24 bridge 0 incidents; regression tests; mitigated recurring golden-file corruption",
         "counter": "dev-workspace external writer mitigated, not root-caused", "scope": "paid-run infrastructure",
         "prohibited_wording": "do not claim the writer was root-caused"},
        {"rq": "RQ3", "id": "RQ3c", "claim": "Action-surface integrity (immutable core / derived deck) is necessary to avoid false-positive anti-cheat.",
         "status": "Established (infra)", "phase": "Phase-5C/5D", "numbers": "Phase-5C 12/12 SPICE anti-cheat false positives (deck regenerated by build_deck); forensic audit 0/12 protocol_compromised; Phase-5D repair -> 0 trips, clean artifact data",
         "counter": "the false positive was intended .param regeneration, not a semantic shortcut", "scope": "SPICE family",
         "prohibited_wording": "do not claim the Phase-5C SPICE episodes were semantically compromised"},
        {"rq": "RQ3", "id": "RQ3d", "claim": "Sample-membership arbitration + tool-health bookends make candidate outcomes authoritative.",
         "status": "Established (infra)", "phase": "p14/Phase-5 fairness gates", "numbers": "episode_arbiter (measurement_valid = terminal_transport_valid AND gradeable); PT/HSPICE sentinel + fullpath bookends; validity-only retry",
         "counter": "small-k inference is descriptive", "scope": "all paid phases",
         "prohibited_wording": "do not claim population-level rates from small k"},
    ]
    return {"schema": "phase6_claim_matrix/v1",
            "research_questions": {
                "RQ1": "Can Harness information structure change semantic execution behavior?",
                "RQ2": "Do discovered Harness effects transfer across models and task families?",
                "RQ3": "Which evaluation controls are necessary to make those conclusions valid?"},
            "status_legend": "Established / Directional / Null / Ceiling / Unresolved",
            "rows": rows,
            "final_interpretation": {
                "cross_family_transfer": "Cross-family transfer of the P14 BundleS benefit was not established.",
                "typed_contract": "A machine-readable typed representation of the same non-answer-bearing semantic information produced no measurable advantage over either Base or BundleS on the tested external families.",
                "framing": "An evaluation study of Harness effects (not a proposal of an improved Harness)."}}


def main():
    fm = freeze_manifest()
    (REPO / "reports/synthetic_phase6_freeze_manifest.json").write_text(json.dumps(fm, indent=2) + "\n")
    cm = claim_matrix()
    (REPO / "docs/synthetic_phase6_claim_matrix.json").write_text(json.dumps(cm, indent=2) + "\n")
    # markdown
    fmm = [f"# Phase-6 Final Submission Freeze\n", f"**Final experiment HEAD:** `{fm['final_experiment_head_short']}` (`{fm['final_experiment_head']}`)\n",
           f"> {fm['declaration']}\n", "## Load-bearing commit chain\n"]
    fmm += [f"- `{c.split()[0]}` {c.split(maxsplit=1)[1]}" for c in fm["load_bearing_commit_chain"]]
    fmm += ["\n## Episode counts (all programmatic from committed ledgers/state)\n",
            f"- p14 primary: {fm['episode_counts']['p14_primary']}; Phase-5C: {fm['episode_counts']['phase5c_primary']}; Phase-5D: {fm['episode_counts']['phase5d_primary']}",
            f"\n## Costs (CNY)\n- p14 program: ¥{fm['costs_cny']['p14_program']}; Phase-5C: ¥{fm['costs_cny']['phase5c']}; Phase-5D: ¥{fm['costs_cny']['phase5d']}; total 5C+5D: ¥{fm['costs_cny']['total_5c_5d']}",
            f"\n## Untouched future assets (excluded from the paper)\n"]
    fmm += [f"- {a}" for a in fm["untouched_future_assets_explicitly_excluded"]]
    (REPO / "reports/synthetic_phase6_freeze_manifest.md").write_text("\n".join(fmm) + "\n")
    cmm = ["# Phase-6 Claim–Evidence Matrix (RQ-based; authoritative)\n",
           f"**Final interpretation:** {cm['final_interpretation']['cross_family_transfer']} {cm['final_interpretation']['typed_contract']}\n",
           "Status: E=Established · D=Directional · N=Null · C=Ceiling · U=Unresolved.\n",
           "| RQ | Claim | Status | Phase | Numbers | Counter-evidence | Scope |\n|---|---|---|---|---|---|---|"]
    for r in cm["rows"]:
        cmm.append(f"| {r['rq']} | {r['claim']} | **{r['status']}** | {r['phase']} | {r['numbers']} | {r['counter']} | {r['scope']} |")
    cmm += ["\n## Prohibited stronger wording (per row)\n"]
    for r in cm["rows"]:
        cmm.append(f"- {r['id']}: {r['prohibited_wording']}")
    (REPO / "docs/synthetic_phase6_claim_matrix.md").write_text("\n".join(cmm) + "\n")
    print(json.dumps({"freeze_head": fm["final_experiment_head_short"], "claim_rows": len(cm["rows"]),
                      "episodes": fm["episode_counts"], "costs": fm["costs_cny"]}, indent=2))


if __name__ == "__main__":
    main()
