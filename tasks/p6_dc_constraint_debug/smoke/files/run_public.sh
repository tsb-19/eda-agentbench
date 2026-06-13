#!/bin/bash
# DC Constraint Debug — public run script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

DC_CMD="${EDA_DC_CMD:-dc_shell}"

# Check if dc_shell is available
if ! command -v "$DC_CMD" &>/dev/null; then
    echo "SKIP: dc_shell not found (EDA_DC_CMD=$DC_CMD)"
    echo "PUBLIC_RESULT: SKIP"
    exit 0
fi

# Run dc_shell and capture output
DC_OUTPUT=$("$DC_CMD" -f run_public.tcl 2>&1)
DC_EXIT=$?

echo "$DC_OUTPUT"

# Check for DC-level errors in output (not just exit code)
# DC often exits 0 even when constraint commands fail
DC_ERRORS=$(echo "$DC_OUTPUT" | grep -c "^Error:" || true)
DC_CRASH=$(echo "$DC_OUTPUT" | grep -cPi "\babort\b|segmentation fault|core dumped" || true)

if [ $DC_EXIT -ne 0 ] || [ "$DC_CRASH" -gt 0 ]; then
    echo "PUBLIC_RESULT: FAIL (exit=$DC_EXIT, fatal=$DC_CRASH)"
    exit 1
elif [ "$DC_ERRORS" -gt 0 ]; then
    echo "PUBLIC_RESULT: FAIL ($DC_ERRORS DC errors)"
    exit 1
else
    echo "PUBLIC_RESULT: PASS"
    exit 0
fi
