# Public parser: extract the requested metric's value from the HSPICE .lis (handles scale suffixes).
import re, sys, json
SCALE = {'':1,'f':1e-15,'p':1e-12,'n':1e-9,'u':1e-6,'m':1e-3,'%':1e-2,'k':1e3,'x':1e6,'meg':1e6,'g':1e9,'t':1e12}
lis = open(sys.argv[1]).read() if len(sys.argv) > 1 else open("hspice_run.lis").read()
metric = sys.argv[2] if len(sys.argv) > 2 else "gain"
name = {"gain": "gain_db", "gbw": "gbw_hz", "pm": "pm_deg", "slew": "slew_v", "vdsat": "vdsat_v"}[metric]
val = None
for line in lis.splitlines():
    m = re.match(r"^\s*" + re.escape(name) + r"\s*=\s*([0-9.eE+\-]+[a-zA-Z%]*)", line)
    if m:
        tok = m.group(1).lower()
        mm = re.match(r"^([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)([a-z%]*)$", tok)
        if mm:
            try:
                val = float(mm.group(1)) * SCALE.get(mm.group(2), 1); break
            except ValueError:
                pass
if val is not None and metric == "gbw":
    val = val / 1e6  # Hz -> MHz
print(json.dumps({"metric": metric, "value": val, "measure_name": name}))
