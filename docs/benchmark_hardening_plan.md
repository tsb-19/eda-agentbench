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

## 3. Three families, three techniques (the technique is not one-size-fits-all)

### A. Debug / repair family — P1, P5, P6-constraint, P7-SpyGlass, P7-PrimeTime
**Technique:** inject a *real* corner-case defect (the kind that escapes weak
verification and bites in silicon), keep the public test on the common case only, and
make the hidden test a deep suite of corner vectors scored by fraction-passed.
**Gap probed:** does the model reason about the untested corner like a careful
engineer, or only pattern-match the visible test? (axes 1, 3, 4)
**Template:** the P1 subtle-bug pilot (`generators/p1_subtle_bugs.py`).
**Realism gate for bug selection:** every injected bug must be one a real engineer
could plausibly write and that a reviewer would flag as a true defect. Prefer bugs
grounded in real datapath/control pitfalls (sign, overflow, saturation, rounding,
reset, edge/CDC, FSM corner) over syntactic trickery.

### B. Report-QA family — P3, P6-synthesis, P8
**Technique:** replace lookup-a-number questions with multi-step *quantitative*
reasoning over the real report — compute the slack, derive which path/cell is the
offender, reason about a trade-off — with plausible distractors.
**Gap probed:** can the model analyze a real tool report like an engineer, instead of
grepping a value? (axes 2, 5, 6)
**P8 caveat:** P8 is already hard but flat. Fixing it is a *discrimination* problem,
not a difficulty problem — likely it needs less ambiguity and more graded,
competence-separating sub-questions, so a better analyst scores higher rather than
everyone landing at 0.74.

### C. Generation (P2) and numeric-sim (P4) — already discriminating
**Technique:** leave mostly as-is; tune only. P2 (write correct SVA/testbench) spreads
at 0.44; P4 (hit numeric targets within tolerance) is the best discriminator at 7/10.
Both already probe real skills. Lowest priority.

---

## 4. Priority & sequencing (by empirical saturation, cheapest-first within a tier)

1. **Prove the debug-family technique on P1** (in flight). P1 is the worst (10/10)
   and the cheapest to iterate: pure VCS + synthetic RTL, local iverilog pre-flight,
   ~¥2 per model round.
2. **Port to the other fully-saturated debug tracks:** P7-SpyGlass (10/10), then
   P6-constraint (9/10). Same generator pattern, real lint/constraint defects.
3. **QA family:** P6-synthesis (10/10), P3 (7/10) → quantitative multi-step questions.
   Separately **re-target P8** toward discrimination.
4. **Remaining debug:** P7-PrimeTime (7/10), P5 (6/10).
5. **Skip / tune only:** P2, P4.

After each track is hardened, re-derive its difficulty labels from the model data.

---

## 5. The hardening loop (data-driven, with the realism guardrail)

```
author hardened tasks   (each passes the §0 realism test)
   -> validate goldens   (scripts/validate_dataset.py: golden=1.0, margin >= 0.15)
   -> small model run    (5 models, ~¥2)
   -> scan_discrimination (saturation down? spread up? mean off the ceiling?)
   -> FAILURE-REALISM REVIEW  (read what models got wrong: is it a REAL gap?)
   -> iterate            (if a class is "hard but flat", retarget; if contrived, cut)
```

The failure-realism review is the step that keeps us honest to §0: the scan tells us
*whether* a task discriminates; only reading the failures tells us whether it
discriminates *for a reason that matters*.

---

## 6. Self-assessment of the P1 pilot bugs against §0 (honest)

The six subtle bugs in the current pilot, judged by the realism test:

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

## 7. Proven so far

- **Multi-fault (bug count) is NOT the lever:** 1→3 easy bugs moved the mean only
  1.000→0.993. Recall-style tasks stay saturated no matter how many you stack.
- **The metric mechanism works:** the fractional PASS/FAIL evaluator gives continuous
  scores; the deep hidden suite makes any incomplete fix register as a partial score.
- **The subtle-bug content discriminates by construction:** golden=1.0, do-nothing
  buggy=0.57–0.70, margins 0.27–0.38 through real VCS. Whether the *models* spread
  (the real-gap question) is what the in-flight pilot answers next.
