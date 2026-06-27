#!/bin/bash
# Public handoff feedback runner (p12 stale-package triangle). Reads only agent-visible files
# (flow_config.json, the netlist it names, constraints.sdc, handoff_manifest.json, tiny.db). It
# NEVER references hidden grading files. The HANDOFF_PUBLIC verdict is hoisted to the TOP of stdout
# so it stays visible under a small observation window; the full PrimeTime log follows after.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
if ! command -v "$PT_CMD" >/dev/null 2>&1; then
    echo "SKIP: pt_shell not found (EDA_PT_CMD=$PT_CMD)"
    exit 0
fi
RAW="$("$PT_CMD" -f run_public.tcl 2>&1)"
echo "$RAW" | grep -E '^HANDOFF_PUBLIC:' || echo "HANDOFF_PUBLIC: UNKNOWN no_verdict"
echo "$RAW" | grep -E '^PUBLIC_HINT:' || true
echo "----- full PrimeTime log -----"
printf '%s\n' "$RAW"
exit 0
