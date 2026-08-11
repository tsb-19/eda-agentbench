# Phase-7 Synthesis Status (post Study-A execution + historical bug audit)

Per the manuscript-timing directive (section F), the v3 manuscript rewrite is **deferred**
until (i) the historical STA bug audit is resolved, (ii) Study B human-label status is known,
and (iii) the Study C static audit is complete. Status of each:

## (i) Historical STA bug audit — RESOLVED (see phase7a_sta_bug_audit.md)
The `run_hidden.sh` malformed-JSON bug was **latent in the pilot but never triggered**: 0/30
pilot STA episodes submitted `functional_close`, so all graded correctly. The malformed field
is evaluator-only (the agent sees the clean `run_public.sh`), and `semantic_binding` is
computed from the submitted tuple + hidden provenance (independent of `signoff_result.json`).
**No pilot erratum is required**; pilot data (semantic-binding counts and secondary dimensions)
are intact. Fixed before the prospective run; 18 Phase-7A `functional_close` submissions all
graded `pt_signoff_green=1.0`. **The prospective 12-instance Study A is authoritative.**

## (ii) Study B — CLOSED: preregistered but unexecuted
Packets/rubric/consent/IRB frozen (commit `12671d9`). **Securing qualified independent HUMAN
annotators is a human-organizational action outside the automated agent's capability.** Per the
directive, Study B is closed as: **"preregistered but unexecuted because qualified independent
human annotators were unavailable."** No labels were collected; no LLM annotator was substituted.
The frozen materials remain available for future execution by the research team. Study B does
not block submission.

## (iii) Study C — COMPLETE (commit `338a486`)
Static audit of the 26 officially documented Terminal-Bench 2.0→2.1 repairs (PR #53
"Terminal-Bench 2.1" in `harbor-framework/terminal-bench-2`), with the 2.0/2.1 snapshots and
manifest frozen + hashed before coding. Result (retrospective taxonomy application — NOT a claim
of prediction/prevention/runtime-validation): **direct 1 / partial 21 / not-covered 4** of 26;
layers L1 capability 17, L3 execution 10, L4 artifact integrity 1, Other 4; L2 sampling 0;
6 multi-layer. Honest outcome: partial conceptual overlap, limited direct coverage. Source-
resolution discrepancy logged (legacy `terminal-bench-1` PR #53 is unrelated; excluded). TB
runtime permanently cancelled. See `reports/synthetic_phase7c_terminalbench_audit.md`.

---

## LOCKED v3 manuscript directions (apply at v3; NOT yet applied)

### B — STA external-validity claim (prospective batch is primary STA evidence)
Use the prospective 12-instance batch as primary STA evidence (do NOT pool the historical 3
into the n=12 headline):
- 12 prospective instances; Base mean = 0.208; BundleS = 0.333; TypedContract = 0.458.
- BundleS vs Base = 3 improve / 2 decline / 7 tie; exact sign-test p = 1.0; instance-level
  permutation sensitivity p = 0.31.
- Use the locked wording: *"Prospective STA confirmation did not establish a transferable
  BundleS benefit. The descriptive direction reversed relative to the original three-instance
  pilot, illustrating the instability of conclusions drawn from very small task samples."*
- Do **not** state BundleS is significantly better. TypedContract may be reported as
  descriptively highest, but **no TypedContract advantage is established.**
- Do **not** retain the old main-text description of STA as a clean `Base 0.50 > BundleS 0.33`
  negative result.

### E — Related-work refresh (add two current papers at v3)
1. **"No More, No Less: Task Alignment in Terminal Agents" (TAB).** Explicitly distinguish:
   TAB = selecting necessary environmental cues while ignoring plausible distractors; our
   construct = role-conditioned semantic binding and provenance/authority attribution,
   including tool-green wrong bindings after evidence is available. **Do not claim TAB studies
   the same failure construct.**
2. **"LongHorizon-Harness: Advancing Long-Horizon Agents for Real-World Tasks".** Use as
   evidence that **some** Harness interventions can transfer across benchmarks. This sharpens
   the central claim to: *"Transfer is an empirical property that must be tested rather than
   inferred from within-family confirmation"* — **not** "Harness improvements generally fail
   to transfer."

## Out of scope (per directive)
No new mechanism-search tasks; no new Harness wording beyond the locked directions; no DeepSeek
extension; no P14 held-out-2 consumption; no Terminal-Bench runtime. No push.
