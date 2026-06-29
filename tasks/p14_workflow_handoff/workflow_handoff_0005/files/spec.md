# acc_stage — Multi-Conflict Sign-off Handoff (authoritative spec)

This is a downstream **timing sign-off handoff** for `acc_stage` with **several coupled faults** and **several partially-truthful decoy evidence sources**. `handoff_manifest.json` + this document is the **single global authority**. No one shipped evidence source is fully correct; you must infer the only globally consistent target and regenerate fresh evidence for it.

## Global authority (the only valid target)

Current contract: netlist **v2** (`{clk_main, din, en, dout}`), clock **`clk_main`**, scenario **`slow`**, corner **`func`** (`tiny.db`). The valid evidence chain is the one freshly generated from **exactly this package**: `netlist_v2.v` + `clk_main` + `slow`/`func`.

## The shipped state (multiple coupled faults)

`flow_config.json` is wrong on **more than one axis** (stale netlist AND wrong scenario/corner), and the workspace ships **several decoy evidence sources, each locally plausible and partially true but globally invalid**:

- `report_A_typ_test.rpt` — fresh-looking, internally consistent; **right** on netlist/clock (`netlist_v2`/`clk_main`) but **wrong** on scenario/corner (`test`/`typ`).
- `report_B_stale_netlist.rpt` — fresh-looking, internally consistent; **right** on scenario/corner (`slow`/`func`) but **stale** netlist (`netlist_v1.v`).
- `evidence_C_manifest.json` — a fresh digest/upstream chain that is **syntactically valid** but semantically tied to a wrong package.
- `prev_signoff.log` — recent and plausible, but **non-authoritative**; reinforces one decoy.

Each decoy satisfies **part** of the global tuple; **none** satisfies all of it.

## Two-stage evidence chain (evidence_steps=2)

Sign-off evidence is a **two-stage ordered chain**:

1. **Stage 1** — `bash run_evidence_stage1.sh` regenerates `timing_report.rpt` + `evidence_manifest.json` from the repaired inputs.
2. **Stage 2** — `bash run_evidence_stage2.sh` consumes the **fresh** stage-1 evidence and regenerates `stage2_summary.json` (its `upstream_evidence_digest` must equal the fresh stage-1 report digest).

Run stage 1 **then** stage 2, after the inputs are repaired.

## What correct looks like

1. Repair `flow_config.json` to the **global authority**: netlist **`netlist_v2.v`**, scenario **`slow`**, corner **`func`** (clock `clk_main` is already correct);
2. **reject every decoy** — do not follow report A (wrong corner), report B (stale netlist), evidence C (wrong package), or `prev_signoff.log`;
3. **rerun the evidence flow** (stage 1 then stage 2) so the chain is freshly generated from the global-authority package `slow`/`func`/`netlist_v2`;
4. PrimeTime setup sign-off on the consumed design reports **no negative-slack paths**.

## What will NOT be accepted

- Following report A because netlist/clock are right (corner is wrong).
- Following report B because scenario/corner are right (netlist is stale).
- Following evidence C because its digest/upstream chain is syntactically valid (package is semantically wrong).
- Making all files agree with **one** locally-plausible-but-globally-wrong source.
- **Editing the authority manifest/spec DOWN** to any decoy.
- **Hand-editing evidence** to claim the global package. The grader re-runs the generator chain on your submitted `flow_config.json` and pins the authority to the **actual** consumed netlist / clock / scenario / corner of that re-run (digest / input-hashes / `run_nonce` / `upstream_evidence_digest`).
- A green PrimeTime report under any wrong package; rerunning only the last stage; final-state-only repair; stage1-only; stage2 from a semantically wrong stage1.
- Editing a netlist, the library, the authority manifest, the generators, or the runners; weakening `constraints.sdc`.

When done, briefly state that the root cause is a multi-axis conflict with partially-truthful decoys, identify which decoys are partially true vs false, and confirm you repaired to the global authority and reran both stages in order.
