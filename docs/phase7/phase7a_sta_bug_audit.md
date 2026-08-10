# Phase-7A Historical STA Pilot — `run_hidden.sh` Bug Audit (no model calls; no trajectory regrading)

## Bug mechanism (recap)
`run_hidden.sh` (Family A STA grading path) computed
`AEX=$(grep -cE 'set_false_path|set_multicycle_path' applied_hidden.sdc 2>/dev/null || echo 0)`.
When `grep -c` finds **no** match it prints `0` **and** exits 1, so `|| echo 0` appended a
second `0`, emitting malformed JSON `"applied_exception_lines": 0⏎0`. The grader
(`grade_sta_handoff.py`) then failed to parse `signoff_result.json` (`_load → None → {}`) and
`pt_signoff_green` defaulted to **False**. Fixed in the generator + 36 new task dirs (commit
`0f39628`) by `|| echo 0 → || true`.

## Trigger condition
The malformed JSON occurs **iff the submitted binding produces no exception line** in
`applied_hidden.sdc`. `build_applied_sdc.py` emits `set_false_path` for `cdc_isolate`/
`reset_exempt`, `set_multicycle_path` for `scan_override`, and **nothing** for
`functional_close`. So the bug triggers exactly on a `functional_close` submission (or a
malformed/missing intent).

## 1. Was the malformed `signoff_result.json` agent-visible during the trajectory? — **No.**
The agent's visible runner is `run_public.sh` (`metadata.run_command = bash run_public.sh`;
`run_public.sh` is in `files.visible`). `run_public.sh` runs `build_applied_sdc.py` +
`run_public.tcl` (timing + exception feedback) and contains **no** `grep -c`/`signoff_result`
writing — it is clean. `run_hidden.sh` is the **grading-time** path (`files.hidden`); the
`STAHandoffEvaluator` re-runs `grade_sta_handoff.py` in the evaluator workspace, which reads
the `signoff_result.json` that `run_hidden.sh` wrote. The malformed field is therefore
**evaluator-only**, never shown to and never influencing the agent.

## 2. Did it affect only post-hoc evaluator fields? — **Yes (structurally); and in the pilot, none at all.**

## 3. Was semantic-binding correctness independently re-derived? — **Yes.**
`grade_sta_handoff.py` computes `semantic_binding` (submitted == golden on the typed axes),
`provenance_attested` (from `derivation_edges`), `coverage_cell_consistent`, and
`check_view_legal` from `exception_config.json` + `signoff_intent_truth.json` — **never** from
`signoff_result.json`. Only `pt_signoff_green` and (via the `applied` default) `not_masking`
read `signoff_result.json`. The Phase-5C report additionally re-graded `semantic_binding`
independently (`_sem_subtype`). So the primary outcome is provably independent of the bug.

## 4. Which pilot runs were affected? — **0 / 30.**
Scanned all 30 STA pilot episodes (Phase-5C: 12; Phase-5D: 18; `p15_eval_0001..0003` ×
conditions × 2 reps). **Every** episode submitted an exception-applying intent
(`cdc_isolate` / `reset_exempt` / `scan_override`) → `applied_hidden.sdc` contained a
`set_false_path`/`set_multicycle_path` line → `grep -c` found a match → valid JSON →
`pt_signoff_green` read correctly (1.0 where green). **No pilot episode submitted
`functional_close`**, so the bug never triggered. `pt_signoff_green`, `not_masking`, and
`total_score` are all correct in the pilot; `semantic_binding` was independent regardless.

## Dimension impact (pilot)
| dimension | source | bug-affected? |
|---|---|---|
| semantic_binding | submitted + truth | No (independent) |
| provenance_attested | derivation_edges | No (independent) |
| coverage_cell_consistent | truth + submitted | No (independent) |
| check_view_legal | truth + submitted | No (independent) |
| pt_signoff_green | signoff_result.json | **No pilot episode triggered** → correct |
| not_masking | signoff_result.json (applied) | not triggered → correct |
| total_score | weighted sum | correct |

## Classification
- **Agent-visible / behavior-affecting?** No — `run_hidden.sh` is grading-time; the agent sees
  only the clean `run_public.sh`. → **NOT protocol-affected.**
- **Evaluator-only + semantic independent?** Yes — and moreover **0 pilot episodes triggered**
  the bug, so no secondary dimension was corrupted either.

## Verdict
The historical STA pilot is **unaffected**: the bug was **latent** in the pilot's
`run_hidden.sh` but never triggered (no `functional_close` submissions), so no erratum is
required and no pilot data (semantic-binding counts *or* secondary dimensions) need correction.
The bug was fixed before it could affect the prospective batch: the 18 `functional_close`
submissions in the Phase-7A run all graded `pt_signoff_green = 1.0` (fix verified). **The
prospective 12-instance Study A remains authoritative.** (SPICE/Family-B `run_hidden.sh` uses a
different pattern and is not affected by this specific bug.)
