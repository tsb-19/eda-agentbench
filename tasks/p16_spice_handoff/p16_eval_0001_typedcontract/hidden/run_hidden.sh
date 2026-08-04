#!/bin/bash
# Hidden grader: build deck from submitted meas_config, run HSPICE, parse, grade (6 dimensions).
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
HS_CMD="${EDA_HSPICE_CMD:-hspice}"
PY_CMD="${EDA_PY_CMD:-python3}"
if ! command -v "$HS_CMD" >/dev/null 2>&1; then echo '{"sim_ok": false, "fatal": "hspice not found"}' > measure_result.json; exit 0; fi
"$PY_CMD" build_deck.py
HS_OUT="$("$HS_CMD" -i circuit_built.sp -o hspice_run 2>&1)"; RC=$?
METRIC="$(python3 -c 'import json;print(json.load(open("meas_config.json"))["metric"])')"
PJ="$("$PY_CMD" parse_measure.py hspice_run.lis "$METRIC")"
VALUE=$(echo "$PJ" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("value"))')
ANALYSIS=$(python3 -c 'import json;a={"gain":"ac","gbw":"ac","pm":"ac","slew":"tran","vdsat":"dc"};print(a.get("'$METRIC'","ac"))')
SIM_OK=$( [ $RC -eq 0 ] && [ -f hspice_run.lis ] && [ "$VALUE" != "None" ] && echo true || echo false )
cat > measure_result.json <<JSON
{"sim_ok": $SIM_OK, "value": ${VALUE:-null}, "metric": "$METRIC", "analysis": "$ANALYSIS", "hspice_rc": $RC}
JSON
"$PY_CMD" grade_spice_handoff.py
exit 0
