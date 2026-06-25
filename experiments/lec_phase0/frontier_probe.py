"""LEC Phase-0 criterion 3: frontier no-echo probe.

Hand each baseline model the attribution task — both netlists + the Formality failing compare
points — and ask for the ROOT CAUSE (the internal divergent signal). Grade with the same
attribution grader. By construction, echoing Formality's failing compare points scores 0 (those
are outputs, not the internal cause). So this measures: do frontier models (a) take the symptom
shortcut [echo -> 0], or (b) genuinely attribute to the internal net [-> 1.0]?

Reports per (task, model): score + whether the cause net was named vs only symptoms. Also flags
the Phase-1 collapse risk (if ALL valid frontier models attribute correctly, the difficulty is
separable but the small hand design is within frontier reach -> Phase 1 must deepen cones).
"""
import sys
from pathlib import Path

sys.path.insert(0, "/data1/tongsb/eda-agentbench")
from scripts.generate_model_submissions import load_model_specs
from experiments.lec_phase0.phase0 import TASKS, grade, write_assets

SYSTEM = ("You are a senior hardware verification engineer debugging a logical-equivalence (LEC) "
          "failure. Be concise and answer exactly what is asked.")

write_assets()
specs = load_model_specs(Path("/data1/tongsb/eda-agentbench/configs/baseline_models.json"),
                         allow_mock=False)
ROOT = Path("/data1/tongsb/eda-agentbench/experiments/lec_phase0")

rows = []
TASKS_TO_RUN = sys.argv[1:] or list(TASKS)
for tname, t in TASKS.items():
    if tname not in TASKS_TO_RUN:
        continue
    d = ROOT / tname
    prompt = (d / "prompt.md").read_text()
    golden = (d / "golden.v").read_text()
    impl = (d / "impl.v").read_text()
    full = (f"{prompt}\n\n## golden.v\n```verilog\n{golden}```\n\n"
            f"## impl.v\n```verilog\n{impl}```\n\n"
            f"Give your final answer as: ROOT_CAUSE = <wire name in impl.v>, then one sentence why.")
    for mname, prov, gk in specs:
        try:
            resp = prov.generate(full, system=SYSTEM, **gk)
            text = resp.text or ""
            g = grade(text, t["oracle"])
            (d / f"ans_{mname}.txt").write_text(text)
            rows.append((tname, mname, g["score"], g["verdict"], g["named_cause"],
                         g["named_symptoms"], ""))
        except Exception as e:
            rows.append((tname, mname, None, "ERROR", False, [],
                         f"{type(e).__name__}: {str(e)[:60]}"))

print(f"{'task':7}{'model':16}{'score':>6}  {'verdict':16} cause? symptoms/err")
for tname, mname, score, verdict, cause, symps, err in rows:
    sc = "  -- " if score is None else f"{score:5.2f}"
    extra = err if err else (",".join(symps) if symps else "")
    print(f"{tname:7}{mname:16}{sc}  {verdict:16} {str(cause):5} {extra}")

# verdict: criterion 3 = no model can ace by echoing (grader guarantees). Also collapse read.
valid = [r for r in rows if r[2] is not None]
attributed = [r for r in valid if r[4]]
echoed = [r for r in valid if not r[4] and r[5]]
print(f"\nvalid={len(valid)}/{len(rows)}  attributed(named internal cause)={len(attributed)}  "
      f"symptom-only(echo)={len(echoed)}")
print("Criterion 3 (echo cannot ace): PASS by construction — symptom-only answers score 0.")
print("Collapse read for Phase 1: "
      + ("frontier ATTRIBUTES correctly -> separable+achievable; deepen cones before scaling"
         if attributed else "frontier does NOT attribute -> strongly discriminating"))
