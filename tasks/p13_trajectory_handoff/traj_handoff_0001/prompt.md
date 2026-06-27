# Task: restore the acc_stage handoff AND regenerate fresh sign-off evidence

You are handed a downstream **timing sign-off handoff package** whose evidence is **out of date**.
Repair the package to the authority contract, then **rerun the evidence flow** so the report and its
provenance manifest are freshly generated from the repaired inputs. A green PrimeTime report alone, a
hand-edited report, or a stale report left in place will **not** pass.

## What you can do

- Read `spec.md` and `handoff_manifest.json` (the **authority**: netlist v2 / clk_main / func / typ),
  `netlist_v2.v` / `netlist_v1.v`, `flow_config.json`, `constraints.sdc`, `pt_signoff.tcl`,
  `run_evidence.sh` (the generator), `timing_report.rpt`, `evidence_manifest.json`.
- Run `bash run_public.sh` for feedback. It reports whether the consumed package matches the authority
  and whether the evidence is `FRESH` / `STALE` / `MISSING` relative to the current inputs. The
  `TRAJECTORY_PUBLIC:` verdict is on the first line.
- Run `bash run_evidence.sh` to **regenerate** `timing_report.rpt` + `evidence_manifest.json` from the
  *current* `flow_config.json` + `constraints.sdc`.
- Edit `flow_config.json` and `constraints.sdc`. The evidence files (`timing_report.rpt`,
  `evidence_manifest.json`) are produced by `run_evidence.sh` — do not hand-write them.

## The correct trajectory

1. Repair `flow_config.json` to consume `netlist_v2.v` (the authority netlist).
2. Repair `constraints.sdc` to bind `clk_main` (so the v2 sequential paths are constrained).
3. Run `bash run_evidence.sh` to regenerate fresh `timing_report.rpt` + `evidence_manifest.json`.
4. Confirm `bash run_public.sh` shows `evidence=FRESH`, `signoff=OK`, and the consumed package matches
   the authority.

## What will NOT be accepted

- **Final files fixed but evidence not regenerated.** The grader re-runs the generator on your
  submitted inputs and requires the submitted evidence to match that fresh re-run — the recorded input
  hashes, the report digest, and the deterministic `run_nonce` must all reflect the repaired package
  and the actual PrimeTime result.
- **Hand-editing `timing_report.rpt` or `evidence_manifest.json`** (digest / nonce will not match the
  re-run).
- **Leaving the stale evidence** after repairing the inputs, or **running the generator before
  repairing** (the evidence then binds to the wrong/stale inputs).
- A green report on the stale v1/clk_old island (the wrong design).
- Editing a netlist, the library, the authority manifest, `run_evidence.sh` / `gen_evidence.py` /
  `evidence_signoff.tcl`, or the runners; weakening `constraints.sdc` (timing exceptions / loosened
  period).

When done, briefly state the root cause and the repair, and confirm you rer­an the evidence flow.
