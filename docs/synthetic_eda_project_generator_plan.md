# Synthetic Industrial EDA Project Generator — Direction Plan

Status: **DESIGN DRAFT (planning only).** No generator code, no commercial-tool runs, no b04-heavy
tasks. Authored on branch `synthetic-project-generator` (worktree `../eda-agentbench-synthetic`),
based on checkpoint `01b0356`, while the Phase-2 reliability run continues untouched in the main
worktree.

This document explains *why* the benchmark should move from single-task solvability to synthesizing
mini industrial EDA **projects**, what we have already ruled out, and the new thesis. The companion
docs define the mechanism taxonomy (`synthetic_failure_taxonomy.md`) and the minimal first closed
loop (`synthetic_phase0_mvp.md`).

---

## 1. Why pivot — the evidence we already paid for

Across this hardening cycle we repeatedly built a *small, self-contained, single-root-cause* EDA task,
gave the frontier models the real commercial tools, and watched the difficulty collapse. The pattern is
consistent enough to treat as a finding, not an accident. Directions already excluded **with data**:

| Direction explored | What we built | Why it was retired |
|---|---|---|
| **P5 / P6 / P7 local debug** | one broken SDC / netlist / lint deck, fix-and-rerun under DC / PrimeTime / SpyGlass | Once the agent can actually run the tool (post-`env_shim` fix, #94), top models localize and fix a single seeded fault near-perfectly. Spread came from *reliability*, not capability — which is exactly what the reliability layer now measures, not a new task. |
| **P9 ExceptionDebug** (PT false-path / over-constrain) | scalar-Liberty → `.db` → `report_timing`, false-path-on-a-must-meet-path detector | Phase-0 GO on b04, but the frontier aced both the *stated* intent and the *RTL-inferred* intent. Retired 2026-06-23 (see memory `p9-exception-debug-mechanism`, `single-localization-saturation`). |
| **Intent inference** (recover designer intent from RTL, judge a constraint against it) | inferred-intent falsification variant of P9 | Frontier reconstructed intent well enough that "did the fix match true intent" stopped discriminating. |
| **Combinational LEC attribution** (Formality) | mutation-oracle: which mutation breaks equivalence, attribute the failing point | `fm_shell` validated on b04 (#116); Phase-0 experiment (#118) showed single-fault attribution saturates the same way localization does. |
| **MCMM budget + hidden corner** | over-constrain detector hidden behind a multi-corner budget | Probe (#119) was noise — the "hidden corner" added variance, not a measurable capability gap; high search-collapse risk. |
| **Sequential equivalence** | sequential-equivalence Phase-0 falsification (#120) | Same single-localization saturation; cheap probe killed it before a full build. |

**Cross-cutting lesson (memory `single-localization-saturation`):** small single-fault localization is
frontier-saturated. Difficulty does **not** come from hiding the fault more cleverly, adding budget
pressure, or obscuring intent — each of those adds *noise*, not *signal*. The cheap-probe-first
discipline (always falsify before building) is the only reason this cost weeks and not months.

What *did* survive is orthogonal to task content: the **reliability / calibration layer** (Phase-1,
commits up to `01b0356`) — same model flips pass/fail on identical input, confidently certifies wrong
answers, returns empty, or truncates. That layer is now built and is being exercised by the Phase-2
agentic run. It is a *measurement* over existing tasks, not a new task family. The open question it
cannot answer is: **what task family is genuinely hard for a capable, tool-equipped agent?**

---

## 2. New thesis

> **Small self-contained single-root-cause EDA tasks are saturated for frontier agents. The next
> benchmark should synthesize mini industrial EDA projects with realistic multi-artifact failure
> mechanisms and machine-checkable commercial-tool oracles.**

The unit of difficulty moves from *a single broken file* to *a small but real project* — RTL + SDC +
flow scripts + spec/README + golden reports — in which a failure is introduced as a **mechanism that
propagates across artifacts and flow stages**, not a single line. The hard part is no longer "find the
broken line"; it is "reconcile what the spec says, what the constraints encode, what the tool reports,
and what the downstream stage consumed" — the everyday reconciliation work of a chip engineer.

Why this should resist the collapse we keep hitting:

- **No single grep-able fault.** The symptom surfaces in stage *N* (e.g. PrimeTime timing) but the root
  cause lives in stage *N−1*'s handoff (e.g. a constraint that drifted from the spec, or a generated
  clock the SDC and the netlist disagree about). The agent must trace *across* artifacts.
- **Multiple plausible "fixes" that are wrong.** A real project admits over-constraining, masking the
  symptom, or fixing the consumer instead of the producer — all of which a single-file task cannot
  express. The oracle distinguishes *fixed the mechanism* from *suppressed the symptom*.
- **The oracle stays machine-checkable.** Because we *generate* the golden project and *inject* the
  mechanism, we always hold ground truth: the golden flow passes, the mutant flow fails with a specific
  tool-visible symptom, and the oracle checks the mechanism is actually resolved (not that a diff
  matches). This is the same execution-based, marker-parsing grading the P6/P7 evaluators already use —
  extended from one file to a project.

This is explicitly **not** a return to single-localization with extra decoration. The taxonomy doc
defines each mechanism as a *cross-artifact / cross-stage drift*, and every one carries an explicit
"could the frontier shortcut this?" risk note so we falsify before we scale.

---

## 3. What we reuse (this is why it stays in this repo, not a new repo)

The pivot needs almost none of its scaffolding rebuilt — the value is in reusing the hardened harness:

- **`schema.py`** — `metadata.json` already models `files.{visible,editable,hidden,forbidden}`,
  `run_command`, `scoring.{weights,evaluator,metrics}`, `data_type` (incl. `flow_synthetic`), the `tool`
  enum (vcs/dc/pt/spyglass/icc2/innovus/starrc/...), and a `generator` block. A project task is a
  *superset* of a file task, not a new schema. (One additive field for multi-artifact manifests may be
  needed — see MVP doc §Schema.)
- **Workspace builder** (`agentic/workspace.py`) — the two-phase model (agent workspace = visible+editable
  only; evaluator workspace = agent edits + hidden overlay) already enforces hidden/oracle isolation and
  `detect_hidden_shadows` reward-hack detection. A multi-file project drops straight into `files/` +
  `hidden/`.
- **Tool detector + env shim** (`tools/detector.py`, `tools/env_shim.py`) — `EDA_TOOL_ROOT` rewrite and
  PATH injection already give the agent the real VCS/DC/PT toolchain on b04. No change needed.
- **Evaluator pattern** (`evaluator/base.py`, `dc_constraint_debug.py`, `primetime_sta_debug.py`) —
  execution-based grading where the *hidden run script emits anchored markers*
  (`^CONSTRAINTS_OK`, `^CONSTRAINTS_SCORE: <frac>`) and the evaluator only parses markers from the log.
  A project oracle is the same idea with markers spanning multiple stages.
- **Anti-cheat** (`anti_cheat/guard.py` SHA-256 forbidden-file guard + `workspace.detect_forbidden_modifications`
  / `detect_hidden_shadows`) — directly applicable; a project has *more* forbidden files (every script,
  every golden report), which strengthens the guard rather than complicating it.
- **Reliability / calibration layer** (`reliability.py`, `scripts/reliability_report.py`,
  `--elicit-confidence` / `--temperature`, agentic protocol capture) — scoring **must** flow through
  this. A project task that is solvable-but-unreliable is still a useful data point; the layer already
  separates capability from infra (429/empty) from protocol failure (nocommit/budget/anti-cheat).
- **Reporting** (`scripts/benchmark_report.py`, leaderboard, discrimination scan) — project tasks are
  just new tracks in the inventory; the dynamic count test added at `01b0356` already tolerates new
  tracks without breaking the gate.
- **CLI** (`run-agent`, `run-agent-dataset`) and orchestrator (`run_agentic_baseline.py`) — run projects
  with the same commands; only the track name changes.

A separate repo would fork all of the above and immediately rot. The right move is a **new track family
inside EDA-AgentBench**, developed on its own branch/worktree to keep the integration branch clean
(per CLAUDE.md "Parallel Worktree Development Rules").

---

## 4. Non-goals (this round)

- No generator implementation yet — design only.
- No commercial-tool execution, no b04-heavy runs, no touching the Phase-2 run directory.
- No expansion to ICC2 / Spectre / Formality / StarRC in the MVP — VCS + DC + PrimeTime only
  (see MVP doc). Physical / analog / LEC mechanisms are *designed* in the taxonomy but *deferred* in
  implementation.
- No new reliability metrics — reuse the layer as-is.
- No claim that this is hard until a cheap multi-model probe says so (Phase-0D gate).

---

## 5. Recommended next steps (detailed in the MVP doc)

1. **Phase 0A** — hand-author ONE mini golden project (RTL + SDC + scripts + spec + golden reports) that
   passes the real VCS+DC+PT flow. Proves the project shape and the golden-pass oracle.
2. **Phase 0B** — implement exactly ONE mutation mechanism (constraint drift) as an automated mutator on
   that golden project; confirm the mutant fails with a tool-visible symptom.
3. **Phase 0C** — oracle validation: golden→pass, mutant→fail, and the oracle distinguishes
   *mechanism-fixed* from *symptom-suppressed* on a couple of hand-written wrong "fixes".
4. **Phase 0D** — a cheap 3-model probe (gateway + b04, small) to falsify difficulty *before* scaling.
5. **GO / NO-GO** — only scale to more mechanisms / more projects if 0D shows a real, non-noise gap that
   survives the reliability layer. Otherwise retire cheaply, like the six directions above.

Guardrails (held from the whole cycle): cheap-probe-before-build; reuse don't fork; EDA tools only on
b04 (`/tmp` or `~/Desktop/tsb`, clean up, no internet/pip); shim stays outside the repo; never commit
credentials or raw tool outputs; never modify hidden/oracle/forbidden/scoring to make a score; grade the
known-correct golden through the same path before trusting any number; ¥1000 total budget — Phase 0 is
deliberately tiny.
