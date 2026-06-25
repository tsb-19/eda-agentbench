#!/bin/bash
# Public feedback runner (run me as many times as you like).
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$SCRIPT_DIR"
PT_CMD="${EDA_PT_CMD:-pt_shell}"
if ! command -v "$PT_CMD" >/dev/null 2>&1; then echo "SKIP: pt_shell not found (EDA_PT_CMD=$PT_CMD)"; exit 0; fi
"$PT_CMD" -f run_public.tcl 2>&1
exit 0
