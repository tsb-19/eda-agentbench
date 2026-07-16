# Phase-4W fairness gate verdict

- Gate #1 source equivalence (0013==0010, 0014==0009, full vectors): **PASS**
- Gate #2 held-out relational (golden=1.0; wrong-axis typed-rejected+signoff-green; stale/mutant low): **PASS**
- Plausibility (wrong-axis signoff-green all tasks): **PASS**
- **ALL HARD GATES: PASS**

## candidate vectors (total | signoff/evidence_gen/explanation)

| task | golden | wrong_axis | stale_decoy | unchanged_mutant |
|---|---|---|---|---|
| 0009 | 1.0 | 1.0/1.0/1.0 | 0.2 | 1.0/0.0/1.0 | 0.1 | 0.0/0.0/1.0 | 0.1 | 0.0/0.0/1.0 |
| 0010 | 1.0 | 1.0/1.0/1.0 | 0.2 | 1.0/0.0/1.0 | 0.1 | 0.0/0.0/1.0 | 0.1 | 0.0/0.0/1.0 |
| 0011 | 1.0 | 1.0/1.0/1.0 | 0.2 | 1.0/0.0/1.0 | 0.1 | 0.0/0.0/1.0 | 0.1 | 0.0/0.0/1.0 |
| 0012 | 1.0 | 1.0/1.0/1.0 | 0.2 | 1.0/0.0/1.0 | 0.1 | 0.0/0.0/1.0 | 0.1 | 0.0/0.0/1.0 |
| 0013 | 1.0 | 1.0/1.0/1.0 | 0.2 | 1.0/0.0/1.0 | 0.1 | 0.0/0.0/1.0 | 0.1 | 0.0/0.0/1.0 |
| 0014 | 1.0 | 1.0/1.0/1.0 | 0.2 | 1.0/0.0/1.0 | 0.1 | 0.0/0.0/1.0 | 0.1 | 0.0/0.0/1.0 |

## source-equivalence detail
- 0013 vs 0010 all candidates match: `True`
- 0014 vs 0009 all candidates match: `True`

## held-out
{
  "0011": {
    "golden_total_1.0": true,
    "golden_all_components_1.0": true,
    "wrong_axis_signoff_green": true,
    "wrong_axis_evidence_rejected": true,
    "wrong_axis_total_0.2": true,
    "stale_decoy_low": true,
    "unchanged_mutant_low": true
  },
  "0012": {
    "golden_total_1.0": true,
    "golden_all_components_1.0": true,
    "wrong_axis_signoff_green": true,
    "wrong_axis_evidence_rejected": true,
    "wrong_axis_total_0.2": true,
    "stale_decoy_low": true,
    "unchanged_mutant_low": true
  }
}

## plausibility
{
  "wrong_axis_signoff_green_all_tasks": true,
  "stale_decoy_signoff_red_source_and_heldout": true,
  "stale_decoy_note": "stale-decoy is a netlist-family rejection (netlist_v1 under pinned clk_main has no clk_main -> PT red); red in source AND held-out alike (faithful preservation). signoff-green-while-rejected holds for wrong-axis (the role-binding decoy relevant to C6)."
}
