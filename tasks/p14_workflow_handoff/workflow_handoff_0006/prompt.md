# Task: infer the unique globally-consistent package AND regenerate the fresh sign-off chain

You are handed a downstream **timing sign-off handoff** whose evidence is out of date AND whose **correct recovery target is NOT stated in any single file**. Infer it by intersecting the constraints in `spec.md` (netlist family C1 + clock coverage C2 + scenario/corner signoff pair C3), then **rerun the evidence flow (two ordered stages)** so the evidence is freshly generated from the inferred package.

Steps:
1. Infer the unique globally-consistent package (intersect C1 ∧ C2 ∧ C3) — do NOT trust any single shipped source; each decoy (report_A / report_B / report_C / evidence_D) satisfies only a subset.
2. Repair `flow_config.json` to that netlist + (scenario, corner) pair (the clock is already the intended clock — do not change it).
3. Run `bash run_evidence_stage1.sh` to regenerate `timing_report.rpt` + `evidence_manifest.json` from the repaired inputs.
4. Run `bash run_evidence_stage2.sh` to regenerate `stage2_summary.json` (binds the fresh stage-1 digest).
5. Confirm `bash run_public.sh` shows `evidence=FRESH stage2=FRESH`, `signoff=OK`, non-zero intended-clock coverage, and the consumed package == the inferred unique assignment.

You may edit `flow_config.json`. Do **not** edit netlists, the library, the manifest, the decoy reports, the generators, or the runners; do not hand-write evidence.

When done, briefly state the constraint-graph root cause, which decoys are pairwise-plausible, and confirm you inferred the unique assignment and reran both stages in order.
