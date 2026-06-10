#!/bin/bash
set -e
# This script runs from the work_dir (where circuit.sp lives)
# Hidden files are copied to work_dir root by the evaluator
WORK_DIR="$(pwd)"
# Copy submission circuit for hidden test
cp "$WORK_DIR/circuit.sp" "$WORK_DIR/circuit_hidden.sp"
# Append hidden measurement to the netlist
sed -i 's/^\.end$/.measure TRAN tdfall TRIG v(in) VAL=0.9 FALL=1 TARG v(out) VAL=0.9 FALL=1\n.end/' "$WORK_DIR/circuit_hidden.sp"
# Run HSPICE
hspice -i "$WORK_DIR/circuit_hidden.sp" -o hidden_run 2>&1
