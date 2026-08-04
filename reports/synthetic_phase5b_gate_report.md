# Phase-5B Gate Report

**Status: PASS — all gates green; ready for Phase-5C authorization review.** Branch `synthetic-phase0a`. No model calls; no push.

**Grader status:**
- Family A (STA/PrimeTime): *real-tool construct-validated on the excluded STA development instance*
- Family B (SPICE/HSPICE): *real-tool construct-validated on the excluded SPICE development instance*

**Accepted construct-validity claim:** *In both new semantic families, an incorrect handoff can remain syntactically valid, execute successfully on the real engineering tool, and produce plausible green or numeric output. Ordinary tool success is therefore insufficient to establish semantic correctness; independent provenance or authority attestation is required.*

## Gate results (machine-readable: `reports/synthetic_phase5b_gate_report.json`)

| Gate | Result |
|---|---|
| Real-tool hard-feasibility (5 criteria), all 6 primary instances | PASS |
| Wrong-binding feasibility (tool-green wrong binding rejected by provenance), all 6 | PASS |
| Disclosure — output-channel (≥2 plausible candidates after the full visible surface) | PASS |
| Disclosure — semantic-diff (no golden disclosure under any condition) | PASS |
| Information-equivalence (BundleS/TypedContract same facts; both omit golden) | PASS |
| Fairness infra (STA + SPICE sentinel/fullpath/measurement-control on real PT/HSPICE) | PASS |
| Independence (operational structural independence, 5 criteria) | PASS |
| Reproducibility (deterministic seed-regeneration → byte-identical truth) | PASS |
| Anti-cheat (hidden-evidence isolation regression tests) | PASS |
| Schedules frozen (exact-counterbalanced, position-balanced) | PASS |
| Analysis frozen (instance = primary unit; descriptive-only bootstrap) | PASS |
| Phase-5C budget rule frozen | PASS |
| Custody hashed (`cig.freeze` over instance roots + code) | PASS |

## Six primary instances (3 STA + 3 SPICE), structurally diverse
Each passes the hard gate + output-channel + semantic-diff + info-equivalence; truth/authority/decoy/wrong-green signatures are distinct within each family (not lexical relabels). Wrong-green candidates: tool-accepted, execute, nonzero/complete/parseable output, plausible under frozen criteria, rejected by provenance/authority (not by tool failure).

## Fairness infrastructure
- Family B: `hspice_health_sentinel` (proactive health metadata), `spice_fullpath_check` (score-independent reference), `spice_measurement_control` (block bookends; admissible iff both healthy = symmetric whole-block invalidation; valid-unfavorable = hard fail; validity-only retry; recovered degradation in a gradeable episode does NOT replace). Validated on real HSPICE.
- Family A: `sta_fairness` analog (p15 launder+signoff+grade path). Validated on real PrimeTime.

## Schedules (frozen, unexecuted)
- **Qwen-only 24-episode core** (binding under the committed-ledger budget, ~¥318 remaining; within-task 2-rep replication preserved).
- Full-48 variant (selected only if ≥¥650–700 confirmed at review).
- DeepSeek-24 extension (all 6 tasks, never selectively on favorable families; separately authorized).
- TypedContract is a separately-authorized secondary — not in any schedule.

## Phase-5C budget rule (frozen)
Hard spend ceiling = confirmed available balance; per-slot conservative estimate (Qwen ¥12.04 / DeepSeek ¥11.09 from committed Phase-4 ledgers); replacement reserve (max 2/slot); only terminal measurement-invalid attempts may be replaced; if projected remaining cost > ceiling, stop with an incomplete collection. No k-cut / rep-reduction / instance-omission / condition-shortening / selective continuation / TypedContract-budget consumption after results are observed.

## Independence claim
*Operational structural independence under the five preregistered criteria* (not a proof). Shared generic infrastructure disclosed (PT/HSPICE shims, tiny.db, laundering, integrity guard, executor, arbiter, custody). Family × tool confound recorded (STA via PrimeTime, SPICE via HSPICE → family differences not attributable to semantic domain vs tool environment; inference limited to within-family within-model Base-vs-BundleS).

**Stop for review.** Phase-5C paid execution is separately authorized and gated on budget-balance confirmation (Qwen-24 vs full-48).
