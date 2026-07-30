#!/bin/bash
# Hidden reference re-run (p14). Recomputes the CORRECT evidence chain from the SUBMITTED
# repaired inputs using TRUSTED hidden copies of the generators, in a private scratch dir, so
# the oracle has its own reference for each stage's digest/hashes/nonce. The agent-side copies
# are never used. Writes ref_timing_report.rpt + ref_evidence_manifest.json (+ ref_stage2 for
# evidence_steps=2) into the eval workspace.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
PY_CMD="${EDA_PY_CMD:-python3}"
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/p14ref.XXXXXX")"
cp netlist_v1.v netlist_v2.v tiny.lib tiny.db "$SCRATCH/" 2>/dev/null
cp gen_evidence_stage1_trusted.py "$SCRATCH/gen_evidence_stage1.py"
cp evidence_signoff_trusted.tcl "$SCRATCH/evidence_signoff.tcl"
cp flow_config.json constraints.sdc "$SCRATCH/" 2>/dev/null
( cd "$SCRATCH" && EDA_PT_CMD="$PT_CMD" EDA_PY_CMD="$PY_CMD" "$PY_CMD" gen_evidence_stage1.py >/dev/null 2>&1 )
cp "$SCRATCH/timing_report.rpt" ref_timing_report.rpt 2>/dev/null
cp "$SCRATCH/evidence_manifest.json" "$SCRATCH/evidence_manifest.json" 2>/dev/null
cp "$SCRATCH/evidence_manifest.json" ref_evidence_manifest.json 2>/dev/null
cp gen_evidence_stage2_trusted.py "$SCRATCH/gen_evidence_stage2.py"
cp evidence_signoff_stage2_trusted.tcl "$SCRATCH/evidence_signoff_stage2.tcl"
( cd "$SCRATCH" && EDA_PT_CMD="$PT_CMD" EDA_PY_CMD="$PY_CMD" "$PY_CMD" gen_evidence_stage2.py >/dev/null 2>&1 )
cp "$SCRATCH/stage2_summary.json" ref_stage2_summary.json 2>/dev/null
rm -rf "$SCRATCH"
