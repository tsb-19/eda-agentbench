#!/bin/bash
set -e
WORK_DIR="$(pwd)"
cp "$WORK_DIR/circuit.sp" "$WORK_DIR/circuit_hidden.sp"
sed -i 's/^\.end$/.measure TRAN tdfall TRIG v(in) VAL=0.9 FALL=1 TARG v(out) VAL=0.9 FALL=1\n.end/' "$WORK_DIR/circuit_hidden.sp"
hspice -i "$WORK_DIR/circuit_hidden.sp" -o hidden_run 2>&1
