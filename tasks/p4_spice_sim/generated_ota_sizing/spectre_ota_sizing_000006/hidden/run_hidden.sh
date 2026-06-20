#!/bin/bash
# P4 op-amp sizing - HIDDEN runner: enforce the locked devices/load (only ibias
# and cc may be tuned), then score the AC response against the spec (continuous).
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
def inst_param(inst, key):
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
# Locked: the load cap cl and the gm-defining device widths (w of m1, m6). These
# fix the "physics"; the design must be met through ibias and cc, not by resizing.
for inst, key in (("cl", "c"), ("m1", "w"), ("m6", "w")):
    want = lock.get(inst + "_" + key)
    if want is None:
        continue
    got = inst_param(inst, key)
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

python3 measure_ac.py ac.csv spec.json --mode hidden
