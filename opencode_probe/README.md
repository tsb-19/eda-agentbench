**English | [中文](README.zh.md)**

# `opencode_probe/` — the external-scaffold arm's own root

This directory holds everything the OpenCode external-scaffold probe produces. It sits at the
repository root, deliberately **not** under `reports/`, for the same reason
[`phase8a/`](../phase8a/README.md) does: `scripts/frozen_membership_verify.py` scans all of
`reports/` for `path → sha256` pairs, so writing here would change the frozen pin count. An early
Phase-8A draft that wrote under `reports/` drove the count 1065 → 1979 and silently resolved one of
the two expected mismatches.

## What this arm is, and what it is not

It is a **separately named study**, authorized after the `a89e084` freeze by `CLAUDE.md` hard
constraint 1. That programme stays closed; nothing here may be summed with, averaged into, or
differenced against any number the paper reports.

It is **not** a measurement of "the scaffold effect". OpenCode necessarily replaces the action
surface and the prompt frame, both of which the paper's §2 counts as task information, so
`OpenCode − controlled runner` is not a scaffold effect and is never computed. The estimand is the
**treatment effect within OpenCode**. See
[`docs/opencode_probe_analysis_plan.md`](../docs/opencode_probe_analysis_plan.md), which fixed the
questions before any outcome existed, and
[`docs/opencode_scaffold_probe_scope.md`](../docs/opencode_scaffold_probe_scope.md) for the
integration surface.

## Layout

```
config/opencode.json     the pinned OpenCode configuration; every value is asserted by readback
evidence/preflight.json  zero-call preflight record — config, filesystem and sandbox checks
```

`config/opencode.json` carries **no secret**. The provider takes its key from the `API_KEY`
environment variable via OpenCode's `env` field, so the key is never written to a file here, and the
preflight asserts that the resolved provider block contains no literal secret.

## Status

**Nothing has been run.** No model call, no episode. The zero-call preflight passes four of its five
checks; the fifth — filesystem isolation of the oracle — is blocked because `bwrap` cannot create a
user namespace on this host (`kernel.apparmor_restrict_unprivileged_userns=1`, and `bwrap` is not
setuid). That check is one of the three the probe may not proceed without, so the arm is stopped
there pending a decision recorded in the scope audit's §8.

## Reproduce the preflight

```bash
export PATH="$HOME/.opencode/bin:$PATH"
python3 scripts/opencode_probe_preflight.py          # zero model calls
python3 scripts/opencode_probe_preflight.py --json   # machine-readable
python3 -m pytest tests/test_opencode_probe.py -q    # plan and claim-scope guards
```
