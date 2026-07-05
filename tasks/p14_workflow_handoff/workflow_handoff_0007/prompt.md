# Task: infer the unique type-correct package, bind each value to its own axis, AND regenerate the fresh sign-off chain

You are handed a downstream **timing sign-off handoff** whose evidence is out of date AND whose `flow_config.json` carries a **value-swap** on scenario/corner. The typed-axis vocabulary is **published** in `axis_schema.json` -- the challenge is correct **binding**, not vocabulary hiding. Infer the unique typed assignment by intersecting the constraints in `spec.md` (C1 netlist family + C2 clock identity + C3 scenario-typed + C4 corner-typed + C5 scenario/corner pair), bind each value to its OWN axis, then **rerun the evidence flow (two ordered stages)** so the evidence is freshly generated from the inferred package.

Steps:
1. Infer the unique typed assignment (intersect C1-C5); bind each value to its own axis. Do NOT trust any single shipped source; each decoy is locally plausible but mis-typed.
2. Repair `flow_config.json` to that netlist + typed `(scenario, corner)` pair + clock identity (the clock is already `clk_main` -- do not change it).
3. Run `bash run_evidence_stage1.sh` to regenerate `timing_report.rpt` + `evidence_manifest.json` from the repaired inputs.
4. Run `bash run_evidence_stage2.sh` to regenerate `stage2_summary.json` (binds the fresh stage-1 digest).
5. Confirm `bash run_public.sh` shows `evidence=FRESH stage2=FRESH`, `signoff=OK`, non-zero intended-clock coverage, and the consumed package == the inferred typed assignment.

A package with the correct netlist+clock still PrimeTime-signs-off GREEN when scenario/corner are swapped -- type binding, not signoff, is what rejects it. You may edit `flow_config.json`. Do **not** edit netlists, the library, the manifest, `axis_schema.json`, the decoy reports, the generators, or the runners; do not hand-write evidence.

When done, briefly state the axis-binding root cause, which decoys are mis-typed, and confirm you inferred the unique typed assignment and reran both stages in order.
