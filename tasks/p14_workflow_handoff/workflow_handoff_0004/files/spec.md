# acc_stage — Scenario/Corner Provenance Sign-off Handoff (authoritative spec)

This is a downstream **timing sign-off handoff** for `acc_stage`. The consumed **netlist and clock are already correct** (`netlist_v2.v` on `clk_main`). The defect is in the **scenario / corner provenance**: the shipped evidence was generated under the **wrong scenario/corner**, and the evidence manifest **claims** the authority scenario/corner while actually binding the wrong one. `handoff_manifest.json` + this document is the **authority**.

## Current design intent (authority)

Current contract: netlist **v2** (ports `{clk_main, din, en, dout}`), clock **`clk_main`**, scenario **`slow`**, corner **`func`** (`tiny.db`). The evidence chain must be **generated under `slow`/`func`**.

## The defect

The authority says scenario **`slow`** / corner **`func`**, but `flow_config.json` selects the **wrong** scenario/corner (`test`/`typ`), so the shipped evidence was generated under the wrong provenance. `evidence_manifest.json` *claims* `slow`/`func` but its run actually used `test`/`typ` (its `run_nonce` and input provenance bind the wrong scenario/corner). The decoy `prev_corner_signoff.log` reinforces the wrong `test`/`typ` story but is **non-authoritative**.

## Two-stage evidence chain (evidence_steps=2)

Sign-off evidence is a **two-stage ordered chain**:

1. **Stage 1** — `bash run_evidence_stage1.sh` regenerates `timing_report.rpt` + `evidence_manifest.json` from the repaired inputs.
2. **Stage 2** — `bash run_evidence_stage2.sh` consumes the **fresh** stage-1 evidence and regenerates `stage2_summary.json` (its `upstream_evidence_digest` must equal the fresh stage-1 report digest).

Run stage 1 **then** stage 2, after the inputs are repaired.

## What correct looks like

1. **Do not** change the netlist or clock — they are already correct (`netlist_v2.v` / `clk_main`);
2. repair `flow_config.json` so its **scenario** is **`slow`** and its **corner** is **`func`** (up to the authority);
3. **rerun the evidence flow** (stage 1 then stage 2) so the evidence is freshly generated under `slow`/`func`;
4. PrimeTime setup sign-off on the consumed design reports **no negative-slack paths**.

## What will NOT be accepted

- Leaving the evidence under the wrong scenario/corner.
- **Editing the authority manifest or spec DOWN** to the wrong scenario/corner.
- **Hand-editing the evidence** to *claim* `slow`/`func`. The grader re-runs the generator chain on your submitted `flow_config.json` and pins the authority to the **actual** scenario/corner of that re-run (digest / input-hashes / `run_nonce` / `upstream_evidence_digest`).
- A green PrimeTime report produced under the wrong scenario/corner.
- Trusting the `prev_corner_signoff.log` decoy as authority.
- Editing a netlist, the library, the authority manifest, the generators, or the runners; weakening `constraints.sdc`.

When done, briefly state the root cause (wrong scenario/corner provenance) and the repair, and confirm you reran the evidence flow (both stages, in order).
