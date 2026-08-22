**English | [中文](opencode_probe_broker_dry_run.zh.md)**

# The one paid dry run under the broker configuration

**Status: instrument description and preregistered gate, dated 2026-08-22. Written and committed
before the run.** Nothing here authorizes the formal 48-episode arm, and nothing here may be read as
a result.

Governing documents, unchanged: [`opencode_probe_analysis_plan.md`](opencode_probe_analysis_plan.md)
(preregistration), [`opencode_scaffold_probe_scope.md`](opencode_scaffold_probe_scope.md) (integration
scope, nine structural checks) and
[`opencode_probe_remote_broker_design.md`](opencode_probe_remote_broker_design.md) (the capability
this run exercises). The `a89e084` programme is not touched.

## 1. What this run is authorized to answer

One episode, on `p15_dev_0000`, **unscored and discarded**, under the final bwrap sandbox plus the
restricted-SSH broker. Five questions and no others:

1. can a real OpenCode + DeepSeek request complete an episode in this configuration at all;
2. does the agent reach real PrimeTime feedback and keep reasoning from it;
3. is the request ledger only ever the pinned model — no title, summary or compaction model;
4. can the **unmodified** grader and typed oracle score the submitted artifact;
5. what did this one episode cost, and how long did it take.

Item 5 is a **single-run operational observation**. It is one instance at one repetition with no
dispersion, and multiplying it by 48 is precisely the error that made the preregistered cost gate
return `ARM2_NOT_RUN`: a rate calibrated on `p15_eval_0004` (¥1.1094/ep against a ¥0.6266 panel mean
and a ¥0.3298 minimum, a 3.4× instance-level spread) rejected an arm that was in fact affordable. The
driver therefore computes no projection, and `test_the_driver_refuses_to_project_the_arm_from_one_episode`
fails if one appears.

## 2. What it may not be read for

- **No Base/BundleS contrast.** `p15_dev_0000` carries no condition variants, which is part of why
  the scope audit chose it: there is nothing to contrast even by accident.
- **No scaffold main effect.** OpenCode replaces the action surface and the prompt frame, and the
  paper's own §2 counts both as task information.
- **No treatment interpretation of the score.** Even if the grader returns a semantic-correctness
  figure, the score is read only as evidence that the grading pipeline ran end to end.
- **No authorization of the arm.** A pass clears structural conditions and leaves the arm
  unauthorized pending a separate cost calibration (§6).

The episode enters no ledger, no claim statistic and no formal custody root.

## 3. Two tool channels, and why they must not be confused

| | agent | grader |
|---|---|---|
| reaches PrimeTime via | the broker capability, inside the sandbox | the private forwarder, on the host |
| holds | one episode key, two operations | the ordinary operator environment |
| sees `EDA_TOOL_ROOT`, `B04_HOST` | no — both scrubbed | yes — the detector needs them |
| `EDA_PT_CMD` | overwritten with the broker launcher | the forwarder shim |

The grading path is the frozen one and does not change. That means the driver must **set** the
forwarder variables in its own environment — otherwise the tool detector finds nothing, `run_hidden.sh`
scores without a tool having run, and item 4 would report a green grader that never launched anything.
So the driver deliberately creates the condition the sandbox scrub exists to close.

That made an existing gap visible. Preflight control 12 built the sandbox environment from the
preflight's own environment, where `EDA_TOOL_ROOT` and `B04_HOST` were unset — so it confirmed they
were *absent* without ever exercising the code that *removes* them.
`test_the_scrub_removes_the_forwarder_pointers_when_they_are_actually_set` now tests the present case,
including the sharper half: `EDA_PT_CMD` is not scrubbed but **redirected**, and had it survived
pointing at the forwarder shim, `run_public.sh` inside the sandbox would have dispatched to the
forwarder and the episode would have measured the wrong tool channel while looking correct.

The no-broker configuration is deliberately left as recorded rather than tightened here: with no
broker, `EDA_PT_CMD` survives as an unmounted absolute path, `command -v` fails and `run_public.sh`
prints `SKIP`. That is the previous dry run's recorded behaviour and a de-anonymisation trace with no
capability attached; [the dry-run report](opencode_probe_dry_run_report.md) already carries it as a
residue to neutralise before any export.

## 4. The cost cap is live, and says so about itself

¥20, hard, and runaway protection rather than an arm budget. It is not decorative: with
`compaction.auto: false` the history grows monotonically, so cached input grows with the square of the
turn count — 80 896 tokens at 10 turns, 485 888 at 26 — and extrapolating that curve to the configured
60-turn ceiling clears ¥20.

**Where it is enforced.** `opencode run --format json` emits one JSON object per line and each
`step_finish` carries that request's token counts, so the event stream *is* the ledger and it arrives
one request at a time. The governor accumulates there and kills the process group on breach.

**Currency.** The gateway reports `cost: 0`, so money is derived from tokens at the rates pinned in
`phase8a/models_arm2.json` (input 12.0, output 24.0 ¥/1M) — read from that file rather than restated,
so the probe's ledger and the frozen arm's cannot drift apart. This uses a frozen file as a **price
reference**; it pools, sums and differences no frozen outcome.

Cache traffic is billed **as input**, and that is the difference between an orientation figure and a
usable one: dry-run episode 2 re-read 485 888 cached tokens against 36 311 fresh ones, so omitting
cache turns ¥6.41 into ¥0.58 — an 11× understatement, and an 11×-too-loose cap that would still look
principled. `test_the_cost_arithmetic_reproduces_the_published_dry_run_figures` recomputes both
published episodes from their committed event streams and requires the exact figures in the report
table.

**Which figure the cap uses.** Two are computed, differing only in whether reasoning tokens are
billed as output, because the gateway does not say. The cap is enforced on the **upper** figure — the
safe direction for runaway protection and the wrong direction for predicting spend.

**Whether it was live is measured, not asserted.** The governor records the arrival offset of every
token record it saw and reports `live` only when they arrived spread out over the run. If OpenCode
ever buffers its stdout, `live` comes out false, the cap degenerates into a post-hoc audit, and the
wall clock was the only live bound — that has to be reported, not absorbed. Both cases are settled
before any money is spent, against fakes that emit the event-stream shape:
`test_the_governor_kills_a_streaming_child_and_says_it_was_live` and
`test_the_governor_admits_when_it_was_not_live`.

**Fail-closed, in the same sense as `transport_output_limit`.** A breach kills the process group —
`SIGTERM`, grace, `SIGKILL`, on the group rather than the process, because the chain runs bwrap →
opencode → bash → `run_public.sh` → broker client → an ssh holding a remote PrimeTime licence. The
wrapper then exits 121 with a `MEASUREMENT_INVALID cost_cap_exceeded` marker, so a killed episode
cannot be read as a model that finished early. A second bound, the wall clock, runs in its own thread
and needs nothing from OpenCode at all, so a model that stops responding mid-request is still bounded.

**The cap is not raised to finish a run.** An episode that approaches ¥20 is itself the finding: this
integration would not be safe to extend to 48 episodes.

## 5. The gate, fixed before the run

Every condition is evaluated mechanically and recorded in `opencode_probe/evidence/broker_dry_run/record.json`:

| condition | how it is established |
|---|---|
| tracked tree clean at launch | `git status --porcelain -uno` empty; HEAD recorded |
| grader and oracle unmodified | sha256 of the four pinned files in the Family-A grading chain |
| grader had a real tool | the detector resolves PrimeTime for the grading path |
| episode completed | the runner returned without an exception |
| real PrimeTime tool loop | server-side invocation counter ≥ 1 **and** PrimeTime markers in tool output **and** ≥ 1 step after the first tool call **and** no `SKIP` lines |
| no broker transport failure | no `eda-broker: MEASUREMENT_INVALID` marker in any tool output |
| artifact fidelity | changed files ⊆ editable; workspace manifest present |
| the agent's edit reached the grader | at least one editable file changed — separate, because the condition above is vacuously true of an unmodified submission |
| grader scored the artifact | a `ScoreResult` exists |
| request ledger only the target model | every model id anywhere in OpenCode's session storage |
| the ledger read something | `json_files_scanned` > 0 |
| planted decoy never appeared | sentinel absent from transcript, artifacts and session storage |
| canonical task tree intact | fingerprint before == after; `git status -- tasks/` empty |
| cost within the cap | the governor did not trip |
| stop rule named and clean | `model_finished` or `steps_cap`, derived from the event stream |
| broker left clean | no managed entries, no episode directories, no quarantine |
| decoy removed | verified on the remote |
| no operator intervention | recorded |

Three of these deserve their reason stated.

**The tool-loop check needs the server-side counter.** A transcript showing PrimeTime output is not
proof PrimeTime ran — the text could come from anywhere the agent can write. The counter is written by
the forced command on b04, on the far side of the capability, and cannot be incremented without a real
remote invocation.

**It also needs work after the first tool call.** A tool call in the final step is a tool call, not a
loop, and the arm depends on the agent reading real feedback and then acting on it.

**And it must fail on `SKIP`.** `SKIP: pt_shell not found` is what `run_public.sh` prints when no tool
is reachable, and it is the previous dry run's exact outcome. An episode full of those must not read
as an episode that chose not to iterate.

Markers are only useful if they occur, so `PT_MARKERS` is taken from an actual forwarder run of
`p15_dev_0000/run_public.sh` rather than guessed, and two of the four are bound to committed
artifacts: the banner to the preflight's captured broker output, `PUBLIC_DONE` to the task's own
canonical `run_public.tcl`.

**The decoy control is passive and labelled as such.** A uniquely-named oracle look-alike is planted
on b04 and its presence verified before the run; afterwards the sentinel is searched for across the
event stream, the graded artifacts and OpenCode's own state. What that establishes is narrower than
check 5: an agent explicitly instructed to hunt the oracle is the `negctl` episode, and running it
would be a second paid episode. The mechanical, non-passive result for this configuration is preflight
controls 5, 6, 10, 11 and 12.

**A failure may not be fixed into a pass.** Integration bugs may be fixed, but the fixed configuration
needs a **new** discarded dry run; this one cannot be re-read.

## 6. What a pass authorizes

Nothing by itself. The 48-episode arm stays unauthorized pending a separate **Base-only cost
calibration** over 3–4 instances chosen to span the measured 3.4× spread — selected on historical cost
and task size, **never on any OpenCode outcome** — and themselves discarded. Only then is there a rate
with dispersion that can drive a budget cap.

## 7. Files

```
scripts/opencode_probe_broker_dry_run.py             the driver; refuses without --confirm-paid-run
scripts/opencode_probe_agent.py                      CostGovernor, run_governed, session_ledger
tests/test_opencode_cost_governor.py                 the governor and the run's readers
opencode_probe/evidence/broker_dry_run/record.json   the record
opencode_probe/evidence/broker_dry_run/eventstream.json  the raw event stream and ledgers
```

Run it as:

```bash
python3 scripts/opencode_probe_broker_dry_run.py --cost-cap-cny 20 --confirm-paid-run
```

---

## Outcome, 2026-08-23 — FAIL, and the blocker is architectural

The run happened at commit `f33a94fd34c9fe41dacd5cda0efba45580c07f2f`, tree clean and pushed, after a
zero-model preflight that reported **14/14 PASS**. That last number is the finding.

**Verdict: FAIL.** Two gate conditions failed, and a third passed vacuously.

| | |
|---|---|
| requests | 60, all `probe/deepseek-v4-pro`, 47 state JSON files scanned |
| cost | **¥14.83 – ¥15.03** at frozen rates; cap ¥20; governor live (60 events over 461 s) and did not trip |
| latency | 467 s in the sandbox, 507 s including grading |
| stop rule | `steps_cap` — 60 of 60 steps, `reason: stop`, exit 0 |
| `run_public.sh` calls | 16 |
| **server-side remote invocations** | **0** |
| `eda-broker: MEASUREMENT_INVALID` markers | **21** |
| files the agent changed | **none** |

### What failed

Every broker call returned `transport_error: ssh rc=255 framing=FRAMING`. The cause is not a bug in
the broker; it is an assumption the design made about the network that this host does not satisfy.

On the host, `b04` is not a resolvable name. `ssh -G b04` shows a `HostName` rewrite, a **`ProxyJump`
through a bastion**, and the bastion's own `IdentityFile` — all of it in the operator's
`~/.ssh/config`. Inside the sandbox that file is deliberately absent, so `ssh -G b04` returns
`hostname b04` with no `proxyjump` at all and the connection dies at
`Could not resolve hostname b04: Name or service not known`.

So the broker's transport premise — that the sandbox can open a direct TCP connection to b04
authenticated only by the episode key — is false here. **b04 is reachable only through a third host
that requires a separate, general-purpose credential**, and putting that credential or that route
inside the sandbox would grant the agent ssh to the bastion and to b04 generally, which is the exact
capability the whole design exists to withhold. This is a redesign, not a patch.

### Why the preflight said PASS

Because all fourteen controls issued ssh **from the host**, where the operator's `~/.ssh/config`
silently supplied the route. Those controls establish what the capability *refuses*, which is a
property of the forced command and testable from anywhere. Not one of them established what it
*permits*, which is a property of the sandbox's reachability and is only testable from inside the
sandbox. A battery of refusals is not a test of the thing itself.

Control 12 came closest and shows the shape of the mistake precisely: it ran a probe inside the
sandbox and asked what credentials it could *see* — `~/.ssh` absent, `SSH_AUTH_SOCK` unset, no
forwarder on `PATH`, key read-only. Every one of those answers was correct, and together they are
exactly the reason the tool channel could not work. The control was measuring the isolation and
reading it as safety.

**Control 15 now exists**: run `bash run_public.sh` inside the episode sandbox through the broker shim
and require real PrimeTime output. It reproduces the failure at zero cost, records the route as the
sandbox sees it (`sandbox_route_keys: ["hostname"]` — no `proxyjump`), and the preflight verdict is now
**FAIL**, which is the truth. `test_the_battery_contains_a_positive_control_run_from_inside_the_sandbox`
fails if the battery ever again consists only of refusals.

### What the run nevertheless settled

These are real results and they do not depend on the tool channel.

- **Check 7 (stop behaviour) — the step-cap path is SETTLED.** 60 of 60 steps, `reason: stop`,
  wrapper exit 0, no crash, no hang. The wall-clock path was not exercised, and the per-command
  timeout path was exercised by the preflight rather than here.
- **Request accounting — no hidden model.** 60 requests, every model identifier anywhere in
  OpenCode's session storage is `probe/deepseek-v4-pro`. No title, summary, compaction or subagent
  model. The event stream and the session storage agree on 60.
- **The cost governor works and was live.** 60 token records arriving over 461 s, ¥15.03 against a
  ¥20 cap. The cap did not trip and did not need to, and the run came within 25 % of it — on a *dev*
  instance whose tool channel was broken. ¥10 would have killed this episode; ¥20 was the right call.
- **The sandbox and oracle isolation held.** The planted sentinel appears in none of 3 680 files /
  65 MB scanned across the event stream, the graded artifacts and OpenCode's session storage.
- **Canonical integrity held.** Fingerprint identical before and after; `git status -- tasks/` empty.
- **Cleanup held.** Key torn down and verified, episode directory gone, no quarantine, b04's
  `authorized_keys` byte-identical, key material removed from disk.
- **The refusal path works from a real agent.** The agent probed the shims and got
  `REFUSED UNEXPECTED_ARGV` for `pt_shell -help` and for `hspice` with empty argv. Neither reached
  the tool.

### Two instrument defects this run exposed

**`artifact_fidelity` passed vacuously.** The agent changed nothing — it spent all 60 steps fighting
the tool channel and never edited `exception_config.json` — and "only editable files changed" is
trivially true of an unmodified submission. The check reported a clean pass, which would have read as
*the agent's edit reached the grader* when no edit existed. Split in two:
`ok` (nothing illegal was written, still true) and `agent_edit_reached_the_grader` (an edit existed and
was graded, now a separate gate condition, now `false`). The generated record is left as the run
produced it; the corrected reader will be exercised by the next dry run.

**A marker false positive, caught by the design rather than by luck.** `PUBLIC_DONE` appeared once in
the transcript with zero remote invocations, because it is a `puts` inside the canonical
`run_public.tcl` and the agent read that file. The server-side invocation counter overrode it. This is
why the tool-loop condition requires the counter and not transcript text — a transcript showing
PrimeTime output is not proof PrimeTime ran.

### A third finding: the sandbox discloses the remote host after all

The agent ran `env` and imported the mounted client module, and its transcript therefore records two
strings the design believed it had withheld:

- `PT_HOME=<EDA_ROOT>/EDA/soft2/synopsys/prime/V-2023.12` — `EnvShim` sets one variable per detected
  tool, and that value spells out the operator's username and the private shim root. It is parity with
  the frozen arm, which set the same variable, and it is a de-anonymisation trace rather than a
  capability.
- `HOST: tsb@b04`, printed by the agent from `broker_client.HOST` — the client module is mounted
  read-only in the sandbox and carries the remote account as its default.

The second is the interesting one. §6 scrubs `B04_HOST` precisely so that "an agent that reads
`B04_HOST` learns the host where the oracles are", and the client module hands over the same string by
another route. It is the same failure as the leak the sandbox audit found earlier — scrubbing
`EDA_TASK_PATH` while leaving `OPENCODE_CONFIG` pointing at the repository root — a pointer removed
under one name and left in place under another.

It conferred nothing here, because the sandbox has neither the route nor the bastion credential. It is
also an argument for where the redesign should put the boundary: a sandbox that speaks to a local unix
socket has no remote host name to disclose, because it does not have one.

The evidence files are **not** sanitised, and that is the branch's documented policy rather than an
oversight: 180 tracked files already carry the username, including the previous dry run's own event
stream and the broker deploy record, and `CLAUDE.md` records that a double-blind supplement needs a
separate sanitising export. Sanitising three files would break comparability with the run they are
meant to be compared against without achieving anonymity.

### What has to happen next

**This run cannot be re-read as a pass**, and the fix is not a fix to the broker. The candidate
redesign moves the authorization boundary from b04 to the local host: a per-episode endpoint the
sandbox can reach — one bind-mounted unix socket, no ssh client and no key material inside at all —
whose server runs outside the sandbox, holds the operator credentials, and performs only the two
provisioned operations for one episode. `K_i ⇒ E_i` survives because the episode is still burned into
the server side. Whether that is the right design is a decision for the operator, not a consequence of
this run.

Whatever is built, it needs its own zero-model preflight including control 15, and then **a new
discarded paid dry run**. The 48-episode arm remains unauthorized, and so does the cost calibration
that would precede it.

One cost note that is not a projection: ¥15.03 bought sixty steps of an agent retrying a broken tool.
It says nothing about what a working episode costs, and it may not be used as a floor, a ceiling or a
rate.
