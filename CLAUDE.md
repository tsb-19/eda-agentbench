# CLAUDE.md

## What this branch is

`iclr2027-artifact` is the reproducibility artifact for one paper: **Auditing Generalization Claims
for LLM Agent Harnesses: Semantic Binding and Measurement Validity** (ICLR 2027, manuscript **v19**
in `submission/`; v14 and earlier are immutable historical freezes).

It is a **slimmed** branch. `master` is also EDA-AgentBench, a 2892-task commercial-EDA benchmark;
that benchmark is not in the paper and is not here. If a task needs P1–P9, a per-track generator, a
removed report or the `datagen/` factory, it belongs on `master` — do not recreate any of it here.
`docs/REMOVED.md` lists everything removed with `git checkout master -- <path>` recovery.

Start from `README.md`, then `docs/artifact_map.md` (every paper claim → the files that produce it).

## Hard constraints

Violating any of these silently invalidates the paper's claims. They are not style rules.

1. **Experiments are permanently closed.** No paid model call, no new episode, no alteration of
   frozen task semantics. The experiment freeze HEAD is `a89e084`. Every reported number is
   re-derived from committed ledgers at or before it.
2. **`reports/evidence/` is read-only.** 1337 files of frozen custody records. It also holds
   **1065 `path → sha256` pins** on the membership code that was in force when each batch of paid
   episodes ran. Any file appearing in a pin must stay byte-identical. Check before editing
   anything under `scripts/`, `generators/`, `tests/` or `eda_agentbench/`:

   ```bash
   python3 -c "import sys; sys.path.insert(0,'scripts'); \
     from frozen_membership_verify import collect_pins, SCAN_ROOT; \
     print('<path>' in collect_pins(SCAN_ROOT))"
   ```

   The 1065 pins are **1020 task files, 36 scripts, 6 generator files and 3 package modules** —
   no test and no document is sha256-pinned. Untouchable: `scripts/llm_agent_driver.py`,
   `canonical_integrity.py`, `episode_arbiter.py`, `chain_executor.py`, `fairness_retry.py`,
   `measurement_control.py`, `fullpath_check.py`, both health sentinels, `run_agentic_baseline.py`,
   `run_chain_guarded.py`, `sta_fairness.py`, the `phase4*`/`phase5*` freeze, fairness and
   generation scripts; `generators/p15_sta_handoff_gen.py`, `p16_spice_handoff_gen.py`,
   `phase5_audits.py`, both cross-family graders, `p16_spice_handoff/plausibility_spec.json`;
   `eda_agentbench/agentic/workspace.py` and `evaluator/{sta,spice}_handoff.py`.

   Distinguish **pinned** from **merely referenced**: many tests and two documents are *named* in
   the frozen manifests without a hash. Naming means the path must stay valid; only a hash means
   the bytes must stay identical. Unpinned and editable: `cli.py`, `schema.py`,
   `agentic/runner.py`, `task/{loader,validator}.py`, `evaluator/workflow_handoff.py`,
   `scripts/check`, `scripts/validate_dataset.py`, every test, and the docs.
3. **`submission/` develops forward; past versions are immutable.** The working manuscript is
   **v19** and may be edited. What may never happen is the other direction: do not rewrite a
   historical commit or tag, do not edit a past version's section in `FREEZE_HASHES.md`, and do not
   retroactively present a post-hoc finding as preregistered. Every past freeze (v14 and earlier)
   must stay recoverable byte-for-byte from its recorded commit and hashes — verify with a rebuild
   before claiming otherwise. Any new version needs: regenerated derived tables, a full rebuild, the
   page-limit gate, an anonymity re-scan, a new `FREEZE_HASHES.md` section with its own hash table,
   and updated `docs/provenance.md` + `docs/artifact_map.md` (both languages).
4. **Two paths may not move.** `docs/phase7/phase7_synthesis.md` (sha256 recorded in
   `submission/FREEZE_HASHES.md`) and
   `docs/synthetic_p14_phase4w_clarity_bundle_ablation_design.md` (cited by path inside a frozen
   manifest).
5. **`tasks/p13_trajectory_handoff/traj_handoff_0001/` stays.** It is not a studied family — it is
   the asset substrate `generators/p14_workflow_handoff_gen.py:38` reads. Do not "clean it up".

## The gate

Run before every commit. All three steps must pass:

```bash
scripts/check
#   [1] pytest, tool-free subset          expect: 0 failed
#   [2] structural task validation        expect: 84/84
#   [3] frozen membership                 expect: 1065 pins / 9 missing / 2 mismatch / 1 multi-sha
```

Plus, for anything touching reports, scripts or docs:

```bash
python3 scripts/phase7c_study1_ledger.py      --check   # 58 + 12 = 70 episodes
python3 scripts/phase7c_claim_statistics.py   --check   # 12.5 / [-12.5, 41.7] / -16.7
python3 scripts/phase7d_semantic_proxy_gap.py --check   # 169 included / 82 tool-green wrong bindings
python3 scripts/phase7e_answer_identifiability.py --check  # 294 universe; BundleS 9-147, never 1
python3 scripts/phase8a_claim_statistics.py --check     # arm1 k=6: -2.8 / [-31.9, 26.4]; 7-of-36
#                                                       # arm2 k=2: +12.5 / [-16.7, 41.7]; not established
python3 scripts/phase8a_arm2_gate.py          --check    # verifies the recorded ARM2_NOT_RUN decision
python3 scripts/phase8a_arm2_cost_calibration.py --check # projected ¥53.14 vs realized ¥38.46
python3 scripts/slim_link_check.py                     # no dangling repository references
cd submission && make distclean && make                # 24 pp, 325 053 bytes
python3 scripts/submission_page_limit_check.py         # main text ends on p9 (ICLR limit 9)
```

Never read the main-text page count off page arithmetic. ICLR's 9-page rule is about whether main
text appears *above* the `REFERENCES` heading on the heading's own page, and the heading can begin
mid-page: "references are on p10, so the main text is 9 pp" once reported 9 with 580 main-text words
above them. `submission_page_limit_check.py` asserts the real condition and is fail-closed. Related
layout fact — trimming text *before* the last float does not shorten the tail; the floats repack and
absorb it. Only cuts after the final table move the boundary.

**The membership gate is expected to report non-zero counts.** 9 missing files are gitignored
HSPICE build products; 2 mismatches are generators edited after the phase-5B/5C freeze; 1 multi-sha
file is legitimately versioned. They are carried forward deliberately — see
`docs/frozen_membership_baseline.json`. Do not "fix" them to zero: a verifier tuned until it prints
nothing would hide the next real mutation.

`make clean` keeps `main.pdf`, so plain `make` after `clean` is a no-op. Use `distclean` before any
build whose log you intend to measure, and count pdflatex start banners rather than trusting that a
log exists — a page count was once measured off a stale PDF this way.

## The object of study

A **semantic handoff**: bind a tuple to canonical typed roles from role-misleading evidence. A wrong
binding still produces a green tool signoff (**tool-green**), so only a typed provenance/authority
oracle rejects it.

| Family | Directory | Tool | Paper role |
|---|---|---|---|
| workflow (PVT axes) | `tasks/p14_workflow_handoff/` — 27 instances | PrimeTime | Study I: S0, S1, S2-M |
| Family A (provenance DAG) | `tasks/p15_sta_handoff/` — 15×3 + dev | PrimeTime | Study II: S2-F |
| Family B (request–authority join) | `tasks/p16_spice_handoff/` — 3×3 + dev | HSPICE | Study II: S2-F ceiling |

Results, in the paper's own words: **observed** at S0, **replicated once** at S1, **not established**
at S2-M, S2-F or S3. A prospective 12-instance panel reversed the descriptive direction of a
3-instance pilot without establishing anything. No stable minimal component was isolated. Do not
restate any of these more strongly than the paper does; the paper is *about* not doing that.

**S3 is measured but not established, and the two must not be confused.** The joint model x family
cell holds 72 `deepseek-v4-pro` episodes at k=2 (Phase-8A arm 2): +12.5 pp, 5 instances improving to
2 declining, sign test *p*=0.45, band -16.7 to +41.7. So the point estimate favours BundleS and the
discrimination reaches no conclusion — "not established", never "shown absent" and never "no effect".
Four further rules attach to that cell, the first three enforced by tests:

1. **Its execution is not preregistered.** It ran after the preregistered cost gate returned
   `ARM2_NOT_RUN`. Never write that it was preregistered and executed per `docs/phase8a_prereg.md`.
   What governs it is `docs/phase8a_arm2_analysis_plan.md`, committed before any of its outcomes were
   read; `phase8a_report.py` refuses to build the arm-2 report if that plan is absent.
2. **k=2 carries no magnitude claim, and its aggregate is not comparable to arm 1's k=6 aggregate.**
   Arm 1 measured 7 of 36 cells disagreeing across six identical repetitions.
3. **Nothing is pooled** across Phase-7A, arm 1 and arm 2. No n=24, no k=8, no summed episode count.
4. **The cross-model concordance is descriptive, and most of it is degenerate.** 10 of 12 instances
   classify identically, but **5 of those agreements are floor/floor or ceiling/ceiling** — no
   expressible difference in either arm, so they record shared instance difficulty, not a shared
   response. The non-degenerate content is 4 of the 5 jointly informative instances agreeing in
   sign, which arises with probability 0.1875 under independent signs. Report it as *consistent with
   recurring task-specific structure*. Never as "nearly model-invariant", never as "heterogeneity is
   a property of the instances rather than the backend" — both were in v17 and both were corrected
   in v18. The sign-exchangeability figure is appendix-only, labelled a descriptive sensitivity
   calculation, and no verdict may be derived from it. Applying a looser standard to this post-hoc
   claim than to the treatment effect (*p*=0.45 → "not established") is the exact failure the paper
   is about.

**The cross-BATCH concordance is a different, better-supported contrast, and is still bounded.** Arm
1's k=2 and k=6 batches share a model and share instances; only depth changes, so the degenerate-
agreement objection above does not apply and the finding stands. What it licenses is that the
instance-level heterogeneity is **not wholly attributable** to sampling noise at k=2 — never "is a
property of the instances, not sampling noise", which v18 still said in the appendix while §5 said
the weaker thing about the same comparison. The bound is the paper's own k=6 batch: 7 of 36 cells
disagree internally across six identical repetitions, so run noise persists at k=6 and recurrence
excludes low repetition as the *whole* explanation, not as a contributor. Both statements must sit at
that strength and carry the 7-of-36 figure; `test_the_cross_batch_concordance_excludes_only_the_whole_explanation`
fails if either drifts.

## Measurement-validity rules

These are the paper's second contribution, so they are also how work here must be conducted.

- An infrastructure timeout, gateway error or worker failure is **measurement-invalid** — never a
  capability failure.
- A **valid wrong score is a hard failure** and may not be retried away. `scripts/fairness_retry.py`
  grants retries for infrastructure faults only.
- **Verify that the verification ran.** Count a tool's start banners before believing any
  log-derived number; prove a recorded hash reproducible by building twice.
- A monitor **inherits the custody of its reference standard**. A day-long "remote tool outage" was
  in fact the test harness writing into the canonical tree; the monitor was right and the
  attribution was wrong. See `docs/incident_golden_corruption.md`. The tripwire
  `test_canonical_golden_fingerprint_intact` in `tests/test_fullpath_check.py` now fails
  immediately if anything writes into the canonical dataset — if it fires, restore with
  `git checkout -- <path>`, find the writer, and never commit the corruption.
- **Non-streaming transport censors thinking models** mid-reasoning via the socket-inactivity
  timeout. `EDA_BENCH_STREAM_RESPONSES=1` is required for them; without it a transport artifact is
  recorded as a model failure.
- Write the inclusion rule down **and** make the code assert it. A stated rule did not stop an
  aggregation keyed by `(condition, model)` from collapsing 70 episodes to 54.

## Layout

```
submission/        the frozen manuscript and its generated tables
tasks/             the three families + the p13 asset substrate
generators/        the three family generators, their typed graders and substrates
eda_agentbench/    the harness: loader, agentic runner, two-phase workspace, anti-cheat, llm
scripts/           audit infrastructure + per-phase freeze/fairness/analysis scripts
reports/           evidence base; reports/evidence/ is frozen
docs/              bilingual documentation (EN + .zh.md)
```

Evaluators resolve dynamically through `eda_agentbench/evaluator/resolve.py`
(`"module.Class"`, or `"package.module:Class"` for test support). Adding an evaluator needs no
dispatch edit; an unknown spec raises rather than falling back to a different grader.

## Agentic runner controls (`scripts/llm_agent_driver.py`; CLI flag > env > default)

* `EDA_BENCH_LLM_REQUEST_TIMEOUT_SEC` (300) — per-operation socket **inactivity** timeout
* `EDA_BENCH_LLM_REQUEST_DEADLINE_SEC` (300) — hard wall-clock deadline; kills the isolated
  request worker, covering slow-drip stalls
* `EDA_BENCH_MAX_CHAT_RETRIES` (4) — the single retry authority; fresh worker per attempt
* `EDA_BENCH_STREAM_RESPONSES` — SSE opt-in; **required for thinking models**
* `EDA_BENCH_PRESERVE_FINAL_WORKSPACE` — preserve submitted files + hash manifest per episode

## Working rules

- Prefer Python for generators, runners, evaluators and report scripts; simple shell for tool
  invocation. Keep tool setup out of generators — nothing hardcodes an EDA path.
- Every **reader-facing** documentation change ships both languages: `x.md` and `x.zh.md`, with
  the `**English | [中文](x.zh.md)**` header. A monolingual reader-facing doc is an incomplete
  change. Deliberately English-only, for the reasons given in `README.md`: this file, the frozen
  `docs/phase7/*` and `docs/synthetic_*` records, and task `prompt.md`/`spec.md`/`glossary.md`
  (experimental stimuli — rewording them would change the measurement).
- Generated artifacts go in `reports/`, never in `docs/`.
- Never commit `.env`, `runs/`, `workspaces/`, raw simulator output (`*.log *.lis *.raw *.trn *.st0
  *.sw0 *.ac0 *.ic0`), license paths or API keys.
- Sanitize before publishing any log: `<USER> <HOST> <PROJECT_ROOT> <LICENSE_SERVER> <EDA_ROOT>`.
  Note that this branch is **not** anonymised — roughly 212 frozen custody files still carry a
  username or host name, and they cannot be rewritten without breaking the custody chain. A
  double-blind supplement needs a separate sanitising export.
- Do not push this branch or create tags on it without being asked.
