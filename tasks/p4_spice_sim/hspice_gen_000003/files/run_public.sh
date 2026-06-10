#!/bin/bash
set -e
WORK_DIR="$(pwd)"
hspice -i "$WORK_DIR/circuit.sp" -o public_run 2>&1
