# Phase-4Z Experiment-Freeze Manifest

**Frozen at HEAD:** `30436d3` (`30436d3156bca287526eec4f060ef23c9ea1ae9d`) · **Branch:** synthetic-phase0a · **No paid calls / no further data collection.**

## Declaration

> No subsequent data collection (paid model calls or mechanism-search experiments) contributes to the current paper. The experimental program is frozen at this HEAD. Held-out-family-2 is preserved untouched as a future-replication asset.

## Load-bearing commit chain

- `d8fb7bd` — canonical-tree integrity guard (freeze/verify/enforce + FAILED_INTEGRITY)
- `a1ce79e` — track p14 prev_signoff.log artifacts (worktree-checkout completeness)
- `4aef6a6` — eval-workspace _ensure_writable-before-overlay (guarded-run fix)
- `1f9d4a6` — C24 bridge report (not_established)
- `c18bb1a` — Stage-3/C24 conclusion amendment (C2xC4 unresolved)
- `f2ab1ae` — Phase-4Z consolidated synthesis
- `30436d3` — Phase-4Z paper outline + claim-evidence matrix

<details><summary>Full commit chain (latest 25)</summary>

```
30436d3 docs(p14): Phase-4Z paper outline + claim-evidence matrix (no paid calls)
f2ab1ae docs(p14): Phase-4Z consolidated evidence synthesis (no paid calls)
c18bb1a docs(p14): Stage-3 + C24 bridge conclusion amendment — C2xC4 joint-effect hypothesis UNRESOLVED (report-only)
1f9d4a6 report(p14): Phase-4Y C24 bridge — in-window C24/0021 k=4 NOT replicated at threshold (2/4, 1 axis) under the integrity guard
9d76645 feat(p14): C24 bridge pre-run freeze (re-run on workspace-fix 4aef6a6) — in-window C24/0021 k=4 under the canonical-tree integrity guard
4aef6a6 fix(agentic): _ensure_writable before eval-workspace overlay (guarded-run 0.00 fix)
a1ce79e fix(p14): track curated prev_signoff.log task artifacts (were dropped by *.log gitignore)
d8fb7bd feat(infra): canonical-tree integrity guard for paid runs (freeze/verify/enforce + FAILED_INTEGRITY stop)
5a7f8db docs(p14): Stage-3 wording amendment — candidate C2xC4 interaction, not a formally identified super-additive interaction (report-only)
315f247 chore(reports): refresh dataset inventory summaries for p14 0022-0027 (2923 -> 2929)
39d9609 report(p14): Phase-4Y Stage-3 C2-only vs C4-only — both_weak (bundle interaction), k=4 Qwen
3f058e1 feat(p14): Phase-4Y Stage-3 pre-run gate — fairness ALL_PASS (block measurement-control) + freeze (C2-only 0022 vs C4-only 0023, k=4, exact-counterbalanced)
7f36954 feat(p14): held-out family-2 static freeze (golden fast/lowpower; Base/+C2/+C4/+C24) — no model calls
95aa33c feat(p14): Stage-3 fairness under block measurement-control (validated; b04 window unhealthy)
f6a716e feat(infra): score-independent measurement-control — Level-2 full-path check + block protocol (tested)
8381570 feat(p14): Phase-4Y Stage-3 construction (C2-only 0022 vs C4-only 0023) — fairness blocked by b04 golden-corruption
007aa7b docs(p14): Phase-4Y Stage-2 acceptance — narrow C24 conclusion, C1 'not stable sufficient', b04 outage + held-out-1 caveat (report-only)
1c2cc6a report(p14): Phase-4Y Stage-2 C1 vs C24 — C1 does NOT eliminate axis errors (refutes cell 5)
05bb7cd feat(p14): Phase-4Y Stage-2 pre-run gate PASS — C1 vs C24 fairness + freeze (b04 recovered)
b5a16d2 feat(p14): Phase-4Y Stage-2 construction (C1 0020 vs C24 0021) — FAIRNESS BLOCKED BY b04 OUTAGE
751e38f feat(p14): fairness-gate validity-based retry + b04/PT health sentinel (tested)
ffc23e5 docs(p14): Phase-4Y Stage-1 causal-wording correction (report-only)
934ed44 report(p14): Phase-4Y Stage-1 Schema vs Contract — Schema 2/3 > Contract 1/3 (directional, within Qwen)
1d2b2c9 chore: refresh auto-generated benchmark summary/inventory (p14 17->19, total 2921)
50e2ded feat(p14): Phase-4Y Stage-1 pre-run freeze — Schema (0018) vs Contract (0019), Qwen
```
</details>

## Phase × task × model matrix (numbers read from report JSON + episode ledgers)

| phase | design | tasks | model | conditions | primary | excluded | invalid | aborted | cost ¥ |
|---|---|---|---|---|---|---|---|---|---|
| 4W-Run1 | confirmatory | 0013/0014 | Qwen3.7-Max | V1/V9 | 6 | 0 | 0 | 0 | 60.71 |
| 4W-Run2 | confirmatory | 0015/0016 | Qwen3.7-Max | BundleS/BundleD | 6 | 0 | 0 | 0 | 76.79 |
| 4W-Held | frozen held-out confirmation | 0011/0017 | Qwen3.7-Max | Base/Held | 6 | 0 | 0 | 0 | 64.78 |
| 4X-S1 | confirmatory (deviation disclosed) | 0009/0010(0015) | DeepSeek-V4-Pro | Base/BundleS | 6 | 2 | 0 | 1 | 73.79 |
| 4X-S1B | no-call audit (0 episodes) | — | Qwen3.7-Max | — | 0 | 0 | 0 | 0 | 0.00 |
| 4X-S1C | confirmatory | 0009/0010(0015) | DeepSeek-V4-Pro | Base/BundleS | 8 | 1 | 0 | 0 | 81.44 |
| 4Y-S1 | sequential exploratory localization | 0018/0019 | Qwen3.7-Max | Schema/Contract | 6 | 0 | 0 | 0 | 73.63 |
| 4Y-S2 | sequential exploratory localization | 0020/0021 | Qwen3.7-Max | C1/C24 | 8 | 0 | 0 | 0 | 95.21 |
| 4Y-S3 | sequential exploratory localization | 0022/0023 | Qwen3.7-Max | C2/C4 | 8 | 0 | 0 | 0 | 101.67 |
| 4Y-Bridge | null/inconclusive replication | 0021 | Qwen3.7-Max | C24 | 4 | 0 | 0 | 0 | 54.23 |
| **TOTAL** | | | | | **58** | **3** | **0** | **1** | **682.25** |

**Transport:** SSE streaming (EDA_BENCH_STREAM_RESPONSES=1; inactivity 120s, hard deadline 300s, max 1 retry) for all model phases.

## Report inventory (SHA-256)

22 files under `reports/synthetic_p14_phase4*`. Full hashes in the `.json` companion; sample:

```
b10c2f9e8e2e8ef3…  reports/synthetic_p14_phase4w_heldout.json
860ec290c4736aa1…  reports/synthetic_p14_phase4w_run1.json
ad92d9da767e8142…  reports/synthetic_p14_phase4w_run2.json
64c77d2195cb680a…  reports/synthetic_p14_phase4x_dev.json
cd766045f65a537a…  reports/synthetic_p14_phase4x_stage1b.json
30fe4ca390cf0b2a…  reports/synthetic_p14_phase4x_stage1c.json …
```

## Evidence inventory

19 evidence dirs under `reports/evidence/p14_phase4*`; custody byte-match MANIFEST/SHA256SUMS present in each episode dir. Hashes in the `.json` companion.

## Held-out-family-2

- **Status:** UNTOUCHED future-replication asset; not run, not altered, no variant selected on existing outcomes
- Manifest: `reports/evidence/p14_phase4y_heldout2/MANIFEST.json` (present: True, sha256 `bdcc8654108b659c…`)

## Integrity guard (mandatory infrastructure)

- Authoritative control commit: `d8fb7bd`; mandatory for all future fairness gates / paid runs / evidence extraction / custody. Root development workspace is non-authoritative; `chmod 444` is defense-in-depth only.
- Guard file hashes in the `.json` companion.

## Typo check

- Sought `C2×C2` / `C2xC2` across `reports/` and `docs/`: **0 occurrences** — no C2xC2 typo; all forms are C2xC4.

