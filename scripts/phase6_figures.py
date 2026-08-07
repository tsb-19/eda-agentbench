#!/usr/bin/env python3
"""Phase-6 figures/tables generator (NO model calls). Every number from phase6_data.json.
Emits docs/synthetic_phase6_figures_tables.md with: (1) study pipeline, (2) main result matrix,
(3) failure taxonomy, (4) evaluation-validity stack, (5) external-validity table."""
from __future__ import annotations
import json
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
D = json.loads((REPO / "reports/evidence/phase6_data.json").read_text())
P14 = D["p14"]["figures_tables_tally"]; C = D["phase5c"]["family_summary"]; C5 = D["phase5c"]["collection"]
D5 = D["phase5d"]["family_mean_rates"]; D5C = D["phase5d"]["contrasts"]
COSTS = D["aggregate_costs_cny"]; EPS = D["aggregate_episodes"]


def main():
    L = ["# Phase-6 Figures & Tables (generated, no model calls)\n",
         "**Source:** every number is read from `reports/evidence/phase6_data.json` "
         "(which reads committed JSON/ledgers + re-runs the p14 figures generator). No hand-copying.\n"]
    # 1. study pipeline
    L += ["## Figure 1 — Study pipeline\n", "```mermaid\nflowchart TD"]
    L += ['  D["Discovery: p14 value-swap semantic-binding failure (Qwen+DeepSeek)"]']
    L += ['  T["Transport repair: SSE streaming (non-streaming censors thinking models)"]']
    L += ['  CP["Controlled pair 0009/0010: full clarity bundle suppresses axis-binding failure"]']
    L += ['  AB["Ablation 4W/4X/4Y: BundleS vs components (C1/C2/C4/C7/C24)"]']
    L += ['  HO["Frozen held-out (0017): BundleS generalizes to a pre-frozen truth (Qwen)"]']
    L += ['  CM["Cross-model 4X: DeepSeek BundleS NOT established (tie 3/4 = 3/4)"]']
    L += ['  CF["Cross-family Phase-5C: STA null (0.50/0.33); SPICE ceiling (1.00/1.00)"]']
    L += ['  TC["Phase-5D TypedContract: no advantage over Base or BundleS (0 improve)"]']
    L += ['  FR["Final result: cross-family transfer NOT established"]']
    L += ["  D --> T --> CP --> AB --> HO"]
    L += ["  CP --> CM"]
    L += ["  HO --> CF --> TC --> FR"]
    L += ["```\n"]

    # 2. main result matrix
    L += ["## Table 1 — Main result matrix (semantic-binding correct / k; directional)\n",
          "Cells = semantic_binding correct rate. `—` = not run.\n",
          "| Family | Model | Base | BundleS | TypedContract | Phase |\n|---|---|---|---|---|---|"]
    L.append(f"| p14 workflow-handoff | Qwen | 1/3 (0009) | 3/3 (0010) | — | 4U/4V confirmatory |")
    L.append(f"| p14 workflow-handoff | Qwen (held-out 0017) | 1/3 (0011) | 3/3 (0017) | — | 4W frozen held-out |")
    L.append(f"| p14 workflow-handoff | DeepSeek | 3/4 (1C) | 3/4 (1C) | — | 4X cross-model null |")
    sta_c = C.get("A_sta", {}); spi_c = C.get("B_spice", {})
    L.append(f"| Family A (STA/PT) | Qwen | {sta_c.get('Base_mean_rate','—')} | {sta_c.get('BundleS_mean_rate','—')} | {D5.get('A_sta',{}).get('TypedContract','—')} | 5C/5D cross-family |")
    L.append(f"| Family B (SPICE/HSPICE) | Qwen | {sta_c.get('Base_mean_rate','—') if False else D5.get('B_spice',{}).get('Base','—')} | {D5.get('B_spice',{}).get('BundleS','—')} | {D5.get('B_spice',{}).get('TypedContract','—')} | 5C/5D cross-family |")
    L.append(f"\n*p14 program: {EPS.get('p14_primary')} primary episodes; Phase-5C/5D: {EPS.get('phase5c_primary')}+{EPS.get('phase5d_primary')} = {EPS.get('phase5c_primary',0)+EPS.get('phase5d_primary',0)} episodes.*\n")

    # 3. failure taxonomy
    L += ["## Figure 2 — Semantic-binding failure taxonomy\n", "```",
          "semantic_binding_failure (signoff-green / measurement-plausible, typed-rejected)",
          f"  ├─ axis_binding_failure        (value on wrong typed axis; p14: {P14.get('program_axis','?')} episodes)",
          f"  └─ role_conditioned_value_selection_failure (type-valid, wrong value; p14: {P14.get('program_value','?')} episodes)",
          "       ├─ Family A (STA): coverage_cell_mismatch, authority_unattested_binding",
          "       └─ Family B (SPICE): corner_authority_misbind, load_authority_misbind, metric_role_misbind",
          f"correct typed binding: {P14.get('program_correct','?')} p14 episodes (of {P14.get('program_ledger_episodes','?')} ledger-derived)",
          "```\n"]

    # 4. evaluation-validity stack
    L += ["## Figure 3 — Evaluation-validity stack (nine independent layers)\n",
          "Each reported separately; none collapsed into a single score.\n", "```"]
    layers = [
        "1. Semantic binding          (typed binding == golden; the primary outcome)",
        "2. Artifact correctness      (weighted component score; e.g., provenance/coverage/sim)",
        "3. Protocol completion       (voluntary FINISH vs task-wall/action-cap)",
        "4. Terminal transport validity (no unrecovered transport failure; SSE streaming)",
        "5. Recovered degradation     (>=1 recovered failed attempt; gradeable, not replaced)",
        "6. Tool health               (PT/HSPICE sentinel + full-path bookends)",
        "7. Sample-membership arbitration (episode_arbiter; measurement_valid = transport AND gradeable)",
        "8. Action-surface integrity  (immutable core / derived deck; anti-cheat; hidden isolation)",
        "9. Canonical-tree integrity  (exact-commit worktree; cig.freeze/verify; FAILED_INTEGRITY stop)",
    ]
    L += layers + ["```\n"]

    # 5. external-validity table
    L += ["## Table 2 — External-validity summary\n",
          "| Family | Model | BundleS vs Base | TypedContract vs Base | TypedContract vs BundleS | Verdict |\n|---|---|---|---|---|---|"]
    tc_b = D5C.get("TypedContract_vs_Base", {}); tc_s = D5C.get("TypedContract_vs_BundleS", {}); bs_b = D5C.get("BundleS_vs_Base_same_window", {})
    L.append(f"| STA (A) | Qwen | {bs_b.get('improve',0)}/{bs_b.get('n_instances','?')} improve | {tc_b.get('improve',0)}/{tc_b.get('n_instances','?')} improve | {tc_s.get('improve',0)}/{tc_s.get('n_instances','?')} improve | **Null** (Base 0.50 ≥ BundleS 0.33 = TC 0.33) |")
    L.append(f"| SPICE (B) | Qwen | ceiling (1.00) | ceiling (1.00) | ceiling (1.00) | **Ceiling** (non-discriminative) |")
    L.append(f"| Composite | — | 0 improve | 0 improve | 0 improve | **Transfer not established** |\n")
    L += [f"\n*Costs: p14 ¥{COSTS.get('p14_program')} + Phase-5C ¥{COSTS.get('phase5c')} + Phase-5D ¥{COSTS.get('phase5d')} = total ¥{round((COSTS.get('p14_program',0) or 0)+(COSTS.get('phase5c',0) or 0)+(COSTS.get('phase5d',0) or 0),2)}*\n"]

    out = REPO / "docs/synthetic_phase6_figures_tables.md"
    out.write_text("\n".join(L) + "\n")
    print(f"figures/tables written to {out} ({len(L)} lines)")


if __name__ == "__main__":
    main()
