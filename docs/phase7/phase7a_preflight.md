# Phase-7A Study A — Pre-Flight Check Report (before any paid episode)

All six pre-execution verifications PASS. The pre-flight discovered and fixed one
critical grading-path bug (exactly the purpose of step 3). No paid model calls.

## 1. Construction commit + task hashes
- Construction commit: `db8a73b` (12 instances, 36 condition trees).
- 36 distinct custody sha256 over instance roots (recomputed after the step-3 fix below).
- All 12 hard-gate PASS, wrong-green-unattested on all 12.

## 2. All 12 instances pass the frozen real-PT hard gates
Confirmed from the construction report AND a fresh direct re-bake: every golden
and wrong binding is signoff-green on real PrimeTime (e.g. p15_eval_0004 golden
worst_slack=+0.600). The 5-criterion hard gate passes on all 12.

## 3. PT sentinel + full-path check  → **found and fixed a grading-path bug**
- `fullpath_check`: healthy (27 s).
- `sta_fairness` (STA health + fullpath + measurement-control) initially reported
  the golden signoff NOT green — contradicting the authoritative bake. Root cause:
  **`run_hidden.sh` emitted malformed JSON.** Its line
  `AEX=$(grep -cE '...' applied_hidden.sdc 2>/dev/null || echo 0)` double-prints
  when `grep -c` finds no match (it prints `0` AND exits 1, so `|| echo 0` adds a
  second `0`), producing `"applied_exception_lines": 0⏎0`. The grader then fails
  to parse `signoff_result.json` and `pt_signoff_green` defaults to **False**.
  `bake_golden` (the construction gate) is unaffected because it writes
  `signoff_result.json` in Python.
- **Fix (grading infrastructure, not task semantics):** `|| echo 0` → `|| true`
  in the generator template (`generators/p15_sta_handoff_gen.py`) and in all 36
  new task dirs' `run_hidden.sh`. After the fix: valid JSON, correct
  `pt_signoff_green` (0004 functional_close `AEX=0`; 0007 cdc_isolate `AEX=1`;
  both green). `sta_fairness` now reports before/after healthy, admissible, no
  hard fails.
- **Impact on frozen pilot (0001-0003):** their `pt_signoff_green` *component*
  was systematically False under the old buggy path; their **semantic_binding**
  outcome (the Phase-5/6 headline) is unaffected (it does not read
  `signoff_result.json`). Per the immutability rule, the pilot instances are left
  frozen; only the 12 new instances are patched.

## 4. 72-episode schedule hash + position balance
- `reports/evidence/phase7a_sta72_schedule.json`, manifest sha `df087d24…`.
- 72 episodes, all 12 blocks position-balanced; no duplicate `(task, condition, rep)` slots.

## 5. Execution infrastructure
`episode_arbiter`, `canonical_integrity`, `chain_executor`, `run_chain_guarded`,
`pt_health_sentinel`, `fullpath_check` all present and parse cleanly. Custody,
durable run-state, telemetry, and the committed sample-membership arbiter are wired.

## 6. `scripts/check` failure resolution (compatibility fix)
The pre-existing 2929/2949 failure was a **`task_id` format-regex gap**: the
schema regex recognized `workflow_handoff_NNNN` (so p14 passed) but not the
`p15_*/p16_*` STA/SPICE track IDs. Fix: extend the regex to accept
`p15_[a-z]+_[0-9]{4}|p16_[a-z]+_[0-9]{4}` — a validator change that touches no
frozen task semantics or data. `scripts/check` now **PASSES 2985/2985**; all 52
schema tests still pass.

## Statistical hierarchy (frozen before execution)
- **Primary confirmatory contrast:** BundleS vs Base (12 new instances).
- **Secondary preregistered contrasts:** TypedContract vs Base; TypedContract vs BundleS.
- The 12 new tasks are the prospective dataset; the old 3 STA instances are NOT pooled into the primary n.
- Per instance: 2 Base / 2 BundleS / 2 TypedContract outcomes; instance-level rate per condition; paired condition differences; improve/decline/tie; within-instance rep agreement. **Task instance is the independent unit.** An exact paired sign/permutation analysis is a sensitivity analysis only; the 72 trajectories are NOT treated as n=72.
