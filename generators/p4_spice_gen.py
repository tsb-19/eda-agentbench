"""P4 SPICE Sim task generator — RC rise/fall delay + RLC settling, HSPICE + Spectre."""

from __future__ import annotations

import json
from pathlib import Path

from generators.base import BaseGenerator


# ---------------------------------------------------------------------------
# HSPICE netlists
# ---------------------------------------------------------------------------

def _hspice_netlist(r: str, c: str, pulse_width_ns: float, sim_time_ns: float,
                    circuit_type: str = "rc_rise_delay") -> str:
    pw = f"{pulse_width_ns}n"
    pt = f"{pulse_width_ns * 2}n"
    st = f"{sim_time_ns}n"
    measures = {
        "rc_rise_delay": (
            ".measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1\n"
            ".measure tran tdfall trig v(in) val=0.9 fall=1 targ v(out) val=0.9 fall=1"
        ),
        "rc_fall_delay": (
            ".measure tran tdfall trig v(in) val=0.9 fall=1 targ v(out) val=0.9 fall=1\n"
            ".measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1"
        ),
    }
    m = measures[circuit_type]
    return f"""\
* {circuit_type.replace('_', ' ').title()} - HSPICE netlist
.global 0

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p {pw} {pt}

* RC low-pass filter
r1 in out {r}
c1 out 0 {c}

* Analysis
.tran 50p {st}

* Measure delays
{m}

.end
"""


def _hspice_rlc_netlist(r: str, l: str, c: str,
                         pulse_width_ns: float, sim_time_ns: float) -> str:
    pw = f"{pulse_width_ns}n"
    pt = f"{pulse_width_ns * 2}n"
    st = f"{sim_time_ns}n"
    return f"""\
* RLC bandpass filter - HSPICE netlist
.global 0

* Power supply
vdd vdd 0 dc 1.8

* Input pulse
vin in 0 pulse 0 1.8 1n 500p 500p {pw} {pt}

* RLC bandpass filter
l1 in mid {l}
r1 mid out {r}
c1 out 0 {c}

* Analysis - timestep fine enough for LC oscillation
.tran 2n {st}

* Measure delays
.measure tran tdrise trig v(in) val=0.9 rise=1 targ v(out) val=0.9 rise=1
.measure tran tdfall trig v(in) val=0.9 fall=1 td={pw} targ v(out) val=0.9 fall=1

.end
"""


# ---------------------------------------------------------------------------
# HSPICE run scripts
# ---------------------------------------------------------------------------

def _hspice_run_public(circuit_type: str = "rc_rise_delay") -> str:
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


def _hspice_run_hidden(circuit_type: str = "rc_rise_delay") -> str:
    sed_extra = ""
    if circuit_type == "rc_rise_delay":
        sed_extra = (
            "sed -i 's/^\\.end$/.measure TRAN tdfall TRIG v(in) VAL=0.9 FALL=1"
            " TARG v(out) VAL=0.9 FALL=1\\n.end/' \"$WORK_DIR/circuit_hidden.sp\""
        )
    elif circuit_type == "rc_fall_delay":
        sed_extra = (
            "sed -i 's/^\\.end$/.measure TRAN tdrise TRIG v(in) VAL=0.9 RISE=1"
            " TARG v(out) VAL=0.9 RISE=1\\n.end/' \"$WORK_DIR/circuit_hidden.sp\""
        )
    else:
        sed_extra = "true  # tdrise already measured in public run"
    return f"""\
#!/bin/bash
set -e
WORK_DIR="$(pwd)"
cp "$WORK_DIR/circuit.sp" "$WORK_DIR/circuit_hidden.sp"
{sed_extra}
hspice -i "$WORK_DIR/circuit_hidden.sp" -o hidden_run 2>&1

python3 -c "
import re, json, os

existing = {{}}
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


# ---------------------------------------------------------------------------
# Spectre netlists
# ---------------------------------------------------------------------------

def _spectre_netlist(r: str, c: str, pulse_width_ns: float, sim_time_ns: float,
                     circuit_type: str = "rc_rise_delay") -> str:
    pw = f"{pulse_width_ns}n"
    pt = f"{pulse_width_ns * 2}n"
    st = f"{sim_time_ns}n"
    topology = {
        "rc_rise_delay": (
            f"r1 (in out) resistor r={r}\n"
            f"c1 (out 0) capacitor c={c}"
        ),
        "rc_fall_delay": (
            f"r1 (in out) resistor r={r}\n"
            f"c1 (out 0) capacitor c={c}"
        ),
    }
    topo = topology[circuit_type]
    return f"""\
// {circuit_type.replace('_', ' ').title()} - Spectre netlist
simulator lang=spectre
global 0

// Power supply
vdd (vdd 0) vsource type=dc dc=1.8

// Input pulse
vin (in 0) vsource type=pulse val0=0 val1=1.8 delay=1n rise=500p fall=500p width={pw} period={pt}

// RC low-pass filter
{topo}

// Analysis
tran tran stop={st} errpreset=moderate

// Save outputs
save in out
"""


def _spectre_rlc_netlist(r: str, l: str, c: str,
                          pulse_width_ns: float, sim_time_ns: float) -> str:
    pw = f"{pulse_width_ns}n"
    pt = f"{pulse_width_ns * 2}n"
    st = f"{sim_time_ns}n"
    return f"""\
// RLC bandpass filter - Spectre netlist
simulator lang=spectre
global 0

// Power supply
vdd (vdd 0) vsource type=dc dc=1.8

// Input pulse
vin (in 0) vsource type=pulse val0=0 val1=1.8 delay=1n rise=500p fall=500p width={pw} period={pt}

// RLC bandpass filter
l1 (in mid) inductor l={l}
r1 (mid out) resistor r={r}
c1 (out 0) capacitor c={c}

// Analysis - timestep fine enough for LC oscillation
tran tran stop={st} errpreset=moderate maxstep=2n

// Save outputs
save in out
"""


# ---------------------------------------------------------------------------
# Spectre run scripts
# ---------------------------------------------------------------------------

def _spectre_run_public(circuit_type: str = "rc_rise_delay") -> str:
    crossing_logic = """\
threshold = 0.9
in_rise = find_crossing_time(times, in_vals, threshold, rise=True)
out_rise = find_crossing_time(times, out_vals, threshold, rise=True)

metrics = {}
if in_rise is not None and out_rise is not None:
    metrics['tdrise'] = out_rise - in_rise

in_fall = find_crossing_time(times, in_vals, threshold, rise=False)
out_fall = find_crossing_time(times, out_vals, threshold, rise=False, t_start=in_fall)
if in_fall is not None and out_fall is not None:
    metrics['tdfall'] = out_fall - in_fall
"""
    return f"""\
#!/bin/bash
set -e
WORK_DIR="$(pwd)"
spectre circuit.scs +escchars +log spectre.out -format nutascii 2>&1 | tee spectre_public.log

python3 -c "
import re, json, os

def find_crossing_time(times, values, threshold, rise=True, t_start=None):
    for i in range(1, len(values)):
        if t_start is not None and times[i] < t_start:
            continue
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
    json.dump({{}}, open('metrics.json', 'w'))
    exit(0)

with open(raw_file) as f:
    content = f.read()
data = {{}}
values_section = content.split('Values:')
if len(values_section) < 2:
    json.dump({{}}, open('metrics.json', 'w'))
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

{crossing_logic}
json.dump(metrics, open('metrics.json', 'w'), indent=2)
"
"""


def _spectre_run_hidden(circuit_type: str = "rc_rise_delay") -> str:
    if circuit_type in ("rc_rise_delay", "rc_fall_delay"):
        crossing_logic = """\
threshold = 0.9
in_fall = find_crossing_time(times, in_vals, threshold, rise=False)
out_fall = find_crossing_time(times, out_vals, threshold, rise=False)

metrics = {}
if in_fall is not None and out_fall is not None:
    metrics['tdfall'] = out_fall - in_fall
"""
    else:
        crossing_logic = """\
threshold = 0.9
in_rise = find_crossing_time(times, in_vals, threshold, rise=True)
out_rise = find_crossing_time(times, out_vals, threshold, rise=True)

metrics = {}
if in_rise is not None and out_rise is not None:
    metrics['tdrise'] = out_rise - in_rise
"""
    return f"""\
#!/bin/bash
set -e
WORK_DIR="$(pwd)"

spectre circuit.scs +escchars +log spectre_hidden.out -format nutascii 2>&1 | tee spectre_hidden.log

python3 -c "
import re, json, os

def find_crossing_time(times, values, threshold, rise=True, t_start=None):
    for i in range(1, len(values)):
        if t_start is not None and times[i] < t_start:
            continue
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
    existing = {{}}
    if os.path.isfile('metrics.json'):
        try: existing = json.load(open('metrics.json'))
        except: pass
    json.dump(existing, open('metrics.json', 'w'), indent=2)
    exit(0)

with open(raw_file) as f:
    content = f.read()
data = {{}}
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

{crossing_logic}
existing = {{}}
if os.path.isfile('metrics.json'):
    try: existing = json.load(open('metrics.json'))
    except: pass
existing.update(metrics)
json.dump(existing, open('metrics.json', 'w'), indent=2)
"
"""


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_PROMPTS = {
    "rc_rise_delay": (
        "# Task: Fix RC Low-Pass Filter Rise Time\n\n"
        "## Problem\n\n"
        "The RC low-pass filter in `{circuit_file}` has a rise time that is too slow.\n"
        "The input signal is a pulse from 0V to 1.8V with 500ps rise/fall times.\n\n"
        "The 50% rise delay (time for output to reach 0.9V on the rising edge) must be\n"
        "between {pub_min_ns}ns and {pub_max_ns}ns.\n\n"
        "## Your Task\n\n"
        "1. Analyze the circuit in `{circuit_file}`\n"
        "2. Identify the component causing the slow rise time\n"
        "3. Modify the editable file to fix the rise delay\n"
        "4. Run `bash run_public.sh` to verify your fix\n\n"
        "## Constraints\n\n"
        "- You may only modify `{circuit_file}`\n"
        "- Do not modify `run_public.sh` or any other files\n"
        "- The RC filter topology must remain the same (series R, shunt C)\n"
        "- The input signal parameters must not change\n\n"
        "## Files\n\n"
        "- `{circuit_file}` — {tool_name} netlist (editable)\n"
        "- `run_public.sh` — Public test script (read-only)\n"
    ),
    "rc_fall_delay": (
        "# Task: Fix RC Low-Pass Filter Fall Time\n\n"
        "## Problem\n\n"
        "The RC low-pass filter in `{circuit_file}` has a fall time that is too slow.\n"
        "The input signal is a pulse from 0V to 1.8V with 500ps rise/fall times.\n\n"
        "The 50% fall delay (time for output to reach 0.9V on the falling edge) must be\n"
        "between {pub_min_ns}ns and {pub_max_ns}ns.\n\n"
        "## Your Task\n\n"
        "1. Analyze the circuit in `{circuit_file}`\n"
        "2. Identify the component causing the slow fall time\n"
        "3. Modify the editable file to fix the fall delay\n"
        "4. Run `bash run_public.sh` to verify your fix\n\n"
        "## Constraints\n\n"
        "- You may only modify `{circuit_file}`\n"
        "- Do not modify `run_public.sh` or any other files\n"
        "- The RC filter topology must remain the same (series R, shunt C)\n"
        "- The input signal parameters must not change\n\n"
        "## Files\n\n"
        "- `{circuit_file}` — {tool_name} netlist (editable)\n"
        "- `run_public.sh` — Public test script (read-only)\n"
    ),
    "rlc_settling": (
        "# Task: Fix RLC Filter Response Time\n\n"
        "## Problem\n\n"
        "The RLC bandpass filter in `{circuit_file}` has a response time that is too slow.\n"
        "The input signal is a pulse from 0V to 1.8V with 500ps rise/fall times.\n\n"
        "The 50% rise delay (time for output to reach 0.9V on the rising edge) must be\n"
        "between {pub_min_ns}ns and {pub_max_ns}ns.\n\n"
        "## Your Task\n\n"
        "1. Analyze the circuit in `{circuit_file}`\n"
        "2. Identify the component causing the slow response\n"
        "3. Modify the editable file to fix the rise delay\n"
        "4. Run `bash run_public.sh` to verify your fix\n\n"
        "## Constraints\n\n"
        "- You may only modify `{circuit_file}`\n"
        "- Do not modify `run_public.sh` or any other files\n"
        "- The RLC filter topology must remain the same (series L, series R, shunt C)\n"
        "- The input signal parameters must not change\n\n"
        "## Hint\n\n"
        "- An overdamped RLC circuit responds more slowly than a well-damped one\n"
        "- The damping ratio depends on R, L, and C values\n\n"
        "## Files\n\n"
        "- `{circuit_file}` — {tool_name} netlist (editable)\n"
        "- `run_public.sh` — Public test script (read-only)\n"
    ),
}


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------

class P4SPICEGenerator(BaseGenerator):
    """Generates P4 SPICE Sim tasks (HSPICE + Spectre, multiple circuit types).

    Task index ranges (100 tasks each):
      0-99:   RC rise delay (50 HSPICE + 50 Spectre)
      100-199: RC fall delay (50 HSPICE + 50 Spectre)
      200-299: RLC settling  (50 HSPICE + 50 Spectre)
    """

    CIRCUIT_TYPES = ["rc_rise_delay", "rc_fall_delay", "rlc_settling"]

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

    @staticmethod
    def _rlc_trise(r: float, l: float, c: float, v_threshold: float = 0.9,
                   v_dc: float = 1.8) -> float:
        """Calculate rise time for RLC bandpass filter (voltage across C).

        Step response: v_c(t) = V_dc * [1 - e^(-zeta*w0*t) * sin(wd*t + phi) / sqrt(1-zeta^2)]
        where phi = arccos(zeta).

        For underdamped (zeta < 1): solve numerically.
        For overdamped (zeta >= 1): use dominant root.
        """
        import math
        alpha = r / (2.0 * l)
        w0 = 1.0 / math.sqrt(l * c)
        zeta = alpha / w0

        if zeta < 1.0:
            wd = w0 * math.sqrt(1.0 - zeta ** 2)
            phi = math.acos(zeta)
            # Need: e^(-alpha*t) * sin(wd*t + phi) / sqrt(1-zeta^2) = 1 - v_threshold/v_dc
            target = (1.0 - v_threshold / v_dc) * math.sqrt(1.0 - zeta ** 2)
            # Binary search for t
            t_lo, t_hi = 1e-12, 100e-6
            for _ in range(100):
                t_mid = (t_lo + t_hi) / 2.0
                val = math.exp(-alpha * t_mid) * math.sin(wd * t_mid + phi)
                if val > target:
                    t_lo = t_mid
                else:
                    t_hi = t_mid
            return (t_lo + t_hi) / 2.0
        else:
            # Overdamped: v_c(t) = V_dc * [1 - A1*e^(s1*t) - A2*e^(s2*t)]
            gamma = math.sqrt(max(zeta ** 2 - 1.0, 1e-12))  # dimensionless
            s1 = -w0 * (zeta - gamma)  # dominant root (less negative, rad/s)
            # Approximate: v_c(t) ≈ V_dc * [1 - e^(s1*t)] for large t
            # Need: 1 - e^(s1*t) = v_threshold/v_dc
            # e^(s1*t) = 1 - v_threshold/v_dc
            # s1*t = ln(1 - v_threshold/v_dc)
            # t = ln(1 - v_threshold/v_dc) / s1
            return math.log(1.0 - v_threshold / v_dc) / s1

    def _generate_rlc_config(self, local_index: int) -> dict:
        """Generate a diverse RLC config from the RNG."""
        r_sol_choices = [100, 150, 220, 330, 470, 560, 680, 820,
                         1000, 1200, 1500, 1800, 2200, 2700, 3300]
        r_sol = self.rng.choice(r_sol_choices)
        r_bug_mult = self.rng.uniform(4.0, 10.0)
        r_bug = int(r_sol * r_bug_mult)

        l_choices = [1e-6, 2.2e-6, 3.3e-6, 4.7e-6, 6.8e-6,
                     1e-5, 2.2e-5, 3.3e-5, 4.7e-5, 6.8e-5,
                     1e-4, 2.2e-4, 3.3e-4, 4.7e-4]
        l_val = self.rng.choice(l_choices)

        c_choices = [1e-12, 2.2e-12, 4.7e-12, 1e-11, 2.2e-11,
                     4.7e-11, 1e-10, 2.2e-10, 4.7e-10, 1e-9]
        c = self.rng.choice(c_choices)

        import math
        omega0 = 1.0 / math.sqrt(l_val * c)
        zeta_sol = r_sol / (2.0 * math.sqrt(l_val / c))

        trise_sol = self._rlc_trise(r_sol, l_val, c)
        trise_bug = self._rlc_trise(r_bug, l_val, c)

        trise_sol_ns = trise_sol * 1e9
        range_frac = self.rng.uniform(0.15, 0.35)
        pub_min = trise_sol_ns * (1.0 - range_frac) * 1e-9
        pub_max = trise_sol_ns * (1.0 + range_frac) * 1e-9

        period_ns = 2.0 * math.pi / omega0 * 1e9 if zeta_sol < 1.0 else trise_sol_ns
        pulse_width_ns = max(50.0, period_ns * 5.0)
        sim_time_ns = max(pulse_width_ns * 2.0, trise_bug * 1e9 * 3.0)

        return {
            "r_bug": r_bug, "r_sol": r_sol, "l": l_val, "c": c,
            "pub_min": pub_min, "pub_max": pub_max,
            "hid_min": pub_min, "hid_max": pub_max,
            "pulse_width_ns": pulse_width_ns, "sim_time_ns": sim_time_ns,
        }

    def generate_one(self, task_index: int) -> Path:
        n_per_type = 100
        type_idx = task_index // n_per_type
        if type_idx >= len(self.CIRCUIT_TYPES):
            type_idx = len(self.CIRCUIT_TYPES) - 1
        circuit_type = self.CIRCUIT_TYPES[type_idx]

        n_tool_split = n_per_type // 2
        local_index = task_index % n_per_type
        is_spectre = local_index >= n_tool_split
        tool = "spectre" if is_spectre else "hspice"
        prefix = "spectre" if is_spectre else "hspice"

        if circuit_type == "rlc_settling":
            cfg = self._generate_rlc_config(local_index)
        else:
            cfg = self._generate_rc_config(local_index)

        # Task IDs: offset by type_idx * 1000 + 2000 to avoid conflicts
        task_id = f"task_{2000 + type_idx * 1000 + task_index:06d}"
        task_dir = self.output_dir / f"{prefix}_{circuit_type}_{task_index:06d}"
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
            if circuit_type == "rlc_settling":
                l_str = f"{cfg['l']}"
                (task_dir / "files" / "circuit.scs").write_text(
                    _spectre_rlc_netlist(r_bug_str, l_str, c_str, pw, st))
                (task_dir / "solution" / "circuit.scs").write_text(
                    _spectre_rlc_netlist(r_sol_str, l_str, c_str, pw, st))
            else:
                (task_dir / "files" / "circuit.scs").write_text(
                    _spectre_netlist(r_bug_str, c_str, pw, st, circuit_type))
                (task_dir / "solution" / "circuit.scs").write_text(
                    _spectre_netlist(r_sol_str, c_str, pw, st, circuit_type))
            (task_dir / "files" / "run_public.sh").write_text(
                _spectre_run_public(circuit_type))
            (task_dir / "hidden" / "run_hidden.sh").write_text(
                _spectre_run_hidden(circuit_type))
        else:
            if circuit_type == "rlc_settling":
                l_str = f"{cfg['l']}"
                (task_dir / "files" / "circuit.sp").write_text(
                    _hspice_rlc_netlist(r_bug_str, l_str, c_str, pw, st))
                (task_dir / "solution" / "circuit.sp").write_text(
                    _hspice_rlc_netlist(r_sol_str, l_str, c_str, pw, st))
            else:
                (task_dir / "files" / "circuit.sp").write_text(
                    _hspice_netlist(r_bug_str, c_str, pw, st, circuit_type))
                (task_dir / "solution" / "circuit.sp").write_text(
                    _hspice_netlist(r_sol_str, c_str, pw, st, circuit_type))
            (task_dir / "files" / "run_public.sh").write_text(
                _hspice_run_public(circuit_type))
            (task_dir / "hidden" / "run_hidden.sh").write_text(
                _hspice_run_hidden(circuit_type))

        # Make scripts executable
        (task_dir / "files" / "run_public.sh").chmod(0o755)
        (task_dir / "hidden" / "run_hidden.sh").chmod(0o755)

        # Circuit filename
        circuit_file = "circuit.scs" if is_spectre else "circuit.sp"
        tool_name = "Spectre" if is_spectre else "HSPICE"

        # Write prompt
        pub_min_ns = f"{cfg['pub_min'] * 1e9:.2f}"
        pub_max_ns = f"{cfg['pub_max'] * 1e9:.2f}"
        prompt = _PROMPTS[circuit_type].format(
            circuit_file=circuit_file,
            tool_name=tool_name,
            pub_min_ns=pub_min_ns,
            pub_max_ns=pub_max_ns,
        )
        (task_dir / "prompt.md").write_text(prompt)

        # Determine metric names
        pub_measure = "tdrise"
        hid_measure = "tdfall"

        # Write metadata
        circuit_ext = "scs" if is_spectre else "sp"
        generator_info = {
            "script": "p4_spice_gen.py",
            "seed": self.seed,
            "config_index": local_index,
            "tool": tool,
            "circuit_type": circuit_type,
            "r_bug": cfg["r_bug"],
            "r_sol": cfg["r_sol"],
            "c": cfg["c"],
            "pulse_width_ns": cfg["pulse_width_ns"],
        }
        if circuit_type == "rlc_settling":
            generator_info["l"] = cfg["l"]

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
                        "measure": pub_measure,
                        "min": cfg["pub_min"],
                        "max": cfg["pub_max"],
                    },
                    "hidden": {
                        "measure": hid_measure,
                        "min": cfg["hid_min"],
                        "max": cfg["hid_max"],
                    },
                },
            },
            "sanitizer": {"enabled": True},
            "generator": generator_info,
            "version": "1.0.0",
        }
        (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")

        return task_dir
