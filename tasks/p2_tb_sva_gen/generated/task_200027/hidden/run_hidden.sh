#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "=== Mutant 1 ==="
vcs -full64 -sverilog -timescale=1ns/1ps design_mutant1.sv tb.sv -o simv_mutant1 -quiet 2>&1
./simv_mutant1 2>&1
echo "=== Mutant 2 ==="
vcs -full64 -sverilog -timescale=1ns/1ps design_mutant2.sv tb.sv -o simv_mutant2 -quiet 2>&1
./simv_mutant2 2>&1
