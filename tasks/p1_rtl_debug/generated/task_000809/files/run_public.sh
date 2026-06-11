#!/bin/bash
set -e
cd "$(dirname "$0")"
vcs -full64 -sverilog design.sv tb_public.sv -o simv_public -quiet
./simv_public
