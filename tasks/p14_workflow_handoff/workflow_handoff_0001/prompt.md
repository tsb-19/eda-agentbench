# Task: restore the acc_stage handoff AND regenerate the fresh sign-off evidence chain

You are handed a downstream **timing sign-off handoff** whose evidence is **out of date**. Repair the package to the authority contract, then **rerun the evidence flow** so the evidence is freshly generated from the repaired inputs. A green report alone, hand-edited evidence, stale evidence left in place, will **not** pass.

## The correct trajectory

1. Repair `flow_config.json` to consume `netlist_v2.v`.
2. Repair `constraints.sdc` to bind `clk_main`.
3. Run `bash run_evidence_stage1.sh` to regenerate `timing_report.rpt` + `evidence_manifest.json`.
4. Confirm `bash run_public.sh` shows `evidence=FRESH`, `signoff=OK`, and the consumed package matches the authority.

## What you can edit / run

- Edit `flow_config.json` and `constraints.sdc`.
- Run `bash run_public.sh` for verdict-first feedback (FRESH/STALE/MISSING).
- Run the evidence generators to regenerate evidence — do not hand-write evidence files.
- Do not edit netlists, the library, the authority manifest, the generators, or the runners.

When done, briefly state the root cause and the repair, and confirm you reran the evidence flow.
