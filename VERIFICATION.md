# Verification record — `iclr2027-artifact`

Every gate below was green on `master@cc797ffe` **before** the first deletion and is green now.
Re-run them all with the commands shown; each is deterministic and needs no EDA tool, no network
and no model call.

中文版：[VERIFICATION.zh.md](VERIFICATION.zh.md)。

Recorded at `dd867c84` on `iclr2027-artifact`, branched from `master@cc797ffe`.

**This is a snapshot, and two of its rows have deliberately moved since.** The branch later took a
new manuscript freeze (v13), so the PDF row below records v12 (15 pp, `bbf948bf…`) rather than the
current artifact, and the pytest count has grown with the tests added alongside it. The recorded
numbers are left as measured — this file's claim is that slimming preserved `master`'s baselines,
and rewriting its measurements would destroy that claim. Current submission hashes and page counts
live in [`submission/FREEZE_HASHES.md`](submission/FREEZE_HASHES.md).

## G1 — frozen membership (`scripts/frozen_membership_verify.py`)

Re-hashes every `path → sha256` pin recorded by the pre-run manifests under `reports/evidence/`
and requires the counts to match `docs/frozen_membership_baseline.json` exactly. **A non-zero
report is the correct one** — see that file for why each count is legitimately non-zero.

```
pinned paths : 1065
missing      : 9
    tasks/p16_spice_handoff/p16_eval_0001_base/files/circuit_built.sp
    tasks/p16_spice_handoff/p16_eval_0001_bundles/files/circuit_built.sp
    tasks/p16_spice_handoff/p16_eval_0001_typedcontract/files/circuit_built.sp
    tasks/p16_spice_handoff/p16_eval_0002_base/files/circuit_built.sp
    tasks/p16_spice_handoff/p16_eval_0002_bundles/files/circuit_built.sp
    tasks/p16_spice_handoff/p16_eval_0002_typedcontract/files/circuit_built.sp
    tasks/p16_spice_handoff/p16_eval_0003_base/files/circuit_built.sp
    tasks/p16_spice_handoff/p16_eval_0003_bundles/files/circuit_built.sp
    tasks/p16_spice_handoff/p16_eval_0003_typedcontract/files/circuit_built.sp
mismatch     : 2
    generators/p15_sta_handoff_gen.py  now 2784bc1158fd  pinned e0a68acb9198
    generators/p16_spice_handoff_gen.py  now 8954b666af74  pinned 4083a9dbdde7
multi-sha    : 1
    scripts/phase5c_run.py
```

## G2+G3 — `scripts/check` (pytest, task structure, custody pins)

```
$ scripts/check
== [1/3] pytest (tool-free unit suite; -m 'not requires_tools') ==
482 passed, 2 skipped in 86.75s (0:01:26)

== [2/3] structural dataset validation (schema + files + golden present) ==
p13_trajectory_handoff       1     1/1
p14_workflow_handoff        27    27/27
p15_sta_handoff             46    46/46
p16_spice_handoff           10    10/10
ALL STRUCTURALLY VALID (schema + required files + golden present).
TOTAL: 84/84 valid

== [3/3] frozen membership (path->sha256 pins under reports/evidence/) ==
(the G1 output above, verbatim)
frozen membership matches the recorded baseline

CHECK PASSED
```

## G4 — Study I ledger reproduces from the frozen records

```
$ python3 scripts/phase7c_study1_ledger.py --check
  "correct": 41,
  "axis_binding_failure": 24,
  "role_conditioned_value_selection_failure": 5,
  "cells": 21,
  "program_primary": 58,
  "controlled_pair": 12,
  "total": 70
}
```

## G5 — claim statistics reproduce from the frozen records

```
$ python3 scripts/phase7c_claim_statistics.py --check
{"ok": true, "sta_delta_pp": 12.5, "sta_band_pp": [-12.5, 41.7], "pilot_delta_pp": -16.7, "fisher": {"S0": 0.4, "S1": 0.4, "S2-M": 1.0}, "resolved_snapshot_retained": false}
```

## G6 — manuscript rebuilds byte-identically

Counting pdflatex **start banners** rather than trusting that a log exists: `make clean` keeps
`main.pdf`, so a plain `make` afterwards is a no-op, and a v9 page count was once measured off a
stale PDF for exactly that reason.

```
$ cd submission && make distclean && make
pdflatex start banners : 3
Output written on main.pdf (15 pages, 268459 bytes).
sha256                 : bbf948bfc533e3162eef4a299a1215b2664b0d3189bccc51ed65d257aba7a2e1
git status after build : clean (the rebuild is byte-identical)
```

## G7 — no dangling repository references (`scripts/slim_link_check.py`)

Resolves every repository path referenced by a kept file. `reports/evidence/**` is exempt
(frozen and unrepairable; covered by G1 instead). 15 prose or planned-name references are
allowlisted in the script with a stated reason each.

```
scanned 4160 tracked files; 1075 references resolved
no dangling repository references
```

## G8 — the diff contains only what it should

```
21577  files deleted
18  files added
35  files modified or renamed

tracked files : 25722 -> 4164  (-83.8%)
tracked bytes : 43.2 MB -> 18.5 MB
```

The known-recurring corruption tripwire held throughout: 
`tasks/p14_workflow_handoff/workflow_handoff_0009/solution/flow_config.json` never became `{}`
(guarded by `test_canonical_golden_fingerprint_intact`, which runs in G2).

## Baselines this reproduces

| Gate | `master@cc797ffe` | this branch |
|---|---|---|
| frozen membership | 1065 / 9 / 2 / 1 | 1065 / 9 / 2 / 1 |
| pytest (tool-free) | 1133 passed, 0 failed | 482 passed, 0 failed (35 test files removed with the tracks and modules they covered) |
| structural tasks | 2985 / 2985 | 84 / 84 |
| ledger `--check` | 58 + 12 = 70 | 58 + 12 = 70 |
| claim stats `--check` | 12.5 / [-12.5, 41.7] / -16.7 | 12.5 / [-12.5, 41.7] / -16.7 |
| PDF | 15 pp, 268 459 B, `bbf948bf…` | 15 pp, 268 459 B, `bbf948bf…` |
| dangling references | 50 | **0** |
