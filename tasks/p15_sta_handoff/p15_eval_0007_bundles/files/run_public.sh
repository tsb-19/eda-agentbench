#!/bin/bash
# Public feedback runner (iterate as much as you like). Translates your exception_config
# binding to an SDC exception, then reports real PrimeTime timing + active exceptions.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
if ! command -v "$PT_CMD" >/dev/null 2>&1; then echo "SKIP: pt_shell not found (EDA_PT_CMD=$PT_CMD)"; exit 0; fi
PY_CMD="${EDA_PY_CMD:-python3}"
"$PY_CMD" build_applied_sdc.py
"$PT_CMD" -f run_public.tcl 2>&1
exit 0
