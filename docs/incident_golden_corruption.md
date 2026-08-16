**English | [中文](incident_golden_corruption.zh.md)**

# Incident: the canonical golden truncated to `{}` — root cause and fix

**Status:** RESOLVED, 2026-08-12. **Scientific impact: none** — the corruption never reached a
commit, so no frozen experiment, evidence manifest or submission artifact was affected.

## Summary

`tasks/p14_workflow_handoff/workflow_handoff_0009/solution/flow_config.json` — the canonical
golden of the p14 controlled pair — was repeatedly truncated to the two bytes `{}`. It was
believed for weeks to be an *unidentified external process* writing every few hours.

It was not external. The writer was **the repository's own test suite**:
`tests/test_fullpath_check.py` contained four statements of the form

```python
(L2.G.TRACK / L2.REFERENCE_TASK / "solution" / "flow_config.json").write_text("{}")
```

which resolve to the real canonical path. There was no `tmp_path` isolation and no teardown, so
**every** `pytest` / `scripts/check` run corrupted the file and left it corrupted.

## Proof

Single-file run, nothing else touched:

| | sha256 | bytes | content |
|---|---|---|---|
| before | `c80812cce61d10c1…` | 249 | valid, 7 keys |
| after `pytest tests/test_fullpath_check.py` | `44136fa355b3678a…` | 2 | `{}` |

`44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a` is the sha256 of `{}`.

## What this corrects

1. **"Every few hours" was an artifact of observation.** The real trigger is *every test run*.
   The five recurrences during the 2026-08 repository cleanup line up exactly with the five
   `scripts/check` invocations made before commits A/B/C/D/F.
2. **The "targeted" appearance had a mundane cause** — a hard-coded path, not a selective writer.
3. **The ~21 h "b04 outage" was this bug.** `scripts/fullpath_check.py` pins
   `REFERENCE_FC_HASH = c80812cc…`, the healthy hash. After a test run the fingerprint mismatched,
   so `config_fingerprint_ok=False` → `healthy=False`. b04 was healthy the whole time.
4. **No host-level forensics were needed.** (For the record: this host has no passwordless
   `sudo`, and no `inotifywait`/`auditctl`/`fatrace`, so `inotify` timing plus Linux-audit
   attribution was not available anyway. `inotify` also cannot name the writing process; only an
   audit/eBPF path can. A static search for a literal `{}` write found the cause in minutes.)

## Fix

`check()` only requires the reference `solution/flow_config.json` to **exist and parse** — the
tests already stub `hashlib.sha256` and set `REFERENCE_FC_HASH="x"`, so its contents are
irrelevant. Writing into the canonical tree served no purpose.

- `fake_track` fixture redirects `G.TRACK` to a `tmp_path` tree containing the stand-in file;
  the canonical dataset is never touched.
- `stub_fingerprint` fixture removes the four-way duplication of the hash stubbing.
- **New tripwire** `test_canonical_golden_fingerprint_intact` asserts, using the real `G.TRACK`
  and the real `hashlib`, that the canonical golden still matches the frozen fingerprint. Any
  future test or tool that writes into the canonical dataset now fails immediately instead of
  silently corrupting it and resurfacing days later as a fake tool outage. Verified to fire:
  corrupting the file makes it fail with the expected/actual hashes.

Result: `pytest tests/test_fullpath_check.py` → 7 passed, canonical golden byte-identical.

## Correction that could not be applied in place

`scripts/canonical_integrity.py` still says in its module docstring that "an unidentified
external process kept rewriting the frozen golden … (every few hours)". **That statement is now
known to be wrong, and it must stay.** The file's current sha256
`bd946813e9c2ee6f704f26505ae3ae4d316258ddf21611c9b1094967838e6748` is hash-pinned by four
frozen manifests:

- `reports/evidence/p14_phase4y3_c24_bridge/membership_code_manifest.json` (`committed_membership_code_sha256`)
- `reports/evidence/p14_phase4y3_c24_bridge/canonical_integrity_manifest.json` (`code_hashes`)
- `reports/evidence/phase5d_freeze/phase5d_freeze.json` (`custody_manifest.code_hashes`)
- `reports/evidence/phase5b_custody_manifest.json` (`code_hashes`)

Editing even a comment would invalidate all four attestations. A frozen artifact records what was
believed at freeze time; this document is the correction of record.

Two further sites keep the superseded attribution, for the same reason or as history:

- `reports/synthetic_p14_phase4z_synthesis.md` §7 item 8 ("Unresolved external writer … not
  root-caused"). Also **hash-pinned**: its sha256 `92ed19d26e8ca62d…` is recorded in
  `reports/synthetic_p14_phase4z_freeze_manifest.json`. Unchanged; superseded by this document.
- A historical Phase-6 manuscript draft, which repeated the same attribution. It was removed with
  the rest of the research chronology on this branch (see `docs/REMOVED.md`); it survives on
  `master` as a record of what that draft said.

**The submitted manuscript needs no change.** It never relied on the external-process explanation:
the audit table rows read *"Canonical-source mutation (Art)"* and *"Golden rewrite read as tool
outage"*, and §6 says *"a silent golden rewrite would have masqueraded as a day-long tool outage"*.
Those statements are attribution-free and remain true — only the writer's identity changed, and the
control that caught it is the same one described. Verified by text-extracting `submission/main.pdf`:
zero occurrences of "unidentified" or "external process".

**The integrity guard itself remains fully warranted.** Its purpose was never limited to this
writer: it defends the canonical tree against *any* writer, including an agent `RUN` using an
obfuscated absolute path, and it stops a chain on mutation rather than silently restoring and
continuing. Only its stated motivation was wrong.

## Object database

`git fsck --full --strict` → exit 0; 32 dangling commits and 1 dangling tree (residue of
worktrees and branches removed earlier in the program), no corruption or missing objects. This is
expected and is *not* evidence about this incident: an external write to an already-checked-out
file leaves the object database perfectly healthy. `git fsck` checks object connectivity and
validity; the working-tree fingerprint guard checks something entirely different. Both are needed.

## Generalizable lessons

**1. A health check is only as trustworthy as the isolation of its reference standard.**
The tool-health sentinel behaved exactly as designed: it compared the reference artifact against a
frozen fingerprint, found a mismatch, and reported `healthy=False`. It was *correct* and still
produced a wrong diagnosis, because the artifact it measured against had been mutated by the test
harness it was supposed to be independent of. The failure was not in the monitor's logic but in the
custody of its reference. Stated generally:

> A monitor that validates a system against a reference standard can only be trusted if that
> reference standard is itself isolated from the test harness. Otherwise the monitor faithfully
> reports a real mismatch and attributes it to the wrong subsystem — here, ~21 h of investigation
> pointed at a remote tool server that was healthy the whole time.

This is a stronger and more general claim than "an external process wrote a file", and it is the
part worth carrying into any future extension of this benchmark's measurement-validity apparatus:
*reference-standard custody is a first-class validity layer, not an implementation detail.*

**2. When the corrupted content is a distinctive literal, search for the literal first.**
`{}` is a near-unique fingerprint. Grepping for `write_text("{}")` / `json.dump({}` found the cause
in about two minutes and beat an entire host-level forensic plan (`inotify` timing, `/proc/*/fd`
snapshots, targeted `strace`) that would have taken hours and — on this host, with no passwordless
`sudo` and no `inotifywait`/`auditctl`/`fatrace` — could not have attributed the write to a process
at all. Content-first, then process-level.

**3. "Previously ruled out" is not evidence.** The earlier investigation explicitly excluded the
true cause on the strength of a generalization: *"all tests use `tmp_path`; `scripts/check` is
innocent."* That generalization was never checked against this one file. Ask what was actually
verified, on which specific artifact and code path — a conclusion supports only the scope it was
tested at, which is the same discipline the accompanying paper argues for with its claim-scope
lattice. (The paper deliberately does *not* call that structure a ladder: the point is that the
scope coordinates are partially ordered, so widening one is incomparable to widening another.)

## Standing guidance

- The tripwire is the primary control. If it fires: restore with
  `git checkout -- tasks/p14_workflow_handoff/workflow_handoff_0009/solution/flow_config.json`,
  then find the new writer. Never commit the corruption.
- Paid or frozen-evidence runs still go through the exact-commit isolated worktree and
  `scripts/canonical_integrity.py` (pre/post-episode hash verification, `FAILED_INTEGRITY` stop).
- Tests must never write into `tasks/`. Stage a `tmp_path` copy and redirect the module's track
  root instead.
