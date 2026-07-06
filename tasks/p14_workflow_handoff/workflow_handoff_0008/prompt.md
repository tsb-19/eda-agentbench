# Task: infer the typed-axis membership AND the unique typed package, then regenerate the fresh sign-off chain

You are handed a downstream **timing sign-off handoff** whose evidence is out of date AND whose `flow_config.json` carries a value-swap on the typed axes. The typed axes are **NOT** published as a schema -- infer membership from the report context (`op_point=` / `mode=`), the spec terminology, PVT notation, and the coverage facts. Then infer the unique typed assignment (intersect C1–C5), repair `flow_config.json`, and **rerun the evidence flow (two ordered stages)** so the evidence is freshly generated from the inferred package.

Steps:
1. Infer axis membership from the evidence (PVT notation reveals the operating-point values; the coverage fact reveals the clock; the manifest+interface reveal the netlist; the remaining axis is the signoff mode).
2. Infer the unique typed assignment by intersecting C1–C5; reject every pairwise-plausible decoy.
3. Repair `flow_config.json` to the inferred netlist + (scenario, corner) pair + clock identity.
4. Run `bash run_evidence_stage1.sh` to regenerate `timing_report.rpt` + `evidence_manifest.json`.
5. Run `bash run_evidence_stage2.sh` to regenerate `stage2_summary.json` (binds the fresh stage-1 digest).
6. Confirm `bash run_public.sh` shows `evidence=FRESH stage2=FRESH`, `signoff=OK`, non-zero intended-clock coverage, and the consumed package == the inferred typed assignment.

A package with the correct netlist+clock still PrimeTime-signs-off GREEN when the typed axes are swapped -- typed binding, not signoff, is what rejects it. You may edit `flow_config.json`. Do **not** edit netlists, the library, the manifest, `glossary.md`, the decoy reports, the generators, or the runners; do not hand-write evidence.

When done, briefly state the axis-binding root cause (which values are operating-point vs signoff-mode and how you inferred it), which decoys are mis-typed, and confirm you inferred the unique typed assignment and reran both stages in order.
