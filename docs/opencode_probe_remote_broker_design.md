**English | [中文](opencode_probe_remote_broker_design.zh.md)**

# A restricted-SSH EDA broker for the OpenCode probe

**Status: design, dated 2026-08-21. Its transport premise is REFUTED on this host as of 2026-08-23 —
read that first: [the dry-run outcome](opencode_probe_broker_dry_run.md#outcome-2026-08-23--fail-and-the-blocker-is-architectural).**
The design assumed the sandbox can open a direct connection to b04 authenticated only by the episode
key. In fact b04 is reachable only through a bastion whose route and credential live in the operator's
`~/.ssh/config`, which the sandbox deliberately does not have, so every broker call from inside the
sandbox fails with `Could not resolve hostname b04`. Everything below about the capability model, the
managed block, the batch lifecycle, the protocol, the caps and the error taxonomy stands and was
measured; what does not stand is that an agent can reach it. Nothing here authorizes the formal
48-episode arm. It addresses exactly one of the reasons the arm cannot start — the blocker recorded in
[`opencode_probe_dry_run_report.md`](opencode_probe_dry_run_report.md) §5 — and leaves the others
where they are. Check 7 remains UNSETTLED. Check 5 does not inherit its earlier PASS: that PASS was
established in the tools-absent configuration, and this design changes the configuration, so check 5
must be established again under it. No model call may be spent until the zero-call remote-broker
preflight passes.

Governing documents, unchanged and not reinterpreted:
[`opencode_probe_analysis_plan.md`](opencode_probe_analysis_plan.md) (preregistration) and
[`opencode_scaffold_probe_scope.md`](opencode_scaffold_probe_scope.md) (integration scope, nine
structural checks). The `a89e084` programme is not touched by anything below.

## 1. The problem

The EDA tools on this host are remote. A private forwarder mirrors `$PWD` to `tsb@b04` over `rsync`,
runs the tool there under a login shell, and syncs results back. For the OpenCode agent to receive
real public tool feedback, that forwarder and `~/.ssh` would have to be mounted into the sandbox —
which grants the agent `ssh tsb@b04`, i.e. arbitrary command execution on the host where grading
deposits the oracles.

The two requirements are therefore in direct conflict, and the dry run measured both sides of it:

| Configuration | Check 2 (tool feedback) | Check 5 (oracle isolation) |
|---|---|---|
| tools unmounted — what was dry-run | **fails**: `run_public.sh` returns `SKIP` | **passes** |
| tools mounted, forwarder as-is | would pass | **fails**: `cat /tmp/eda_shim_*/signoff_intent_truth.json` over ssh |

The leak is **cross-episode**, not merely within-episode: grading episode *N* deposits that
instance's truth file on the remote, where episode *N+1* of the same instance could read it. At the
time of the dry run b04 held 1501 `eda_shim_*` workspaces containing 1049 `run_hidden` scripts, 1049
grader copies and 1049 truth files. Those have since been removed, but **cleaning `/tmp` is
necessary and not sufficient** — the next grading run recreates them, so the fix has to be that no
agent-reachable operation can read them at all.

## 2. What the broker is

A **capability**, not a channel. The agent is not given a way to reach b04 that is then restricted;
it is given exactly two named operations and no way to express anything else.

Three credentials, three scopes:

| Who | Credential | Can do |
|---|---|---|
| Host, outside the sandbox | the normal `~/.ssh` | everything; provisions and tears down episodes |
| Agent, inside the sandbox | a per-episode ed25519 probe key | two named ops, for one episode |
| Grader, outside the sandbox | normal credentials, frozen path unchanged | unchanged |

### 2.1 The key is the episode

The probe key is generated per episode and destroyed at teardown. Its `authorized_keys` line carries
the episode id **inside the forced command**, so the agent cannot select an episode — there is no
field in which to name one:

```
restrict,from="<host-ip>",command="/home/tsb/eda-probe-broker/broker.sh <episode_id>" ssh-ed25519 AAAA… probe-<episode_id>
```

`restrict` (OpenSSH ≥ 7.2) implies `no-pty`, `no-X11-forwarding`, `no-port-forwarding`,
`no-agent-forwarding` and `no-user-rc`. It is used rather than the five individual options because
it is **default-deny**: an option added by a future OpenSSH is denied unless this line opts back into
it, whereas an enumeration silently gains whatever is invented next.

`command=` is what kills `scp`, `sftp` and `rsync`. Each of those needs to start its own server
binary on the remote (`scp -t`, `sftp-server`, `rsync --server`) and none of them ever gets to run
one. `from=` pins the source address as defence in depth; it is not load-bearing.

Revocation is exact: delete the line and the key is dead. Concurrent episodes each get their own
line, their own key and their own id.

**The line lives in a delimited managed block, and nothing outside it is ever rewritten.**

```
# BEGIN EDA-OPENCODE-PROBE
# probe-entry {"episode": "…", "added": "…"}
restrict,command="/home/tsb/eda-probe-broker/broker.sh …" ssh-ed25519 AAAA… probe-…
# END EDA-OPENCODE-PROBE
```

This matters because b04's `~/.ssh/authorized_keys` holds **two real user keys in 687 bytes** — one
`ssh-rsa`, one `ssh-ed25519`, and a trailing blank line. A partial write there locks the operator out
of the host that runs every EDA tool. So every mutation is: acquire the mutex → read → write a
sibling temp → `fsync` → `os.replace` → `fsync` the directory → release. A failed mutation leaves the
previous file byte-identical and removes its own temp, and teardown of episode A can never remove
episode B's line. `audit --reap` removes managed entries whose episode is no longer live, because a
probe key outliving its episode is a capability nobody is holding.

The trailing blank line is not a detail to be tidied away: a renderer that eats it would change the
one region the operator cares about. The round trip is verified on that exact shape — two keys, blank
line, trailing newline — and the file comes back byte-identical.

The mutex is a `mkdir`, not `flock`: `$HOME` on b04 is NFS
(`qhdx.inspurnfs.com:/data/home/b04`), where `flock(2)` is emulated through the lock manager and
`nfs(5)` disclaims both cluster-coherent caching and lock survival across a network partition.

### 2.2 The formal arm installs all 48 keys at once

Per-episode `add_entry` / `remove_entry` exist and are used by the preflight and by any single-episode
dry run, where there is one episode and an operator watching. **The formal arm does not use them.**
All 48 public keys are installed in **one** atomic rewrite under **one** lock before the arm, and
removed in one more after it, so `authorized_keys` is byte-static for the entire arm. Each episode's
sandbox mounts only its own private key.

The reason is not tidiness. A per-episode design needs 96 correct mutual-exclusion operations (48
installs, 48 removals) against a substrate whose own manual page declines to guarantee the primitive,
and the stake is the operator's real login keys. Batching reduces that to two acquisitions, both at
arm boundaries, where a failure is visible before any episode has run and after all of them have.

Nothing is given up. The property the arm needs is

> holding episode *i*'s key implies you can only run episode *i*,

and that lives in each line's `command=`, not in *when* the line was written. Cross-episode selection
stays unrepresentable, concurrent episodes still work, and the number of lines is the only thing that
changed.

Ordering is what makes failure safe. Validation of the whole plan, then key generation, then
manifests, then the remote episode directories — and only after all of that, the single
`add_entries` call. A failure before that call leaves **zero** probe keys authorized. A failure of the
*verification* after it rolls the keys back and refuses to write a batch record, because "48 keys and
no record" is worse than either "no keys" or "48 keys and a record".

Verification does not rewrite the file it is checking. It reads the managed block back and requires
three things: the entry set matches, each line's `command=` names its own episode and no other, and
the sha256 of the **non-managed region** equals what it was before. That last quantity is the one the
operator cares about, and the preflight samples it **three** times — before, while all 48 keys are
installed, and after teardown. Comparing whole files would be useless during the batch; comparing
only before and after would pass a bug that dropped a user key for the duration of the arm and
restored it at the end.

While `opencode_probe/broker/batch.json` exists, `provision` and `teardown` refuse to run. That is
what makes "`authorized_keys` is static during the arm" a mechanical property rather than an
intention: no retry loop or stray helper can quietly reintroduce the 48 rewrites.

### 2.3 The mutex never breaks a lock on age alone

`mkdir(2)` is atomic in its create step, which is what a mutex needs. It is **not** a correct
distributed lock, and `mkdir(2)` records NFS infelicities of its own, so the stale rule is written to
be safe when the primitive is not. The owner record carries `owner_host`, `owner_pid`, `owner_nonce`,
`created_at` and `heartbeat`, and staleness is measured from the heartbeat so a legitimately long
operation is never mistaken for a dead one.

| Situation | Action |
|---|---|
| age ≤ `stale_sec` | wait. Never broken, even if the owner is verifiably dead. |
| age > `stale_sec`, owner on **this** host, pid alive | wait. A slow operation is not a dead one. |
| age > `stale_sec`, owner on **this** host, pid gone | verified death — quarantine, then re-contest. |
| age > `stale_sec`, owner elsewhere, or record unreadable | liveness **unverifiable** — quarantine by atomic `rename`, then re-contest. Never `rm` in place. |

The rule that "age > threshold ⇒ delete the lock" is specifically rejected. It races: A is alive but
slow, B judges A stale on the clock alone, B deletes, and A and B then rewrite `authorized_keys`
concurrently. Quarantine closes that: the rename is atomic so exactly one breaker wins, and if the
old owner was alive after all, its release reads the owner record, sees a nonce that is not its own,
and frees **nothing**. Quarantined locks are reported by `audit` and never auto-removed — each one is
a record that somebody's lock was taken from them.

### 2.4 `SSH_ORIGINAL_COMMAND` is never read

The broker does not reference the variable — not to parse it, not to validate it, not to log it. A
forced command that inspects `SSH_ORIGINAL_COMMAND` has re-created the arbitrary-command channel and
merely put a filter in front of it; every such filter is one quoting bug from being bypassed. The
operation is selected from a structured request on **stdin** instead, so the only thing an attacker
controls is a JSON document that must satisfy a whitelist.

## 3. Protocol

One request per connection, on stdin, length-framed and capped. The frame is
`EDABROKER1 <n>\n<n bytes of JSON>\n`: b04's login shell writes a banner and an `lsof: command not
found` of its own, and framing makes a polluted stream a **detected** transport failure rather than
an unexplained parse error. The right response to banner noise is a protocol layer, not a grep.

```json
{"op": "sta_public",
 "inputs": {"exception_config.json": "<base64>", "run_public.tcl": "<base64>", "…": "…"}}
```

Response on stdout, also framed:

```json
{"op": "sta_public", "rc": 0, "stdout": "…", "stderr": "…",
 "artifacts": {}, "invocation": 3, "elapsed_s": 41.2}
```

**No filename supplied by the client is ever used as a path.** The broker validates that the input
key set is *exactly* the op's declared set — not a superset, not a subset — every key matches
`^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$`, and `.` and `..` are excluded explicitly because they are legal
basenames and are not files. Each accepted input is then written under a name the broker already
knows from its own table. Path traversal is not defended against by sanitising `../`; it is
unrepresentable, because the client's strings never reach the filesystem.

**There is no archive extraction of any kind.** `tar xf -` is absent rather than hardened, and that
is a design decision worth stating: an archive the agent controls can carry `../`, absolute paths,
symlinks and hardlinks, and every one of those is a shape a whitelist of bare names simply does not
have. Hardening an extractor means enumerating the tricks; not having one means there is nothing to
enumerate.

### 3.1 Input classification

Every public file falls into exactly one of three classes, and the class decides what the broker
does with it:

| Class | Example | Broker behaviour |
|---|---|---|
| **editable** | `exception_config.json`, `meas_config.json` | agent's bytes accepted verbatim — this is the intervention |
| **canonical** | `run_public.tcl`, `build_applied_sdc.py`, `design.v`, `tiny.db`, `circuit_core.sp` | sha256 checked against a pinned manifest; **refused on divergence** |
| **generated** | `agent_applied.sdc`, `circuit_built.sp` | never sent; regenerated remotely by the canonical script |

The editable set is one file per family. Everything else the tool reads is canonical, and the
manifest pins it. `tiny.lib` is *not* an input to `sta_public`: `run_public.tcl` sets
`link_path "* tiny.db"` and reads `tiny.db`. `parse_measure.py` is not an input to `spice_public`
either — it runs locally on the returned `.lis`.

### 3.2 Divergence is refused at execution time and recorded

```
broker: REFUSED op=sta_public reason=NON_EDITABLE_DIVERGENCE
        file=run_public.tcl canonical=sha256:9f2c… supplied=sha256:41ab…
```

Nothing crosses to b04, and the attempt is written into the episode record. This is **stricter than
the frozen runner**, which shipped whatever was in `$PWD` and caught tampering at *scoring* time via
`check_tcl_injection` and `detect_forbidden_modifications`. Post-hoc detection is sufficient when the
consequence is a bad score; it is not sufficient when the consequence is the agent reading the
oracle, because detecting the read afterwards does not un-read it.

The scoring-time anti-cheat is unchanged and still runs. The broker's refusal is an additional,
independent event, and is recorded as one.

### 3.3 Where the manifest comes from

The sandbox mounts no task tree — that is check 5 — so the client cannot know canonical bytes and
cannot be trusted to. The manifest is installed on b04 by the **host**, using the host's normal
credentials, before the sandbox starts. It contains sha256 values and an op name; it contains no
oracle and no task content, so its presence on b04 is not itself a disclosure.

### 3.4 What the pinning costs, stated rather than inferred

The broker **pins tool-authoritative inputs to their canonical task versions**. The frozen runner did
not: it shipped whatever was in `$PWD` and caught tampering at scoring time. That is a real
difference in the action surface, and since §2 of the paper counts the action surface as task
information, it is written down here rather than left for a reader to discover.

So: **this design does not claim byte-for-byte action-surface parity with the frozen runner.** The
tool-call contract is *more* explicit under the broker than under the forwarder. Two consequences
follow, and both are stated at that strength:

- What the broker forbids is not a superset of what the grader forbids, and the two are not the same
  list. For p15 the measured `metadata.json` `forbidden` list is
  `["design.v", "constraints.sdc", "run_public.sh", "run_public.tcl", "tiny.db", "tiny.lib", …]` — it
  **omits** `build_applied_sdc.py`, `partition_pins.json` and `intent_exception.json`, all three of
  which `build_applied_sdc.py` reads and all three of which change the real PrimeTime result. An
  agent editing `partition_pins.json` under the frozen runner would have altered the tool feedback
  and passed anti-cheat. The broker refuses it at execution time. For p16 the forbidden list is
  already complete; the broker pins both families the same way regardless, because "the grader
  happens to forbid it" is a different guarantee from "the tool cannot be given it".
- Post-hoc detection is enough when the consequence is a bad score. It is not enough when the
  consequence is a leaked oracle, because detecting the read afterwards does not un-read it.

The scoring-time anti-cheat is unchanged and still runs. The broker's refusal is an additional,
independent event, and is recorded as one.

## 4. The two operations

The op boundary sits **at the EDA tool**, so that both `run_public.sh` scripts execute verbatim and
no hash-pinned canonical file has to be modified to accommodate the broker.

| op | runs remotely, all canonical | returns |
|---|---|---|
| `sta_public` | `build_applied_sdc.py` → `pt_shell -f run_public.tcl` | bounded stdout/stderr |
| `spice_public` | `build_deck.py` → `hspice -i circuit_built.sp -o hspice_run` | bounded stdout/stderr **+ `hspice_run.lis`** |

`parse_measure.py` is deliberately *outside* `spice_public`. It runs locally, from canonical bytes,
after the op returns — which is what `run_public.sh` already does. Putting it inside the op would
force either a double parse or a modification to a pinned script.

Returned artifacts are whitelisted per op by name and size cap. `hspice_run.lis` is raw simulator
output: it is already in `.gitignore` and is never committed.

### 4.1 The bounds, as numbers

"Bounded" is worth nothing without values, so they are fixed here — and each is justified by a
**measurement**, recorded in `opencode_probe/evidence/raw_output_audit.json`.

| Bound | Value | Measured maximum | Headroom | Why this value |
|---|---|---|---|---|
| request, on stdin | 2 MiB | 50 642 B | 41× | upper bound over every calibration directory: whole `files/` inflated by 4/3 |
| `stdout` returned | 1 MiB | 3 205 B | 327× | measured raw PrimeTime output, untruncated |
| `stderr` returned | 1 MiB | 0 B | — | both `run_public.sh` scripts merge stderr with `2>&1` |
| `hspice_run.lis` artifact | 8 MiB | 4 695 B | 1787× | measured raw simulator output |
| remote wall clock | 180 s | — | — | parity with the frozen per-command timeout |

The calibration set is every instance directory in both families holding `files/run_public.sh` — 56
of them — and coverage of the 24 directories the formal panel would use is a **precondition of the
verdict**, not a summary statistic. A maximum over whichever instances happened to run is the same
defect as an aggregate over whichever episodes happened to finish.

> The transport cap and the observation cap are different quantities on different layers. 4000 bytes
> is how much the model sees in one observation; the transport cap is how much the broker may return
> at all. The frozen runner lets an agent redirect a large output to a file and paginate it back, so
> a transport cap below the real output size would make the probe's action surface *weaker* than the
> control's. The bound is therefore set from measured raw output — ≥ 8× headroom over the complete
> calibration set — not from `64 KiB / 4000 B = 16`.

The measurement also disposes of the superseded justification more thoroughly than the objection to
it did. Real PrimeTime output is 3 205 bytes, **below** the frozen runner's 4000-byte observation cap.
So `64 KiB is 16× 4000 B` was not merely reasoning about the wrong layer: the observation cap it
reasoned from almost never bound on these tasks at all, while the transport quantity it was meant to
justify had never been measured.

**And the limit of that justification, stated in the same place.** Headroom over a finite calibration
set is **not** a proof that a cap can never bind, and this design does not rely on one.
`1 MiB > 8 × 3 205 B` is a fact about 56 measured directories, not about every future PrimeTime
invocation. What covers the gap is the runtime behaviour in §4.2, which does not depend on the audit
being exhaustive.

### 4.2 The error taxonomy, and why a cap hit is fail-closed

Six statuses, kept apart on purpose. Collapsing any two of them would let an infrastructure fault be
recorded as model behaviour, which is the measurement-validity rule this project exists to defend.

| Status | Meaning | Client exit | Measurement-invalid? |
|---|---|---|---|
| `ok` | the tool ran; `rc` is the tool's own | the tool's `rc` | no |
| `tool_timeout` | the tool ran and exceeded its wall clock | 124 | no — a tool fact |
| `refused` | the request was illegal; nothing crossed to the remote | 126 | no — an agent fact |
| `broker_error` | the broker itself failed | 125 | **yes** |
| `transport_error` | ssh or framing failed; not a tool result | 125 | **yes** |
| `transport_output_limit` | an output exceeded a transport cap | 125 | **yes** |

**`transport_output_limit` is fail-closed and there is no truncating path at all.** On a cap hit the
response carries no `stdout`, no `stderr` and no `artifacts`; the client prints nothing on stdout,
writes `eda-broker: MEASUREMENT_INVALID transport_output_limit: …` on stderr, and exits 125. The
episode is measurement-invalid and is discarded — it measured infrastructure, not a model, and no
aggregate may include it.

A truncation was considered and rejected. It would be a *second* observation cap — invisible to the
agent, absent from the frozen arm, and indistinguishable in a log from real tool output. The cost of
failing closed is one discarded episode; the cost of truncating is a contaminated measurement that
looks clean. That asymmetry is the whole argument.

**One limitation, inherited rather than chosen.** Both `run_public.sh` scripts are sha256-pinned task
files that end in `exit 0` and merge stderr into stdout with `2>&1`. So the client's exit code of 125
does **not** survive to whatever invoked `run_public.sh` — the only carrier that does is the
`eda-broker: MEASUREMENT_INVALID <status>:` marker in the merged text, which is why it is worded to
match the frozen forwarder's own `eda-shim: remote execution … failed` convention. Any consumer that
classifies episodes must key on the marker, not on a return code. Patching `run_public.sh` is not
available and should not be wanted: it is one of the 1020 sha256-pinned task files.

**The agent influences no argv.** The client is invoked as the `pt_shell` or `hspice` shim, ignores
its arguments entirely, and selects the op from the name it was invoked as. The arguments in
`run_public.sh` are canonical and already known to the broker.

## 5. Workspace lifecycle

```
~/eda-probe-broker/ep/<episode_id>/          0700, created by the host at provision
~/eda-probe-broker/ep/<episode_id>/inv-<n>/  0700, created and destroyed per invocation
```

Deliberately **not under `/tmp`**. `/tmp` is where the retained evaluator mirrors accumulate and
where every other tool on a shared host writes; a private root under `$HOME` is the point.

Cleanup runs on **every** exit path — success, protocol error, validation refusal, tool failure,
wall-clock timeout and signal. Each step runs in its own session (`start_new_session=True`), and a
wall-clock overrun sends `SIGTERM` to the whole **process group**, waits out a 10 s grace, then sends
`SIGKILL`.

The process group is the point, and `subprocess`'s own timeout is not enough. Killing only the direct
child leaves orphan `pt_shell` descendants that hold licences and keep writing into whatever runs
next — which on a shared EDA host means the next episode's workspace. The broker therefore reports the
process **group** it killed (`killed_pgid`) and which step overran (`timed_out_step`), and the
preflight observes the property on real processes rather than asserting it: it shortens the wall clock
through the manifest, starts real PrimeTime, and then asks `ps -g <pgid>` whether anything is left.

Both halves of that check were wrong before they were right, in the same way — a check that cannot
say the thing it appears to say:

- **It could pass vacuously.** With a 5 s wall clock PrimeTime finished, the response came back `ok`,
  and "no orphan survived" was true only because nothing had been killed. The check now requires the
  kill to have happened *and* to have landed on the `TOOL` step rather than on the Python build
  script — otherwise the observation is about the wrong process.
- **It could only fail.** The first version asked `pgrep -u $USER -f pt_shell`, which matches the
  shell *running the pgrep*, because that shell's own command line contains the string `pt_shell`. It
  reported exactly one survivor on every run, including the run in which nothing had been killed.
  Asking about the process group cannot self-match: the probe's shell is in a different group.
- **Then it failed on a column header.** `ps -o pid=,args=` is parsed by procps as "column `pid` with
  header `,args=`", so an *empty* process group still prints one line — the header — which the check
  again read as a survivor. Separate `-o` flags print nothing, and the parse now additionally requires
  a line to begin with a pid.

Three failures in a row, none of them about the broker and all of them about the instrument. That is
worth stating rather than tidying away: an instrument that has not been checked against a known-empty
and a known-nonempty case is not yet a measurement. The unit test now does both — it asserts a killed
group is reported and empty, and that a step which *finishes* reports no killed group at all, so
"nothing was killed" can never be read as "the kill left nothing".

Cleanup is verified rather than assumed: the preflight asserts the invocation directory is absent
after each call, and that teardown leaves neither the episode directory nor the key line.

## 6. Sandbox credential isolation

Three of these are already true of the sandbox built for the dry run and are **asserted rather than
built**; the fourth is new.

| Property | Status |
|---|---|
| `~/.ssh` not present in the sandbox | already true — only `~/.opencode/bin` is bound |
| `SSH_AUTH_SOCK` unset | already true — `SSH_` is in `SCRUB_PREFIXES` |
| no agent socket reachable | already true — `/run` is not mounted |
| probe key + pinned `known_hosts`, and nothing else | new |

The client invokes ssh with `-o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes -o
StrictHostKeyChecking=yes -o UserKnownHostsFile=<pinned> -o ControlMaster=no`, so it cannot fall back
to a key or a host key it was not given.

### 6.1 The launcher's filename is part of the interface

`run_public.sh` dispatches through `EDA_PT_CMD` / `EDA_HSPICE_CMD`, and the client selects its op from
`argv[0]` — so the two launchers are two differently-named executables, and the **name is
load-bearing**. They are Python scripts with a shebang, not shell wrappers, and that distinction is
not cosmetic:

```sh
#!/bin/sh
exec python3 .../broker_client.py "$@"      # WRONG: argv[0] becomes broker_client.py
```

Python sets `sys.argv[0]` to the script it was handed, so a shell wrapper destroys the name and every
call arrives as `argv0=broker_client.py` and is refused `UNKNOWN_SHIM`. With a shebang the kernel
hands Python the launcher's own path and `argv[0]` is `.../pt_shell`.

This was a real defect, and the way it was caught is the part worth keeping. The unit test asserted
that the launcher's *source text* mentioned `broker_client.py`, which the broken wrapper satisfied
while breaking the only property that mattered; the preflight caught it because the preflight actually
runs the tool. The test now **executes** each launcher and reads back which op resolved. A test that
inspects an artifact instead of exercising it can agree with a defect indefinitely.

### 6.2 Every remote command is quoted as one word

`ssh host bash -lc <script>` does not pass argv through. ssh joins its remaining arguments with spaces
and hands the result to the **remote** shell, which parses them again — so an unquoted `bash -lc 'a;
b'` sends only `a` to `bash -lc` and lets the remote login shell run `b`. The frozen forwarder quotes
for this reason (`ssh "$HOST" "bash -lc '...'"`).

Unquoted, this failure is quiet and misleading rather than loud. It produced a deploy that reported
"no python3 on the remote login PATH" while, in the same output, printing the `pt_shell` and `hspice`
it had just resolved; and an `ls .../inv-* | wc -l` that counted the remote home directory and
reported 19 leftover invocation directories where there were none. There is now one quoting
implementation, in `broker_admin._ssh`, and the preflight routes through it rather than having a
second.

## 7. Negative controls

Each must fail, and the preflight fails if any succeeds. This mirrors the treatment check 5 received
after the dry run: a battery of named bypasses, not a list of guessed absent paths.

| # | Attempt | Expected |
|---|---|---|
| 1 | arbitrary command — `ssh -i probe_key tsb@b04 'cat /etc/passwd'` | forced command runs, ignores the command, no valid framed request on stdin → `REFUSED FRAMING` |
| 2 | unknown op — `{"op":"ls"}` | `REFUSED UNKNOWN_OP` |
| 3 | input key set with an extra name | `REFUSED INPUT_SET_MISMATCH` |
| 4 | input name that expresses a path — `../hidden/signoff_intent_truth.json` | `REFUSED ILLEGAL_INPUT_NAME` |
| 5 | `scp -i probe_key file tsb@b04:/tmp/` | fails, no `scp -t` server |
| 6 | `sftp -i probe_key tsb@b04` | fails, no `sftp-server` |
| 7 | PTY — `ssh -tt -i probe_key tsb@b04` | PTY allocation refused |
| 8 | port forwarding — `ssh -L 9999:localhost:22` | refused, and no listener established |
| 9 | agent forwarding — `ssh -A` | refused, and no socket exists to forward |
| 10 | **cross-episode** — episode A's key naming episode B in every JSON field, in argv, and via `SendEnv` | served for A or refused; B's directory never touched |
| 11 | **planted decoy** — a unique sentinel written to `/tmp/eda_shim_PREFLIGHT/signoff_intent_truth.json`, then read through every op and field | the sentinel never appears in any response |
| 12 | sandbox credential isolation | `~/.ssh` absent, `SSH_AUTH_SOCK` unset, only `key`/`known_hosts`/`bin` under `/tmp/eda-probe`, key read-only, no forwarder on PATH |
| 13 | **full-size batch** — install 48 episode keys in one rewrite, tear them down in one | the non-managed region byte-identical before, during and after; 48 entries during, 0 after; every line forces only its own episode; the operator's own key still authenticates while the batch is live |
| 14 | **cap hit** — stdout cap lowered below the measured 3 205 B, then real PrimeTime run | `transport_output_limit`; no `stdout`/`stderr`/`artifacts` in the response; client exits 125 with empty stdout |
| 15 | **positive control** — `bash run_public.sh` inside the episode sandbox, through the broker shim | real PrimeTime output; no `MEASUREMENT_INVALID`, no `SKIP`, and at least one marker that reading the canonical tcl could not produce |

Controls 1–11 and 13–14 are properties of the remote configuration; controls 12 and 15 are properties
of the sandbox. All fifteen cost zero model calls.

**Control 15 exists because the first fourteen passed while the tool channel could not work at all.**
Every one of them issues ssh from the HOST, where the operator's `~/.ssh/config` silently supplies the
route to b04 — a `HostName` rewrite and a `ProxyJump` through a bastion. Inside the sandbox that file is
absent by design, so `ssh -G b04` yields `hostname b04` with no `proxyjump` and the connection dies at
`Could not resolve hostname b04`. Controls 1–14 establish what the capability REFUSES, which is a
property of the forced command and testable from anywhere; control 15 establishes what it PERMITS,
which is a property of the sandbox's reachability and testable only from inside. A battery of refusals
is not a test of the thing itself, and control 12 shows the shape of the error exactly: it confirmed
`~/.ssh` absent and no forwarder on `PATH`, every answer correct, and those answers together are the
reason nothing worked. It was measuring the isolation and reading it as safety. See
[the dry-run outcome](opencode_probe_broker_dry_run.md#outcome-2026-08-23--fail-and-the-blocker-is-architectural).

**Control 11 is why this beats `find /tmp`.** Broker correctness may not depend on b04's `/tmp` being
clean: the dry-run report measured 1492 `eda_shim_*` directories holding both families' truth files,
those were removed, and the next grading run recreates them. Proving the tree is empty proves nothing
about the next episode. The property is therefore established against a deliberately planted truth
file — what is tested is capability isolation, not filesystem cleanliness.

**Control 13 is the one that can lock the operator out of the EDA host**, so it is written most
carefully. It uses the 48 episode *ids* the formal arm would install — 48 being the number whose NFS
exposure batching exists to remove — but prefixes each with `PREFLIGHT__` and points every one at
`p15_dev_0000`'s files. So the `authorized_keys` write is exactly the size the arm would perform, no
studied instance is provisioned by a preflight, and no residue can be mistaken for a real arm. It
also re-authenticates with the operator's own key while the batch is live, because "the bytes look
right" and "the key still works" are different claims and only the second is the one that matters at
2 a.m.

**Control 14 lowers the cap rather than manufacturing a 1 MiB PrimeTime log.** The episode manifest
may lower a cap and shorten the wall clock; it may never raise or extend either, so a manifest can
never buy an episode more transport or more tool time than the calibrated bounds allow. What the
control asserts is that the reduced-cap response contains a shortened `stdout` under *no* key name.

### 7.1 Forwarder equivalence, and a normalisation that is measured rather than chosen

The strongest parity evidence available at zero model cost: run `run_public.sh` on `p15_dev_0000`
through the frozen forwarder and through the broker client, normalise both, and require the public
observations to be equal.

Normalisation is where this check could quietly become worthless. A rule set that grows until the two
texts agree is the same failure as a verifier tuned until it prints nothing. So the rules are split in
two, and only the first half is written by hand:

- **Static rules**, listed in the record with the number of lines each dropped — version and copyright
  banners, dates, clock times, timing lines, licence chatter, pids. The check fails if any single rule
  accounts for more than 20% of the output.
- **A stability control, derived by measurement and symmetric between the paths.** Each path is run
  several times (3 forwarder, 2 broker). For every line **shape** — the line with its numeric runs
  masked — the set of values it takes *within* a path is collected. A shape is comparable only if it
  takes exactly one value in **both** paths; a shape unstable in either is excluded and listed with
  every value it was observed to take. Nothing is dropped on the strength of a hand-written rule.

That control earned its place immediately, and then earned its final form the hard way. The first
honest comparison differed on exactly one line:

```
-Maximum memory usage for this session: 2897.31 MB
+Maximum memory usage for this session: 2897.26 MB
```

Adding a memory-usage regex would have made that disappear and would have been indistinguishable, in
the record, from normalising away a real difference. So the first version ran the forwarder twice and
dropped whatever differed between those two runs. Two further defects followed, and both are worth
keeping in the record because both are the same mistake in different clothing — trusting an
under-sampled instrument:

1. **Exact-text matching was too narrow.** Two forwarder runs gave 2897.26 and 2897.31; the broker
   gave a *third* value, 2897.27, which the literal drop set left standing and reported as a
   difference the control had already shown to be noise. Matching by masked shape fixed it.
2. **One pair on one side was too small a sample.** In a later run the two forwarder runs happened to
   report the *same* value, so the control detected nothing, nothing was dropped, and the check failed
   on noise it had identified correctly minutes earlier. A gate that fails at random is not a gate.
   Several runs on **both** sides fixed it.

The check fails if the excluded set exceeds 10% of the output, because a large exclusion means there is
little content left to be equal about.

Measured: 82 lines compared, cross-path diff empty, one unstable shape at 1.2% of output — the memory
line, observed taking 2897.26, 2897.27 and 2897.31 MB across five runs — and no identifier present in
the broker's output that is absent from the forwarder's.

**Scope limit.** PrimeTime only. The comparison needs an instance outside every studied panel and p16
has none of the studied generation — `p16_dev_0000` predates the immutable-core scheme — while
provisioning a studied p16 instance from a preflight is not acceptable. The HSPICE path rests on the
shared broker/client code and the artifact round trip, not on its own end-to-end comparison.

**And `rc_equal` is nearly vacuous here**, because `run_public.sh` ends in `exit 0` unconditionally.
It is recorded for completeness; `normalised_equal` is the assertion that carries the weight.

## 8. Check 6 — a pre-arm parity correction

**The correction.** Check 6's criterion changes from absolute unrecoverability to parity with the
frozen runner:

| | Before | After |
|---|---|---|
| criterion | the agent "cannot recover the overflow *by any path*" | OpenCode-specific overflow backing stores unreachable; agent-created workspace files allowed exactly where the frozen runner allows them |
| must hold | — | `<state>/data/opencode/tool-output/*` and `/tmp/opencode/*` unreachable |
| allowed | — | redirect-then-paginate, because `llm_agent_driver.py:67` permits it too |

**Why.** The dry run recorded check 6 as PARTIAL and recorded the reason honestly: the
scaffold-specific hole is closed — every read of the truncation backing store returned not-found,
because the read-only bind prevents the overflow from being persisted at all — but the agent
recovered a >4000-byte output by redirecting it to a workspace file and paginating it back with
`read` at `offset`/`limit`.

The frozen driver has the same escape. It truncates each observation to 4000 bytes
(`llm_agent_driver.py:585,742`) and its deny regex (`llm_agent_driver.py:67`) blocks
`EDA_TASK_PATH|/hidden|/solution|/oracle|run_hidden|../` — it does not block
redirect-then-read-a-slice. The observation *budget* differs between the scaffolds; the observation
*bound* never existed in either.

So the original criterion demanded a property the control never had, and would have failed the probe
for being **equal to the frozen runner**. That is a defective criterion, not a defective probe. The
quantity check 6 exists to protect is comparability of the observation budget, and parity is exactly
that quantity.

**Why this is a pre-arm correction and not a post-hoc rescue.** The distinction matters here more
than usual, because the paper is about not making it loosely:

- It is made **before the formal arm runs**, and no formal-arm outcome exists to be read.
- It was provoked by a **dry-run episode that is unscored and discarded by authorization**, on
  `p15_dev_0000`, an instance in no studied panel and carrying no condition variants — so no
  Base/BundleS contrast existed to be seen, and none was computed.
- It **tightens as well as loosens**: the backing-store requirement becomes explicit and mandatory
  where the old wording folded it into a general prohibition.
- It is recorded as a dated amendment with its own heading, not by editing the original text to look
  as though it always said this.

The correction changes `opencode_scaffold_probe_scope.md` in both languages, and
`test_check6_is_parity_not_absolute` asserts the corrected wording is present and the absolute
wording is gone.

## 9. Disclosed context — the frozen arm had this exposure too

The frozen driver's deny regex is
`(EDA_TASK_PATH|/hidden\b|/solution\b|/oracle\b|run_hidden|\.\./)`. It does not mention `ssh`, `b04`
or the forwarder. A frozen episode could therefore have run `ssh tsb@b04 cat
/tmp/eda_shim_*/signoff_intent_truth.json`, and the mediated `RUN:` grammar would have passed it
through.

This is recorded because it is the reason the broker is stricter than parity, and stating it is
better than quietly building a stronger control and implying the frozen arm had one. Three limits on
what it means:

- A grep of the committed records under `reports/` for direct `ssh`/`b04` invocation returns **0
  hits**, so the exposure was available and, in the committed record, not exercised. That is a
  statement about what the records contain, not a full audit — no audit was performed.
- The `a89e084` programme is closed. This is not a defect to be fixed there, no episode is rerun, and
  no frozen number changes.
- It does not license reading the broker as a scaffold improvement. The scaffold main effect is
  excluded by construction and is not computed; `test_no_scaffold_main_effect_claim` still applies.

## 10. What this design does not establish

Stated explicitly, because the failure mode this project keeps guarding against is a check that
passes in a configuration nobody will use:

- **Its transport premise does not hold on this host.** Established 2026-08-23 by the paid dry run and
  reproduced at zero cost by control 15. The sandbox cannot reach b04 at all, because the route is a
  `ProxyJump` through a bastion and it lives in `~/.ssh/config`. Closing this needs a different
  authorization boundary — a per-episode endpoint on the local host rather than on b04 — not a patch.
- **It does not authorize the formal arm.** Check 7's step-cap path is now settled by that dry run;
  its wall-clock path is not, and this design does not touch either.
- **Check 5 does not carry over.** Its PASS was established with the tools absent. This design mounts
  a tool channel, so check 5 must be established again, under the configuration the arm would
  actually use, before it counts.
- **It does not make the arm affordable.** The cost question is separate and the dry run refused to
  project it from one short instance for reasons the `ARM2_NOT_RUN` post-mortem already paid for.
- **It does not deliver Layer 1 by itself.** `n_tool_green_wrong` needs a real green tool signal
  *and* an unreachable oracle. This design is an attempt at the second while restoring the first;
  whether it succeeds is what the preflight measures.
- **It does not establish that a transport cap can never bind.** §4.1 measures headroom over a finite
  calibration set; §4.2's fail-closed behaviour covers the rest. The two must not be conflated into
  "the caps are non-binding".
- **It does not establish byte-for-byte action-surface parity with the frozen runner.** §3.4 records
  the difference — the broker pins tool-authoritative inputs to canonical task versions and the
  frozen runner did not — rather than resolving it.
- **Forwarder equivalence is established for the PrimeTime path only.** The comparison needs an
  instance outside every studied panel, and p16 has none of the studied generation: `p16_dev_0000`
  predates the immutable-core scheme, so its `build_deck.py` writes `circuit_built.sp` from scratch
  with no `circuit_core.sp` and the op table cannot service it. Provisioning a studied p16 instance
  from a preflight is not an acceptable substitute. The HSPICE path therefore rests on the shared
  broker/client code and the artifact round trip, not on its own end-to-end comparison.
- **It does not settle anything that needs a real model request.** Check 7 in particular is a
  dynamic property, and a zero-call preflight that reported it settled would be disguising a dynamic
  check as a static one. The one authorized paid episode and its preregistered gate are
  [`opencode_probe_broker_dry_run.md`](opencode_probe_broker_dry_run.md); the ¥20 live cost cap that
  bounds it is described there and is fail-closed in the same sense as §4.2.

## 11. Files and verification

```
scripts/eda_broker/broker_protocol.py                op table, framing, caps, error taxonomy
scripts/eda_broker/authorized_keys_block.py          managed block, mutex, batch install/teardown
scripts/eda_broker/remote_broker.py                  deployed to b04; the forced command
scripts/eda_broker/broker_sh.template                rendered into <root>/broker.sh at deploy
scripts/eda_broker/broker_client.py                  in-sandbox client; the pt_shell/hspice shim
scripts/eda_broker/broker_admin.py                   host-side deploy / provision / batch / teardown
scripts/opencode_probe_raw_output_audit.py           zero-call transport-headroom calibration
scripts/opencode_probe_remote_broker_preflight.py    zero-call; writes the evidence record
scripts/opencode_probe_agent.py                      binds the capability into the sandbox
scripts/opencode_probe_broker_dry_run.py             the one paid episode; see its own document
tests/test_eda_broker.py                             protocol, classification, refusal, controls
tests/test_opencode_cost_governor.py                 the live cost cap and the run's readers
opencode_probe/evidence/raw_output_audit.json        the measured bounds behind section 4.1
opencode_probe/evidence/remote_broker_preflight.json the record
opencode_probe/broker/deploy.json                    remote interpreter, per-file sha256, host key
opencode_probe/broker/batch.json                     present only while a batch is live
```

None of these paths is sha256-pinned under `reports/evidence/`, and none of the pinned files is
modified. Verify before editing anything under `scripts/`:

```bash
python3 -c "import sys; sys.path.insert(0,'scripts'); \
  from frozen_membership_verify import collect_pins, SCAN_ROOT; \
  print('<path>' in collect_pins(SCAN_ROOT))"
```

Gate, all of which must pass before the preflight verdict is believed:

```bash
scripts/check                                                    # 1065 pins / 9 / 2 / 1
python3 -m pytest tests/test_eda_broker.py tests/test_opencode_probe.py -q
python3 scripts/opencode_probe_raw_output_audit.py               # zero model calls
python3 scripts/opencode_probe_remote_broker_preflight.py        # zero model calls
python3 scripts/slim_link_check.py
```
