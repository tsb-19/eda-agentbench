# Public: translate meas_config.json into circuit_built.sp (deck params + analysis).
import json
cfg = json.load(open("meas_config.json"))
CAV = json.load(open("corner_models.json"))["corner_av"]
LDC = json.load(open("load_models.json"))["load_c"]
corner = cfg.get("corner"); load = cfg.get("load_condition")
av = CAV.get(corner, 50.0); cload = LDC.get(load, 5e-12)
open("circuit_built.sp", "w").write(
 "* Family B measurement-handoff circuit (built from meas_config)\n"
 ".param av=%g cload=%g\n"
 "vin in 0 dc 0 ac 1\n"
 "ein outc 0 in 0 av\n"
 "r1 outc outa 1e3\n"
 "c1 outa 0 1.59e-9\n"
 "r2 outa out 1e3\n"
 "c2 out 0 cload\n"
 "rl out 0 1e12\n"
 ".ac dec 20 1 1g\n"
 ".measure ac gain_db max vdb(out)\n"
 ".measure ac gbw_hz when vdb(out)=0 fall=1\n"
 ".end\n" % (av, cload))
