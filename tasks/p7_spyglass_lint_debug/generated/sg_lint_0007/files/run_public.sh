#!/bin/bash
# SpyGlass Lint Debug — public run script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

SG_CMD="${EDA_SG_CMD:-sg_shell}"

# Check if sg_shell is available
if ! command -v "$SG_CMD" &>/dev/null; then
    echo "SKIP: sg_shell not found (EDA_SG_CMD=$SG_CMD)"
    exit 0
fi

# Run sg_shell with TCL script
SG_OUTPUT=$("$SG_CMD" -tcl run_public.tcl 2>&1)
SG_EXIT=$?

echo "$SG_OUTPUT"

# Parse the Goal Violation Summary from SpyGlass output
# Format:
#   Goal Violation Summary:
#       Waived   Messages:                      0 Errors,      0 Warnings,      0 Infos
#       Reported Messages:         0 Fatals,    1 Errors,      1 Warnings,      3 Infos
VIOLATION_COUNT=0

REPORTED_LINE=$(echo "$SG_OUTPUT" | grep "Reported Messages:" | tail -1)
if [ -n "$REPORTED_LINE" ]; then
    FATALS=$(echo "$REPORTED_LINE" | grep -oP '\d+(?=\s+Fatal)' || echo "0")
    ERRORS=$(echo "$REPORTED_LINE" | grep -oP '\d+(?=\s+Error)' || echo "0")
    WARNINGS=$(echo "$REPORTED_LINE" | grep -oP '\d+(?=\s+Warning)' || echo "0")
    VIOLATION_COUNT=$((FATALS + ERRORS + WARNINGS))
fi

echo "Lint violations: $VIOLATION_COUNT"

if [ "$SG_EXIT" -ne 0 ] && [ "$VIOLATION_COUNT" -eq 0 ]; then
    # sg_shell exited nonzero but no violations found — treat as crash
    echo "LINT_FAIL"
    exit 1
fi

if [ "$VIOLATION_COUNT" -gt 0 ]; then
    echo "LINT_FAIL"
    exit 1
else
    echo "LINT_PASS"
    exit 0
fi
