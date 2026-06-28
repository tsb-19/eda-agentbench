# acc_stage — Workflow / Multi-Stage Evidence-Chain Sign-off Handoff (authoritative spec)

This is a downstream **timing sign-off handoff** for `acc_stage` whose evidence is **out of date**. Make the handoff consistent with the authority **and regenerate fresh sign-off evidence by rerunning the flow in order** — editing evidence by hand or leaving stale evidence in place is not acceptable. `handoff_manifest.json` + this document is the **authority**.

## Current design intent (post-ECO v2)

Current contract: netlist **v2** (ports `{clk_main, din, en, dout}`), clock **`clk_main`**, scenario **func**, corner/library **typ** (`tiny.db`). Legacy **v1** (`{clk_old, din, dout}`) is provenance-only and must **not** be consumed.

## The defect

The authority says **v2 / clk_main**, but the consumers lag: `flow_config.json` selects stale `netlist_v1.v`, `constraints.sdc` binds stale `clk_old`, and the shipped evidence is the old v1/clk_old run. The stale evidence *correctly* describes the stale inputs — locally self-consistent but wrong against the authority.

## Two-stage evidence chain (evidence_steps=2)

Sign-off evidence here is a **two-stage chain** and the stages are **ordered**:

1. **Stage 1** — `bash run_evidence_stage1.sh` regenerates `timing_report.rpt` + `evidence_manifest.json` from the repaired inputs (the input-path timing evidence).
2. **Stage 2** — `bash run_evidence_stage2.sh` consumes the **fresh** stage-1 evidence and regenerates `stage2_summary.json` (the register-path summary). Its `upstream_evidence_digest` must equal the fresh stage-1 report digest.

You must run stage 1 **then** stage 2, after the inputs are repaired. A stage-2 summary built from a stale or missing stage 1 (or generated before the repair) will not match the hidden re-run and will fail.

## What correct looks like

1. `flow_config.json` consumes the **v2** netlist;
2. `constraints.sdc` binds **`clk_main`**;
3. you have **rerun the evidence flow** (stage 1 then stage 2) so the evidence is freshly generated from the repaired inputs;
4. PrimeTime setup sign-off on the consumed design reports **no negative-slack paths**.

## What will NOT be accepted

- A green PrimeTime report alone (the stale island self-signs-off green on the wrong design).
- **Editing the evidence files by hand.** The grader re-runs the generator chain on your submitted inputs and rejects any evidence that does not match (digest / input-hashes / `run_nonce` / `upstream_evidence_digest`).
- **Leaving stale evidence** after repairing, or **running a generator before repairing**.
- **A stage-2 summary built from a stale/missing stage 1**, or running stage 2 before stage 1.
- Editing a netlist, the library, the authority manifest, the generators, or the runners; weakening `constraints.sdc` (timing exceptions / loosened period).

When done, briefly state the root cause and the repair, and confirm you reran the evidence flow (both stages, in order).
