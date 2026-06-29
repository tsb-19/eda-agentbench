# Task: resolve the multi-conflict handoff AND regenerate the fresh global-authority evidence chain

You are handed a downstream **timing sign-off handoff** with **several coupled faults** and **several partially-truthful decoy evidence sources**. `handoff_manifest.json` / `spec.md` define the **single global authority**: `netlist_v2.v` + `clk_main` + `slow`/`func`. No shipped evidence source is fully correct — each decoy is right on some axes and wrong on others. Diagnose the global authority, **reject every decoy**, repair `flow_config.json` to the global package, then **rerun the evidence flow (two ordered stages)**. Following any single decoy, hand-edited evidence, or a green report under a wrong package will **not** pass.

## The correct trajectory

1. Repair `flow_config.json` to the global authority: `netlist_v2.v`, scenario `slow`, corner `func` (clock `clk_main` is already correct — do not change it).
2. Run `bash run_evidence_stage1.sh` to regenerate `timing_report.rpt` + `evidence_manifest.json` from the global-authority package.
3. Run `bash run_evidence_stage2.sh` to regenerate `stage2_summary.json` (binds the fresh stage-1 digest).
4. Confirm `bash run_public.sh` shows `evidence=FRESH stage2=FRESH`, `signoff=OK`, and the consumed package == the global authority.

## What you can edit / run

- Edit `flow_config.json` (netlist/scenario/corner). Do **not** change the clock or the netlists.
- Run `bash run_public.sh` for verdict-first feedback (FRESH/STALE/MISSING).
- Run the evidence generators to regenerate evidence — do not hand-write evidence files.
- Do not edit netlists, the library, the authority manifest, the decoy reports, the generators, or the runners.

When done, briefly state that the root cause is a multi-axis conflict with partially-truthful decoys, identify which decoys are partially true vs false, and confirm you repaired to the global authority and reran both stages in order.
