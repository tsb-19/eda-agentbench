# P8 PnR Report QA

## Overview

P8 PnR Report QA is a report-based question-answering track for physical implementation reports. Given synthetic ICC2-style or Innovus-style PnR reports, agents answer precise physical design questions.

**This is report-QA, not execution-debug.** Reports are synthetic/sanitized. No ICC2/Innovus license is required for pytest.

## Task Structure

Each task contains:
- `report.txt`: Synthetic PnR report (visible, forbidden to modify)
- `prompt.md`: Questions to answer (visible, forbidden to modify)
- `answer.txt`: Agent fills in JSON answers (visible, editable)
- `solution/answer.txt`: Oracle answers (hidden from agent)

## Question Types

| Category | Fields |
|----------|--------|
| Timing | setup_wns, setup_tns, setup_violations, hold_wns, hold_tns, hold_violations, worst_endpoint, worst_startpoint, timing_met |
| Utilization | core_utilization, placement_density, instance_count, sequential_count |
| Area | cell_area, macro_area, total_cell_area, buffer_count |
| Congestion | max_horizontal_overflow, max_vertical_overflow, total_overflow, congested_bins, worst_congestion_layer, congestion_pass |
| Routing | total_wirelength, drc_total, shorts, opens, antenna_violations, route_completed |
| Power | internal_power, switching_power, leakage_power, total_power |
| Flow Status | stage, tool_family, design_name |

## Scoring

- **answer_match** (0.9): Exact match for strings/ints, 2% tolerance for floats, exact match for booleans
- **explanation** (0.1): Defaults to 1.0 in submission mode

## Tool Families

- **ICC2-style**: Reports with `:` separator, ICC2 header
- **Innovus-style**: Reports with `=` separator, Innovus header

## Dataset Size

- Smoke: 1 task
- Generated: 100 tasks
- Total: 101 tasks
- ICC2: ~45 tasks, Innovus: ~56 tasks

## Validation

```bash
# Run P8 tests
pytest tests/test_p8_pnr_report_qa.py -v

# Run smoke
bash scripts/run_pnr_report_qa_smoke.sh

# Evaluate all P8 tasks
eda-bench evaluate-dataset tasks --track p8_pnr_report_qa --submission-mode solution
eda-bench evaluate-dataset tasks --track p8_pnr_report_qa --submission-mode buggy
```

## Known Limitations

- Reports are synthetic, not from real ICC2/Innovus runs
- Only basic PnR metrics are covered
- No layout visualization or GDSII parsing
- Parser handles both `:` and `=` separators but may not cover all report variants
