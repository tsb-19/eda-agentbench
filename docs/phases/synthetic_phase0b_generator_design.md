# Synthetic Phase-0B — Tiny Deterministic Constraint-Drift Generator

Status: **DESIGN DRAFT (planning only).** Worktree `../eda-agentbench-synthetic-phase0a`, branch
`synthetic-phase0a` (Phase-0A committed: `ffa41f9` docs + `b957a8c` feat). Companion to
`synthetic_phase0a_design.md` (the hand-authored contract this generalizes), `synthetic_failure_taxonomy.md`
(mechanism **A**), `synthetic_eda_project_generator_plan.md`. **No generator code, no b04 runs, no commit**
in this round — this designs the generator well enough to build next and fixes the parameterization,
invariants, and acceptance gates the 5–10 variants must satisfy.

## Goal of Phase-0B (read this first — it scopes everything below)

Phase-0B turns the **one** hand-authored `syn_proj_0001` into a **tiny deterministic generator** that emits
**5–10** `acc_stage`-style timing-constraint projects of the same mechanism family:

> golden project → constraint-drift mutant → PrimeTime oracle → evaluator score

It proves the **generator contract** — *can we mass-produce fair, oracle-checkable, byte-deterministic
variants without leaking answers or breaking the Phase-0A / Phase-2 provisioning invariants?* — **not
difficulty.** Difficulty remains the **Phase-0D** question, and only becomes meaningfully measurable once a
*set* of variants exists (one hand sample cannot tell easy-task from lucky-sample). Constraint-drift stays,
per the taxonomy and our standing honesty, the **most shortcut-prone** mechanism: a model that reads
`spec.md`, recomputes the IO budget, and writes it back solves any single variant in one reconciliation
step. The durable deliverable is therefore the **reusable generator machinery** — deterministic timing
solve + fair task emission + acceptance filter — which also carries mechanism **B** (flow-handoff drift) and
the later multi-mechanism projects even if constraint-drift NO-GOs on difficulty.

**Scope lock (unchanged from the request):** one design family (`acc_stage` registered-datapath variants),
one failure mechanism (constraint drift = a wrong *value*), one oracle family (PrimeTime sign-off +
spec-equivalence marker). **No** model run, **no** k=5, **no** second mechanism, **no** scale benchmark, **no**
ICC2 / Spectre / Formality / SpyGlass, **no** push, **no** touching the other two worktrees, **no** deletion
of the `synthetic-project-generator` worktree/branch.

### Closed-form timing backbone (the critical enabler, inherited from Phase-0A)

Every variant is timed by PrimeTime against the **reused P9 scalar Liberty** (`tiny.db`: `BUFX1 = 0.10 ns`,
`DFFX1` clk→Q `0.08`, setup `0.02`). With clock period `T`, uncertainty `U`, and a buffer chain of depth `D`,
each of the three governed arc kinds has an **exact** slack — confirmed on b04 for `syn_proj_0001` to the
0.01 ns:

| Arc kind | Governed by | Slack closed form | `syn_proj_0001` (T=4.0, U=0.10) |
|---|---|---|---|
| input → reg (`din`,`en`) | `set_input_delay` `I` | `(T − U − 0.02) − I − 0.10·D` | din: `3.88 − 1.8 − 0.50 = +1.58` |
| reg → reg (internal) | clock period `T` | `(T − U − 0.10) − 0.10·D` | `3.80 − 0.50 = +3.30` |
| reg → out (`dout`) | `set_output_delay` `O` | `(T − U − O) − 0.08 − 0.10·D` | `2.92 − 1.2 = +1.72` |

The mutant drifts exactly one budget value, so exactly one arc's slack moves; all others are invariant.
`syn_proj_0001`: `O 1.2→3.2` ⇒ reg→out slack `+1.72 → −0.28` (a real, predictable PT violation) while the
worst golden slack is `+1.58`. **Because every slack is known in closed form, the generator can *solve* for
depths and a drift magnitude that guarantee golden-pass / mutant-fail with a fixed margin — no trial PT runs
needed to construct a task, only to validate it.**

---

## 1. What will be parameterized

The generator samples a parameter vector from `random.Random(seed)` and solves the backbone for feasible
depths. Each knob below is a real lever on the timing or the spec, not cosmetic.

| Parameter | Range (first increment) | Effect |
|---|---|---|
| **clock period `T`** | `{2.0, 3.0, 4.0, 5.0}` ns | sets the available-time base for all three arcs |
| **clock uncertainty `U`** | `{0.05, 0.10, 0.15}` ns | tightens every arc equally; a gradeable clock property |
| **input delay `I`** (target value) | derived, `0.6 … 2.0` ns | governs the input→reg arcs (`din`,`en`) |
| **output delay `O`** (target value) | derived, `0.6 … 2.0` ns | governs the reg→out arc (`dout`) — the usual drift target |
| **spec budget arithmetic** | 2–4 terms per IO budget | how the spec *states* `I`/`O`: `I = t_co + flight`, `O = t_su + flight`, optionally `× derate` or `+ jitter`. The generator picks the terms; the **sum is never written** (see §6) |
| **arc depths `D_in, D_reg, D_out`** | solved (see below) | calibrate each golden slack into `[+margin, comfortable]`; the drifted arc is placed so a realistic Δ pushes it `≤ −margin` |
| **mutation type within constraint drift** | `{output_delay↑, input_delay↑, uncertainty↑}` | *which* one budget value drifts. All stay single-mechanism (a wrong value), one-line diff, symptom-producing (drift tightens a governed arc into violation) |
| **drift magnitude Δ** | solved, `≥ golden_slack_X + margin` | guarantees the drifted arc crosses `0` by ≥ `margin` |

**Deferred-within-0B (documented, gated on a grader change — see §7/§8):**

| Parameter | Why deferred | Timing semantics when enabled |
|---|---|---|
| **datapath width `W`** | `[get_ports {din[*]}]` / bussed ports require the hidden grader to match port *families* (`din`, `din[0]`, `din[*]`) instead of the whole-word `din` it hardcodes today (`grade_spec.py:63,70`). | `W` drives the reg→reg / reg→out depth as a synthesized carry chain (`D ∝ ⌈log2 W⌉` or `∝ W`), making width a genuine slack lever — not just a wider port |
| **number of registered stages `S`** | adds extra reg→reg arcs and a longer runner/netlist; raises the bar that over-constraining the period breaks *more* paths | each added stage is one more internal arc that must independently meet; the IO-budget mechanism is unchanged |

The first generator increment varies **everything that needs zero hidden-grader change** — `T`, `U`, the IO
budgets and their spec decomposition, the depths, which-property-drifts, and Δ. That already yields far more
than 10 distinct, fair variants. `W`/`S` are a clean second increment once the grader is port-family-driven,
and are **not** required for the Phase-0B GO gate.

**Depth/Δ solve (deterministic, per arc).** For the drifted arc `X` with golden value `Vg` and fixed term
`F` (`0.02` for input arcs, `0.10` for reg→reg, `0.08+` for reg→out), pick
`D_X = ⌊(T − U − Vg − F − margin) / 0.10⌋` so `golden_slack_X ∈ [margin, margin + 0.10)`, then
`Δ = golden_slack_X + margin + ε` so `mutant_slack_X ≤ −margin`. Non-drifted arcs get depths giving slack
`≥ margin` with headroom. `margin = 0.05` (the P9 `_MARGIN`; keeps float jitter from flipping a verdict).
A parameter vector with no feasible integer `D_X ≥ 1` (e.g. `Vg` too close to `T`) is **rejected and
re-sampled** — a build-time guarantee, not a post-hoc hope.

---

## 2. What must remain invariant

These are **hard invariants** every generated task must satisfy; the acceptance filter (§6) discards any
sample that violates one. They are the Phase-0A §6 contract + the Phase-2 PT-provisioning lesson
(`pt-agentic-provisioning-bug`), now enforced *per generated task* rather than once by hand.

1. **Public runner never references hidden-only artifacts.** Generated `run_public.{sh,tcl}` read only
   `design_netlist.v`, `tiny.db`, `constraints.sdc` (all in `files/`). They must never name `run_hidden.*`,
   `run_signoff.tcl`, `grade_spec.py`, or `spec_truth.json`, nor print `CONSTRAINT_SPEC*`.
2. **Agent workspace is runnable without any hidden file.** `create_agent_workspace` copies only `files/`;
   `bash run_public.sh` there must produce the real PT symptom with zero missing inputs — no fabrication is
   ever necessary or tempted.
3. **Hidden oracle injected only in a fresh grading session.** `run_hidden.*`, `run_signoff.tcl`,
   `grade_spec.py`, `spec_truth.json` are overlaid by `create_evaluator_workspace` **after** the agent exits;
   the agent process can never read them.
4. **Visible spec is sufficient but not a literal answer key.** `spec.md` states the budget *terms*
   (`t_co`, `t_su`, `flight`, …) so the correct `I`/`O` is derivable, but the final value `I`/`O` (and the
   golden SDC numbers) appear **nowhere** in any visible file (§6 filter F6). The agent must reconstruct the
   arithmetic, not copy.
5. **Golden passes** through the agent's own path: `SIGNOFF_OK ∧ CONSTRAINT_SPEC_OK` ⇒ total `≈ 1.0`.
6. **Mutant fails with margin:** real PT setup violation on the drifted arc, and
   `golden.objective − mutant.objective ≥ 0.15` (CLAUDE.md C2).
7. **Masking / over-constrain gets partial, not full.** Any edit that silences the symptom without restoring
   the spec budget (loosen `T`, zero/pad a delay, add a `false_path`, inflate `U`) scores below the true fix
   and **fails the strict pass gate** (§5).

Determinism is itself an invariant: same seed ⇒ byte-identical task tree (§4).

---

## 3. Generator output layout

Identical shape to `syn_proj_0001` (the standard `files/` + `hidden/` + `solution/` split); the generator
just templates the values. **No layout change, no schema field added** — the flat `files` lists already hold
a multi-file project.

```text
tasks/p10_synthetic_project/syn_proj_<NNNN>/
  prompt.md                    # templated: ports/clock restated, mechanism-neutral wording
  metadata.json                # templated: task_id, files lists, weights, generator{} provenance (§4)
  files/                       # = the agent workspace (create_agent_workspace copies ONLY this)
    spec.md                    # AUTHORITY: budget terms only, value never stated (forbidden-to-edit)
    design.v                   # behavioural RTL (forbidden-to-edit)
    design_netlist.v           # scalar-delay timing model, depths from the solve (forbidden-to-edit)
    tiny.lib, tiny.db          # reused P9 scalar Liberty (forbidden-to-edit)
    constraints.sdc            # the MUTANT (drifted) SDC — the ONLY editable file
    run_public.sh | .tcl       # symptom runner (forbidden-to-edit)
  hidden/                      # evaluator-only (never seeded to the agent)
    run_hidden.sh | .tcl       # launder: read_sdc → write_sdc applied_hidden.sdc
    run_signoff.tcl            # fresh session → ^SIGNOFF_OK / ^SIGNOFF_FAIL
    grade_spec.py              # spec-equivalence grader → ^CONSTRAINT_SPEC_OK / SCORE / DETAIL
    spec_truth.json            # GENERATED ORACLE METADATA: intended {period,U,I,O,ports,tols,forbid_exc}
  solution/
    constraints.sdc            # the GOLDEN SDC (golden-pass gate; differs from the mutant in one line)
```

- **task_id pattern:** `syn_proj_[0-9]{4}` (already in the schema regex, both sites). Smoke/hand task keeps
  `syn_proj_0001`; the generator emits `syn_proj_0002 …` (id_start parameter, mirroring P7's `id_start`).
- **files / hidden / solution:** exactly the eight visible / five hidden / one solution files above;
  `editable = ["constraints.sdc"]`; `forbidden` = every other visible + every hidden script.
- **prompt.md / metadata.json:** templated per task; weights `constraint_spec 0.6 / signoff 0.3 /
  explanation 0.1`, evaluator `synthetic_project.SyntheticProjectEvaluator` (both unchanged from 0A).
- **generated oracle metadata:** `hidden/spec_truth.json` is the machine-readable answer key the generator
  derives from the sampled budget; it is the single source the grader checks against and is **never** placed
  in `files/`.

The hidden runner scripts and `tiny.{lib,db}` are **near-constant** across variants (they reference the fixed
top name `acc_stage`, `design_netlist.v`, `tiny.db`); the generator copies them verbatim. Only `spec.md`,
`design.v`, `design_netlist.v`, `constraints.sdc`, `solution/constraints.sdc`, `spec_truth.json`, `prompt.md`,
`metadata.json` carry per-task values.

---

## 4. Determinism and provenance

- **Seed handling.** `SyntheticProjectGenerator(BaseGenerator)` uses the inherited
  `self.rng = random.Random(seed)`; `generate_one(task_index)` draws **all** randomness from `self.rng` in a
  fixed order. No wall-clock, no `datetime.now()`, no `os.urandom`, no set-ordering leaks (sort any dict
  iteration) — so `generate_batch(count)` at a fixed seed is **byte-reproducible**. (This mirrors P7/P9 and
  is asserted by a regen-diff test, §7.)
- **Task parameter JSON.** Every sampled + solved value is recorded in `metadata.json` under the existing
  `generator{}` block (the schema already allows `generator.{script,seed,params}`), exactly as
  `syn_proj_0001` records `mutation`, `period_ns`, `expected_input/output_delay_ns`,
  `golden/mutant_worst_slack_ns`, `golden/mutant_signoff`. Phase-0B adds the full vector: `T`, `U`, the IO
  budget term decomposition, the chosen depths, `mutation_property`, `Δ`, and the closed-form
  `golden_worst_slack_ns` / `mutant_worst_slack_ns`. This block **is** the per-task provenance.
- **Golden/mutant diff expectation.** Generator guarantees (and a test asserts) that `solution/constraints.sdc`
  and `files/constraints.sdc` differ in **exactly one line** — the drifted property — and are otherwise
  byte-identical. The diff line and the from/to values are recorded in `generator.params.mutation`.
- **Exact provenance stored per task.** `metadata.generator` carries: `script` name, `seed`, `task_index`,
  the parameter vector, the predicted slacks, and a short `derivation` string per IO budget (e.g.
  `"t_su 0.90 + flight 0.30"`). `spec_truth.json` carries the same intended values + tolerances. Together
  they let any reviewer reconstruct *why* a task is the way it is and re-derive the golden by hand.

---

## 5. Scoring contract

Unchanged from Phase-0A — the generator inherits the proven evaluator and pass predicate; it does **not**
introduce new scoring.

- **`^SIGNOFF_OK` / `^SIGNOFF_FAIL`** — real PrimeTime setup sign-off (worst slack `≥ −0.001`), from the
  fresh `run_signoff.tcl` session reading the laundered SDC. Weight `signoff 0.3`.
- **`^CONSTRAINT_SPEC_OK`** — emitted by `grade_spec.py` **only** when the laundered SDC matches the spec on
  **all** properties `{period, uncertainty, input_delay(all required ports), output_delay(all required
  ports), no masking exceptions}` within tolerance. Strict gate ⇒ `constraint_spec` weight `0.6` is credited
  in full only here.
- **`^CONSTRAINT_SPEC_SCORE: <frac>`** — diagnostic fraction of properties satisfied; surfaced in `details`,
  **grants no partial credit** (the gate is binary on `_OK`).
- **Pass gate.** `total = 0.6·[spec_ok] + 0.3·[signoff_ok] + 0.1·[explanation]`; harness `passed = total ≥
  0.5`. With explanation `0.1` always present in submission mode, `total ≥ 0.5 ⟺ (SIGNOFF_OK ∧
  CONSTRAINT_SPEC_OK)` — the intended predicate the reliability layer consumes.
- **Partial / masking cases** (continuous score, but **fail** the gate):

  | Agent action | SIGNOFF | SPEC_OK | total | gate |
  |---|---|---|---|---|
  | restore the spec value (**true fix**) | OK | yes | **1.0** | **pass** |
  | leave the mutant | FAIL | no | 0.1 | fail |
  | loosen `T` / inflate `U` to clear it | OK | no (clock≠spec) | 0.4 | fail |
  | zero / pad the drifted delay to clear it | OK | no (IO≠spec) | 0.4 | fail |
  | add `set_false_path` to mask | OK | no (exception) | 0.4 | fail |
  | edit `spec.md` to match the mutant | — | — | — | **anti-cheat** (forbidden) |
  | fabricate `spec_truth.json` / `run_*` | — | — | — | **anti-cheat** (hidden-shadow) |

- **Score margin requirement.** Per task, `golden.objective − mutant.objective ≥ 0.15` (CLAUDE.md C2). By
  construction it is `0.9 − 0.0 = 0.9` (golden: spec+signoff objective `0.9`; mutant: both `0`), far above
  the floor — the acceptance filter (§6) still re-checks it on the *measured* b04 scores, never assumes it.

---

## 6. Filtering / acceptance criteria

The generator emits a **candidate**, then runs a two-tier gate; a candidate failing **any** filter is
**discarded and re-sampled** (deterministically, by advancing the rng), so the shipped set is fair by
construction. Tier-1 is tool-free (runs in the generator / `scripts/check`); Tier-2 is the b04 PT gate
(`validate_dataset.py`, run on the generated glob).

| # | Filter | Tier | Discard if … |
|---|---|---|---|
| F1 | **golden passes** | T2 (C1) | golden `total < 1.0 − eps` on real PT (closed form predicts pass; b04 confirms) |
| F2 | **mutant fails** | T2 | mutant does not produce `SIGNOFF_FAIL` (drifted arc not actually negative) |
| F3 | **margin** | T2 (C2) | `golden.objective − mutant.objective < 0.15` |
| F4 | **no hidden leak in public scripts** | T1 | any `run_public.*` / visible file references `run_hidden`, `run_signoff`, `grade_spec`, `spec_truth`, or `CONSTRAINT_SPEC` |
| F5 | **over-constrain is not full credit** | T1 | the canonical masking edits (loosen `T`, zero `O`, add `false_path`) score **full** through `grade_spec.py` — i.e. the strict gate is not actually strict for this variant (regression of the §5 table on the generated `spec_truth.json`) |
| F6 | **no literal answer leak** | T1 | the golden `I` or `O` value (or any golden SDC numeric) appears as a standalone token anywhere in `files/` (`spec.md`, RTL, netlist, runners) — the spec must state *terms*, never the sum |
| F7 | **determinism** | T1 (C3) | re-generating at the same seed is not byte-identical, or grading the golden twice differs by `≥ eps` |
| F8 | **structural validity** | T1 | `structural_validate(task_dir)` reports any issue (schema, required files, golden present) |
| F9 | **anti-cheat live** | T1 | `detect_hidden_shadows` / `detect_forbidden_modifications` do not flag a fabricated `spec_truth.json` / edited `spec.md` for this task |

F1–F3 reuse `validate_dataset.py`'s C1/C2/C3 verbatim (no new gate code). F4/F6/F9 are cheap string/AST
scans the generator runs on its own output before emitting. F5 is the §5 wrong-fix table re-run against the
*generated* truth file (the discriminator must survive every parameterization, not just the hand one). The
self-test discipline from the validator (`--self-test` flagged exactly the 5 bad P4 tasks) applies: the
generated golden must grade `≈ 1.0` through the **same** evaluator path before any model number is trusted.

---

## 7. Tests to add

Tool-free (`pytest -m "not requires_tools"`), mirroring `tests/test_synthetic_project.py` and
`tests/test_scan_discrimination.py`. The real golden-pass / mutant-fail on PT is the b04 gate (§8); these
prove the generator's *contract* locally.

1. **Deterministic generation (same seed).** `SyntheticProjectGenerator(seed=S).generate_batch(N)` twice into
   two temp dirs ⇒ byte-identical trees (recursive file hash). (F7)
2. **Different seeds → different parameterized tasks.** Seeds `S` and `S+1` differ in at least the drifted
   property / period / IO budget (not just the task_id), and neither degenerates (both solve to feasible
   depths). (§1 solve)
3. **Generated public scripts have no hidden references.** For every generated task, the F4 scan passes —
   `run_public.*` and all `files/` reference only agent-workspace files. (F4)
4. **Generated workspace runnable without hidden files.** `create_agent_workspace` on a generated task
   contains every file `run_public.tcl` reads, and no hidden artifact. (Invariant 2 / F-provisioning, reusing
   the `test_synthetic_project.py::test_public_flow_runnable_in_agent_workspace` pattern.)
5. **Golden/mutant score separation.** Using the **closed-form-predicted** marker logs (golden →
   `SIGNOFF_OK`+`CONSTRAINT_SPEC_OK`; mutant → `SIGNOFF_FAIL`+`SPEC_SCORE<1`), the real evaluator scores
   golden `1.0` / mutant `≤ 0.1`, margin `≥ 0.15`; and a one-line diff between `solution/` and `files/`
   `constraints.sdc`. (F1–F3 predicted; F-diff)
6. **Masking / over-constrain not full credit.** For every generated `spec_truth.json`, the §5 masking matrix
   (loosen `T`, zero/pad `O`, `false_path`, drift `I`) graded by the task's own `grade_spec.py` yields
   `full=False, frac<1.0`. (F5)
7. **Generated inventory / schema validation.** Every generated `metadata.json` passes `validate_metadata`
   (task_id regex, weights sum 1.0, editable⊆visible, hidden∩visible=∅) and `structural_validate`; the track
   stays `p10_synthetic_project`. (F8)
8. **No literal answer leak.** For every generated task, the golden `I`/`O` value is absent as a standalone
   token from all `files/`. (F6)

`scripts/check` regenerates `reports/*` (via `export_benchmark_summary.py`) to include the new task count,
exactly as in Phase-0A.

---

## 8. Phase-0B implementation plan

**Files to create:**

- `generators/p10_synthetic_project_gen.py` — `SyntheticProjectGenerator(BaseGenerator)`:
  - `__init__(self, seed, output_dir, id_start=2)` (mirrors P7).
  - timing-solve helpers (`_solve_depths`, `_solve_drift`) implementing §1's closed form + reject-and-resample.
  - templating helpers (`_spec_md`, `_netlist`, `_golden_sdc`, `_mutant_sdc`, `_spec_truth`, `_prompt`,
    `_metadata`) that emit byte-stable text from the parameter vector.
  - `generate_one(task_index)` writes the §3 layout; copies `tiny.{lib,db}` from
    `generators/assets/p10_synthetic_project/` (a copy of, or shared path to, the P9 asset) and the
    near-constant `run_public.*` / `run_hidden.*` / `run_signoff.tcl`.
- `generators/assets/p10_synthetic_project/{tiny.lib,tiny.db}` — copy of the reused P9 asset (or a documented
  shared path), so the generator has a stable local asset root like every other track.
- `scripts/generate_synthetic_project_tasks.py` — thin driver (mirrors
  `scripts/generate_p7_primetime_sta_debug_tasks.py`): construct the generator, `generate_batch(count)` into
  `tasks/p10_synthetic_project/`, print the created ids. **CLI entry point:**
  `python3 scripts/generate_synthetic_project_tasks.py --count 8 --seed 42`.
- `tests/test_synthetic_project_gen.py` — the §7 tests.

**Files to modify (minimal, documented):**

- `tasks/p10_synthetic_project/syn_proj_0001/hidden/grade_spec.py` — **only if** the deferred width/port
  parameters are enabled: make `parse_applied_sdc` take the required port lists (driven by `spec_truth.json`)
  instead of the hardcoded `for p in ("din","en")` / `("dout",)` (lines 63/70). For the first increment
  (ports stay `{din,en,dout}`) **no change is needed** — `spec_truth.json` already carries `ports`, and the
  generator simply writes the same fixed port set. (If touched, it is one shared-grader edit, documented per
  CLAUDE.md.)
- `reports/*` — regenerated by `scripts/check` to reflect the new task count (generated artifact, as in 0A).
- **No change** to `schema.py` (regex + enum already admit the track/id), `cli.py` (evaluator dispatch
  already wired), or `synthetic_project.py` (evaluator unchanged).

**How many tasks first.** Generate **8** (`syn_proj_0002 … syn_proj_0009`) — comfortably in the 5–10 GO band,
enough spread across `T` × mutation-property × budget to make a later Phase-0D probe non-degenerate, small
enough to b04-gate cheaply. The hand `syn_proj_0001` stays as the smoke/reference.

**Expected `scripts/check` behavior.** Tool-free: structural validation count rises (`2893 → 2901`),
`p10_synthetic_project` shows `9/9` valid, all `pytest -m "not requires_tools"` green (the §7 generator tests
+ the existing 17 contract tests), `reports/*` regenerated. No b04 needed for `scripts/check`.

**Expected PrimeTime validation command (b04 only; `/tmp` or `~/Desktop/tsb`, clean up, no internet/pip).**
The authoritative golden-pass / mutant-fail / margin gate over the generated set:

```bash
python3 scripts/validate_dataset.py --tasks-root tasks/p10_synthetic_project \
    --glob 'syn_proj_000[2-9]' --check-determinism --concurrency 2
```

This greps the same C1 (golden `≈1.0`) / C2 (margin `≥0.15`) / C3 (determinism) gate the whole benchmark
uses, through the real `pt_shell`, on every generated task — the fairness gate, applied to the batch.

**Runtime / cost estimate.** Generation is pure Python (sub-second, **¥0** gateway). The b04 gate is PT-only:
~2 PT sessions/task (launder+signoff) × golden+mutant ≈ 4 license-time invocations/task × 8 ≈ a couple of
minutes of seat time, **effectively ¥0** of the gateway budget (no model runs in Phase-0B). The model probe
(Phase-0D, separate) is where gateway spend begins — at the Phase-2 anchor (~¥0.59/episode), 3 models × 8
tasks × k=3 ≈ **¥43**, well within ¥1000.

---

## 9. GO / NO-GO

Phase-0B gates the **generator contract**; Phase-0D (separate, after) gates **difficulty**. Keep them
distinct so a "too easy" verdict never discards the reusable generator.

**Phase-0B GO** (proceed toward Phase-0D, and the generator becomes the mechanism-A factory) requires the
generator to emit **at least 5** tasks that are **all**:

1. **Deterministic** — byte-identical on regeneration at the same seed (test 1 / F7).
2. **Structurally valid** — `structural_validate` + `validate_metadata` clean; track/id correct (test 7 / F8).
3. **PT-validated on b04** — golden `total ≈ 1.0` (C1), mutant `SIGNOFF_FAIL`, `golden − mutant objective ≥
   0.15` (C2), determinism (C3) — the `validate_dataset.py` command above passes on the generated glob.
4. **Masking-resistant** — the §5 wrong-fix matrix fails the strict gate for **every** generated task
   (test 6 / F5); no over-constrain reaches full credit.
5. **Leak-free & fair** — no hidden reference in public scripts (F4), no golden value as a visible literal
   (F6), anti-cheat live (F9); provisioning invariants §2 hold per task.

**NO-GO / stop and reconsider** if any of:

- The generator becomes a **brittle task copier** — it can only re-skin `syn_proj_0001` (e.g. only the period
  varies, every variant has the same budget/depths), so the "set" is one task wearing 8 hats and a Phase-0D
  probe would still measure a single sample.
- **Answers leak** — F6 cannot be satisfied without making the spec un-derivable (the budget decomposition
  always reduces to a single copyable literal), i.e. the mechanism can't be both solvable-from-spec and
  not-trivially-copyable at generator scale.
- **Provisioning invariants cannot be held automatically** — some parameterization reintroduces the Phase-2
  hidden-netlist class of bug or breaks the strict pass predicate, and the filter can't catch it cheaply.

Record the verdict as a memory entry + one-line status (as every prior direction was), so the next cycle —
Phase-0D probe, or mechanism-B on the same machinery — inherits the evidence. **Reminder: even a GO here is
still "contract proven at scale," not difficulty. Constraint-drift's shortcut risk is unchanged; Phase-0D is
where a real model finally meets these tasks.**

---

## Guardrails (restated, unchanged)

Cheap-probe-before-build; reuse don't fork; EDA tools **only on b04** (`/tmp` or `~/Desktop/tsb`, clean up,
no internet/pip); shim stays outside the repo; never commit credentials or raw tool outputs; never modify
hidden/oracle/forbidden/scoring to manufacture a score; grade the golden through the same path before
trusting any number; minimal + documented edits to any shared file (`grade_spec.py` only if width/ports are
enabled); ¥1000 total budget — Phase-0B generation + b04 gate are effectively free, the model spend is the
later 0D probe; do not touch the other two worktrees or the reliability directories; **no generator code in
this round, no b04 runs, no model eval, no k=5, no second mechanism, no commit/push** without explicit
instruction.
