"""P4 SPICE Sim task generator — RC low-pass filter, HSPICE + Spectre."""

from __future__ import annotations

import json
from pathlib import Path

from generators.base import BaseGenerator

# RC parameter sets: (R_buggy, R_solution, C, public_min, public_max, hidden_min, hidden_max)
# Each row generates one HSPICE + one Spectre task
_RC_CONFIGS = [
    {"r_bug": "10k",  "r_sol": "1.2k",  "c": "10p", "pub_min": 8e-9,  "pub_max": 15e-9, "hid_min": 8e-9,  "hid_max": 15e-9},
    {"r_bug": "22k",  "r_sol": "2.2k",  "c": "4.7p","pub_min": 5e-9,  "pub_max": 12e-9, "hid_min": 5e-9,  "hid_max": 12e-9},
    {"r_bug": "4.7k", "r_sol": "560",   "c": "22p", "pub_min": 6e-9,  "pub_max": 14e-9, "hid_min": 6e-9,  "hid_max": 14e-9},
    {"r_bug": "15k",  "r_sol": "1.5k",  "c": "6.8p","pub_min": 5e-9,  "pub_max": 11e-9, "hid_min": 5e-9,  "hid_max": 11e-9},
    {"r_bug": "33k",  "r_sol": "3.3k",  "c": "3.3p","pub_min": 5e-9,  "pub_max": 12e-9, "hid_min": 5e-9,  "hid_max": 12e-9},
]


def _hspice_netlist(r: str, c: str) -> str:
    return f"""\
* RC low-pass filter - HSPICE netlist
.global 0
.param rp={r}

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p 100n 200n

* RC low-pass filter
r1 in out {r}
c1 out 0 {c}

* Analysis
.tran 50p 150n

* Measure rise delay
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1

.end
"""


def _hspice_run_public() -> str:
    return """\
#!/bin/bash
set -e
WORK_DIR="$(pwd)"
hspice -i "$WORK_DIR/circuit.sp" -o public_run 2>&1
"""


def _hspice_run_hidden() -> str:
    return """\
#!/bin/bash
set -e
WORK_DIR="$(pwd)"
cp "$WORK_DIR/circuit.sp" "$WORK_DIR/circuit_hidden.sp"
sed -i 's/^\\.end$/.measure TRAN tdfall TRIG v(in) VAL=0.9 FALL=1 TARG v(out) VAL=0.9 FALL=1\\n.end/' "$WORK_DIR/circuit_hidden.sp"
hspice -i "$WORK_DIR/circuit_hidden.sp" -o hidden_run 2>&1
"""


def _spectre_netlist(r: str, c: str) -> str:
    return f"""\
// RC low-pass filter - Spectre netlist
simulator lang=spectre
global 0

// Power supply
vdd (vdd 0) vsource type=dc dc=1.8

// Input pulse
vin (in 0) vsource type=pulse val0=0 val1=1.8 delay=1n rise=500p fall=500p width=100n period=200n

// RC low-pass filter
r1 (in out) resistor r={r}
c1 (out 0) capacitor c={c}

// Analysis
tran tran stop=150n errpreset=moderate

// Save outputs
save in out
"""


def _spectre_run_public() -> str:
    return """\
#!/bin/bash
set -e
WORK_DIR="$(pwd)"
spectre circuit.scs +escchars +log spectre.out -format nutascii 2>&1 | tee spectre_public.log

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
    json.dump({}, open('metrics.json', 'w'))
    exit(0)

with open(raw_file) as f:
    content = f.read()
data = {}
values_section = content.split('Values:')
if len(values_section) < 2:
    json.dump({}, open('metrics.json', 'w'))
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

log = open('spectre_public.log').read()
for m in re.finditer(r'(\\w+)\\s*=\\s*([0-9eE.+\\-]+[a-zA-Z]*)', log):
    name = m.group(1).lower()
    try:
        val = float(m.group(2))
        if name not in ('stop', 'step', 'start', 'errpreset', 'cpu', 'elapsed', 'used', 'total'):
            metrics[name] = val
    except ValueError:
        pass

json.dump(metrics, open('metrics.json', 'w'), indent=2)
"
"""


def _spectre_run_hidden() -> str:
    return """\
#!/bin/bash
set -e
WORK_DIR="$(pwd)"
cp "$WORK_DIR/circuit.scs" "$WORK_DIR/circuit_hidden.scs"

# Replace rise measurement with fall measurement
sed -i 's/trig=v(in) val=0.9 rise=1/trig=v(in) val=0.9 fall=1/g' "$WORK_DIR/circuit_hidden.scs" 2>/dev/null || true
sed -i 's/targ=v(out) val=0.9 rise=1/targ=v(out) val=0.9 fall=1/g' "$WORK_DIR/circuit_hidden.scs" 2>/dev/null || true

spectre circuit_hidden.scs +escchars +log spectre_hidden.out -format nutascii 2>&1 | tee spectre_hidden.log

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

raw_file = 'circuit_hidden.raw'
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
in_fall = find_crossing_time(times, in_vals, threshold, rise=False)
out_fall = find_crossing_time(times, out_vals, threshold, rise=False)

metrics = {}
if in_fall is not None and out_fall is not None:
    metrics['tdfall'] = out_fall - in_fall

existing = {}
if os.path.isfile('metrics.json'):
    try: existing = json.load(open('metrics.json'))
    except: pass
existing.update(metrics)
json.dump(existing, open('metrics.json', 'w'), indent=2)
"
"""


class P4SPICEGenerator(BaseGenerator):
    """Generates P4 SPICE Sim tasks (HSPICE + Spectre RC low-pass)."""

    def generate_one(self, task_index: int) -> Path:
        cfg = _RC_CONFIGS[task_index % len(_RC_CONFIGS)]
        is_spectre = task_index >= len(_RC_CONFIGS)
        tool = "spectre" if is_spectre else "hspice"
        prefix = "spectre" if is_spectre else "hspice"

        # Use offset 100 to avoid conflicting with P1 task IDs (0-99)
        # Use "gen" prefix to avoid overwriting smoke tasks
        task_id = f"task_{100 + task_index:06d}"
        task_dir = self.output_dir / f"{prefix}_gen_{task_index:06d}"
        task_dir.mkdir(parents=True, exist_ok=True)

        (task_dir / "files").mkdir(exist_ok=True)
        (task_dir / "hidden").mkdir(exist_ok=True)
        (task_dir / "solution").mkdir(exist_ok=True)

        # Write circuit files
        if is_spectre:
            (task_dir / "files" / "circuit.scs").write_text(_spectre_netlist(cfg["r_bug"], cfg["c"]))
            (task_dir / "solution" / "circuit.scs").write_text(_spectre_netlist(cfg["r_sol"], cfg["c"]))
            (task_dir / "files" / "run_public.sh").write_text(_spectre_run_public())
            (task_dir / "hidden" / "run_hidden.sh").write_text(_spectre_run_hidden())
        else:
            (task_dir / "files" / "circuit.sp").write_text(_hspice_netlist(cfg["r_bug"], cfg["c"]))
            (task_dir / "solution" / "circuit.sp").write_text(_hspice_netlist(cfg["r_sol"], cfg["c"]))
            (task_dir / "files" / "run_public.sh").write_text(_hspice_run_public())
            (task_dir / "hidden" / "run_hidden.sh").write_text(_hspice_run_hidden())

        # Make scripts executable
        (task_dir / "files" / "run_public.sh").chmod(0o755)
        (task_dir / "hidden" / "run_hidden.sh").chmod(0o755)

        # Circuit filename
        circuit_file = "circuit.scs" if is_spectre else "circuit.sp"

        # Write prompt
        prompt = f"""\
# Task: Fix RC Low-Pass Filter Rise Time

## Problem

The RC low-pass filter in `{circuit_file}` has a rise time that is too slow.
The input signal is a pulse from 0V to 1.8V with 500ps rise/fall times,
100ns pulse width, and 200ns period.

The 50% rise delay (time for output to reach 0.9V on the rising edge) must be
between {cfg['pub_min']*1e9:.0f}ns and {cfg['pub_max']*1e9:.0f}ns.

## Your Task

1. Analyze the circuit in `{circuit_file}`
2. Identify the component causing the slow rise time
3. Modify the editable file to fix the rise delay
4. Run `bash run_public.sh` to verify your fix

## Constraints

- You may only modify `{circuit_file}`
- Do not modify `run_public.sh` or any other files
- The RC filter topology must remain the same (series R, shunt C)
- The input signal parameters must not change

## Files

- `{circuit_file}` — {'Spectre' if is_spectre else 'HSPICE'} netlist (editable)
- `run_public.sh` — Public test script (read-only)
"""
        (task_dir / "prompt.md").write_text(prompt)

        # Write metadata
        circuit_ext = "scs" if is_spectre else "sp"
        meta = {
            "task_id": task_id,
            "track": "p4_spice_sim",
            "tool": [tool],
            "difficulty": "easy",
            "data_type": "template_synthetic",
            "resource_preset": "fast",
            "timeout_sec": 120,
            "max_tool_calls": 10,
            "max_patch_attempts": 3,
            "max_output_tokens": 16000,
            "files": {
                "visible": [f"circuit.{circuit_ext}", "run_public.sh"],
                "editable": [f"circuit.{circuit_ext}"],
                "hidden": ["run_hidden.sh"],
                "forbidden": ["run_public.sh", "run_hidden.sh"],
            },
            "run_command": "bash run_public.sh",
            "scoring": {
                "weights": {
                    "tool_run": 0.3,
                    "output_generated": 0.2,
                    "public_metric": 0.2,
                    "hidden_metric": 0.2,
                    "explanation": 0.1,
                },
                "evaluator": "spice_sim.SPICESimEvaluator",
                "explanation_weight": 0.1,
                "metrics": {
                    "public": {
                        "measure": "tdrise",
                        "min": cfg["pub_min"],
                        "max": cfg["pub_max"],
                    },
                    "hidden": {
                        "measure": "tdfall",
                        "min": cfg["hid_min"],
                        "max": cfg["hid_max"],
                    },
                },
            },
            "sanitizer": {"enabled": True},
            "generator": {
                "script": "p4_spice_gen.py",
                "seed": self.seed,
                "config_index": task_index % len(_RC_CONFIGS),
                "tool": tool,
            },
            "version": "1.0.0",
        }
        (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")

        return task_dir
