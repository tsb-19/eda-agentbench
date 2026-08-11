# Repository Cleanup and Documentation De-staling — Design

**Date:** 2026-08-11
**Status:** approved (scope + both judgment calls confirmed by the user)
**Context:** the repository is simultaneously (a) a working benchmark codebase and (b) the reproducibility artifact for an ICLR 2027 submission that has just been frozen and pushed (`3d3e77b`). Every cleanup action must preserve (b).

## Goal

Reduce documentation staleness and repository clutter, and reclaim local disk, **without touching any frozen scientific artifact**. Explicitly *not* a refactor: no script restructuring, no behavioural code changes.

## Verified safety boundaries

These were established by direct inspection, not assumption. Do not re-derive; do not violate.

| Object | Status | Evidence |
|---|---|---|
| `tasks/` (136M, 22 420 tracked files) | **frozen dataset — never touch** | `scripts/check` gates 2985/2985 |
| `submission/` | **ICLR final — never touch** | pushed `3d3e77b` |
| `reports/evidence/` (1334 tracked files) | **frozen custody evidence + pre-run manifests — read-only** | per-episode SHA256SUMS; pre-registration manifests |
| experiment freeze HEAD `a89e084` | **immutable** | no experiments may be reopened |
| `docs/phase7/phase7_synthesis.md` | **hash-pinned — must not move** | `submission/FREEZE_HASHES.md` pins its SHA-256 |
| `docs/synthetic_p14_phase4w_clarity_bundle_ablation_design.md` | **path-pinned — must not move** | `reports/evidence/p14_phase4w_fairness/MANIFEST.json` → `predeclared_interpretation_table` references this path as prose; the manifest is frozen and may not be edited, so the path must remain valid |
| `scripts/` (62 one-off phase scripts) | **structure preserved** | they are the paper's reproducibility path |

Verified **safe to edit**: `scripts/phase6_freeze_matrix.py`, `scripts/phase6_figures.py`, `scripts/phase4z_figures_tables.py` — grepped against every manifest under `reports/evidence/` and `submission/`: **0 hits**, i.e. none is hash-frozen membership code.

## Key finding: an un-backed-up evidence orphan

An audit hashing all 73 `preserved/` artifacts under `runs/` against every tracked file in `reports/` found **72 byte-identical matches in git and exactly 1 orphan**:

```
runs/phase7a/p15_eval_0004/20260808_225705/preserved/exception_config.json
```

Its timestamp appears in **0** tracked files, and `reports/evidence/phase7a_state.json` records `replaced: 1` with all six `p15_eval_0004` episodes marked `measurement_valid: true`. The orphan is therefore the artifact of the single **validity-only replacement** disclosed in the manuscript — a discarded episode whose artifact has never been in git. Deleting `runs/` without rescuing it would irreversibly destroy the only record of the one replacement the paper reports.

The rest of `runs/` (167M: `dataset_*`, `baseline`, agentic run trees) is regenerable bulk evaluation output containing no custody evidence.

## Work items

### A. Rewrite `CLAUDE.md`
Stale on three counts: task count `2912` (actual **2985**); header still reads `2026-07 — branch synthetic-phase0a` (now `master`, 2026-08); and the entire Phase-5→7C manuscript/submission arc is absent (`Phase-5|6|7`, `ICLR`, `submission`, `manuscript` occur **0** times). Correct the facts and add a submission-state section. Preserve the existing structure, tone and conventions.

### B. Consolidate superseded status docs
`current_status`, `current_v0_status`, `roadmap` (6 files incl. `.zh`, last touched June) overlap and are two months stale. Merge into a single `docs/status.md` + `docs/status.zh.md` reflecting current reality. Content must be preserved in the merge; the old filenames need not survive (user decision). Repair the 4 known inbound cross-links (`](roadmap.md)` ×2, `](current_status.md)` ×2).

### C. Archive research-chronology docs
`git mv` **46** `synthetic_*` / `phase*` / `reliability_*` / `lec_*` / `next_gen_*` / `benchmark_hardening_*` docs into `docs/phases/` (flat; content unchanged, git history preserved). This leaves `docs/` top level holding only evergreen documentation. Excluded from the move: the path-pinned p14 clarity-bundle design doc (above).

Mandatory companion edits — three scripts write into the moved paths and would silently recreate stale duplicates at the old locations:

| Script | Line | Output path to update |
|---|---|---|
| `scripts/phase6_freeze_matrix.py` | 136, 156 | `docs/synthetic_phase6_claim_matrix.{json,md}` |
| `scripts/phase6_figures.py` | 82 | `docs/synthetic_phase6_figures_tables.md` |
| `scripts/phase4z_figures_tables.py` | 14 | `docs/synthetic_p14_phase4z_figures_tables.md` |

Also repair cross-links among the moved documents (`](phase6_design.md)` etc.).

### D. Test hygiene
A bare `pytest tests/` reports **7 failures**; all are EDA-tool tests (P5/HSPICE, P9/PrimeTime, smoke/VCS) failing purely because the commercial tools are absent locally. They are correctly marked `requires_tools` and correctly excluded by `scripts/check` (`-m "not requires_tools"`), but they *fail* rather than *skip*, so a bare run looks like a broken repository. Add a tool-presence `skipif` so a bare run is green, and fix the inaccurate "auto-skip" wording in the `scripts/check` header comment.

### E. Archive superseded reports
Move superseded phase reports from the `reports/` top level into the existing `reports/archive/`. The selection criterion is explicit and conservative: a report is archived only if a later report in the same series supersedes it (e.g. an earlier run of the same phase/stage) **and** its path is referenced by no tracked manifest, no `docs/` file, and no script. Anything referenced anywhere stays put. `reports/evidence/` is untouched, as are the reports the manuscript's frozen numbers derive from (`synthetic_phase7a_sta72_report.*`).

### F. Reclaim disk (~170M)
1. **Rescue the orphan first**: copy it to `reports/evidence/phase7a_discarded/` with a short README recording that it is the discarded artifact of the single validity-only replacement, plus its original path and run timestamp. This *adds* to the evidence base; it modifies nothing frozen.
2. Then delete `runs/` (167M), `pilot_p1mf|p1subtle|p1subtle_nohint/` (2.4M, gitignored and regenerable from the seeded `prototype_p1_*` generators), and the 25 `__pycache__` trees.

## Commit structure

Six independent commits, in order **A, B, C, D, E, F**, running `scripts/check` after each. The destructive step (F.2) runs last and only after the orphan is committed (F.1).

## Verification

- `scripts/check` passes (2985/2985) after every commit.
- After C: re-running the three edited scripts writes into `docs/phases/`, and no file reappears at a top-level moved path.
- After D: bare `pytest tests/` is green (0 failed), and `scripts/check` still passes.
- After F.1: the orphan is tracked in git and byte-identical to the source before F.2 deletes it.
- `git status` clean at the end; `tasks/` shows no modification at any point (guards against the recurring `workflow_handoff_0009/solution/flow_config.json` → `{}` corruption, which must be restored and never committed if it recurs).

## Out of scope

Restructuring `scripts/`; any change under `tasks/`, `submission/`, or `reports/evidence/` (beyond the additive orphan rescue); reopening any experiment; editing any frozen manifest.
