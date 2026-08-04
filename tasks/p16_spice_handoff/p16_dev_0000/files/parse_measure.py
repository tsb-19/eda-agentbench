# Public-ish parser: extract the requested metric's value from the HSPICE .lis.
import re, sys, json
lis = open(sys.argv[1]).read() if len(sys.argv) > 1 else open("hspice_run.lis").read()
metric = sys.argv[2] if len(sys.argv) > 2 else "gain"
name = {"gain": "gain_db", "gbw": "gbw_hz", "pm": "pm_deg", "slew": "slew_v", "vdsat": "vdsat_v"}[metric]
val = None
for line in lis.splitlines():
    m = re.match(r"^\s*" + re.escape(name) + r"\s*=\s*([0-9.eE+\-]+)", line)
    if m:
        try:
            val = float(m.group(1)); break
        except ValueError:
            pass
# gbw is in Hz; report in MHz. gain is in dB already.
if val is not None and metric == "gbw":
    val = val / 1e6
print(json.dumps({"metric": metric, "value": val, "measure_name": name}))
