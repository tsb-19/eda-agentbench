#!/bin/bash
# DC Constraint Debug — public run script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

DC_CMD="${EDA_DC_CMD:-dc_shell}"

# Check if dc_shell is available
if ! command -v "$DC_CMD" &>/dev/null; then
    echo "SKIP: dc_shell not found (EDA_DC_CMD=$DC_CMD)"
    exit 0
fi

# Run dc_shell and capture both stdout and stderr
DC_OUTPUT=$("$DC_CMD" -f run_public.tcl 2>&1)
DC_EXIT=$?

echo "$DC_OUTPUT"

exit $DC_EXIT
