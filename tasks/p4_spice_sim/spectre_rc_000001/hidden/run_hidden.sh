#!/bin/bash
set -e
# Hidden test: measure fall delay on copy of circuit
WORK_DIR="$(pwd)"

# Copy circuit for hidden measurement
cp "$WORK_DIR/circuit.scs" "$WORK_DIR/circuit_hidden.scs"

# Run Spectre with nutascii format
spectre circuit_hidden.scs +escchars +log spectre_hidden.out -format nutascii 2>&1 | tee spectre_hidden.log

# Parse waveform data and compute fall delay, merge into metrics.json
python3 -c "
import re, json, os

def find_crossing_time(times, values, threshold, rise=True):
    \"\"\"Find time when waveform crosses threshold.\"\"\"
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

# Find nutascii output file
raw_file = 'circuit_hidden.raw'
if not os.path.isfile(raw_file):
    print(f'WARNING: No raw output file found for hidden test')
    # Merge empty with existing
    existing = {}
    if os.path.isfile('metrics.json'):
        try:
            existing = json.load(open('metrics.json'))
        except json.JSONDecodeError:
            pass
    json.dump(existing, open('metrics.json', 'w'), indent=2)
    exit(0)

# Parse nutascii format
with open(raw_file, 'r') as f:
    content = f.read()

# Extract data values
data = {}
values_section = content.split('Values:')
if len(values_section) < 2:
    print('WARNING: No Values section found')
    exit(0)

for line in values_section[1].strip().split('\n'):
    parts = line.strip().split()
    if len(parts) >= 3:
        idx = int(parts[0])
        data[idx] = [float(x) for x in parts[1:]]

# Organize by variable
times = []
in_vals = []
out_vals = []
for idx in sorted(data.keys()):
    row = data[idx]
    times.append(row[0])
    in_vals.append(row[1])
    out_vals.append(row[2])

# Compute fall delay (50% of 1.8V = 0.9V)
threshold = 0.9
in_fall = find_crossing_time(times, in_vals, threshold, rise=False)
out_fall = find_crossing_time(times, out_vals, threshold, rise=False)

metrics = {}
if in_fall is not None and out_fall is not None:
    tdfall = out_fall - in_fall
    metrics['tdfall'] = tdfall
    print(f'Input crosses 0.9V falling at: {in_fall:.4e} s')
    print(f'Output crosses 0.9V falling at: {out_fall:.4e} s')
    print(f'Fall delay (tdfall): {tdfall:.4e} s')
else:
    print(f'WARNING: Could not find crossing times (in_fall={in_fall}, out_fall={out_fall})')

# Merge with existing metrics.json (from public run)
existing = {}
if os.path.isfile('metrics.json'):
    try:
        existing = json.load(open('metrics.json'))
    except json.JSONDecodeError:
        pass

existing.update(metrics)
json.dump(existing, open('metrics.json', 'w'), indent=2)
print(f'Combined metrics: {existing}')
"
