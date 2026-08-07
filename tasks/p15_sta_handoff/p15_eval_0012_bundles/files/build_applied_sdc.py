# Public: translate exception_config.json (+ partition_pins.json + intent_exception.json)
# into agent_applied.sdc. Deterministic; same logic run_public and run_hidden use.
import json
cfg = json.load(open("exception_config.json"))
pins = json.load(open("partition_pins.json"))["partition_pins"]
iexc = json.load(open("intent_exception.json"))["intent_exception"]
base = open("constraints.sdc").read().splitlines()
lines = [l for l in base]
intent = cfg.get("intent_class"); part = cfg.get("target_partition")
exc = iexc.get(intent, {"type": "none"})
if exc.get("type") == "false_path" and part in pins:
    lines.append("set_false_path -from [get_pins %s] -to [get_pins %s]" % (pins[part]["from"], pins[part]["to"]))
elif exc.get("type") == "multicycle" and part in pins:
    lines.append("set_multicycle_path %d -setup -from [get_pins %s] -to [get_pins %s]"
                 % (exc.get("cycles", 2), pins[part]["from"], pins[part]["to"]))
open("agent_applied.sdc", "w").write("\n".join(lines) + "\n")
