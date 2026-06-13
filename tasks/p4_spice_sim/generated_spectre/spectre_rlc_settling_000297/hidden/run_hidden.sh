#!/bin/bash
set -e
WORK_DIR="$(pwd)"

spectre circuit.scs +escchars +log spectre_hidden.out -format nutascii 2>&1 | tee spectre_hidden.log

python3 -c "
import re, json, os

def find_crossing_time(times, values, threshold, rise=True):
    for i in range(1, len(values)):
        if rise:
            if values[i-1] < threshold and values[i] >= threshold:
                frac = (threshold - values[i-1]) / (values[i] - values[i-1])
                return times[i-1] + frac * (times[i] - times[i-1])
        else:
            if values[i-1] > threshold and values[i] <= threshold:
                frac = (threshold - values[i-1]) / (values[i] - values[i-1])
                return times[i-1] + frac * (times[i] - times[i-1])
    return None

raw_file = 'circuit.raw'
if not os.path.isfile(raw_file):
    existing = {}
    if os.path.isfile('metrics.json'):
        try: existing = json.load(open('metrics.json'))
        except: pass
    json.dump(existing, open('metrics.json', 'w'), indent=2)
    exit(0)

with open(raw_file) as f:
    content = f.read()
data = {}
values_section = content.split('Values:')
if len(values_section) < 2:
    exit(0)

for line in values_section[1].strip().split(chr(10)):
    parts = line.split()
    if len(parts) >= 4:
        idx = int(parts[0])
        data[idx] = [float(x) for x in parts[1:]]

times, in_vals, out_vals = [], [], []
for idx in sorted(data.keys()):
    row = data[idx]
    times.append(row[0])
    in_vals.append(row[1])
    out_vals.append(row[2])

threshold = 0.9
in_rise = find_crossing_time(times, in_vals, threshold, rise=True)
out_rise = find_crossing_time(times, out_vals, threshold, rise=True)

metrics = {}
if in_rise is not None and out_rise is not None:
    metrics['tdrise'] = out_rise - in_rise

existing = {}
if os.path.isfile('metrics.json'):
    try: existing = json.load(open('metrics.json'))
    except: pass
existing.update(metrics)
json.dump(existing, open('metrics.json', 'w'), indent=2)
"
