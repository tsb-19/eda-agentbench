# Task: resolve the semantic-role binding, infer the unique package, AND regenerate the fresh sign-off chain

You are handed a downstream **timing sign-off handoff** whose evidence is out of date AND whose `flow_config.json` carries a value-swap on the signoff axes. The reports use canonical `scenario` / `corner` labels; glossary.md states the disjoint typed axes. Infer the unique assignment by intersecting the constraints in `spec.md` (C1 netlist family + C2 clock coverage + C3 scenario-typed + C4 corner-typed + C5 signoff pair), reject every pairwise-plausible decoy, repair `flow_config.json`, and **rerun the evidence flow (two ordered stages)** so the evidence is freshly generated from the inferred package.

Steps:
1. Resolve the semantic role of each report field label from the report intersection. Then Infer the unique assignment by intersecting C1–C5; do NOT trust any single shipped source (each decoy is pairwise plausible but role-mismatched).
2. Repair `flow_config.json` to the inferred netlist + `(scenario, corner)` pair + clock identity (the clock is the only one with non-zero intended-clock coverage).
3. Run `bash run_evidence_stage1.sh` to regenerate `timing_report.rpt` + `evidence_manifest.json`.
4. Run `bash run_evidence_stage2.sh` to regenerate `stage2_summary.json` (binds the fresh stage-1 digest).
5. Confirm `bash run_public.sh` shows `evidence=FRESH stage2=FRESH`, `signoff=OK`, non-zero intended-clock coverage, and the consumed package == the inferred assignment.

A package with the correct netlist+clock still PrimeTime-signs-off GREEN when the role fields are swapped -- semantic-role binding, not signoff, is what rejects it. You may edit `flow_config.json`. Do **not** edit netlists, the library, the manifest, `glossary.md`, the decoy reports, the generators, or the runners; do not hand-write evidence.

When done, briefly state the semantic-role binding (which value is the scenario vs the corner and how you resolved it), which decoys are role-mismatched, and confirm you inferred the unique assignment and reran both stages in order.
