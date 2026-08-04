#!/bin/bash
# Public feedback: build the deck from your meas_config, run HSPICE, report the measured value.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
HS_CMD="${EDA_HSPICE_CMD:-hspice}"
PY_CMD="${EDA_PY_CMD:-python3}"
if ! command -v "$HS_CMD" >/dev/null 2>&1; then echo "SKIP: hspice not found (EDA_HSPICE_CMD=$HS_CMD)"; exit 0; fi
"$PY_CMD" build_deck.py
"$HS_CMD" -i circuit_built.sp -o hspice_run 2>&1
echo "=== measured value (no verdict) ==="
"$PY_CMD" parse_measure.py hspice_run.lis "$(python3 -c 'import json;print(json.load(open("meas_config.json"))["metric"])')"
exit 0
