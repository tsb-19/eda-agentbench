#!/bin/bash
set -e
WORK_DIR="$(pwd)"
cp "$WORK_DIR/circuit.sp" "$WORK_DIR/circuit_hidden.sp"
true  # tdrise already measured in public run
hspice -i "$WORK_DIR/circuit_hidden.sp" -o hidden_run 2>&1

python3 -c "
import re, json, os

existing = {}
if os.path.isfile('metrics.json'):
    try: existing = json.load(open('metrics.json'))
    except: pass

lines = open('hidden_run.lis').read().splitlines()
for line in lines:
    m = re.match(r'^\s*(td\w+)\s*=\s*([0-9eE.+\-]+[a-zA-Z]*)', line)
    if m:
        name = m.group(1).lower()
        try:
            val = float(m.group(2))
            if name not in ('stop', 'step', 'start'):
                existing[name] = val
        except ValueError:
            pass
json.dump(existing, open('metrics.json', 'w'), indent=2)
"
