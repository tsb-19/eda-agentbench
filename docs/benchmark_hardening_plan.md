# EDA-AgentBench Hardening Plan — Mapping the Gap to Human Chip Engineers

Status: living document. Started 2026-06-17 after the first model baseline showed
the benchmark is largely saturated and under-discriminating. Owns the cross-track
strategy that backlog `eda-validation-backlog.md` item F points at.

---

## 0. Governing principle (read before designing any task)

**The purpose of this benchmark is to measure where today's models still fall short
of solving _real_ EDA problems — where they are not yet as good as a competent human
chip engineer. It is NOT to manufacture clever, obscure, or contrived problems whose
only value is tripping models up.**

Concretely, every hardened task must pass this gate:

> **Realism test:** If a model gets this wrong, does that correspond to a mistake a
> careful human engineer would *not* make, or to a real defect that would actually
> hurt — in silicon, in the timing/power signoff, or in the design flow? If the only
> thing the task measures is puzzle-solving with no engineering meaning, **cut it.**

Corollaries:

- **Difficulty and discrimination are instruments, not the goal.** We want spread
  because *real capability gaps produce spread*. A task that discriminates for a
  contrived reason (operator-precedence trivia, artificial constraints, format
  pedantry, trick wording) is **noise dressed up as signal** — it inflates the
  numbers without telling us anything about EDA ability.
- **Saturated ≠ "model is good", and hard ≠ "task is good."** Saturation usually
  means the task tests *recall* of a pattern the model already memorized (and so
  would a senior engineer — no gap, no signal). Excessive, flat difficulty (see P8
  below) means we made it hard in a way that doesn't separate competence.
- **Read the failures.** Every hardening round must include a "failure realism"
  review: look at what the models actually got wrong and confirm it is a *real
  engineering gap*, not an artifact of the test. This is the human check that the
  Tier-2 scan (spread/saturation) cannot do by itself.

---

## 1. What "a real capability gap" actually means

These are the axes where a strong chip engineer adds value and where a model may
still fall short. Hardening should make each track probe one or more of them — and
nothing else:

1. **Corner-case reasoning that maps to real bugs.** Overflow/width, sign handling,
   reset/initialization, clock-domain crossing, saturation, rare FSM states. These
   are exactly where real bugs hide *because* the obvious test misses them. A careful
   engineer reasons about the untested corner; a pattern-matcher fixes only what the
   visible test shows.
2. **Tool-feedback diagnosis.** Read a real tool artifact (timing report, lint
   violation, DRC, SPICE waveform, STA path) → find root cause → fix → re-run. This
   is the core EDA loop; interpreting real tool output is a distinct, valuable skill.
3. **System / multi-module reasoning.** Understanding interactions across files and
   interfaces, not just a local one-line patch.
4. **Spec / intent inference.** Deriving intended behavior from a spec or context
   rather than from a spoon-fed hint.
5. **Quantitative analysis.** Computing slack, power, noise margin, settling time,
   gain — from real numbers — and reasoning about trade-offs.
6. **Methodology / tool knowledge.** Correct SDC constraints, legitimate lint
   waivers, correct STA/extraction setup — the "knowing how the flow works" layer.
7. **Analog / physical intuition.** Process corners, RC/RLC behavior, device-level
   effects.

A task that requires (1)–(7) is hard *for the right reason*. A task that is hard only
because it is weird fails the realism test.

---

## 2. Current state — the first baseline (2026-06-17, 5 models × 10/track)

Two distinct failure modes, both bad:

| Track | Saturated | Mean | Spread | Type | Failure mode |
|---|---|---|---|---|---|
| P1 RTL Debug | **10/10** | 1.00 | 0.00 | debug | too easy |
| P6 DC-Synthesis QA | **10/10** | 1.00 | 0.00 | QA | too easy |
| P7 SpyGlass Lint | **10/10** | 1.00 | 0.00 | debug | too easy |
| P6 DC-Constraint | 9/10 | 0.98 | 0.09 | debug | nearly saturated |
| P3 Timing QA | 7/10 | 0.94 | 0.30 | QA | mostly saturated |
| P7 PrimeTime STA | 7/10 | 0.95 | 0.27 | debug | mostly saturated |
| P5 SPICE Debug | 6/10 | 0.89 | 0.36 | debug | partly saturated |
| P2 TB/SVA Gen | 4/10 | 0.91 | 0.44 | gen | acceptable |
| P4 SPICE Sim | 3/10 | 0.89 | 0.28 | sim | acceptable (best) |
| **P8 PnR QA** | 0/10 | **0.74** | **0.09** | QA | **hard but flat** |

- **Saturation (most tracks):** all models score ~1.0 → zero signal. The tasks test
  recall of textbook patterns the frontier has memorized.
- **P8 is the inverse warning:** it is the *hardest* track (lowest mean) yet ties for
  *least* discriminating (spread 0.09) — everyone is stuck at ~0.74 together. That is
  the "made it hard the wrong way" failure: difficulty without competence-separation.
  P8 needs *re-targeting toward discrimination*, NOT more difficulty.

Difficulty labels are also uncorrelated with empirical difficulty (labeled-`hard`
was *more* saturated than `medium`) — so labels must be re-derived from data.

---

## 3. Evaluation protocol — the residual frontier under full tools

This is what the whole program is now organized around. It supersedes any "make the
task hard / measure how much tools help" framing.

**Measure capability, not tool-usage skill.** The target is where the model's EDA
ability falls short of a human engineer's. Tools are not the object of measurement —
they are the *condition* under which the model expresses its ability fully. So we do
not score "how well it used tools" or "how much tools lifted it"; we score whether,
*with the tools a real engineer has*, it still cannot solve the problem.

**The valuable residual = tasks that "model + realistic tools" still cannot fully
solve, graded continuously.** Three boundaries define it:
- Tasks model+tools *fully* solve → **retire them.** They map a capability the frontier
  already has; zero ongoing discrimination. (One-time value: they mark where the
  frontier *is* — but once known, they are dead weight.)
- Tasks *no* model makes any progress on → also dead (no discrimination — the P8
  failure mode).
- **Sweet spot:** the partial-completion band, where models reach *different* depths.
  The spread there is real capability difference, and "which model gets further" is the
  signal we publish.

**Evaluate under full tools, not single-shot.** Single-shot is at best a *floor* probe;
it overstates difficulty, because any no-tool score only rises once the model can
compile, read real output, and self-verify. A result that looks discriminating
single-shot may evaporate under tools (exactly what the P1 subtle-bug pilot warns of).
A task earns its place only if it survives full-tool evaluation.

**Grader validity is the load-bearing requirement under tool access.** With tools, a
weak grader gets gamed, so the bar on the grader rises:
- Passing must require *genuinely solving* — no hardcoded PASS, no degenerate fix that
  satisfies the visible checker while breaking real function (already forbidden by
  CLAUDE.md). Acceptance reflects the real objective (spec / signoff), not "the tool ran
  clean."
- The acceptance verdict stays **hidden from the agent during iteration**, so it cannot
  hill-climb the oracle. What the agent sees is realistic tool *diagnostic* output
  (symptom-level: the real STA report, lint log, sim behavior) — which is what makes
  diagnosis hard — never the graded pass/fail. **Collapse happens iff the feedback
  reveals the graded criterion.**
- Tool access is *realistic*, not infinite brute-force: a tool-call / cost budget, so
  "couldn't solve" means real incapability, not exhausted retries. (Efficiency is itself
  a real engineering quality, but a secondary axis — not the headline.)

**The frontier moves.** What model+tools can't do today it may do in six months.
Hardening is therefore perpetual: retire solved tasks, curate harder real ones, keep
tracing the edge. The signal that matters is performance on the *current residual set*,
not an average over solved-and-unsolved.

## 4. Per-track capability map (derive the method from the capability, case by case)

The method is **not** one-size-fits-all. For each track ask "what does this tool / flow
actually demand of a human engineer?", build the task to demand exactly that, then
evaluate it under the §3 protocol. The grouping below is by grading *substrate* (how a
score is computed), but within each the *method follows the capability*:

| Track(s) | Tool | Real capability it most demands | Method direction |
|---|---|---|---|
| P1 RTL, P5 deck | VCS / HSPICE | functional correctness + corner reasoning | corner-case defect, weak public, deep hidden — **but verify it survives full tools** (P1 single-shot did not separate models) |
| P7 SpyGlass, P7 PrimeTime | spyglass / pt | **tool-feedback diagnosis** (symptom→root cause→fix→re-run) | **naturally agentic** — real violations to diagnose; the first true residual-under-tools test |
| P6 constraint | DC | methodology: are the SDC constraints right | give intent, write constraints that make STA correctly pass (not over-constrain) |
| P3, P6-syn, P8 | pt/dc/icc2 reports | quantitative analysis of a real report | multi-step *computed/derived* answers + distractors, not lookup; P8 needs discrimination, not more difficulty |
| P2 gen | VCS | verification authoring | does the model's TB/SVA catch a battery of mutants (mutation coverage) — already spreads 0.44 |
| P4 sim | HSPICE/Spectre | analog/numeric, meet spec across conditions | numeric closeness over measures — already the best discriminator |

**The biggest under-used axis is tool-feedback iteration.** Everything in the first
baseline was single-shot. The most EDA-authentic and likely most discriminating
dimension — read real tool output, diagnose, fix, re-run, converge under budget — is
exactly the one not yet measured. P7 (real lint/STA violations) and P5 (analog
convergence) are the natural entry points, and the repo already has the `run-agent`
runner.

## 5. The hardening loop (now full-tool, with retire + realism gates)

```
pick a track -> build a task that demands its real capability (§4), passing the §0 realism test
   -> validate goldens         (validate_dataset.py: golden=1.0, margin >= 0.15)
   -> evaluate UNDER FULL TOOLS (run-agent; realistic tool budget; acceptance hidden from the agent)
   -> scan_discrimination       (saturated? dead? or in the partial band with model spread?)
   -> RETIRE GATE               (model+tools fully solve it? -> retire; no residual value)
   -> FAILURE-REALISM REVIEW    (read what models got wrong: is it a REAL engineering gap?)
   -> iterate / curate harder   (frontier moves; keep only residual-band tasks)
```

Two human checks the scan cannot do: the **retire gate** (is this still in the residual,
or has model+tools made it free?) and the **failure-realism review** (does it
discriminate for a reason that matters?). Together they keep the set honest to §0 and §3.

---

## 6. Self-assessment of the P1 pilot bugs against §0 (honest)

The six subtle bugs in the P1 subtle-bug pilot, judged by the realism test:

| Bug | Real-world relevance | Verdict |
|---|---|---|
| signed vs unsigned compare | sign bugs are pervasive and cause real failures | strong |
| arithmetic vs logical right shift | classic fixed-point/DSP defect | strong |
| round-half-up vs truncate | real datapath rounding error (filters/DSP) | strong |
| saturate vs wrap (clip) | essential in DSP/audio/video; wrap is a real bug | strong |
| rising-edge-only vs both-edge pulse | edge detectors everywhere; wrong-edge is real | strong |
| rotate vs shift | real (crypto/CRC) but the most "academic" of the six | acceptable, weakest |

Most are genuine datapath/control defects that separate careful engineers — they pass
the gate. `rotate_left` is the closest to "gotcha"; keep it for now but it is the
first to replace if the failure-realism review shows models miss it for non-substantive
reasons. Going forward, bug selection for the debug family is gated on the realism
test, not on "hardness" alone.

---

## 7. Proven so far (P1 study, complete)

- **Multi-fault (bug count) is NOT the lever:** 1→3 easy bugs moved the mean only
  1.000→0.993, still 8/10 saturated.
- **Subtler bugs + a pointing hint is NOT the lever either:** subtle+hint scored 0.998
  (more saturated than easy multi-fault) — the hint hands over the answer.
- **Removing the hint is the only real single-shot lever:** subtle no-hint dropped
  saturation 8/10→2/10 and reshuffled the model ranking. Keep no-hint as the default
  (also more realistic — real bugs are not labeled). But the ceiling is still ~0.98.
- **The metric mechanism works:** the fractional PASS/FAIL evaluator + deep hidden suite
  give continuous scores; the content discriminates by construction (golden=1.0,
  do-nothing buggy 0.57–0.70 through real VCS).
- **Decisive conclusion:** localized single-shot RTL debug is within frontier capability
  — even the best config sits at ~0.98 *without tools*, and would saturate with them. So
  it is **not the valuable residual.** This is the empirical proof of §3: stop polishing
  isolated single-shot bugs; go find where model+tools still fall short (P7 first).
- **Process wins:** local iverilog pre-flight catches golden bugs for free (one b04
  round-trip instead of many); the failure-realism review confirmed misses are real
  (missed −128 boundary; a fix that broke the common case; an introduced syntax error),
  not artifacts; and it surfaced a grader nit — a bundled compile-break leaves that
  module's corners untested, over-crediting hidden.

---

## 8. Proven so far (agentic study under full tools, 2026-06-18)

> **⚠️ CONFOUND DISCOVERED 2026-06-20 (see §10).** This study's "under full tools"
> premise was **false**: the agent subprocess never received the EDA tools on its PATH,
> so `bash run_public.sh` returned `spectre: command not found` and the agent could not
> run the simulator at all. The passing episodes were models that solved analytically
> *without* the tool; the failing ones spiralled hunting for it. The §8.x taxonomy and
> track verdicts below therefore measure agents **without tool feedback** and must be
> re-derived on the fixed harness (commit `ee70528`). Treat §8 as provisional pending
> the §10 re-baseline.

The full-tool harness (chat + driver + orchestrator) is built and validated against
the §3 protocol; the golden-through-the-path fairness gate earned its keep immediately
by catching a real bug — the agentic runner's `_select_evaluator` had drifted from
`cli.py` and was grading P7/P8 with the wrong evaluator (fixed). Agentic pilots then ran
on P7, P4, P6 (base), and P6 (hard-semantic, #88). Results below; they **supersede the
single-shot reading of §2 for these tracks**.

### 8.1 The agentic-competence failure taxonomy (tool-agnostic)

When a strong model fails *under tools* on a fix-task, it fails in one of three real ways
— observed across **HSPICE/Spectre (P4) AND Design Compiler (P6)**, so the modes are
tool-agnostic:

- **never-edit** — inspects and reasons but never writes a fix (commits nothing).
- **ran-out-no-edit** — exhausts the action/cost budget without committing a fix.
- **broke-deck** — edits so the deck/constraints no longer run; **tools BACKFIRE**, the
  score drops *below* the do-nothing floor (e.g. MiniMax 0.60→0.30 on a P4 probe).

Distinct from these are **infra artifacts** (API 529, killed/timed-out episodes): these
are NOT capability and MUST be excluded and cleanly re-run, never counted as a failure
(the validity gate of `benchmark-hardening-north-star`). The taxonomy is real and the
broke-deck mode is genuinely interesting (it is discrimination single-shot cannot
produce). **But** on easy/saturated tasks the incidence is low, k=1-noisy, and the
strongest models avoid all three — so *easy-task-through-the-loop is not a hard+
discriminating set* by the standing bar (no model may fully pass the set).

### 8.2 Track verdicts under tools

- **P7 SpyGlass + PrimeTime — RETIRE.** Saturated single-shot (1.00 / 0.95) and tools
  only confirm ~1.0 (probe: all 5 models PASS `pt_sta_debug_0001`). No residual.
- **P8 PnR-QA — NOT actually hard; its difficulty was a VALIDITY ARTIFACT (#85/#86).**
  §2 flagged P8 as "hard but flat" (mean 0.74, spread 0.09) and §0 warned it might be
  "hard the wrong way." The real cause is narrower and worse: 8 fields scored **0/N
  across all models and all tasks** purely because the prompt asked a prose question and
  the grader demanded one exact JSON key, so every model answered the correct value under
  a reasonable synonym key (`setup_violating_paths` vs oracle `setup_violations`, etc.).
  After an empirically-derived alias-map in the evaluator, P8 answer_match recovers
  **0.714 → 0.967** (Qwen 1.000) with no regression. **P8 comprehension is near-perfect
  → retire-candidate, not a capability gap.** Lesson for the validator: C1(golden=1.0)+
  C2(margin) cannot catch this; only a *competent-but-differently-keyed real submission*
  reveals it → the Tier-2 scan (#79) must flag "a field 0/N real models ever match" as a
  likely key/spec bug.
- **P6 constraint-debug, base (execution-breaking bugs) — not a hard set.** Agentic over
  10 single-shot-saturated tasks × 5 models: 2 models sweep 10/10; 6 real failures in the
  §8.1 taxonomy (never-edit ×2, ran-out ×1, broke-deck ×2); 2 infra artifacts excluded +
  re-run. Confirms the modes generalize; does not clear the bar.
- **P6 constraint-debug, HARD silent-semantic (#88) — 50/50 = 1.000, fully saturated.**
  Built to chase the residual: inject bugs DC **accepts silently** (wrong clock period,
  wrong/missing IO delay), state the timing spec explicitly, grade **continuously** (the
  fraction of spec properties the laundered applied SDC satisfies), and give the agent
  **no semantic oracle** (the public runner reports only DC-acceptance). The grader is
  proven-discriminating (gate: golden 1.0, do-nothing noop 0.50–0.68, margins 0.32–0.50),
  yet every model fixed every bug on every task. **Making a fully-specified mechanical
  fix-task's bug silent does not create a residual** — the models read the stated spec,
  diff it against the SDC, and correct every deviation.
- **P4 SPICE — THE LONE RESIDUAL.** Single-shot, 3/5 models run the deck but produce wrong
  numerics (public/hidden metric = 0 → 0.60: "ran but wrong number"). Under tools it fans
  out into real spread: DeepSeek 7/9 (broke-deck on two tasks), the other four 9/9. This
  is the discrimination single-shot cannot produce, and it comes from a real capability —
  analog/numeric reasoning toward a spec with **no clean lookup oracle**.

### 8.3 The convergent lesson (P1 + P6 + #88)

| Lever | Pilot | Under tools |
|---|---|---|
| bug **count** (1→3 faults) | P1 multi-fault | mean 1.000→0.993, 8/10 saturated — ✗ |
| bug **subtlety** (corner-case bugs) | P1 subtle no-hint | ~0.98 ceiling → saturates under tools — ✗ |
| bug **silence** (DC accepts, no error) | P6 hard-semantic (#88) | 50/50 = 1.000 — ✗✗ |
| wrong numerics, **no clean oracle** | P4 SPICE | DeepSeek 7/9, real spread — ✓ |

**Count, subtlety, and silence within a mechanical, fully-specified fix-task are NOT
difficulty levers under tools.** Give a frontier model an editor and a stated spec and
it will read both, diff them, and fix every deviation — regardless of how many bugs,
how subtle, or whether the tool flags them. The residual lives only where the reasoning
is **irreducible**:

- **no stated oracle** — the model must itself judge what "correct/good" is (P4 numerics);
- **noisy/ambiguous real tool output** to diagnose (a real report full of red herrings);
- **cross-flow / quantitative tradeoff** — a fix that helps one metric hurts another, with
  no single mechanical answer.

**Next direction:** deepen **P4** (the demonstrated residual) — multi-measurement
closeness scoring, ambiguous/under-specified targets, and tasks whose fix requires a
genuine tradeoff or judgment — rather than another "make-the-bug-harder" pilot, which
the table above shows is a closed branch. **[DONE — see §9.]**

---

## 9. Generalizing the residual recipe to other domains (2026-06-18, #90 → #93)

§8.3's "deepen P4" direction is now **validated**: the **P4 damping-design** track (#90)
makes the agent re-size one component (R) to satisfy **three coupled COMPETING specs**
(prop-delay, overshoot, ±2% settling) that trade via the damping ratio ζ — a real
engineering sweet-spot (ζ≈0.7), scored by continuous graded-closeness. Triple-gated
(analytic self-test 7/7 → real-Spectre calibration → agentic fairness gate) and piloted
5 models × 30 tasks: **no model sweeps** (best GLM/DeepSeek ~7/10 at the near-critical
window), models spread the full [0.33, 1.0] band (GLM/DeepSeek ≫ Qwen ≫ MiniMax/Kimi).
The first hard + discriminating residual built on purpose. **So the recipe is not a P4
quirk — this section distills it and maps where it transfers.**

### 9.1 The recipe (transferable checklist)

A task is a *constructed residual* when ALL five hold. This is the design contract:

1. **≥2 objectives that genuinely COMPETE through a shared knob** — improving one worsens
   another, so no single-metric greedy/bisection wins (the §8.3 "cross-flow tradeoff").
2. **Interior sweet-spot, not "maximize X"** — the optimum requires understanding the
   tradeoff curve, i.e. real engineering judgment, not extremization.
3. **Continuous graded-closeness score** — fraction/closeness per spec, mean over specs;
   reveals the floor / partial / optimal bands that produce model spread.
4. **No graded oracle leaked to the agent** — the agent sees realistic tool *diagnostics*
   (the waveform, the QoR/STA report) and must self-judge; the pass verdict stays hidden
   (the §3 collapse rule). Stating the *specs* is fine; the *solution* must be reasoned.
5. **Acceptance grounded in real tools, never analytic** — caps calibrated from a real
   golden run with margin (the settling-bug lesson); uncalibrated ⇒ scores 0.

If any is missing the task degrades to a mechanical fix-task, which §8.3 proved frontier
models + tools solve regardless of bug count/subtlety/silence.

### 9.2 Candidate cross-domain tracks (ranked by leverage ÷ cost ÷ feasibility-risk)

| Candidate | Tool | Competing tradeoff (shared knob) | Episode cost | Build effort | Feasibility risk | Domain reach |
|---|---|---|---|---|---|---|
| **Analog amp sizing** | Spectre/HSPICE | DC gain ↔ GBW ↔ phase-margin ↔ power (W/L, tail current, comp. cap) | low (~¥0.5, SPICE fast) | LOW (reuse P4 harness; add .ac/.stb metrics) | LOW (self-contained, no lib) | analog-adjacent (deepens P4) |
| **PrimeTime competing-timing ECO** | pt | setup-slack ↔ hold-slack (clock latency / sizing / buffer ECO), or timing ↔ ECO-budget | low-med (STA fast, multi-iter) | MED (P7 PT flow exists; new: a design where setup/hold truly tension) | LOW-MED (P7 proves PT runs; pure timing, no power lib) | **digital — true cross-domain** |
| **DC synthesis QoR closure** | dc | timing(WNS) ↔ area ↔ power (clock target, effort, retiming, ungroup) | med (compile mins × iters → ~¥1–3) | MED-HI (P6 has dc_shell plumbing but only elaborate+SDC; add compile_ultra + 3-report parse) | **MED-HI — needs a characterized .db**; GTECH-only limits it to timing↔area | digital — highest ceiling |
| Floorplan/P&R QoR | icc2/innovus | congestion ↔ timing ↔ utilization | high (10s min/iter) | HIGH | HIGH (runtime) | digital backend |

### 9.3 Recommended first target

**Lead with the PrimeTime competing-timing ECO** — it is the cheapest *digital* track
that actually answers "does the recipe generalize beyond SPICE," and it is feasible on
the **already-working P7 PrimeTime flow** with no power-library dependency. Note it is a
*different capability on the same tool* than the retired P7 PT-debug: that track was a
mechanical "fix the broken constraint so STA passes" (saturated); this one is "balance
competing setup/hold (or timing vs a cell/leakage budget) where no single mechanical fix
satisfies everything" — the §4 "method follows the capability" principle.

Sketch: a netlist + SDC where the worst setup path and a related hold path share clock
structure, so speeding up setup (downstream latency, upsizing) pushes a hold path
negative and vice-versa. The agent applies an ECO (e.g. `set_clock_latency` per pin,
or a sizing/buffer script) to drive **both** worst-setup and worst-hold slack ≥ 0.
Continuous score = graded closeness over {worst setup slack, worst hold slack} (extend
to per-path-group). Calibrate from a golden ECO that meets both with small margin so
naive single-side fixes miss. Hidden verdict; agent sees only `report_timing`.

**In parallel, the analog amp-sizing track is the near-zero-cost confirmation** that the
recipe *mechanics* (4-spec continuous closeness, real-tool calibration, tradeoff that
defeats greedy search) transfer to a richer problem — it reuses the P4 harness almost
verbatim. Worth building as the fast proof even though it deepens analog more than it
crosses domains. **DC synthesis QoR is the high-ceiling stretch goal**, gated on a
build-time check: is a characterized standard-cell `.db` available on b04? If only
GTECH, scope it to timing↔area; if a real lib exists, the full timing/area/power
tradeoff is the most recognizable "chip-engineer judgment" task in the suite.

### 9.4 Build protocol (identical to the P4-damping triple gate)

```
design the competing-tradeoff task (§9.1 contract; §0 realism test)
  -> local self-test of the measurement vs an analytic/known model (no tool spend)
  -> real-tool CALIBRATION: run golden, set caps = golden×margin, verify golden=1.0 AND
     a do-nothing/single-side baseline scores low (margin proves discrimination)
  -> agentic FAIRNESS gate (golden cp-solution = 1.0, noop ≈ floor, anti-cheat clean)
  -> costed pilot (5 models; k=1 first, pass@k only if a band looks noisy)
  -> scan_discrimination (continuous-aware, §91): hard? (no model sweeps) discriminating?
  -> RETIRE + FAILURE-REALISM gates (§5): is the spread a real capability gap?
```

The first three gates are local/cheap and have repeatedly caught real bugs before any
model spend; do not skip them. Each new track extends `CONTINUOUS_COMPONENTS` (§91) with
its score component so the dashboard reports it on the isolated continuous metric.

## 10. The agentic tool-availability confound + re-baseline (2026-06-20, #92→#94)

**What happened.** Scaling P4-damping to 30 tasks (#92) produced a surface result that
looked healthy (0/30 saturated, 26/30 discriminating) but had 4 "dead" tasks where all 5
models sat at the do-nothing floor. Adding tool-output logging to the agent driver (the
log had stored only commands, not output) exposed the cause on the very first command:

```
$ bash run_public.sh
run_public.sh: line 6: spectre: command not found
```

**Root cause.** The agent subprocess was launched with raw `os.environ`; the EnvShim tool
PATH was built *only for the grader*. So the grader could run Spectre (goldens calibrate to
1.0) while the agent it graded could **not run the simulator at all**. Every agentic run
before this (#84/#90/#92, and the §8 study) therefore measured **tool-less** agents:
passes were models that computed the answer analytically and skipped the tool; failures
were models that burned their action budget hunting for the missing binary (even chasing a
red-herring empty `/home/tongsb/spectre`). The "discrimination" was substantially
*coped-with-broken-plumbing*, not engineering — a §0 violation (difficulty from artifact).

**Fix (commit `ee70528`).** Build the EnvShim env before the agent runs and pass it to the
agent subprocess; reuse it for grading. Oracle isolation preserved (driver still strips
`EDA_TASK_PATH`). Driver also now logs each action's `rc` + output tail, and the system
prompt notes the tools are on PATH and WRITE is editable-only.

**Validation (DeepSeek probe, same 20-action budget).** `command not found` 5/5 → 0/5;
the agent runs real Spectre; 3 of 4 ex-dead tasks become solvable; the control recovered
0.39→1.0; episodes finished in 5–8 actions instead of 20 wasted (also cuts cost).

**Meta-lesson (extends §0):** *the harness must give the agent the same tool access the
grader assumes.* A standing pre-flight check belongs in the fairness gate: assert the agent
can invoke each `meta.tool` from its own shell before trusting any agentic number. And
**log tool output** — the bug was invisible until we did.

**Re-baseline result (2026-06-20, ¥118, the first *trustworthy* agentic damping number).**
15 representative tasks (incl. the 4 ex-dead + tightest) × 5 models × **k=3**, median-scored.
Mean spec **0.910** (was 0.55 tool-less), **0/15 dead**, k=1 within-cell stdev 0.118 (so the
k=3 de-noise was load-bearing). Surface "discrimination" 10/15. **But the per-model pattern
is the verdict:**

| | DeepSeek | GLM-5.1 | Kimi-K2.6 | MiniMax-M3 | Qwen3.7-Max |
|---|---|---|---|---|---|
| tasks at 1.00 | **15/15** | **15/15** | 8/15 | 7/15 | **15/15** |

Three of five models score a **perfect 1.00 across the entire set**; *no single task* pulls
DeepSeek, GLM, or Qwen below 1.0. All the spread comes from two mid-tier models (Kimi,
MiniMax) failing idiosyncratic subsets. **So the track collapsed at the frontier** — the
"everyone solves it" branch, not the "still discriminates" branch.

**Interpretation (this is the load-bearing lesson).** The prior "26/30 discriminating, mean
0.55" was *not* engineering discrimination — it was the tool-availability confound measuring
"which model copes with broken plumbing." Remove the confound and the real difficulty of the
task surfaces: **tuning a single R for ζ≈0.7 against three coupled specs is something a
frontier model with a working simulator does reliably in 5–8 iterations.** A single-knob
sweet-spot search, even with competing objectives, is not at the human-engineer frontier.

**Consequence for the north star.** Damping is now a *validated floor track* — it cleanly
separates mid-tier from frontier, and it taught us the recipe (§9.1) + caught the confound
(§10). But it produces **zero signal at the frontier**, so frontier-hard difficulty must come
from a structurally harder track. Do **not** retighten damping by narrowing the ζ tolerance:
an artificially tight acceptance band is contrived difficulty (a §0 "奇技淫巧" violation), not
real engineering — real designs have real tolerance bands. The right move is the **two-stage
Miller OTA amp-sizing track (#93)**: two knobs (ibias, cc), three-way compete (gain↔GBW↔PM),
no single sweet-spot — which is exactly why it was built. The re-baseline result is the
empirical mandate to invest there.

## 11. The amp-sizing track ALSO collapsed — sizing-with-a-simulator may be the wrong frontier (2026-06-20, #93)

We built the OTA amp-sizing track (option A), and the build gates earned their keep: the b04
smoke caught a feedback-polarity bug (golden latched at −180 dB → fixed by swapping the diff
pair inputs; golden then read a textbook 88.7 dB / 238 MHz / 64° PM), and calibration caught a
1-knob design flaw (the buggy only perturbed cc, handing the agent the golden ibias for free).
Fixed to a 2-knob buggy (over-biased + under-compensated); 20/20 calibrated cleanly; fairness
gate clean (agents invoke spectre).

**Then the cheap difficulty probe (6 tasks × 5 models × k=1, ¥11.64) collapsed at the frontier
exactly like damping:** DeepSeek 6/6, Qwen 6/6, GLM 5.99/6 — perfect. All spread was the floor
effect on the two weak models. **Two independent sizing tasks (damping 1-knob, amp 2-knob) now
both collapse once the tool works.**

**Mechanism (the load-bearing insight).** Reading DeepSeek's solve: it fixed the hardest task
(238 MHz) in 13 actions by *raising cc alone* — walking GBW from 1.2 GHz down to 295 MHz while
PM climbed 19.5°→58°; gain never moved. The "2-knob" buggy didn't force 2-knob solving because
over-biasing ibias inflated GBW so far above its (loose, golden×0.8) floor that cc-alone had all
the headroom it needed. More fundamentally: **the simulator is an equalizer.** Given exact
(gain, GBW, PM) feedback every iteration, a frontier model does closed-loop search to the
feasible region in <14 actions — adding a knob or competing specs doesn't change that. This is
intrinsic to the task *class* (continuous sizing + a simulator), not to any one design.

**The emerging conclusion (the §5 fork made concrete).** The frontier gap is probably NOT in
"tune N knobs to meet M specs with a simulator in the loop." Levers that might still make sizing
hard are suspect: tightening floors / forcing a 2-knob bind (under-biased buggy) mostly raise the
*iteration count*, so they make the task hard only by exhausting the action budget — a §0 gimmick,
not engineering. Higher-dimensional sizing (4–5 knobs) is the only non-gimmick sizing lever, and
its payoff is uncertain. The likely-real frontier gap is in task classes with **no closed-loop
search shortcut**: multi-step *diagnosis* (why won't this converge?), *structural* decisions (the
fix is a topology change, not a number), and large-context debug (signal buried in a big design).
