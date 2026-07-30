#!/bin/bash
# Public stage-1 evidence generator (p14). Reruns sign-off on the CURRENT flow_config.json +
# constraints.sdc and (re)writes fresh timing_report.rpt + evidence_manifest.json. Read-only
# (you run it; you do not edit it).
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
PY_CMD="${EDA_PY_CMD:-python3}"
if ! command -v "$PT_CMD" >/dev/null 2>&1; then echo "SKIP: pt_shell not found"; exit 0; fi
EDA_PT_CMD="$PT_CMD" "$PY_CMD" gen_evidence_stage1.py
echo "EVIDENCE_STAGE1_GENERATED timing_report.rpt evidence_manifest.json"
exit 0
