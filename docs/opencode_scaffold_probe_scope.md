**English | [中文](opencode_scaffold_probe_scope.zh.md)**

# OpenCode scaffold probe — integration scope and zero-call alignment audit

**Status: nothing has been run.** No model was called, no episode exists, no frozen result was
touched, and no instance was selected. This document is the *scope audit* that precedes the decision
to run, and it is deliberately not a preregistration.

**That preregistration now exists separately:
[`opencode_probe_analysis_plan.md`](opencode_probe_analysis_plan.md)**, committed before any outcome
field of any OpenCode episode was read, in the manner of
[`phase8a_arm2_analysis_plan.md`](phase8a_arm2_analysis_plan.md). It fixes the questions, the outcome
definitions, the wording standard and the escalation rule; this document fixes the integration
surface and the nine structural checks that gate execution. Where the two touch — the design table,
the pre-committed questions — the plan governs.

**What is authorized is integration plus one unscored, discarded paid dry run.** The 48-episode
formal arm is not authorized and becomes so only if all nine checks below pass. See `CLAUDE.md`
hard constraint 1, which carves this out without reopening the `a89e084` programme.

Everything below about OpenCode was established from **the installed binary** (`opencode 1.18.19`
at `~/.opencode/bin/opencode`), its published config schema (`https://opencode.ai/config.json`),
and its own built-in configuration reference (`opencode debug skill`). Everything about the
controlled runner was read out of the frozen code. Where a fact could not be established without
running an episode, it is marked **must be verified in the dry run** rather than assumed.

## Why this probe, and what it can actually answer

The manuscript (v20) studies a **task-information intervention** with the agent scaffold held
fixed. Every episode in the paper ran through one runner of our own, so the paper's own §7 concedes
that the 82-of-169 tool-green occupancy is a property of that runner. An independent scaffold is
therefore the single most load-bearing piece of external validity the paper is missing.

**But the strict form of the question is not achievable, and it matters that this is said first.**
The paper defines task information as *prompt, visible files, disclosure bundle, public tool
feedback, and action surface*. OpenCode necessarily replaces the action surface and the prompt frame.
So an OpenCode arm does not vary "only the scaffold" — by the paper's own taxonomy it varies the
scaffold **and** two components of task information at once.

What survives that objection is the **interaction**, and it is the interesting quantity anyway:

| | Base | BundleS |
|---|---|---|
| controlled runner | measured (arm 2) | measured (arm 2) |
| OpenCode | probe | probe |

The *scaffold main effect* (row difference) is confounded and must not be reported as a scaffold
effect. The *treatment effect within OpenCode* (column difference in the bottom row) is clean,
self-contained, and is the estimand. Whether it agrees in sign with the top row is a **descriptive
cross-batch comparison**, subject to exactly the discipline the paper already applies to its
cross-batch concordance — and better supported than most, because model, instances, conditions and
*k* can all be held identical (see [Probe design](#minimal-formal-probe-design)).

The second question needs no comparison at all and is the cheaper win: **does tool-green semantic
misbinding still occur under an independent scaffold?** That is a per-episode property of the oracle
versus the tool signal, so it is answerable by counting: a single OpenCode episode that binds a role
wrongly while `run_public.sh` returns green does establish that the failure mode is not exclusive to
our own runner. **The strength of what may be written scales with the count, and a lone instance will
be reported as exactly that** — the reported quantities are `n_semantic_wrong` and
`n_tool_green_wrong` over valid episodes, with no significance claim at any count, and a count of
zero reported with equal prominence. The bound is fixed in
[the analysis plan](opencode_probe_analysis_plan.md#layer-1--primary-external-validity-question-existence-and-frequency),
not after seeing the number.

## The finding that makes this cheap: the seam already exists

`run_single_agentic(task_path, agent_cmd, meta, timeout, ...)` takes `agent_cmd` as a **shell
string** (`eda_agentbench/agentic/runner.py:179`), runs it with `cwd=<agent workspace>`, and then
does everything else itself: evaluator workspace, hidden overlay, `run_public.sh` / `run_hidden.sh`,
the typed oracle, and three anti-cheat checks. The frozen episode runner already builds that string
by hand (`scripts/phase8a_episode_runner.py:187`).

So an OpenCode arm is **a different `agent_cmd`, and nothing else**. No change to the runner, the
two-phase workspace, the graders, the task files or the task semantics. That is the strongest
possible answer to "is the grader unchanged?" — it is not merely unchanged, it is not even reached
by the substitution.

## The alignment target, in exact frozen numbers

Read from `scripts/phase8a_run.py`, `scripts/phase8a_episode_runner.py`,
`scripts/llm_agent_driver.py` and `phase8a/models_arm2.json`:

| Quantity | Frozen value |
|---|---|
| action budget | `--max-actions 60` |
| episode wall clock | `EDA_TIMEOUT` 1800 s; driver stops itself at 1770 s |
| per-command timeout | `min(180, remaining)` s |
| observation truncation | 4000 bytes (driver default; never overridden) |
| sampling temperature | 0.7 |
| `max_tokens` per request | 32000 |
| socket-inactivity timeout | 120 s |
| hard request deadline | 300 s (isolated worker killed) |
| retry authority | 6 retries, fresh worker per attempt, infrastructure faults only |
| transport | SSE streaming **on** |
| confidence elicitation | on (`--elicit-confidence`) |
| action grammar | `RUN:` / `WRITE:` / `FINISH`, **exactly one per turn**, first marker wins |
| write scope | editable basenames only; anything else refused |
| read scope | regex-denied: `EDA_TASK_PATH`, `/hidden`, `/solution`, `/oracle`, `run_hidden`, `../` |
| context management | **none** — history grows monotonically, episode ends at the action cap |

## Per-surface mapping

Verdicts: **EXACT** = can be made identical and verified; **BOUNDED** = can be brought to a
recorded, defensible equivalent; **CANNOT** = irreducible scaffold difference, to be disclosed, not
papered over.

### 1. Workspace and file exposure — EXACT, with one prerequisite

The controlled runner hands the agent a flat `/tmp/eda_agent_*` copy of `<instance>/files/` and
nothing else. OpenCode accepts `--dir`, so it can be pointed at the identical workspace, and the
visible byte set is then identical by construction.

The prerequisite is that OpenCode's **config discovery walks upward from the cwd** (project
`opencode.json` / `opencode.jsonc` / `.opencode/opencode.json`, up to the worktree root) and
separately reads `~/.config/opencode/`. Both are currently clean on this machine — no
`~/.config/opencode/opencode.json`, no `AGENTS.md` at `/`, `/tmp` or `$HOME` — but "currently clean"
is not a control. The wrapper must assert emptiness rather than hope for it, using
`OPENCODE_DISABLE_PROJECT_CONFIG=1` plus an explicit `OPENCODE_CONFIG=<pinned file>`.

The workspace is not a git repository. What OpenCode treats as the "worktree root" in that case
**must be verified in the dry run**.

### 2. Task text — EXACT for the text, CANNOT for the frame

`prompt.md`, `spec.md`, `glossary.md` and `public_check_summary.json` live in `files/` and so arrive
byte-identical via the workspace. The task text can additionally be passed verbatim as the `run`
message.

What cannot be matched is everything OpenCode wraps around it: its own system prompt for the agent,
the JSON schemas of whatever tools remain enabled, and its environment preamble. An agent's `prompt`
field replaces the agent's base prompt, but not the tool schemas and not the environment block. This
is the irreducible half of the "same task information" requirement, and it is the same fact as
[§ Why this probe](#why-this-probe-and-what-it-can-actually-answer): the prompt frame is task
information, so it cannot be held fixed while the scaffold changes.

Four injectors must be shut off explicitly, because each one adds agent-visible content that has no
counterpart in the frozen runs:

| Injector | Control |
|---|---|
| project/global instruction files | `instructions: []`, plus the emptiness assertion above |
| skills, including auto-loaded `~/.claude/skills` and `~/.agents/skills` | `OPENCODE_DISABLE_EXTERNAL_SKILLS=1`, `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1`, `permission.skill: deny` |
| plugins, including auto-discovery from `.opencode/plugin/` | `--pure` / `OPENCODE_PURE=1`, `OPENCODE_DISABLE_DEFAULT_PLUGINS=1`, `plugin: []` |
| MCP servers | `mcp: {}` |

The resolved config also carries `"username": "tongsb"`. That is agent-visible content **and** a
de-anonymisation vector on a branch that is not anonymised; set `username` to a neutral literal.

### 3. Action surface — CANNOT

This is the largest and most honest gap. The frozen grammar is three verbs, one action per turn,
first-marker-wins. OpenCode's `build` agent resolves to `bash, read, write, edit, glob, grep, task,
webfetch, todowrite, skill, question, invalid`, issues **multiple tool calls per assistant turn**,
and edits by patch rather than whole-file overwrite.

It can be narrowed a long way, but four mechanics matter and three of them correct an earlier draft
of this audit:

- **The permission keys are `read, edit, glob, grep, list, bash, task, external_directory, todowrite,
  question, webfetch, websearch, lsp, doom_loop, skill`** — and **`write` is not among them.** Per
  OpenCode's own permission documentation, **`edit` is a single key covering `edit`, `write` *and*
  `patch`**. So permissions cannot allow whole-file writes while denying patch edits; the two share
  one switch. An earlier draft of this section said to allow "`write`/`edit`", which is not a thing
  that can be written.
- **`deny` removes the tool; it does not merely refuse a call.** This was measured, not inferred:
  with the probe permissions applied, `opencode debug agent probe` reports the denied tools as
  *disabled*, and the enabled set collapses from twelve to **`bash, edit, read, write`** (plus
  `invalid`, OpenCode's malformed-call fallback). The deprecated `AgentConfig.tools` boolean map
  produces an identical result, so there is no reason to use the deprecated path. This is better
  alignment than an earlier draft of this section claimed — it asserted that a denied tool stays in
  the schema and injects a refusal observation. It does not. The visible action surface is four
  tools against the frozen driver's three verbs.
- **The resolved defaults already contain duplicate, conflicting rules**, and last-wins is doing real
  work in them: `question` appears as `deny` and then `allow`, and so does `plan_enter`. They also
  contain permission names that **do not appear in the published schema at all** (`plan_enter`,
  `plan_exit`), so the fifteen documented keys are not the complete runtime set. A probe config is
  therefore not verified by what it was written to say — it is verified by reading back
  `opencode debug agent <name>` and inspecting the *resolved* rule list.
- `lsp: false`, `subagent_depth` at its floor and `task: deny` remain correct as written.

It still cannot be made one-action-per-turn, and — now for a named reason rather than an assumption —
there is no permission that makes a patch edit into a whole-file `WRITE`, because `edit` governs
both. **Record this as the scaffold difference the probe is deliberately introducing** — it is the
intervention, not a defect. What must not happen is reporting a row difference as if the action
surface had been held fixed.

### 4. Observation budget — CANNOT by config; depends on the sandbox

`tool_output` defaults to `max_lines` 2000 and `max_bytes` **51200** — 12.8× the frozen 4000-byte
truncation. Setting `tool_output.max_bytes: 4000` matches the number, and reads back correctly.

The trap, and it is worse than an earlier draft of this section said. On overflow OpenCode **writes
the full text to a truncation directory and returns a preview**, and the resolved agent *allows*
`external_directory` for `~/.local/share/opencode/tool-output/*` — **three separate times in the
resolved rule list**. So a capped observation is recoverable by reading a file, which the frozen
driver's hard slice makes impossible.

**That deny cannot be delivered by configuration at all.** Measured against four forms — `"deny"`,
`{"*": "deny"}`, explicit `tool-output` and `/tmp/opencode/*` patterns, and a global `"*": "deny"` —
every one leaves the three built-in allow rules in place, and last-matching-rule-wins gives an
effective action of `allow`. The allow pattern also *follows* `XDG_DATA_HOME`, so giving each episode
its own state directory moves the hole rather than closing it. An earlier draft said "both settings
are needed"; in fact **the cap is enforceable and the deny is inert**, so check 6 rests entirely on a
filesystem control — see §8. Without one, the 4000-byte cap is one tool call from not existing.

### 5. Stop conditions and budget — BOUNDED, with one unit mismatch

| Frozen control | OpenCode equivalent | Note |
|---|---|---|
| `--max-actions 60` | agent `steps` | **Not the same unit** — the schema defines `steps` as *"maximum number of agentic iterations before forcing text-only response"*, and one iteration may carry several tool calls. (`maxSteps` is its `@deprecated` alias; pin `steps`.) Record as a scaffold difference; do not claim equal action budgets. |
| hard request deadline 300 s | provider `options.timeout` (ms) | direct |
| socket inactivity 120 s | provider `options.chunkTimeout` (ms) | direct, streaming only |
| — | provider `options.headerTimeout` | no frozen counterpart; pin it |
| episode wall 1800 s | wrapper `timeout(1)` around `opencode run` | the runner's own `subprocess` timeout still applies |
| per-command 180 s | **no config surfaced** | must be verified in the dry run; otherwise enforce in the wrapper |
| retries 6, infra-only | **no config surfaced** | must be verified in the dry run |
| temperature 0.7 | agent `temperature` | direct |
| `max_tokens` 32000 | provider `models.<id>` options | direct |
| **no compaction** | `compaction.auto` defaults **true** | set `false`; then a long episode overflows context instead of stopping gracefully — that replacement behaviour must be recorded, not hidden |

### 6. Extra model calls — BOUNDED, and it breaks cost accounting if missed

OpenCode ships hidden internal agents `title`, `summary` and `compaction` alongside `build`, `plan`,
`general` and `explore`. These make **additional model requests**, and `small_model` may point at a
different model entirely. Left alone they would (a) spend budget outside the measured arm, (b) put a
second model inside a nominally single-model cell, and (c) inject summarised context no frozen
episode ever saw.

Controls: pin `small_model` to the same model id, pass `--title` explicitly so no title is
generated, `compaction.auto: false`, `task: deny`, and disable the unused primary agents. Then
verify against `opencode stats` that the episode's request count matches the expected one-per-
iteration.

### 7. Grader handoff — EXACT, with two byte-level hazards

Unchanged by construction (see [the seam](#the-finding-that-makes-this-cheap-the-seam-already-exists)).
Two OpenCode defaults would nevertheless corrupt the submitted artifact:

- **`formatter`** — OpenCode formats files it edits. A reformatted `flow_config.json` or `.sdc` is a
  different byte string than the agent wrote, and the grader reads bytes. Set `formatter: false`.
- **`snapshot`** — filesystem snapshot tracking writes state into the working tree. The runner
  diffs a sha256 snapshot of the whole workspace before and after and feeds added files to
  `detect_hidden_shadows` / `detect_forbidden_modifications`. Stray artifacts are at best noise and
  at worst a false anti-cheat violation. Set `snapshot: false`, and confirm in the dry run that the
  post-episode workspace diff contains only the editable files.

### 8. Oracle isolation — CANNOT be achieved by configuration; hard prerequisite

The frozen driver protects the oracle three ways: it never reveals `EDA_TASK_PATH`, it **scrubs
`EDA_TASK_PATH` and `EDA_TASK_ID` from the environment of every `RUN` subprocess**
(`llm_agent_driver.py:693`), and it regex-refuses commands mentioning `hidden`, `solution`,
`oracle`, `run_hidden` or `../`.

The runner exports those variables into the agent command's environment
(`runner.py:424`), the canonical `hidden/` directories are mode 775 — world-readable — and
**OpenCode's `external_directory` permission is a file-tool boundary and is not expected to constrain
`bash`** (must be verified in the dry run — and the safe assumption either way). So `bash: allow`
plus an unscrubbed environment is a direct path to `cat $EDA_TASK_PATH/hidden/handoff_truth.json`,
which would not merely bias the probe, it would void it.

Two layers are required, and neither is optional:

1. **Wrapper env scrub** — the OpenCode `agent_cmd` must delete `EDA_TASK_PATH` and `EDA_TASK_ID`
   before exec, exactly as the driver does. **Implemented and verified** in
   `scripts/opencode_probe_agent.py`.
2. **Filesystem isolation** — run OpenCode with the task tree unmounted, so the oracle is not merely
   un-named but absent. A denylist is a weaker control than an empty mount.

**Layer 2 is currently blocked, and it is the probe's one hard blocker.** `bwrap` 0.9.0 is installed
but fails `setting up uid map: Permission denied`: the binary is not setuid and this host sets
`kernel.apparmor_restrict_unprivileged_userns=1`, so unprivileged user namespaces are unavailable.
`unshare -r` fails the same way. Three ways out, in preference order:

- **Lift the restriction** — `sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0` (or an
  AppArmor profile for `bwrap`). One line, and it restores the design exactly as specified. It is a
  host-wide security-posture change, so it is the operator's decision and not something this audit
  performs.
- **Docker** — the daemon is reachable, but this is **rejected on alignment grounds, not difficulty**:
  containerising the run would change the EDA tool environment, and the tool environment is one of
  the factors the probe exists to hold fixed. It would trade the oracle-isolation confound for a
  tool-environment confound.
- **Parity-only fallback** — env scrub plus `bash`/`read` permission patterns reconstructing the
  driver's `hidden|solution|oracle|run_hidden|\.\.` denylist. This reaches **the same protection the
  frozen runner has, not better**, so check 5 would be downgraded from *"the oracle is absent"* to
  *"the oracle is undisclosed and denylisted"* and must be disclosed at that strength. Note it is
  strictly weaker here than in the frozen runner, because there one mediated action grammar saw every
  command, whereas OpenCode reaches the filesystem through `bash`, `read`, `write` and `edit`.

Because layer 2 also carries check 6 (§4 — the observation cap is unenforceable by config and needs
the truncation directory made read-only), the sandbox decision governs **two** of the nine checks,
one of them mandatory.

A dry-run assertion belongs on top of both layers: an episode whose prompt *instructs* the agent to
read the oracle must fail to find it.

### 9. Publication and anonymity — EXACT

`share: "disabled"` (and the deprecated `autoshare: false`). This branch is not anonymised and
roughly 212 frozen custody files still carry a username or host name; an OpenCode session must never
be uploaded. `--pure` also keeps external plugins from seeing episode content.

## What the zero-call preflight already settled

`scripts/opencode_probe_preflight.py` runs the checks that do not need a model — they are properties
of the config, the filesystem and the sandbox, and a model adds nothing to establishing them. It makes
**zero model calls**; its record is
[`opencode_probe/evidence/preflight.json`](../opencode_probe/evidence/preflight.json).

| Established at zero cost | Result |
|---|---|
| Prompt transfer fidelity | **PASS.** Every section marked TRANSFERRED is byte-identical to what the frozen driver sends, proved by evaluating the driver's own AST rather than grepping its source. Five sections transfer, four are restated, and the frozen `RUN:`/`WRITE:`/`FINISH` grammar does not leak into an OpenCode episode. |
| Check 1 — file exposure | **PASS.** 16 files in the workspace, 16 in `<instance>/files/`, no difference either way, and no `hidden`/`solution`/`oracle` directory present. Uses the real `create_agent_workspace`. |
| Check 2 — injection sources silent | **PASS**, all sixteen assertions: `instructions`/`plugin`/`mcp`/`skills` empty, `username` neutral, `share` disabled, `snapshot`/`formatter`/`lsp`/`autoupdate` off, `tool_output.max_bytes` 4000, `compaction.auto` and `.prune` off, `small_model` equal to `model`, `subagent_depth` 0, and no literal secret in the resolved provider block. |
| Check 2b — resolved permissions | **PASS** for everything enforceable. Denied tools are genuinely *disabled*: the enabled set is `bash, edit, read, write` (plus `invalid`), down from twelve. `external_directory` is the sole exception and is unenforceable by config (§4). |
| Checks 5 and 6a — sandbox | **FAIL, blocked.** `bwrap` cannot create a user namespace on this host (§8). A host setting, not a probe defect. |

Two consequences worth stating plainly. First, **the paid dry run now only has to settle checks 3, 4,
7, 9 and the recoverability half of 6** — the model-behaviour ones. Second, **the mandatory check 5 is
currently failing for a reason no amount of configuration can fix**, so by this document's own abort
criteria the formal arm cannot start until the sandbox question is decided.

## Dry run specification

Two episodes, **both unscored and both discarded**, on `p15_dev_0000` — the family's only development
instance, and the only p15 directory outside every studied panel. The twelve-instance panel is
`p15_eval_0004`–`p15_eval_0015`; `p15_eval_0001`–`0003` are the separately reported three-instance
pilot and are equally off-limits. `p15_dev_0000` carries no condition variants, so the two dry-run
episodes are two repetitions of the same instance — which is sufficient, because all nine checks
below are structural: **none of them looks at a condition contrast, and no instance is selected on
any outcome.**

| # | Check | Pass criterion |
|---|---|---|
| 1 | file exposure | workspace listing identical to `<instance>/files/`; no `hidden`/`solution` path resolvable |
| 2 | injector silence | `opencode debug config` shows empty `instructions`, `plugin`, `mcp`, `skills`; neutral `username` |
| 3 | tool permissions | every denied tool, when attempted, is refused and the refusal appears in the JSON event stream |
| 4 | no human gate | the episode completes unattended; no `ask` remains in the resolved permission set |
| 5 | oracle isolation | a prompt that explicitly asks for the oracle cannot reach it |
| 6 | observation cap | **negative control, not an inspection** — deliberately emit a >4000-byte tool output, then confirm the agent cannot recover the overflow *by any path*: truncated in the returned message, and the truncation file unreadable via `read`, `glob`, `grep` and `bash` |
| 7 | stop behaviour | the `steps` cap and wall clock both terminate cleanly; per-command timeout observed |
| 8 | artifact fidelity | post-episode workspace diff contains only editable files; no formatter rewrite, no snapshot state |
| 9 | request accounting | `--format json` event stream and `opencode stats` agree on request count; no `small_model` call |

**Check 6 has to be a negative control because the failure mode is silent.** If OpenCode shows the
model 4000 bytes on the surface while writing the full output into a directory the model is permitted
to read, then the 4000-byte cap does not exist — it is merely one extra tool call away, and every
observation budget the probe claims to have matched is fiction. Setting `tool_output.max_bytes` and
reading back the setting proves nothing about recoverability. Only provoking an overflow and failing
to retrieve it does.

**Cost calibration is part of the dry run, and the paper's own history says how to do it.** The
`ARM2_NOT_RUN` gate rejected an affordable arm because its rate estimator was calibrated on
`p15_eval_0004`, the dearest of twelve instances (¥1.1094/ep against a ¥0.6266 panel mean and a
¥0.3298 minimum — a 3.4× instance-level spread). Any rate measured here must therefore come from a
sample spanning that spread, and must carry its dispersion into the decision rather than collapsing
to a mean.

## Minimal formal probe design

**Budget note first: this cannot be drawn from the frozen programme.** That programme spent
¥183.9329 of a ¥200 cap and has ¥16.07 left. A scaffold probe needs its own cap, its own ledger and
its own gate.

The design mirrors arm 2 exactly — same model, same twelve frozen instances, same conditions, same
*k*. Stated accurately, and this phrasing matters: **it matches model, task instances, treatment
conditions, replication depth, grader and EDA environment to the existing DeepSeek (*k*=2) panel,
while substituting the execution scaffold and the scaffold-implied interface framing.** It does *not*
make the scaffold the only varied factor — by the paper's own taxonomy OpenCode also changes the
prompt frame and the action surface, so the match is as close as the design admits rather than a
single-factor causal experiment:

| | value |
|---|---|
| model | `deepseek-v4-pro` (as arm 2) |
| instances | all 12 of `p15_eval_0004`–`0015`, **no selection on prior informativeness** |
| conditions | Base, BundleS |
| *k* | 2 (as arm 2) |
| **episodes** | **48** |

Adding TypedContract completes the mirror at 72 episodes. Cost is bounded below by arm 2's realized
¥0.6266/episode → ¥30.1 for 48, but OpenCode's heavier per-request frame and multi-tool turns make a
2–4× multiplier plausible; **the dry run measures this, and nothing here should be treated as a
projection.**

The alternative on the table was 12 × 2 × k=3 = 72. It buys within-cell resolution at the cost of
the exact mirror: at k=3 the OpenCode arm differs from arm 2 in scaffold *and* depth, which
reintroduces the two-factor confound that v18 and v19 spent two revisions cleaning up. **Recommend
k=2 for the mirror.** Note either way that k=2 carries no magnitude claim — arm 1 measured 7 of 36
cells disagreeing across six identical repetitions on this very family.

**Escalation to k=6 is a rule, not a later judgement, and it is fixed in
[the analysis plan](opencode_probe_analysis_plan.md#escalation-to-k6--the-rule-fixed-before-any-outcome)
before any outcome exists.** Stage 1 stays at k=2 because the probe's first purpose is
foreign-scaffold existence plus within-OpenCode behaviour, not a precise Δ. Extension happens if and
only if trajectories are 100% complete, at least 5 instances are informative (neither floor/floor nor
ceiling/ceiling), and cost fits the probe's own cap — and then **regardless of which condition scored
higher**. The failure this forestalls is the outcome-adaptive one: *"we saw +20 pp so we ran more to
confirm it; we saw 0 so we stopped."*

Excluded on purpose: a second model, further Bundle ablations, and SPICE. Each adds a factor before
the first scaffold observation exists.

## Questions fixed in advance

Written down now, before any outcome exists, so that neither can be chosen after the fact:

1. **Does tool-green semantic misbinding occur under an independent scaffold?** Descriptive
   existence and frequency, reported as `n_semantic_wrong` and `n_tool_green_wrong` over valid
   episodes. A wrong binding accepted by a green `run_public.sh` establishes that the failure mode is
   not exclusive to our own runner; a single instance is reported as a single instance, and **no
   significance is claimed at any count**. Licensed in both directions — 0 of *n* is a result and is
   reported with equal prominence — and no contrast is required.
2. **Does the Base → BundleS contrast have an observable effect within OpenCode?** The estimand.
   Reported by the same rules as arm 2 — sign test, instance resampling band, panel anatomy — and
   with the same three-part standard for the word "supported" (*p* < 0.05 **and** band excluding 0
   **and** more improving than declining). Anything less is **not established**, never "no effect".
3. **Does the instance-level response structure recur across scaffolds?** Descriptive only, and
   subject to the degenerate-agreement audit that corrected v18: floor/floor and ceiling/ceiling
   agreements record shared instance difficulty, not shared response, and must be counted out before
   any concordance is quoted.

The scaffold main effect is **not** on this list, and must not be added later: it is confounded with
the prompt frame and the action surface by construction.

## When not to do this

If the dry run cannot deliver checks 1, 5 and 8 — identical file exposure, oracle unreachable,
artifact bytes unaltered — the probe should not run. Those three are not alignment niceties; without
them the arm measures something other than what it claims, and a clean "we could not align this
scaffold" is a more useful contribution than a confounded number.

Checks 3, 4, 6, 7 and 9 failing individually is survivable, provided each failure is **recorded as a
scaffold difference** in the probe's preregistration rather than discovered afterwards.

## What running it would change elsewhere

Two consequences, neither of which is being applied now:

- **CLAUDE.md hard constraint 1** ("Experiments are permanently closed. No paid model call, no new
  episode... The experiment freeze HEAD is `a89e084`") would have to be amended, explicitly and in
  its own commit, to carve out a named scaffold arm with its own cap and ledger while leaving every
  frozen number derived from `a89e084` untouched. That amendment is a decision, not a formality, and
  is deliberately not made in this document.
- **The claim lattice gains a fourth projection.** The paper's configurations are
  `c = (f, i, m)` over family, instance set and model, with projections π_I, π_M, π_F. A scaffold
  arm adds π_S, and every existing verdict — observed at S0, replicated once at S1, not established
  at S2-M, S2-F, S3 — becomes a statement at fixed scaffold. That is a manuscript change of the same
  kind as v20's, and it should follow the probe rather than precede it.

## Verify this document, zero calls

```bash
~/.opencode/bin/opencode --version                 # 1.18.19 — pin this exact version
~/.opencode/bin/opencode agent list                # 7 agents; build allows "*"
~/.opencode/bin/opencode debug agent build         # resolved tools + permission rules
~/.opencode/bin/opencode debug config              # resolved config; assert the injectors are empty
~/.opencode/bin/opencode debug skill               # OpenCode's own config reference
curl -s https://opencode.ai/config.json            # authoritative schema for every key cited above
```

Frozen-side numbers: `scripts/phase8a_run.py:48` (constants),
`scripts/phase8a_episode_runner.py:187` (driver invocation),
`scripts/llm_agent_driver.py:632` (workspace, deadline, env scrub),
`eda_agentbench/agentic/runner.py:179` (the `agent_cmd` seam).
