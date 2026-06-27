# acc_stage — Trajectory / Evidence-Generation Sign-off Handoff (authoritative spec)

This is a downstream **timing sign-off handoff** for the `acc_stage` block whose evidence is **out of
date**. Your job is to make the handoff consistent with the authority **and regenerate fresh sign-off
evidence by rerunning the flow** — editing the report by hand or leaving the stale report in place is
not acceptable. `handoff_manifest.json` together with this document is the **authority**; if a
consumed/generated artifact disagrees, the authority wins.

## Current design intent (post-ECO v2)

Two changes already landed and are recorded in the authority:

1. **Re-synthesis v1 → v2.** The current handoff netlist is **v2**, enable-qualified (ports
   `{clk_main, din, en, dout}`). The legacy **v1** (ports `{clk_old, din, dout}`, no `en`) exists for
   provenance history only and must **not** be consumed.
2. **Clock rename `clk_old` → `clk_main`.** The current clock port is **`clk_main`**.

Current contract: netlist **v2**, clock **`clk_main`**, scenario **func**, corner/library **typ**
(`tiny.db`).

## What the package contains

- `handoff_manifest.json` — the authority contract (read-only): netlist v2, clock clk_main, func, typ.
- `flow_config.json` — **editable**: which netlist the evidence flow consumes.
- `constraints.sdc` — **editable**: the clock binding + I/O budget the flow applies.
- `netlist_v2.v` (current) / `netlist_v1.v` (legacy, provenance only) — read-only.
- `pt_signoff.tcl` — reference description of the consumed flow (documentation).
- `run_evidence.sh` — the **public evidence generator**. Running `bash run_evidence.sh` reruns the
  sign-off flow on the *current* `flow_config.json` + `constraints.sdc` and (re)writes **fresh**
  `timing_report.rpt` and `evidence_manifest.json`. **Read-only** (you run it; you do not edit it).
- `timing_report.rpt` — the generated PrimeTime report. Ships **stale** (a v1/clk_old run). It is a
  *product* of `run_evidence.sh`, not a file to edit.
- `evidence_manifest.json` — the generated machine-checkable provenance record. Ships **stale**
  (records the old v1/clk_old run). Also a *product* of `run_evidence.sh`.
- `tiny.lib` / `tiny.db`, `run_public.sh` / `run_public.tcl`.

## The defect

The authority says **v2 / clk_main**, but the consumers lag: `flow_config.json` selects stale
`netlist_v1.v`, `constraints.sdc` binds stale `clk_old`, and the shipped `timing_report.rpt` +
`evidence_manifest.json` are the **old v1/clk_old run**. The stale evidence *correctly* describes the
stale inputs — the island is locally self-consistent but wrong against the authority.

## What correct looks like

The handoff is correct only when, end-to-end:

1. `flow_config.json` consumes the **v2** netlist the authority names;
2. `constraints.sdc` binds **`clk_main`** so the intended sequential paths are actually constrained;
3. you have **rerun `bash run_evidence.sh`** so `timing_report.rpt` and `evidence_manifest.json` are
   **freshly generated from the repaired inputs** (their recorded input hashes, report digest, and
   `run_nonce` reflect the repaired package and the actual PrimeTime result);
4. PrimeTime setup sign-off on the consumed design reports **no negative-slack paths**.

## What will NOT be accepted

- A green PrimeTime report alone (the stale island self-signs-off green on the **wrong** design).
- **Editing `timing_report.rpt` or `evidence_manifest.json` by hand.** The grader re-runs the
  generator on your submitted inputs and rejects any evidence that does not match that fresh re-run
  (digest / input-hashes / `run_nonce` mismatch).
- **Leaving the stale evidence in place** after repairing the inputs (its hashes no longer match).
- **Running the generator before repairing** (the evidence then binds to stale inputs).
- Editing a netlist, the library, the authority manifest, `run_evidence.sh`, or the runners; weakening
  `constraints.sdc` (timing exceptions / loosened period).

When done, briefly state the root cause and the repair, including that you rer­an the evidence flow.
