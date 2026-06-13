#!/bin/bash
# P8 PnR Report QA Smoke Test
# Does not require ICC2/Innovus tools.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

SMOKE_TASK="tasks/p8_pnr_report_qa/smoke/pnr_report_qa_0000"

echo "=== P8 PnR Report QA Smoke Test ==="
echo "Smoke dir: $SMOKE_TASK"
echo ""

# Validate task metadata
echo "--- Validating task metadata ---"
python3 -c "
import json, sys
sys.path.insert(0, '.')
from eda_agentbench.schema import validate_metadata

with open('$SMOKE_TASK/metadata.json') as f:
    meta = json.load(f)
errors = validate_metadata(meta)
if errors:
    for e in errors:
        print(f'  ERROR: {e}')
    sys.exit(1)
else:
    print(f'Task {meta[\"task_id\"]} ({meta[\"track\"]}): VALID')
    print(f'  Tool: {meta[\"tool\"]}')
    print(f'  Difficulty: {meta[\"difficulty\"]}')
    print(f'  Scoring: {meta[\"scoring\"][\"weights\"]}')
"
echo "PASS: Task validation"
echo ""

# Evaluate with solution (expect PASS)
echo "--- Evaluate with solution (expect PASS) ---"
eda-bench evaluate-task "$SMOKE_TASK" --submission "$SMOKE_TASK/solution" 2>&1 | tail -15
echo ""

# Evaluate with buggy (expect FAIL) - empty answer.txt
echo "--- Evaluate with buggy (expect FAIL) ---"
BUGGY_DIR=$(mktemp -d)
echo '{}' > "$BUGGY_DIR/answer.txt"
eda-bench evaluate-task "$SMOKE_TASK" --submission "$BUGGY_DIR" 2>&1 | tail -15
rm -rf "$BUGGY_DIR"
echo ""

echo "=== Smoke Test Complete ==="
