#!/bin/bash
# Public stage-2 summary-evidence generator (p14, evidence_steps=2). Consumes the stage-1
# evidence_manifest.json and writes stage2_summary.json binding the fresh stage-1 digest. Run
# AFTER stage 1. Read-only.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
PY_CMD="${EDA_PY_CMD:-python3}"
if ! command -v "$PT_CMD" >/dev/null 2>&1; then echo "SKIP: pt_shell not found"; exit 0; fi
EDA_PT_CMD="$PT_CMD" "$PY_CMD" gen_evidence_stage2.py
echo "EVIDENCE_STAGE2_GENERATED stage2_summary.json"
exit 0
