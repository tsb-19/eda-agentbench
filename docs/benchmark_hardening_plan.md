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
