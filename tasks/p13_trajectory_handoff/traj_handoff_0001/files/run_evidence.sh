#!/bin/bash
# Public evidence generator (run me after repairing flow_config.json + constraints.sdc). Reruns the
# sign-off flow on the CURRENT inputs and (re)writes fresh timing_report.rpt + evidence_manifest.json
# via the shared deterministic gen_evidence.py. Reads only agent-visible files; references no hidden
# grading files. Editing this script is forbidden (anti-cheat); just run it.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
PY_CMD="${EDA_PY_CMD:-python3}"
if ! command -v "$PT_CMD" >/dev/null 2>&1; then
    echo "SKIP: pt_shell not found (EDA_PT_CMD=$PT_CMD)"
    exit 0
fi
EDA_PT_CMD="$PT_CMD" "$PY_CMD" gen_evidence.py
echo "EVIDENCE_GENERATED timing_report.rpt evidence_manifest.json"
exit 0
