**English | [中文](README.zh.md)**

# `phase8a/` — why this study's artefacts live outside `reports/`

Phase-8A is a new study run after the ICLR submission was frozen and tagged
(`iclr2027-submission-v5`). Its design and analysis plan are in
[`docs/phase8a_prereg.md`](../docs/phase8a_prereg.md).

```
phase8a/
  evidence/    frozen schedules, prerun integrity manifest, preflight record,
               run state, per-episode custody
  reports/     analysis outputs
```

## Rule 1 — nothing Phase-8A produces may be written under `reports/`

`scripts/frozen_membership_verify.py` sets `SCAN_ROOT = REPO / "reports"` and walks **every**
`*.json` beneath it, harvesting `path -> sha256` pairs in three shapes. Any custody record written
there becomes part of the frozen pin set.

That is not hypothetical. An early draft of `scripts/phase8a_preflight.py` wrote its prerun
canonical-integrity manifest to `reports/evidence/`. The result:

```
pins:     1065 -> 1979
mismatch:    2 -> 1
```

The manifest contributed 914 new pins and, because it recorded the *current* hash of
`generators/p15_sta_handoff_gen.py`, it silently **resolved** one of the two mismatches the frozen
baseline expects. A Phase-8A file had masked a real property of the frozen set.

The temptation is to add an exemption to the verifier, or to record hashes in a fourth shape the
collector does not recognise. Both are the same antipattern CLAUDE.md warns about from the other
direction — *"a verifier tuned until it prints nothing would hide the next real mutation."* So the
verifier is untouched and the study moved instead. `scripts/phase8a_preflight.py` gate 11 asserts
this rule rather than trusting it.

## Rule 2 — never invoke `pt_shell` with the repository as the working directory

`pt_shell` on this host is a forwarder to `b04`
(`/data1/tongsb/eda-remote-shim/bin/forwarder` — the `V-2023.12` in the path is the install
directory name; the binary is `S-2021.06-SP5`). **The forwarder syncs the current working directory
from the remote copy**, and the sync is additive: it restores files that `b04` still holds but that
have been deleted locally, **with their original mtimes intact**.

This is how the three stray `reports/evidence/phase8a_*` files from that early draft kept coming
back. Deleting them locally succeeded; the next `pt_shell` invocation from the repo root restored
them, still stamped with times from before the deletion. The naive reading is "my delete failed" or
"my script recreated them" — both wrong, and both would have led to editing correct code.

Measured behaviour:

| action | effect |
|---|---|
| forwarder invoked with cwd = repo root | remote-only files **restored** locally |
| forwarder invoked with cwd = a temp dir outside the repo | repository untouched |
| `sta_fairness.check(...)` (task-scoped) | repository untouched |
| local-only files | never deleted |
| local edits to tracked or untracked files | never reverted |

So the hazard is bounded, but it is real: a remote tool path can write into the canonical tree. This
is the same class as [`docs/incident_golden_corruption.md`](../docs/incident_golden_corruption.md),
where a day-long "remote tool outage" was in fact the harness writing into the canonical tree — the
monitor was right and the attribution was wrong. Here too the monitor was right.

`scripts/phase8a_preflight.py:_pt_version` therefore stages its Tcl in a `tempfile.TemporaryDirectory`
and passes `cwd=tmp`. Anyone reproducing this work should assume the same discipline for any
forwarded EDA tool.

## Reproducing

```bash
python3 scripts/phase8a_schedule.py --model Qwen3.7-Max-TR --reps 6 --arm 1 --check
python3 scripts/phase8a_preflight.py        # zero paid calls; one unbilled /v1/models listing
python3 scripts/phase8a_report.py --check
```
