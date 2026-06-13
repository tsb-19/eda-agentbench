#!/bin/bash
set -e
WORK_DIR="$(pwd)"
hspice -i "$WORK_DIR/circuit.sp" -o public_run 2>&1

python3 -c "
import re, json

lines = open('public_run.lis').read().splitlines()
metrics = {}
for line in lines:
    m = re.match(r'^\s*(td\w+)\s*=\s*([0-9eE.+\-]+[a-zA-Z]*)', line)
    if m:
        name = m.group(1).lower()
        try:
            val = float(m.group(2))
            if name not in ('stop', 'step', 'start'):
                metrics[name] = val
        except ValueError:
            pass
json.dump(metrics, open('metrics.json', 'w'), indent=2)
"
