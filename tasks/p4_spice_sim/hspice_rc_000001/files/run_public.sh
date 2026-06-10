#!/bin/bash
set -e
cd "$(dirname "$0")"
hspice -i circuit.sp -o public_run 2>&1
