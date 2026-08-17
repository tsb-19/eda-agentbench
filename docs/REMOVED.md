**English | [中文](REMOVED.zh.md)**

# What this branch removed, and how to get it back

`iclr2027-artifact` was cut from `master` at **`cc797ffe`** (tag `iclr2027-submission-v3`) and
reduced to the reproducibility artifact for one paper. **21 574 files were deleted.** Nothing was
lost: every deleted file is intact on `master`, and any of them can be restored with

```bash
git checkout master -- <path>          # or: git show master:<path>
```

The rule was stated by the repository owner and applied literally: **what the paper's main text or
appendix covers is kept; everything else is removed.** The premise is that the paper is already the
filter — its content is what survived scrutiny, so the trial-and-error record behind it does not
belong on a submission branch.

## The largest removal: the P1–P9 benchmark

`master` is also **EDA-AgentBench**, a 2892-task benchmark across 11 tracks (RTL debug, testbench
generation, timing-report QA, SPICE simulation and deck debug, DC synthesis and constraint debug,
SpyGlass lint, PrimeTime STA, PnR report QA, PT exception debug). `submission/main.tex` never
mentions it. It studies three semantic-handoff families and nothing else.

That is not a judgement about the benchmark; it is a scoping fact, and it was confirmed
mechanically before anything was deleted: **every `tasks/` path referenced anywhere under
`reports/` — 1337 files of frozen custody evidence — points at p14, p15 or p16, with zero
references to P1–P9.** The paper's evidence chain and the benchmark are disjoint.

If you came here for the benchmark, use `master`.

## Inventory

| Group | Files | Why removed |
|---|---:|---|
| `tasks/p1_rtl_debug` | 8129 | P1 released track — not in the paper |
| `tasks/p3_timing_report_qa` | 5040 | P3 released track |
| `tasks/p4_spice_sim` | 2244 | P4 released track |
| `datagen/` | 1413 | the P5 spice-deck factory; its only consumer was a removed track |
| `tasks/p2_tb_sva_gen` | 910 | P2 released track |
| `tasks/p5_spice_deck_debug` | 900 | P5 released track |
| `tasks/p6_dc_constraint_debug` | 549 | P6 released track |
| `tasks/p7_primetime_sta_debug` | 530 | P7 released track |
| `tasks/p8_pnr_report_qa` | 505 | P8 released track |
| `tasks/p7_spyglass_lint_debug` | 450 | P7 released track |
| `tasks/p6_dc_synthesis_qa` | 255 | P6 released track |
| `tasks/p9_pt_exception_debug` | 212 | P9 released track (retired as difficulty — frontier-saturated) |
| `tasks/p10_synthetic_project` | 96 | probe family; saturated, superseded by the p14 line |
| `docs/phases/` | 44 | research chronology: saturation syntheses, superseded manuscript drafts, mock reviews, cost and next-step planning |
| `scripts/` | 44 | per-track generators, smoke shells, baseline suite, prompt-variant tooling, `phase6_*` superseded by `phase7c_*` |
| `experiments/` | 36 | retired probes: LEC attribution, MCMM, sequential equivalence, reliability phase-0 |
| `tasks/p11_flow_handoff` | 34 | probe family; saturated |
| `eda_agentbench/` | 33 | 16 per-track evaluators, `pnr/`, `synthesis/`, `timing/`, `prompt/`, `tools/wrappers/`, `task/datagen_bundle.py` |
| `docs/` (top level) | 32 | 8 per-track docs, 5 benchmark docs, 4 internal review rounds, `benchmark_spec` |
| `tests/` | 31 | per-track and per-removed-module tests |
| `reports/` (top level) | 24 | benchmark measurement artifacts, prompt-diversification reports, reliability-layer reports, the phase-6 freeze manifest superseded by phase-7c |
| `tasks/p12_multifact_handoff` | 23 | probe family; saturated |
| `reports/archive/` | 22 | probe reports whose recorded outcome was "saturated / merely positive / superseded" |
| `generators/` | 18 | 16 track generators and the P9 library assets |

## Deliberate exceptions to the rule

Four things the rule would have deleted are kept, each for one reason:

1. **`tasks/p13_trajectory_handoff/traj_handoff_0001/`** (31 files) and
   `eda_agentbench/evaluator/trajectory_handoff.py`. `generators/p14_workflow_handoff_gen.py:38`
   reads that directory as its asset substrate ("REUSE the committed, b04-validated p13
   substrate"), so deleting it would make Study I's family unregenerable. It is **an asset
   substrate, not a studied family** — no paper claim rests on it. Relocating the substrate was
   rejected: it would mean editing a generator that produced frozen, hash-pinned tasks, for no
   scientific gain. Its contract test is kept too, so nothing retained is untested.
2. **`eda_agentbench/llm/` and `reliability.py`.** `scripts/llm_agent_driver.py` is frozen
   membership code and imports both; frozen code may not be edited to remove a dependency.
3. **`scripts/generate_model_submissions.py`, `run_model_baseline.py`, `scan_discrimination.py`.**
   Same reason, one level out: `llm_agent_driver.py`, `phase4y_debug_grade.py` and
   `run_agentic_baseline.py` import them. The first attempt at that commit dropped all three and
   the test suite failed at collection inside a pinned driver.
4. **Four construction-spec documents** relocated from `docs/phases/` to `docs/` rather than
   deleted, because they are the construction record of things the paper asserts, not chronology:
   `synthetic_workflow_generator_spec.md`, `synthetic_phase5a_design.md`,
   `synthetic_phase5a_family_specs.md`, `synthetic_phase5a_generator_grader_plans.md`.

Two paths **could not** move even if it were tidier:
`docs/synthetic_p14_phase4w_clarity_bundle_ablation_design.md` is cited by path inside a frozen
manifest, and `docs/phase7/phase7_synthesis.md` has its sha256 recorded in
`submission/FREEZE_HASHES.md`.

## What changed rather than disappeared

| File | Change |
|---|---|
| `eda_agentbench/cli.py`, `agentic/runner.py` | each carried a ~55-line `if/elif` evaluator chain with a silent fallback to the RTL-debug evaluator; both now delegate to `evaluator/resolve.py`, which resolves dynamically and raises on an unknown spec |
| `eda_agentbench/schema.py` | track, `task_id` and tool enums pruned to the surviving families |
| `eda_agentbench/task/validator.py`, `llm/openai_provider.py` | two comments naming removed modules repaired |
| `scripts/check` | the optional Tier-2 discrimination scan (a benchmark-wide instrument) replaced by the frozen-membership verifier |
| `scripts/validate_dataset.py` | docstring example re-pointed from a removed track to p15 |
| `scripts/phase4z_figures_tables.py` | output moved from `docs/phases/` to `reports/`; re-run output is byte-identical, so this is a relocation, not a regeneration |
| `tests/test_agentic_runner.py` | fixtures re-pointed to `tests/support/qa_stub_evaluator.py`, because all three surviving families need commercial tools and none can exercise the runner tool-free |
| `tests/test_workflow_handoff_gen.py`, `test_trajectory_handoff.py` | the dispatch-parity guards now assert delegation to the shared resolver — the same invariant, expressed against the new structure |
| `reports/README.md` | rewritten as a reviewer-facing evidence index; `README.zh.md` added |

New on this branch: `scripts/frozen_membership_verify.py`, `scripts/slim_link_check.py`,
`docs/frozen_membership_baseline.json`, `docs/artifact_map.md`, this file, and their Chinese
counterparts.

## Known limitation: this branch is not anonymised

About 212 files under `reports/evidence/`, plus roughly 30 kept reports, contain a username, the
remote tool host name, or an absolute home path. They are hash-pinned custody records: rewriting
them would break the very custody chain the paper asserts, and `scripts/frozen_membership_verify.py`
would report the drift.

So this branch is the clean *internal* artifact, not a double-blind supplement. An anonymised
supplement needs a separate sanitising **export** — a derived tarball produced by a substitution
pass, with the substitution table published — not a git edit. That export is not part of this
branch.

## Verifying the slim did no damage

```bash
scripts/check                                          # tests + structure + 1065 custody pins
python3 scripts/slim_link_check.py                     # no dangling repository references
python3 scripts/phase7c_study1_ledger.py --check       # 58 + 12 = 70 episodes
python3 scripts/phase7c_claim_statistics.py --check    # 12.5 / [-12.5, 41.7] / -16.7
cd submission && make distclean && make                # 18 pp, sha256 unchanged
```

Every one of these was green on `master` before the first deletion and is green now. The custody
gate is the load-bearing one: it re-hashes all 1065 `path → sha256` pins recorded by the pre-run
manifests and requires the counts to match `docs/frozen_membership_baseline.json` exactly —
including the 2 pre-existing mismatches and 9 gitignored build products, which are carried forward
rather than quietly cleaned up.
