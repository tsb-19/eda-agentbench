#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "=== Golden Design ==="
vcs -full64 -sverilog design_golden.sv tb.sv -o simv_golden -quiet 2>&1
./simv_golden 2>&1
