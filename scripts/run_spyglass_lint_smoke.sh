#!/bin/bash
# Run P7 SpyGlass Lint Debug smoke test.
# Skips gracefully if SpyGlass is not available.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SMOKE_DIR="$REPO_ROOT/tasks/p7_spyglass_lint_debug/smoke/sg_lint_0000"

if [ ! -d "$SMOKE_DIR" ]; then
    echo "SKIP: Smoke task not generated at $SMOKE_DIR"
    exit 0
fi

echo "=== P7 SpyGlass Lint Debug Smoke Test ==="
echo "Smoke dir: $SMOKE_DIR"

# Check if SpyGlass is available
SG_CMD="${EDA_SG_CMD:-sg_shell}"
if ! command -v "$SG_CMD" &>/dev/null; then
    echo "SKIP: sg_shell not found (EDA_SG_CMD=$SG_CMD)"
    echo "Smoke test passed (graceful skip — SpyGlass not available)"
    exit 0
fi

echo "SpyGlass found: $(which $SG_CMD)"

# Validate task metadata
echo ""
echo "--- Validating task metadata ---"
cd "$REPO_ROOT"
python3 -m eda_agentbench validate-task "$SMOKE_DIR"

# Run solution mode
echo ""
echo "--- Solution mode ---"
SOLUTION_DIR="$SMOKE_DIR/solution"
python3 -m eda_agentbench evaluate-task "$SMOKE_DIR" --submission "$SOLUTION_DIR"

# Run buggy mode — only submit editable files (not forbidden files)
echo ""
echo "--- Buggy mode ---"
BUGGY_DIR=$(mktemp -d)
cp "$SMOKE_DIR/files/design.v" "$BUGGY_DIR/"
python3 -m eda_agentbench evaluate-task "$SMOKE_DIR" --submission "$BUGGY_DIR"
rm -rf "$BUGGY_DIR"

echo ""
echo "=== Smoke Test Complete ==="
