#!/bin/bash
set -e
cd "$(dirname "$0")"
vcs -full64 -sverilog design.sv tb_hidden.sv -o simv_hidden -quiet
./simv_hidden
