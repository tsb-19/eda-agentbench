"""P4 SPICE Sim task generator — RC low-pass filter, HSPICE + Spectre."""

from __future__ import annotations

import json
from pathlib import Path

from generators.base import BaseGenerator


def _hspice_netlist(r: str, c: str, pulse_width_ns: float, sim_time_ns: float) -> str:
    pw = f"{pulse_width_ns}n"
    pt = f"{pulse_width_ns * 2}n"
    st = f"{sim_time_ns}n"
    return f"""\
* RC low-pass filter - HSPICE netlist
.global 0
.param rp={r}

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p {pw} {pt}

* RC low-pass filter
r1 in out {r}
c1 out 0 {c}

* Analysis
.tran 50p {st}

* Measure rise and fall delay
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1
.measure tran tdfall trig v(in) val=0.9 fall=1 targ v(out) val=0.9 fall=1

.end
"""


def _hspice_run_public() -> str:
    return """\
#!/bin/bash
set -e
WORK_DIR="$(pwd)"
hspice -i "$WORK_DIR/circuit.sp" -o public_run 2>&1

python3 -c "
import re, json

lines = open('public_run.lis').read().splitlines()
metrics = {}
for line in lines:
    m = re.match(r'^\\s*(td\\w+)\\s*=\\s*([0-9eE.+\\-]+[a-zA-Z]*)', line)
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
"""


def _hspice_run_hidden() -> str:
    return """\
#!/bin/bash
set -e
WORK_DIR="$(pwd)"
cp "$WORK_DIR/circuit.sp" "$WORK_DIR/circuit_hidden.sp"
sed -i 's/^\\.end$/.measure TRAN tdfall TRIG v(in) VAL=0.9 FALL=1 TARG v(out) VAL=0.9 FALL=1\\n.end/' "$WORK_DIR/circuit_hidden.sp"
hspice -i "$WORK_DIR/circuit_hidden.sp" -o hidden_run 2>&1

python3 -c "
import re, json, os

existing = {}
if os.path.isfile('metrics.json'):
    try: existing = json.load(open('metrics.json'))
    except: pass

lines = open('hidden_run.lis').read().splitlines()
for line in lines:
    m = re.match(r'^\\s*(td\\w+)\\s*=\\s*([0-9eE.+\\-]+[a-zA-Z]*)', line)
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
"""


def _spectre_netlist(r: str, c: str, pulse_width_ns: float, sim_time_ns: float) -> str:
    pw = f"{pulse_width_ns}n"
    pt = f"{pulse_width_ns * 2}n"
    st = f"{sim_time_ns}n"
    return f"""\
// RC low-pass filter - Spectre netlist
simulator lang=spectre
global 0

// Power supply
vdd (vdd 0) vsource type=dc dc=1.8

// Input pulse
vin (in 0) vsource type=pulse val0=0 val1=1.8 delay=1n rise=500p fall=500p width={pw} period={pt}

// RC low-pass filter
r1 (in out) resistor r={r}
c1 (out 0) capacitor c={c}

// Analysis
tran tran stop={st} errpreset=moderate

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

json.dump(metrics, open('metrics.json', 'w'), indent=2)
"
"""


def _spectre_run_hidden() -> str:
    return """\
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

    def _generate_rc_config(self, local_index: int) -> dict:
        """Generate a diverse RC config from the RNG."""
        r_sol_choices = [220, 330, 470, 560, 680, 820,
                         1000, 1200, 1500, 1800, 2200, 2700, 3300, 3900, 4700, 5600, 6800, 8200,
                         10000, 12000, 15000, 18000, 22000, 27000, 33000, 39000, 47000]
        r_sol = self.rng.choice(r_sol_choices)
        r_bug_mult = self.rng.uniform(5.0, 20.0)
        r_bug = int(r_sol * r_bug_mult)

        c_choices = [1e-12, 2.2e-12, 3.3e-12, 4.7e-12, 6.8e-12,
                     1e-11, 1.5e-11, 2.2e-11, 3.3e-11, 4.7e-11,
                     6.8e-11, 1e-10, 1.5e-10, 2.2e-10, 3.3e-10, 4.7e-10]
        c = self.rng.choice(c_choices)

        rc_sol = r_sol * c
        rc_bug = r_bug * c

        target_delay = rc_sol * 0.7
        target_delay_ns = target_delay * 1e9
        range_frac = self.rng.uniform(0.15, 0.35)
        pub_min = target_delay_ns * (1.0 - range_frac) * 1e-9
        pub_max = target_delay_ns * (1.0 + range_frac) * 1e-9

        pulse_width_ns = max(50.0, rc_bug * 1e9 * 3.0)
        sim_time_ns = pulse_width_ns * 1.5

        return {
            "r_bug": r_bug, "r_sol": r_sol, "c": c,
            "pub_min": pub_min, "pub_max": pub_max,
            "hid_min": pub_min, "hid_max": pub_max,
            "pulse_width_ns": pulse_width_ns, "sim_time_ns": sim_time_ns,
        }

    def generate_one(self, task_index: int) -> Path:
        n_types = 50  # 50 HSPICE + 50 Spectre
        is_spectre = task_index >= n_types
        tool = "spectre" if is_spectre else "hspice"
        prefix = "spectre" if is_spectre else "hspice"
        local_index = task_index % n_types

        cfg = self._generate_rc_config(local_index)

        # Use offset 1000 to avoid conflicting with P1 task IDs (0-999)
        task_id = f"task_{1000 + task_index:06d}"
        task_dir = self.output_dir / f"{prefix}_gen_{task_index:06d}"
        task_dir.mkdir(parents=True, exist_ok=True)

        (task_dir / "files").mkdir(exist_ok=True)
        (task_dir / "hidden").mkdir(exist_ok=True)
        (task_dir / "solution").mkdir(exist_ok=True)

        r_bug_str = str(cfg["r_bug"])
        r_sol_str = str(cfg["r_sol"])
        c_str = f"{cfg['c']}"
        pw = cfg["pulse_width_ns"]
        st = cfg["sim_time_ns"]

        # Write circuit files
        if is_spectre:
            (task_dir / "files" / "circuit.scs").write_text(_spectre_netlist(r_bug_str, c_str, pw, st))
            (task_dir / "solution" / "circuit.scs").write_text(_spectre_netlist(r_sol_str, c_str, pw, st))
            (task_dir / "files" / "run_public.sh").write_text(_spectre_run_public())
            (task_dir / "hidden" / "run_hidden.sh").write_text(_spectre_run_hidden())
        else:
            (task_dir / "files" / "circuit.sp").write_text(_hspice_netlist(r_bug_str, c_str, pw, st))
            (task_dir / "solution" / "circuit.sp").write_text(_hspice_netlist(r_sol_str, c_str, pw, st))
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
The input signal is a pulse from 0V to 1.8V with 500ps rise/fall times.

The 50% rise delay (time for output to reach 0.9V on the rising edge) must be
between {cfg['pub_min']*1e9:.2f}ns and {cfg['pub_max']*1e9:.2f}ns.

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
                "config_index": local_index,
                "tool": tool,
                "r_bug": cfg["r_bug"],
                "r_sol": cfg["r_sol"],
                "c": cfg["c"],
                "pulse_width_ns": cfg["pulse_width_ns"],
            },
            "version": "1.0.0",
        }
        (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")

        return task_dir
