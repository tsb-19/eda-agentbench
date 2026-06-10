#!/bin/bash
set -e
# Run Spectre and extract public metrics to metrics.json
WORK_DIR="$(pwd)"

# Run Spectre with nutascii format for easy parsing
spectre circuit.scs +escchars +log spectre.out -format nutascii 2>&1 | tee spectre_public.log

# Parse waveform data and compute rise delay
python3 -c "
import re, json, os

def parse_val(val_str):
    suffixes = {'t': 1e12, 'g': 1e9, 'meg': 1e6, 'k': 1e3, 'm': 1e-3,
                'u': 1e-6, 'n': 1e-9, 'p': 1e-12, 'f': 1e-15, 'a': 1e-18}
    val_str = val_str.strip().lower()
    for suffix, mult in sorted(suffixes.items(), key=lambda x: -len(x[0])):
        if val_str.endswith(suffix):
            try:
                return float(val_str[:-len(suffix)]) * mult
            except ValueError:
                pass
    try:
        return float(val_str)
    except ValueError:
        return None

def find_crossing_time(times, values, threshold, rise=True):
    \"\"\"Find time when waveform crosses threshold.\"\"\"
    for i in range(1, len(values)):
        if rise:
            if values[i-1] < threshold and values[i] >= threshold:
                # Linear interpolation
                frac = (threshold - values[i-1]) / (values[i] - values[i-1])
                return times[i-1] + frac * (times[i] - times[i-1])
        else:
            if values[i-1] > threshold and values[i] <= threshold:
                frac = (threshold - values[i-1]) / (values[i] - values[i-1])
                return times[i-1] + frac * (times[i] - times[i-1])
    return None

# Find nutascii output file
raw_file = 'circuit.raw'
if not os.path.isfile(raw_file):
    # Try in spectre.out directory
    for f in os.listdir('spectre.out') if os.path.isdir('spectre.out') else []:
        if f.endswith('.raw') or f == 'circuit.raw':
            raw_file = os.path.join('spectre.out', f)
            break

if not os.path.isfile(raw_file):
    print(f'WARNING: No raw output file found')
    json.dump({}, open('metrics.json', 'w'))
    exit(0)

# Parse nutascii format
with open(raw_file, 'r') as f:
    content = f.read()

# Extract variables
var_names = {}
for m in re.finditer(r'(\d+)\s+(\w+)\s+\w+', content):
    var_names[int(m.group(1))] = m.group(2).lower()

# Extract data values
data = {}
values_section = content.split('Values:')
if len(values_section) < 2:
    print('WARNING: No Values section found')
    json.dump({}, open('metrics.json', 'w'))
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

# Compute rise delay (50% of 1.8V = 0.9V)
threshold = 0.9
in_rise = find_crossing_time(times, in_vals, threshold, rise=True)
out_rise = find_crossing_time(times, out_vals, threshold, rise=True)

metrics = {}
if in_rise is not None and out_rise is not None:
    tdrise = out_rise - in_rise
    metrics['tdrise'] = tdrise
    print(f'Input crosses 0.9V at: {in_rise:.4e} s')
    print(f'Output crosses 0.9V at: {out_rise:.4e} s')
    print(f'Rise delay (tdrise): {tdrise:.4e} s')
else:
    print(f'WARNING: Could not find crossing times (in_rise={in_rise}, out_rise={out_rise})')

# Also try to extract any measurement results from the log
log = open('spectre_public.log').read()
for m in re.finditer(r'(\w+)\s*=\s*([0-9eE.+\-]+[a-zA-Z]*)', log):
    name = m.group(1).lower()
    val = parse_val(m.group(2))
    if val is not None and name not in ('stop', 'step', 'start', 'errpreset', 'cpu', 'elapsed', 'used', 'total'):
        metrics[name] = val

if metrics:
    json.dump(metrics, open('metrics.json', 'w'), indent=2)
    print(f'Extracted metrics: {metrics}')
else:
    print('WARNING: No measurements found')
    json.dump({}, open('metrics.json', 'w'))
"
