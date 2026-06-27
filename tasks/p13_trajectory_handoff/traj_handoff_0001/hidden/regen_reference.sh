#!/bin/bash
# Hidden reference re-run (p13). Recomputes the CORRECT evidence from the SUBMITTED repaired inputs,
# using TRUSTED hidden copies of the generator (gen_evidence_trusted.py + evidence_signoff_trusted.tcl)
# -- never the agent-side copies -- in a private scratch dir, so the oracle has its own reference for
# report_digest / input_hashes / run_nonce / signoff / paths to compare the submitted evidence against.
# Writes ref_timing_report.rpt and ref_evidence_manifest.json into the eval workspace.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
PY_CMD="${EDA_PY_CMD:-python3}"
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/p13ref.XXXXXX")"
cp netlist_v1.v netlist_v2.v tiny.lib tiny.db "$SCRATCH/" 2>/dev/null
cp gen_evidence_trusted.py "$SCRATCH/gen_evidence.py"
cp evidence_signoff_trusted.tcl "$SCRATCH/evidence_signoff.tcl"
# the SUBMITTED repaired inputs (overlaid into the eval workspace by the harness)
cp flow_config.json constraints.sdc "$SCRATCH/" 2>/dev/null
( cd "$SCRATCH" && EDA_PT_CMD="$PT_CMD" EDA_PY_CMD="$PY_CMD" "$PY_CMD" gen_evidence.py >/dev/null 2>&1 )
cp "$SCRATCH/timing_report.rpt" ref_timing_report.rpt 2>/dev/null
cp "$SCRATCH/evidence_manifest.json" ref_evidence_manifest.json 2>/dev/null
rm -rf "$SCRATCH"
