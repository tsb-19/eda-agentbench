#!/usr/bin/env python3
"""Phase-6 data extractor (NO model calls). Single programmatic source of truth for the
manuscript/figures/matrix. Reads ONLY committed JSON/ledgers (re-runs phase4z_figures_tables to
re-derive the p14 model x mechanism matrix from episode ledgers) and aggregates p14 + Phase-5C +
Phase-5D into reports/evidence/phase6_data.json. No number is hand-copied.
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]


def _j(p):
    try:
        return json.loads((REPO / p).read_text())
    except Exception:
        return {}


def _run_figures_tables():
    """Re-run the p14 figures/tables generator (reads ledgers) -> capture its JSON summary."""
    r = subprocess.run([sys.executable, "scripts/phase4z_figures_tables.py"], cwd=str(REPO),
                       capture_output=True, text=True, timeout=120)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}


def main():
    p14_ft = _run_figures_tables()
    p14_syn = _j("reports/synthetic_p14_phase4z_synthesis.json")
    p14_fm = _j("reports/synthetic_p14_phase4z_freeze_manifest.json")
    p5c = _j("reports/synthetic_phase5c_collection_report.json")
    p5d = _j("reports/synthetic_phase5d_collection_report.json")
    p5c_st = _j("reports/evidence/phase5c_state.json")
    p5d_st = _j("reports/evidence/phase5d_state.json")

    data = {
        "schema": "phase6_data/v1",
        "p14": {
            "headline": p14_syn.get("headline_conclusion"),
            "established": p14_syn.get("established_findings", []),
            "directional_model_scoped": p14_syn.get("directional_or_model_scoped_findings", []),
            "unresolved_or_negative": p14_syn.get("unresolved_or_negative_findings", []),
            "program_totals": p14_fm.get("program_totals", {}),
            "figures_tables_tally": {k: p14_ft.get(k) for k in ("cells", "program_ledger_episodes",
                               "program_correct", "program_axis", "program_value")},
            "commit_chain_head": p14_fm.get("frozen_at_head_short"),
        },
        "phase5c": {
            "collection": p5c.get("collection_status", {}),
            "family_summary": p5c.get("family_summary", {}),
            "conclusion": p5c.get("external_validity_conclusion"),
            "instance_level": p5c.get("instance_level", []),
            "state": {"primary": p5c_st.get("primary"), "spent": p5c_st.get("spent"),
                      "remaining": p5c_st.get("remaining_ledger_balance")},
        },
        "phase5d": {
            "collection": p5d.get("collection_status", {}),
            "family_mean_rates": p5d.get("family_mean_rates", {}),
            "contrasts": p5d.get("predeclared_contrasts_descriptive", {}),
            "instance_level": p5d.get("instance_level", []),
            "state": {"primary": p5d_st.get("primary"), "spent": p5d_st.get("spent"),
                      "remaining": p5d_st.get("remaining_ledger_balance")},
        },
        "aggregate_costs_cny": {
            "p14_program": (p14_fm.get("program_totals", {}) or {}).get("cost_cny"),
            "phase5c": p5c_st.get("spent"), "phase5d": p5d_st.get("spent"),
            "total_5c_5d": round((p5c_st.get("spent") or 0) + (p5d_st.get("spent") or 0), 4),
        },
        "aggregate_episodes": {
            "p14_primary": (p14_fm.get("program_totals", {}) or {}).get("primary"),
            "phase5c_primary": p5c_st.get("primary"), "phase5d_primary": p5d_st.get("primary"),
        },
    }
    out = REPO / "reports/evidence/phase6_data.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2) + "\n")
    # concise stdout
    print(json.dumps({"p14_totals": data["p14"]["program_totals"],
                      "p14_tally": data["p14"]["figures_tables_tally"],
                      "phase5c": data["phase5c"]["family_summary"], "phase5c_conclusion": data["phase5c"]["conclusion"],
                      "phase5d_rates": data["phase5d"]["family_mean_rates"], "phase5d_contrasts": data["phase5d"]["contrasts"],
                      "costs": data["aggregate_costs_cny"], "episodes": data["aggregate_episodes"]}, indent=2))


if __name__ == "__main__":
    main()
