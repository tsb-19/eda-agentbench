**English | [中文](opencode_scaffold_probe_scope.zh.md)**

# OpenCode scaffold probe — integration scope and zero-call alignment audit

**Status: nothing has been run.** No model was called, no episode exists, no frozen result was
touched, and no instance was selected. This document is the *scope audit* that precedes the decision
to run, and it is deliberately not a preregistration — if the probe goes ahead it needs its own
preregistration committed before any outcome is read, in the manner of
[`phase8a_arm2_analysis_plan.md`](phase8a_arm2_analysis_plan.md).

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
versus the tool signal, so a single OpenCode episode that binds a role wrongly while `run_public.sh`
returns green reproduces the paper's central measurement finding on foreign scaffolding.

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

It can be narrowed a long way. The permission keys are exactly `read, edit, glob, grep, list, bash,
task, external_directory, todowrite, question, webfetch, websearch, lsp, doom_loop, skill`, each
taking `allow` / `ask` / `deny`, and within a per-pattern object **the last matching rule wins**, so
broad rules go first. A minimal surface is `bash`, `read` and `write`/`edit` allowed and everything
else denied, with `lsp: false`, `subagent_depth` at its floor and `task: deny`.

It still cannot be made one-action-per-turn, and there is no configuration that makes a patch edit
into a whole-file `WRITE`. **Record this as the scaffold difference the probe is deliberately
introducing** — it is the intervention, not a defect. What must not happen is reporting a row
difference as if the action surface had been held fixed.

### 4. Observation budget — BOUNDED to EXACT, and there is a trap

`tool_output` defaults to `max_lines` 2000 and `max_bytes` **51200** — 12.8× the frozen 4000-byte
truncation. Setting `tool_output.max_bytes: 4000` matches the number.

The trap: on overflow OpenCode **writes the full text to a truncation directory and returns a
preview**, and the default `build` agent explicitly *allows* `external_directory` for
`~/.local/share/opencode/tool-output/*`. So a capped observation is recoverable by reading a file,
which the frozen driver's hard slice makes impossible. Both settings are needed:
`tool_output.max_bytes: 4000` **and** `external_directory` denied for that path (and for
`/tmp/opencode/*`, allowed by the same default).

### 5. Stop conditions and budget — BOUNDED, with one unit mismatch

| Frozen control | OpenCode equivalent | Note |
|---|---|---|
| `--max-actions 60` | agent `steps` | **Not the same unit** — `steps` counts agentic iterations, and one iteration may carry several tool calls. Record as a scaffold difference; do not claim equal action budgets. |
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
   before exec, exactly as the driver does.
2. **Filesystem isolation** — `bwrap` is available on this host. Run OpenCode with the task tree
   unmounted, so the oracle is not merely un-named but absent. A denylist is a weaker control than
   an empty mount, and this is a case where the stronger one is cheap.

A dry-run assertion belongs on top of both: an episode whose prompt *instructs* the agent to read
the oracle must fail to find it.

### 9. Publication and anonymity — EXACT

`share: "disabled"` (and the deprecated `autoshare: false`). This branch is not anonymised and
roughly 212 frozen custody files still carry a username or host name; an OpenCode session must never
be uploaded. `--pure` also keeps external plugins from seeing episode content.

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
| 6 | observation cap | a >4000-byte tool output is truncated **and** the truncation file is unreadable |
| 7 | stop behaviour | the `steps` cap and wall clock both terminate cleanly; per-command timeout observed |
| 8 | artifact fidelity | post-episode workspace diff contains only editable files; no formatter rewrite, no snapshot state |
| 9 | request accounting | `--format json` event stream and `opencode stats` agree on request count; no `small_model` call |

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

The design that makes the scaffold the *only* varied factor mirrors arm 2 exactly — same model, same
twelve frozen instances, same conditions, same *k*:

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

Excluded on purpose: a second model, further Bundle ablations, and SPICE. Each adds a factor before
the first scaffold observation exists.

## Questions fixed in advance

Written down now, before any outcome exists, so that neither can be chosen after the fact:

1. **Does tool-green semantic misbinding occur under an independent scaffold?** Answerable from a
   single episode. A wrong binding accepted by a green `run_public.sh` reproduces the paper's central
   finding on foreign scaffolding. Licensed either way; no contrast required.
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
