#!/bin/bash
# P4 damping design - HIDDEN runner: enforce the locked L1/C1 (only R1 may be
# tuned), then score the simulated waveform against the spec (continuous).
set -e

VIOL=$(python3 - <<'PY'
import json, re
try:
    spec = json.load(open("spec.json"))
except Exception:
    print(""); raise SystemExit
lock = spec.get("lock", {})
try:
    txt = open("circuit.scs").read()
except OSError:
    print("deck_missing"); raise SystemExit
def getval(inst, key):
    for line in txt.splitlines():
        s = line.strip().lower()
        if s.startswith(inst + " ") or s.startswith(inst + "("):
            m = re.search(r"\b" + key + r"\s*=\s*([0-9.eE+\-]+)", s)
            if m:
                try:
                    return float(m.group(1))
                except ValueError:
                    return None
    return None
viol = ""
for inst, key in (("l1", "l"), ("c1", "c")):
    want = lock.get(key)
    if want is None:
        continue
    got = getval(inst, key)
    tol = lock.get("tol", 0.02)
    if got is None or abs(got - want) > tol * abs(want):
        viol = "%s_%s(%s->%s)" % (inst, key, want, got)
        break
print(viol)
PY
)

if [ -n "$VIOL" ]; then
    echo "SPEC_SCORE: 0.0000"
    echo "SPEC_DETAIL: modified_locked_component:$VIOL"
    exit 0
fi

python3 measure_specs.py wave.csv spec.json --mode hidden
