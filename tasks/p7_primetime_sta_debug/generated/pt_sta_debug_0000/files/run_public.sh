#!/bin/bash
# PrimeTime STA Debug — public run script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PT_CMD="${EDA_PT_CMD:-pt_shell}"

# Check if pt_shell is available
if ! command -v "$PT_CMD" &>/dev/null; then
    echo "SKIP: pt_shell not found (EDA_PT_CMD=$PT_CMD)"
    exit 0
fi

# Run pt_shell and capture both stdout and stderr
PT_OUTPUT=$("$PT_CMD" -f run_public.tcl 2>&1)
PT_EXIT=$?

echo "$PT_OUTPUT"

exit $PT_EXIT
