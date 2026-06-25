# LEC-Attribution-Bench — scoping sketch

> **Status:** scoping draft (2026-06-23). Primary next direction per user decision after the
> ExceptionDebug collapse. NOT yet a build plan — Phase 0 GO/NO-GO must pass first.
>
> **>>> PHASE-0 RESULT (2026-06-23): NO-GO for a combinational generator.** Hand-authored Phase-0
> (`experiments/lec_phase0/`) PASSED the separability criteria (golden 1.0 / symptom-lister 0.0 /
> margin 1.0 across 4 variants) — but the frontier probe showed all 4 valid models (Qwen, GLM,
> DeepSeek, MiniMax) attribute even DEEP buried + restructured + decoy cones SURGICALLY. Combinational
> LEC-attribution is frontier-easy → do NOT build the generator. See
> [[single-localization-saturation]]. A future LEC track would have to be SEQUENTIAL or large-scale,
> not combinational single-mutation.
> **Prereq cleared:** `fm_shell` confirmed + RUNNING on b04 at
> `/EDA/soft2/synopsys/fm/S-2021.06-SP5/bin/fm_shell` (Formality, same release as PrimeTime).
> Equivalence smoke PASS (2026-06-23): equivalent pair → "Verification SUCCEEDED", one-mutation pair
> → "Verification FAILED" with the failing compare point localized (see risk #2). See
> `next_gen_benchmark_directions.md` §2.3 (#9),
> memory `next-gen-benchmark-directions`, `p9-exception-debug-mechanism`.

## Why this and not more ExceptionDebug

The P9 inferred-intent probe is the last test of ExceptionDebug. Even if it survives, the
difficulty ceiling of "fix one timing exception" is low. LEC-Attribution targets a
**structurally harder source of uncertainty** that the survey reports and our own §0
tool-feedback table both rank as non-saturable:

- The Formality **counterexample is a SYMPTOM, not the root cause.** A single injected divergence
  fans out to *many* failing compare points; the agent must intersect them back to the **one**
  root cause in the logic cone — not list what the tool already prints. This is the
  Phoenix-bench bottleneck (oracle location +1.4%, but causal signal-flow understanding is the
  hard part), not exception synthesis.
- Running `fm_shell` (getting the failing points) is **necessary but not sufficient** — the same
  contract that worked for P9 grading, but now the *gap* between symptom and cause is real logic
  tracing, not a stated-vs-inferred prose distinction that a frontier model reads in one pass.

## Core mechanism (mutation-oracle, no industrial data)

1. Generator emits a small **golden** design (combinational + light sequential).
2. Produce an **equivalent reference implementation** — either `dc_shell` synthesis of the golden,
   or a generator-authored structurally-different-but-equivalent netlist (decide in Phase 0;
   hand-authored avoids a DC dependency and keeps the generator in control of truth).
3. Inject **exactly one** mutation into the impl (Mantra-style HW operators: inverted polarity,
   operator swap, off-by-one width, dropped/extra flop, wrong constant tie, swapped operands).
   The generator records the mutation **site + type** = the oracle.
4. `fm_shell`: `read` golden + mutated impl, `set_top`, `match`, `verify` → **FAILED** with failing
   compare points + a counterexample pattern.
5. **Agent task:** from the Formality report + both netlists, **attribute** the failure to the
   single root-cause site (and ideally its type) — NOT enumerate the failing compare points.

## Anti-collapse contract (what must hold, mirroring P9)

- **Symptom-lister scores low.** A baseline that echoes Formality's failing compare points (or
  names many candidate sites) must score well below a correct single-site attribution
  (golden − symptom ≥ 0.15). Precision penalised → over-listing is the new "over-constraining".
- **One cause, many symptoms.** Tasks are built so a single mutation produces ≥2 failing compare
  points, forcing intersection rather than 1:1 symptom→fix.
- **Root cause hidden in the cone.** The mutation site is not the failing point itself; it is
  upstream in the fan-in cone, so the agent must trace.
- **Forge-resistant** like P7/P9: launder the Formality report through a fresh session; the
  oracle (mutation site) lives in `hidden/`; grade compares the agent's attribution to it.

## Grading (necessary-but-not-sufficient, partial credit)

- **Primary:** root-cause localization accuracy — does the named site fall on / in the immediate
  fan-in of the true mutation? (set-match against `hidden/oracle.json`).
- **Precision:** penalise extra named sites (no shotgun attribution).
- **Optional fix dimension:** apply the agent's repair → re-run `fm_shell` → SUCCEEDED (only if
  Phase 0 shows repair is gradable without ambiguity).

## Phase 0 GO/NO-GO (cheap b04 probe — the make-or-break, do BEFORE any build)

1. **fm_shell runs equivalence:** golden vs identical → SUCCEEDED; golden vs 1-mutation → FAILED
   with a parseable failing compare point + counterexample. (binary present; run-smoke pending.)
2. **Localizability:** the failing compare point / counterexample maps back to the mutation site
   tightly enough to grade fairly — i.e., synthesis/optimization does **not** smear the divergence
   across the whole cone making attribution underdetermined. *This is the key technical risk* —
   if Formality only says "output Z differs" with no internal handle, attribution may be unfair.
3. **Discrimination floor:** a symptom-lister baseline scores low; a hand-authored correct
   attribution scores high (golden − symptom ≥ 0.15).
4. **Determinism:** same seed → same failing points + same oracle.

**Decision:** only proceed to a generator if all four hold — exactly the gate that saved spend
on P9 (where Phase 0 GO was real but the *task* was still too easy, caught later by the probe;
here the analogous risk is #2, so Phase 0 must stress counterexample granularity, not just
"does it fail").

## Known risks / open questions

- **Counterexample granularity (#2 above)** — PARTIALLY RESOLVED (b04 smoke, 2026-06-23). Formality
  localizes to the failing **compare point** (output/reg endpoint): a 2-output design with one mutation
  on `z` reported `Compare point z failed`, `y` passing, exact port `r:/WORK/top/z` — NOT a vague
  "designs differ". GOOD: real localization signal exists. CAVEAT: the failing point is the ENDPOINT,
  not the root-cause site; for shallow combinational logic they coincide (too easy). The track's whole
  difficulty depends on burying the mutation DEEP in a shared fan-in cone (and fanning one cause to
  ≥2 failing endpoints) so attribution ≠ echoing the failing-point name. Remaining Phase-0 probe:
  confirm a deep-cone mutation still yields a clean, gradable endpoint set (not a smeared whole-cone).
- **Name-mapping** golden↔impl compare points (Formality `match`) — hand-authored equivalent
  netlists with stable net names de-risk this vs DC synthesis.
- **Could still collapse** if frontier models trace small cones easily. Same answer as P9: a small
  infra-filtered frontier probe on the first templates decides — do not trust the direction until
  measured on our own gate with our own models.
- **Env weight** — Formality setup is heavier than PT; keep designs tiny (the scalar-netlist
  philosophy that worked for P9) so the cone is small but the *attribution* still non-trivial.

## Reuse from the banked harness

`BaseGenerator`, the two-phase laundering, `hidden/` oracle isolation, the shadow-artifact
anti-cheat, the `structural_validate` hook, the fairness-gate harness (perfect-agent / symptom
baseline). New: a `lec_attribution` evaluator (parse `LEC_ATTR_SCORE:` marker, same pattern as
`pt_exception_debug`) registered in BOTH dispatchers (the runner + cli — the gotcha that cost a
gate cycle on P9).
