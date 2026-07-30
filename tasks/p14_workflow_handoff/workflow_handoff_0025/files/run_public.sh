#!/bin/bash
# Public feedback runner (p14 workflow handoff). Verdict hoisted to the TOP of stdout.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
if ! command -v "$PT_CMD" >/dev/null 2>&1; then echo "SKIP: pt_shell not found"; exit 0; fi
RAW="$("$PT_CMD" -f run_public.tcl 2>&1)"
echo "$RAW" | grep -E '^WORKFLOW_PUBLIC:' || echo "WORKFLOW_PUBLIC: UNKNOWN no_verdict"
echo "$RAW" | grep -E '^PUBLIC_HINT:' || true
echo "----- full PrimeTime log -----"
printf '%s\n' "$RAW"
exit 0
