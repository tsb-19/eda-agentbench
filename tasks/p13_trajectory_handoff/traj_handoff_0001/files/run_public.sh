#!/bin/bash
# Public feedback runner (p13 trajectory handoff). Reads only agent-visible files; never references
# hidden grading files. The TRAJECTORY_PUBLIC verdict is hoisted to the TOP of stdout so a small obs
# window can't hide it; the full PrimeTime log follows after.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
if ! command -v "$PT_CMD" >/dev/null 2>&1; then
    echo "SKIP: pt_shell not found (EDA_PT_CMD=$PT_CMD)"
    exit 0
fi
RAW="$("$PT_CMD" -f run_public.tcl 2>&1)"
echo "$RAW" | grep -E '^TRAJECTORY_PUBLIC:' || echo "TRAJECTORY_PUBLIC: UNKNOWN no_verdict"
echo "$RAW" | grep -E '^PUBLIC_HINT:' || true
echo "----- full PrimeTime log -----"
printf '%s\n' "$RAW"
exit 0
