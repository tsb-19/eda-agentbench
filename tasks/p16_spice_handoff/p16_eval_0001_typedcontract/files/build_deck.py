# Public: regenerate the executable deck from the IMMUTABLE circuit core + meas_config.
# The core (circuit_core.sp) is integrity-hashed and immutable; only meas_config.json is editable.
import json
cfg = json.load(open("meas_config.json"))
CAV = json.load(open("corner_models.json"))["corner_av"]
LDC = json.load(open("load_models.json"))["load_c"]
av = CAV.get(cfg.get("corner"), 50.0); cload = LDC.get(cfg.get("load_condition"), 5e-12)
core = open("circuit_core.sp").read()              # immutable template
deck = core.replace("{av}", "%g" % av).replace("{cload}", "%g" % cload)
open("circuit_built.sp", "w").write(deck)          # derived artifact (regenerated each run)
