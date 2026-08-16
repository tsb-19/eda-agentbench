# Slim Paper-Artifact Branch (`iclr2027-artifact`) — Design

**Date:** 2026-08-16
**Status:** approved (scope confirmed by the user; documentation plan and verification plan confirmed)
**Branch:** `iclr2027-artifact`, cut from `master@cc797ffe` (tag `iclr2027-submission-v3`)
**Constraint:** `master` is not modified. The branch stays local — no push, no tag — unless separately asked.

## Goal

Produce the repository version that corresponds to the ICLR 2027 submission: a reader who
arrives from the paper should find the three task families the paper studies, the audit
infrastructure it describes, the frozen evidence its numbers derive from, and nothing else.

The governing rule, stated by the user: **what the paper (main text *and* appendix) covers is
kept; everything else is removed.** The hidden premise is that the paper already is the filter —
its content is what survived scrutiny, so process, dead ends and superseded artifacts do not
belong on this branch.

Non-goal: this is not a refactor. Behavioural code changes are limited to what deletion forces.

## What the paper actually covers

`submission/main.tex` (v12, 15 pp) is exclusively the semantic-handoff research line:

- **Study I** (S0, S1, S2-M) — `tasks/p14_workflow_handoff`, the clarity-bundle ablation
- **Study II** (S2-F) — `tasks/p15_sta_handoff` (Family A, prospective *n*=12 + 3-instance pilot)
  and `tasks/p16_spice_handoff` (Family B, non-discriminative ceiling)
- **Study III** — the four-layer measurement-validity protocol, seven audit incidents, and the
  Terminal-Bench 2.0→2.1 external coding
- **Appendices A–G** — worked instance, Study I ledger, STA detail, the 26-task coding,
  chronology and freeze points, infrastructure/custody, positioning

It never mentions the 2892-task P1–P9 benchmark, nor the p10–p13 probe families, nor the
reliability/calibration layer. Independent confirmation: every `tasks/` path referenced anywhere
under `reports/` (1337 files of frozen evidence) points at p14, p15 or p16 — zero references to
P1–P9.

## Derived facts that constrain the cleanup

Established by inspection, not assumption.

| Object | Status | Evidence |
|---|---|---|
| `reports/evidence/**` | **frozen custody evidence — read-only** | per-episode SHA256SUMS + pre-run membership manifests |
| **1065 path→sha256 pins** across `reports/**/*.json` | **must stay byte-identical** | `membership_code_manifest.json`, `prerun_freeze_manifest.json`, `phase5[bc]_*_manifest.json` |
| `docs/phase7/phase7_synthesis.md` | **hash-pinned — must not move or change** | `submission/FREEZE_HASHES.md` records its SHA-256 |
| `docs/synthetic_p14_phase4w_clarity_bundle_ablation_design.md` | **path-pinned — must not move** | `reports/evidence/p14_phase4w_fairness/MANIFEST.json` cites the path as prose |
| `submission/` | ICLR final; PDF is byte-reproducible | `SOURCE_DATE_EPOCH` pinned in the Makefile |
| experiment freeze HEAD `a89e084` | immutable; experiments permanently closed | `docs/SUBMISSION_STATE.md` |
| `generators/p14_workflow_handoff_gen.py:38` reads `tasks/p13_trajectory_handoff/traj_handoff_0001` | **that one directory must survive** | `P13_SRC`; generator header: "REUSE the committed, b04-validated p13 substrate" |
| `eda_agentbench/evaluator/__init__.py` is empty | dropping evaluator files needs no registry edit | — |
| `eda_agentbench/cli.py` dispatches evaluators via an explicit `if/elif` chain | **prune required** | `cli.py:545+` |
| `scripts/llm_agent_driver.py` (hash-pinned) imports `eda_agentbench.llm` and `.reliability` | **both must be kept** | AST import scan |

### Baselines recorded on `master@cc797ffe`

| Gate | Baseline |
|---|---|
| frozen membership | 1065 pins · 9 missing (`p16 circuit_built.sp`, gitignored build products) · 2 mismatch (`p15`/`p16` generators drifted post-phase5b freeze; pre-existing) · 1 multi-sha (`phase5c_run.py`, versioned across phases) |
| `pytest -m "not requires_tools"` | 1133 passed, 13 skipped, 7 deselected |
| `phase7c_study1_ledger.py --check` | rc 0 — 21 cells, 58 program-primary + 12 controlled-pair = 70 |
| `phase7c_claim_statistics.py --check` | rc 0 — `sta_delta_pp 12.5`, band `[-12.5, 41.7]`, `pilot_delta_pp -16.7` |
| `submission`: `make distclean && make` | 3 pdflatex runs, 15 pages, 268 459 bytes, sha256 `bbf948bf…`, tree clean after |

The 2 pre-existing mismatches and 9 missing files are *carried forward unchanged*. The gate is
"reproduces this baseline", not "is empty" — inventing a clean sheet would hide real drift.

## Keep / remove

Projected: **25 722 → ~4 160 tracked files; 43.2 → 18.7 MB.**

| Area | Keep | Remove |
|---|---|---|
| `submission/` | all 16 files | — |
| `tasks/` | `p14_workflow_handoff` (27 inst.), `p15_sta_handoff` (46), `p16_spice_handoff` (10), `p13_trajectory_handoff/traj_handoff_0001` (substrate only) | `p1`–`p12` — 11 released tracks (2892 tasks) + 3 probe families; ≈21 500 files |
| `generators/` | `p14/p15/p16` generators, family graders, substrates, `phase5_audits.py`, `phase5_treatment_mapping/`, `base.py`, `__init__.py` | 14 track generators, `assets/p9_pt_exception_debug/` |
| `eda_agentbench/` | 33 files: CLI, schema, loader/validator, agentic runner + workspace + test_agents, anti-cheat, `llm/`, `reliability.py`, `sanitizer/`, `tools/{detector,env_shim}`, evaluators `workflow_handoff`/`sta_handoff`/`spice_handoff`/`trajectory_handoff`/`base` | 16 per-track evaluators, `pnr/`, `synthesis/`, `timing/`, `prompt/`, `tools/wrappers/`, `task/datagen_bundle.py` |
| `scripts/` | 79: all 56 frozen-pinned, plus phase4W/X/Y/Z, phase5A–D, phase7A, phase7C, and the audit infrastructure (`canonical_integrity`, `episode_arbiter`, `chain_executor`, `fairness_retry`, `measurement_control`, `*_health_sentinel`, `llm_agent_driver`, `run_chain_guarded`, `check`, `validate_dataset`) | 47: track generators, smoke shells, baseline suite, prompt-variant tooling, `phase6_*` (superseded by `phase7c_*`), `scan_discrimination` |
| `reports/` | `evidence/` (1337, untouched) + 61 top-level p14/p15/p16 reports + `README.md` | 16 benchmark artifacts, 2 prompt-diversification, 4 reliability-layer, `archive/` (22 saturated probes), 2 `phase6_freeze_manifest` |
| `docs/` | curated + rewritten (below); `phase7/` keeps synthesis, preregistration, preflight, sta_bug_audit, annotation_freeze | `phases/` (46 chronology docs), 8 per-track docs, `benchmark_tracks`, `adding_tasks`, `baseline_eval`, `prompt_diversification`, `public_release_policy`, `benchmark_spec`, 4 mock-review docs, `SUBMISSION_STATE.md` (merged into provenance) |
| `tests/` | 25: the 11 frozen-pinned, plus core (`conftest`, `anti_cheat`, `sanitizer`, `detector_root_override`, `dataset`, `validate_dataset`, agentic runner/provisioning, probe-artifact preservation) and family tests (`workflow_handoff_gen`, `phase5_*`) | 32 per-track and per-dropped-module tests |
| `datagen/` | — | all 1413 files (P5 factory only) |
| `experiments/` | — | all 36 files (retired LEC / MCMM / sequential-equivalence / reliability probes) |

`tasks/p13_trajectory_handoff/traj_handoff_0001` and `evaluator/trajectory_handoff.py` are kept
**only** because the p14 generator reads that substrate. Both are labelled as such in the docs,
so a reader does not mistake p13 for a studied family. Patching `P13_SRC` to relocate the
substrate was rejected: it would edit a generator that produced frozen, hash-pinned tasks for no
scientific gain.

### Code edits deletion forces

All on files that carry no frozen hash.

| File | Edit |
|---|---|
| `eda_agentbench/cli.py` | prune the evaluator dispatch chain to the kept evaluators; replace the `rtl_debug.VCSRTLEvaluator` default with an explicit error; drop dropped-track references. `_evaluate_single`, `build_buggy_submission`, `solution_submission_path` keep their names and behaviour (`scripts/run_agentic_baseline.py`, hash-pinned, imports them) |
| `eda_agentbench/schema.py` | prune the track enumeration to the surviving tracks |
| `eda_agentbench/agentic/runner.py` | drop dropped-track special cases |
| `scripts/check` | drop step 3 (Tier-2 discrimination scan; `scan_discrimination.py` is removed) and correct the header comment |
| `scripts/validate_dataset.py` | drop the P4-specific real-tool validation path |
| `tests/test_dataset.py`, `test_agentic_runner.py`, `test_validate_dataset.py` | re-point fixtures from dropped tracks to a handoff instance |

## Documentation

Convention preserved: `**English | [中文](x.zh.md)**` header plus a parallel `.zh.md`.

**New (EN + ZH):**

- `docs/artifact_map.md` — the paper↔file map: every claim, table, figure and audit incident in
  `main.tex` resolved to the files that produce it (main matrix, Study I ledger, `\Stat*` macros,
  worked instance, all seven incident rows, Terminal-Bench coding, freeze points, family
  independence). Each row is verified by grep during execution, never asserted.
- `docs/REMOVED.md` — removal inventory: every removed path group, its reason, and
  `git checkout master -- <path>` recovery, anchored at `master@cc797ffe`. Makes the slimming
  auditable rather than a silent loss.

**Rewritten (EN + ZH):** `README` (front door: the claim, the five supports S0/S1/S2-M/S2-F/S3,
layout, five-minute reproduction, what is deliberately absent and where it lives) ·
`docs/reproducibility` (the exact command chain per table; which steps need commercial tools) ·
`docs/datacard` (the 83 handoff instances, conditions, uniqueness gates, hidden/oracle split) ·
`docs/scoring` (typed-binding oracle, the two never-collapsed failure subtypes, the master
evidence gate — replacing the P1–P8 weight tables) · `docs/status.{md,zh.md}` renamed via
`git mv` to `docs/provenance.{md,zh.md}` and rewritten, absorbing `SUBMISSION_STATE.md`
(experiment freeze `a89e084`, submission tag, the two explicit HEADs) ·
`docs/agentic_runner` (examples re-pointed to a p14 instance; driver env vars) ·
`docs/task_schema`, `docs/commercial_tool_policy` (light edits) · `CLAUDE.md` (agent-facing:
what is frozen, what is editable, which gates to run) · `reports/README.md` (reindexed) ·
`docs/overview.zh.html` plus a new EN sibling `docs/overview.html`.

**Added:** `docs/incident_golden_corruption.zh.md` — the incident is a section of the paper and
was English-only.

## Verification

Two new tools, committed first so every later commit is gated:

- `scripts/frozen_membership_verify.py` — walks every `reports/**/*.json`, extracts all
  path→sha256 pins, re-hashes each target, and reports pins / missing / mismatch / multi-sha.
  Passing means "identical to the recorded master baseline".
- `scripts/slim_link_check.py` — resolves every repo-path reference in kept, non-frozen text
  files; fails on a dangling target. `reports/evidence/**` is exempt because G1 covers it.

| | Gate | Must show |
|---|---|---|
| G1 | `python3 scripts/frozen_membership_verify.py` | 1065 pins · 9 missing · 2 mismatch · 1 multi-sha |
| G2 | `python3 -m pytest -q -m "not requires_tools" tests/` | 0 failed |
| G3 | `scripts/check` | `CHECK PASSED` |
| G4 | `python3 scripts/phase7c_study1_ledger.py --check` | rc 0; 58 + 12 = 70 |
| G5 | `python3 scripts/phase7c_claim_statistics.py --check` | rc 0; `12.5` / `[-12.5, 41.7]` / `-16.7` |
| G6 | `cd submission && make distclean && make` | 3 pdflatex runs, 15 pages, 268 459 bytes, sha256 `bbf948bf…`, `git status` clean |
| G7 | `python3 scripts/slim_link_check.py` | no dangling references |
| G8 | `git status`; `git diff master --stat` | clean; only deletions plus the enumerated edits; `tasks/p14_workflow_handoff/workflow_handoff_0009/solution/flow_config.json` never becomes `{}` |

G1–G5 run after every commit. G6–G7 run at the tail and before the final commit. G6 was
exercised on the untouched tree first, so a later LaTeX failure cannot be misattributed to the
toolchain — the same discipline as the v9 stale-PDF incident. Counting pdflatex start banners,
rather than trusting a log's existence, is deliberate for the same reason.

## Commit sequence

1. verifier + link checker + recorded baseline
2. remove P1–P9 released task tracks and p10–p12 probe families
3. remove per-track generators, evaluators and tests; prune `cli.py` / `schema.py` / `runner.py`
4. remove non-paper scripts, `datagen/`, `experiments/`
5. remove benchmark, archive, reliability and phase6 reports; reindex `reports/README.md`
6. remove research-chronology and per-track docs
7. new bilingual front door: `README`, `artifact_map`, `REMOVED`
8. rewrite `reproducibility`, `datacard`, `scoring`, provenance, `agentic_runner`, tool policy (EN + ZH)
9. `CLAUDE.md` and the overview pages
10. `VERIFICATION.md` recording every gate's output

Tooling first so deletions are gated from the start; deletions before documentation so the docs
describe the final tree.

## Known limitation, stated rather than fixed

Roughly 212 files under `reports/evidence/` plus about 30 kept reports contain `tongsb`, `b04`
or `/data1/...`. They are hash-pinned custody records: rewriting them would break the very
custody chain the paper asserts. This branch is therefore **not** an anonymised supplement. A
double-blind supplement needs a separate sanitising *export* — a derived tarball with a published
substitution table — not a git edit. `docs/REMOVED.md` and the README both record this.

## Out of scope

Any change under `submission/`, `reports/evidence/`, or the p14/p15/p16 task trees; reopening
any experiment; editing any frozen manifest; restructuring `scripts/`; anonymisation.
