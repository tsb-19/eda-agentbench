#!/bin/bash
# P4 damping design - PUBLIC runner: simulate, then REPORT the measured
# delay / overshoot / settling. It does NOT tell you pass/fail vs the spec --
# compare the numbers to the spec in the prompt and size R1 yourself.
set -e
spectre circuit.scs +escchars +log spectre_public.out -format nutascii 2>&1 | tee spectre_public.log

python3 - <<'PY'
import os
raw = "circuit.raw"
def dump_empty():
    open("wave.csv", "w").close()
if not os.path.isfile(raw):
    dump_empty(); raise SystemExit
content = open(raw).read()
sec = content.split("Values:")
if len(sec) < 2:
    dump_empty(); raise SystemExit
rows = {}
for line in sec[1].strip().split(chr(10)):
    p = line.split()
    if len(p) >= 4:
        try:
            rows[int(p[0])] = [float(x) for x in p[1:]]
        except ValueError:
            pass
with open("wave.csv", "w") as f:
    f.write("# t v_in v_out" + chr(10))
    for i in sorted(rows):
        r = rows[i]
        f.write("%.9e %.9e %.9e%s" % (r[0], r[1], r[2], chr(10)))
PY

python3 measure_specs.py wave.csv spec_public.json --mode public
