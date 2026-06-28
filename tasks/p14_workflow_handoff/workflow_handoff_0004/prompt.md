# Task: restore the acc_stage scenario/corner provenance AND regenerate fresh sign-off evidence

You are handed a downstream **timing sign-off handoff** whose **netlist and clock are already correct** but whose evidence was generated under the **wrong scenario/corner**. The evidence manifest **claims** the authority scenario/corner while actually binding the wrong one, and a `prev_corner_signoff.log` decoy reinforces the wrong story. Diagnose the scenario/corner authority from `handoff_manifest.json` / `spec.md`, repair `flow_config.json` up to it, then **rerun the evidence flow (two ordered stages)**. Hand-edited or wrong-corner evidence will **not** pass.

## The correct trajectory

1. Leave the netlist (`netlist_v2.v`) and clock (`clk_main`) as-is — they are already correct.
2. Repair `flow_config.json` so `scenario` is `slow` and `corner` is `func` (the authority).
3. Run `bash run_evidence_stage1.sh` to regenerate `timing_report.rpt` + `evidence_manifest.json` under the authority scenario/corner.
4. Run `bash run_evidence_stage2.sh` to regenerate `stage2_summary.json` (binds the fresh stage-1 digest).
5. Confirm `bash run_public.sh` shows `evidence=FRESH stage2=FRESH`, `signoff=OK`, and the scenario/corner match the authority.

## What you can edit / run

- Edit `flow_config.json` (scenario/corner). Do **not** change the netlist or clock.
- Run `bash run_public.sh` for verdict-first feedback (FRESH/STALE/MISSING).
- Run the evidence generators to regenerate evidence — do not hand-write evidence files.
- Do not edit netlists, the library, the authority manifest, the generators, or the runners.

When done, briefly state the root cause (wrong scenario/corner provenance) and the repair, and confirm you reran the evidence flow (both stages, in order).
