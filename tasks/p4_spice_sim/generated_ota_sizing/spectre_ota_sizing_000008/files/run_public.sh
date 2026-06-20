#!/bin/bash
# P4 op-amp sizing - PUBLIC runner: run the AC analysis, then REPORT the measured
# DC gain / gain-bandwidth / phase margin. It does NOT tell you pass/fail vs the
# spec -- compare the numbers to the spec in the prompt and size ibias/cc yourself.
set -e
spectre circuit.scs +escchars +log spectre_public.out -format nutascii 2>&1 | tee spectre_public.log

python3 - <<'PY'
import math, os
raw = "circuit.raw"
def dump_empty():
    open("ac.csv", "w").close()
if not os.path.isfile(raw):
    dump_empty(); raise SystemExit
content = open(raw).read()
# Variable order: find the index of node 'out' among the saved variables.
out_idx = 1
vsec = content.split("Variables:")
if len(vsec) >= 2:
    head = vsec[1].split("Values:")[0]
    for line in head.strip().splitlines():
        p = line.replace("\t", " ").split()
        # lines look like: "<k> <name> <type>"
        if len(p) >= 2 and p[0].isdigit() and p[1].lower() in ("out", "v(out)", "out2"):
            out_idx = int(p[0]); break
sec = content.split("Values:")
if len(sec) < 2:
    dump_empty(); raise SystemExit
# Group the Values section into per-point blocks. A new point starts at a line
# whose first token is the integer point index; collect every float in the block.
points = []
cur = None
for line in sec[1].strip().splitlines():
    toks = line.replace(",", " ").replace("\t", " ").split()
    if not toks:
        continue
    if toks[0].isdigit() and cur is not None and len(cur) > 0:
        # heuristic: a bare leading integer that indexes a NEW point (block already has data)
        # only treat as a new block boundary if we already saw >= one full var
        pass
    # simpler: detect block start by a leading integer index token AND that we expect a new freq
    if toks[0].isdigit() and (cur is None or len(cur) >= 2 * (out_idx + 1)):
        if cur:
            points.append(cur)
        cur = []
        toks = toks[1:]
    if cur is None:
        cur = []
    for t in toks:
        try:
            cur.append(float(t))
        except ValueError:
            pass
if cur:
    points.append(cur)
with open("ac.csv", "w") as f:
    f.write("# freq_hz gain_db phase_deg\n")
    for fl in points:
        # var k complex = (fl[2k], fl[2k+1]); var0 = frequency (imag ~ 0)
        if len(fl) < 2 * (out_idx + 1):
            continue
        freq = fl[0]
        re, im = fl[2 * out_idx], fl[2 * out_idx + 1]
        mag = math.hypot(re, im)
        gdb = 20.0 * math.log10(mag) if mag > 0 else -300.0
        ph = math.degrees(math.atan2(im, re))
        f.write("%.9e %.9e %.9e\n" % (freq, gdb, ph))
PY

python3 measure_ac.py ac.csv spec_public.json --mode public
