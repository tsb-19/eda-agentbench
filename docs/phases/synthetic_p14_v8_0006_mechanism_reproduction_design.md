# p14 v8 — workflow_handoff_0009 design: reproducing the 0006 axis-binding mechanism

**Design-only document.** No code, no tasks, no models, no commits. The goal is to **isolate and reproduce
the exact mechanism that made `workflow_handoff_0006` produce a frontier-model split** (Qwen 8/8; DeepSeek
6/8 with two byte-confirmed axis-binding failures), which `0007` and `0008` both failed to reproduce. This
document defines a controlled mini-family (`0009a`–`0009d`) and the success criteria that distinguish "one
task DeepSeek happened to fail" from "a real, repeatable capability mechanism."

**Central question:** *What exactly in 0006 caused DeepSeek's axis-binding failures, and how can we reproduce
that mechanism in a new task family?*

---

## 1. Motivation

- **0006 produced the first positive frontier-model split** in the p14 ladder: Qwen3.7-Max 8/8 (robust
  saturation, 0 wrong assignments) vs DeepSeek-V4-Pro 6/8 with **two byte-confirmed wrong global
  assignments** on a real capability axis (joint constraint inference / axis-value binding). This is the
  single durable positive result across p10→p14.
- **0007 and 0008 were built as ablations** to explain *why* 0006 was hard, by varying exactly one design
  axis at a time. Both **failed to reproduce the split**:
  - `0007` published the typed-axis schema (`axis_schema.json`) → **saturated** (Qwen 3/3, DeepSeek 3/3, 0
    wrong assignments).
  - `0008` hid the schema (kept the typed-binding oracle) → **still saturated on axis-binding capability**
    (Qwen 3/3, DeepSeek 3/3 correct typed assignment; the single DeepSeek non-pass was a byte-confirmed
    *protocol/chain* failure, not an axis-binding error).
- **Therefore the real mechanism is not simply "typed schema visibility."** Toggling schema publication
  (0007) and schema hiding (0008) both saturate; yet 0006 — also an implicit tuple with report labels —
  produced the failures. The 0006 difficulty must reside in a **different, narrower variable** that 0007 and
  0008 did not preserve.
- **We must isolate the 0006 mechanism before claiming a broad benchmark contribution.** A single hand-built
  positive task instance is a *discovery*, not a result: with n=1 we cannot separate "this task family is
  genuinely discriminative" from "this one task happened to mislead one model once." The path to a defensible
  claim runs through **mechanistic reproduction under a controlled ablation**, not through more k-runs on the
  existing tasks.

---

## 2. Current evidence

| task | design | Qwen3.7-Max | DeepSeek-V4-Pro | verdict |
|---|---|---|---|---|
| **0006** | implicit tuple, canonical `scenario`/`corner` labels, **no glossary / no public summary / no coverage fact / no PVT-leak**, decoys embed conflicting values in headers vs bodies | **8/8** (k=3+k=5), 0 wrong | **6/8**, **2 byte-confirmed axis-binding failures** | **positive frontier split** |
| **0007** | typed-binding oracle **+ published `axis_schema.json`** | 3/3 | 3/3, 0 wrong | **saturated** (binding → vocabulary lookup) |
| **0008** | typed-binding oracle, schema hidden, but **glossary.md + `public_check_summary.json` (coverage fact) + spec binding hint + PVT-leak** all present | 3/3 | 3/3 correct assignment (1 protocol/chain non-pass) | **saturated on axis-binding capability** |

- **Conclusion: 0006 is the only positive mechanism observed so far.** 0007 and 0008 are null results on
  the axis-binding capability axis. The combined k across both ablations (6 DeepSeek episodes, 0 axis-binding
  failures) plus the identical saturation of the two polar-opposite designs is strong evidence that
  *schema visibility* is not the causal variable.
- **Small-n caveat (stated honestly):** DeepSeek's 0006 axis-binding rate was ~25% (2/8). 0 axis-binding
  failures in 3 trials on 0008 is consistent with a residual rate (P(0/3 | 25%) ≈ 0.42). So 0008's null
  result is *qualitatively* established but not *quantitatively* decisive at k=3 — which is exactly why
  reproduction must come from a **mechanistically-matched design validated by ablation**, not from larger k
  on the wrong design.

---

## 3. Failure signatures from 0006

The authority tuple (hidden truth) is `global_authority = [netlist_v2.v, clk_main, slow, func]`, with typed
axis domains `scenario ∈ {slow, typ, fast}` and `corner ∈ {func, test, lowpower}`. **Note the type
structure: `typ` is a *scenario* value and `func` is a *corner* value.** Without a glossary/schema, nothing
in 0006 states this — a fact central to both failures.

### Failure A — value-swap / axis-binding error
- **Submitted:** `scenario=func, corner=typ`.
- **Expected:** `scenario=slow, corner=func`.
- **Type reading:** `func` (a *corner*-axis value) placed in the *scenario* slot; `typ` (a *scenario*-axis
  value) placed in the *corner* slot. This is a **pure cross-axis value swap**.
- **Constraint check:** C1 (netlist=netlist_v2 ✓) + C2 (clock=clk_main ✓) satisfied; **C3 violated** (the
  signoff pair is (slow,func), not (func,typ)).
- **Score:** PrimeTime signoff was **GREEN** (the tiny.db report body is corner-independent, so a mis-typed
  but otherwise-correct package still signs off) → rejected by the typed-binding oracle → **0.20**
  (signoff + explanation only, `EVIDENCE_OK` absent).
- **Why it's a binding error, not a guess:** `func`/`typ` are not random strings — they are the *other*
  axis's valid values. The model produced a **type-plausible mis-binding**, exactly the regime where local
  reading looks consistent but global type semantics are wrong.

### Failure B — axis-binding + value invention + clock-alias error
- **Submitted:** `scenario=func, corner=slow_1.0V_125C, clock=clk`.
- **Expected:** `scenario=slow, corner=func, clock=clk_main`.
- **Type reading:** (i) same `func`-in-scenario-slot swap as Failure A; (ii) **value invention** —
  `slow_1.0V_125C` is a **PVT descriptor** (`<process>_<voltage>_<temperature>`) substituted for the corner
  value (it characterizes a pair but is not a valid `corner` member); (iii) **clock-alias error** — `clk`
  is an invented alias (the real clock axis is `{clk_main, clk_old}`; `clk` is neither and yields zero
  coverage).
- **Constraint check:** C2 also violated (clock alias → zero intended-clock coverage) → PrimeTime signoff
  **FAILED** → **0.10**.
- **Why it's the same family:** the binding error is identical to Failure A, compounded by a PVT-bundle
  hallucination and a clock-name invention. Both failures share the root: **mis-resolving which physical
  token binds to which logical axis.**

### Common pattern (the signature to reproduce)
- **Values are plausible in nearby semantic contexts.** `func`, `typ`, and PVT descriptors all *look* like
  signoff/PVT vocabulary, so a swapped or invented binding is locally invisible — there is no type signal
  in 0006 to flag `func`∉scenario-axis.
- **The model binds labels to the wrong axis.** The failure is a *semantic-role binding* error (which value
  belongs on the scenario axis vs the corner axis), not an arithmetic, lookup, or protocol error.
- **The evidence chain can be internally consistent while semantically wrong.** Failure A signs off GREEN
  with a valid two-stage digest chain — the only thing wrong is the axis assignment. This is exactly the
  "signoff-green-but-mis-typed" case the typed oracle was built to reject.
- **Failure happens despite no protocol / infra / oracle issue.** Byte-confirmed from preserved
  `flow_config` + hashes: not a broken chain, not a timeout, not a budget exhaustion, not an oracle
  false-negative. It is a clean capability failure.

### A concrete artifact observation (grounds the causal reading)
The exact swapped pair DeepSeek submitted in Failure A (`scenario=func corner=typ`) is present **verbatim
inside the report *bodies*** of `report_B_stale_netlist.rpt` and `report_C_wrong_clock.rpt` — the report
sections that look like genuine PrimeTime evidence — while the *correct* pair (`slow/func`) appears in the
report headers and in `report_A`'s body. So 0006 does not merely "have wrong decoys": it **embeds the
swapped binding inside genuine-looking evidence lines, alongside the correct values, with no anchor saying
which is authoritative.** A model that reads a report body and commits gets Failure A for free. (This is an
artifact-level fact; the exact line DeepSeek read is inference, but the value-match is exact.)

---

## 4. Hypotheses for why 0006 worked (and what each survives)

| id | hypothesis | survives 0007/0008? | assessment |
|---|---|---|---|
| **H1** | **Ambiguous report-label semantics** — report labels/roles in 0006 are not explicit enough, so scenario/corner roles must be resolved, not read. | **partly** | Directionally plausible, but needs sharpening: 0006 actually used *canonical* labels (`scenario=`/`corner=`), while 0008 used *non-canonical* ones (`op_point`/`mode`) and still saturated. So "non-canonical labels" is not the cause. The real ambiguity is **conflicting values under those labels + no type anchor** (see H3/H4). |
| **H2** | **No clean public schema or glossary** — values must be inferred from inconsistent reports, not read from a schema/glossary. | **yes** | Strong. 0008 added a glossary + `public_check_summary` (coverage fact) + spec binding hint + PVT-leak; 0006 had **none**. This is a leading candidate — but it is a *negative* condition (absence of help); alone it under-specifies *what* must be inferred. |
| **H3** | **Authority tuple implicit but not scaffolded** — 0006 gives enough clues for a unique solution but no inference *structure* (no coverage fact, no PVT-leak, no pairwise summary) that collapses binding into a near-lookup. | **yes** | **Strongest framing.** This is the precise difference: 0008's "hidden schema" was scaffolded by four independent anchors (glossary, coverage fact, spec hint, PVT notation) that together act as a de-facto schema; 0006 had zero anchors, forcing pure constraint intersection. |
| **H4** | **Decoy structure induces axis swaps** — decoys place correct values in locally-plausible but globally-wrong positions, and embed the swapped pair inside evidence bodies, so a local/body read mis-binds. | **yes** | Strong for the *specific* Failure A: the swapped pair is embedded in report bodies. 0008's swap, by contrast, was isolated and *labeled* (`report_A_context_swap`, called out by `public_check_summary`). 0006's swap is **distributed and unlabeled**. |
| **H5** | **Stage-chain/provenance pressure causes premature commitment** — the two-stage ordered chain makes the model commit to a plausible package before reconciling all axes. | **no** | Weak as a primary cause: 0007 and 0008 have the identical two-stage chain and did not fail on binding. May be a *contributing* amplifier (commit pressure), but not the mechanism. |
| **H6** | **Prompt/report wording specifically misleads** — not the abstract structure, but exact labels/phrasing (e.g., the header-vs-body contradiction, the word choices) caused the failure. | **untested** | Plausible and *entangled* with H1/H4 — the body-embedding (H4) is a wording-level fact. Cannot be ruled out without an ablation that holds structure constant and varies wording. This is exactly what `0009b`/`0009d` test. |

**Leading composite hypothesis (what to reproduce):** **H3 ∧ H4 (and likely H6).** The 0006 difficulty is an
**interaction effect**: an implicit tuple presented with **no inference anchor** (H3) **and** decoys that
**embed the swapped/invented values inside genuine-looking report bodies under ambiguous role labels** (H4),
so that axis-role resolution requires cross-source conflict intersection rather than any single-file read.
H2 is the necessary condition for H3; H1/H6 are entangled surface forms of H4.

---

## 5. What 0007 and 0008 ruled out

- **Full schema visibility removes difficulty (0007).** Publishing `axis_schema.json` (closed vocabularies +
  PVT mapping + type rules) converted typed inference into **vocabulary lookup**: once `scenario_axis
  {slow,typ,fast}` and `corner_axis {func,test,lowpower}` were readable, the `func`/`typ` swap became
  trivially detectable and avoidable.
- **Hiding the schema alone does *not* restore difficulty (0008).** 0008 shipped no `axis_schema.json` yet
  still saturated on axis-binding capability — because it shipped **four other anchors** that together act
  as a de-facto schema:
  1. `glossary.md` stating `op_point`/`mode` are disjoint typed axes and a PVT descriptor is never a valid
     value;
  2. `public_check_summary.json` handing over the **coverage fact** (`intended_clock_coverage:
     {clk_main:1, clk_old:0, clk:0}`) — directly revealing the clock;
  3. `spec.md` "What correct looks like" mapping **op_point→scenario, mode→corner**;
  4. PVT notation `slow_1.0V_125C` **leaking** the scenario token `slow`.
  A domain-aware scripted solver recovers the tuple from visible-only — and so did DeepSeek.
- **The typed-binding oracle alone does not create difficulty.** It is a valid, reusable *hardening*
  mechanism (signoff-green-but-mis-typed → 0.20), but 0008 had it and still saturated on capability.
- **The fairness/inferrability scaffold can itself collapse difficulty.** 0008's anchors were added to
  *prove* human-inferrability (the gate), but they made the task a clean solver path — which a strong model
  also follows. Fairness and difficulty pulled against each other.
- **Therefore future design must reproduce the 0006 ambiguous report-label interaction, not just hide the
  schema.** The variable to control is the **presence/absence of inference anchors and the embedding of
  swapped values in evidence bodies** — not schema publication per se.

---

## 6. Proposed 0009 design principle

- **Recreate 0006-style ambiguity deliberately and minimally.** Ship an implicit tuple with **no glossary,
  no `public_check_summary`, no coverage fact, no PVT-leak, no spec binding hint** — the four anchors that
  collapsed 0008 must all be absent.
- **Preserve human-inferrability through domain-meaningful (not arbitrary) role resolution.** The binding
  must be recoverable by a *chip engineer* using domain knowledge, not by a regex over a leaked token. The
  fairness gate is "a domain expert can resolve it," **not** "a blind scripted solver can regex it."
- **Use report labels whose semantic roles are inferable only by resolving conflicts across multiple
  artifacts.** Specifically: **overloaded labels** — the *same* physical label name is used for *different*
  logical axes in different reports (e.g., `mode` means corner in one report, `corner` means a PVT bundle
  in another). The agent cannot grep a single label; it must resolve, per-source, what each label refers
  to.
- **Embed the swapped / invented values inside genuine-looking report bodies**, exactly as 0006 did — so a
  local/body read yields a plausible-but-wrong binding, and only cross-source intersection rejects it.
- **Keep the typed-binding oracle hidden** (it scores; it is not shipped as a schema). It rejects
  signoff-green-but-mis-typed packages, which is the precise failure signature to detect.
- **Make locally-plausible wrong bindings possible** — wrong values must be the *other* axis's valid members
  (so a swap is type-plausible in absence of a glossary).
- **Ensure exactly one global assignment passes** (offline-proven uniqueness, as in 0006's 36→1) so no
  majority-vote or single-axis fix can pass.

---

## 7. Candidate 0009 task structure

`workflow_handoff_0009` = **implicit tuple + typed-binding oracle + ambiguous/overloaded report-label
semantics + body-embedded swapped values + no axis_schema + no glossary (or ultra-sparse) + no helpful
public summary.** Same `acc_stage` substrate, same two-stage evidence chain, same hidden uniqueness prover
(reused `enumerate_constraint_graph` machinery). Global authority tuple unchanged:
`[netlist_v2.v, clk_main, slow, func]`.

### The overloaded-label mechanism (the new variable)
Different reports use **the same label name for a different axis**, forcing per-source semantic-role
resolution:

- **`report_A_mode_as_corner.rpt`** — uses **`mode`** to mean **corner**. Body carries the corner value
  (`func`) under label `mode=`, plus the right netlist (`netlist_v2.v`) and clock (`clk_main`).
  *Authoritative for: netlist, clock, corner (via `mode`).*
- **`report_B_corner_as_pvt.rpt`** — uses **`corner`** to mean a **PVT bundle**. Body carries
  `corner=slow_1.0V_125C`, a PVT descriptor whose process token `slow` **is** the scenario value (but the
  label `corner` is a trap — it is not the func/test/lowpower corner axis). Stale netlist (`netlist_v1.v`).
  *Authoritative for: scenario (extract `slow` from the PVT bundle), and nothing else.*
- **`report_C_scenario_as_view.rpt`** — uses **`scenario`** to mean a **timing view name** (a non-canonical
  string, e.g. `view_setup_max`), with a wrong clock alias (`clk`). *A pure distractor on the
  scenario/clock axes; right netlist.*
- **`evidence_D_role_mismatch.json`** — a digest-valid two-stage chain whose internal `scenario`/`corner`
  fields are **role-swapped** (the swap embedded in a manifest that otherwise looks fresh).
- **`prev_signoff.log`** — recent, plausible, non-authoritative (gitignored `*.log`, consistent with
  0003–0008).

### Artifacts (public/visible)
- `spec.md` — minimal terminology; states the axes exist and are disjoint but does **not** give a
  value-to-axis table, does **not** name the clock, does **not** give a coverage fact, does **not** hint
  op_point→scenario.
- `handoff_manifest.json` — **partial authority only**: declares the netlist family + interface (C1) and
  design intent; omits clock/scenario/corner values (as in 0006).
- `flow_config.json` — the **mutant**: carries the value-swap on the typed axes (e.g.
  `scenario=func corner=typ`), to be repaired.
- `constraints.sdc` — frozen; weakening forbidden.
- `report_A/B/C` — as above (overloaded labels + body-embedded swap).
- `evidence_D_role_mismatch.json` — fresh-looking chain, role-swapped inside.
- `public_check_summary.json` — **symptoms only** (e.g. "report_A `mode` disagrees with report_B `corner`
  on the signoff pair"; "report_C clock alias yields zero coverage"). It must **report pairwise symptoms,
  never the pairwise resolution, never the clock coverage fact as a clean mapping**. (Contrast: 0008's
  summary handed over `intended_clock_coverage` as a clean dict — that anchor is forbidden here.)
- **No `axis_schema.json`.**
- **No `glossary.md`** (or, only if the fairness gate demands it, an *ultra-sparse* one that defines
  vocabulary without giving the value-to-axis mapping — and even then it must not contain a PVT-leak or a
  disjoint-axis statement strong enough to collapse the binding; this is the riskiest knob and the
  ablation `0009c` exists to measure it).

### Hidden (unchanged from 0006/0008 architecture)
- `grade_workflow.py` (shared `_GRADE_WORKFLOW`, byte-synced across all tasks), `handoff_truth.json`,
  trusted generators, launder/run scripts, `regen_reference.sh`. The typed-binding echecks
  (`typed_scenario_in_scenario_axis`, `typed_corner_in_corner_axis`, `typed_clock_identity`) fold into the
  `EVIDENCE_OK` master gate exactly as in 0007/0008.

---

## 8. Controlled ablation plan

A **mini-family, not a single task**, so the mechanism can be isolated by holding structure constant and
varying one presentation factor at a time. All variants share the same hidden authority tuple, the same
typed-binding oracle, the same uniqueness proof, and the same two-stage chain. Only the *public
presentation* differs.

| variant | presentation | what it tests | prediction if hypothesis H3∧H4 holds |
|---|---|---|---|
| **0009a** | **Closest reproduction of 0006** + the typed oracle added. Overloaded labels (`mode`/`corner`/`scenario` mean different axes per report), body-embedded swap, **no glossary, no public coverage fact, no spec binding hint, no PVT-leak**. | Does the 0006-style interaction reproduce the failure family? | **DeepSeek axis-binding failures reappear**; Qwen saturates. |
| **0009b** | Same as 0009a but with **canonical, unambiguous labels** (each report uses the label that *means* its axis: `corner` means corner, `scenario` means scenario, `mode` removed). | Is **label overload / role ambiguity** the causal factor (H1/H4/H6)? | **Saturates** (removing ambiguity removes the failure) — confirming the mechanism is role-binding, not the decoy count. |
| **0009c** | Same as 0009a but with a **public glossary** (value-to-axis hints / disjoint-axis statement), still no `axis_schema`. | Is **absence of an inference anchor** causal (H2/H3)? | **Saturates** if the glossary is strong enough to act as a de-facto schema (as 0008 showed) — confirming anchors, not just schema files, drive difficulty. |
| **0009d** | Same as 0009a but with **report labels shuffled** (which report carries which overloaded label is randomized; the overload pattern is preserved). | Is it the **specific** label↔axis pairing or **overload-in-general** that bites? | **Preserves difficulty** if overload-in-general is the mechanism; difficulty changes only if a specific pairing matters (which would weaken the claim). |

**Ablation logic:** 0009a is the reproduction attempt. 0009b/0009c are the *negative controls* — each
removes exactly one factor that the hypothesis says is causal; if difficulty vanishes, that factor is
implicated. 0009d is the *randomization control* — it checks the result is not an artifact of one specific
wording. The decisive comparison is **0009a vs 0009b**: same structure, same oracle, same uniqueness, only
the label ambiguity differs.

**Minimum viable experiment:** implement **0009a and 0009b first** (the controlled pair). Run 0009c/0009d
only if 0009a reproduces the failure, to pin the causal factor. Do **not** build a large parameterized
generator before the mechanism is confirmed on the hand-built pair.

---

## 9. Acceptance filters (gate before any model probe)

Every variant must pass all of these on real PrimeTime (b04 via the transparent shim) before a single model
runs. These are the same hardening bar as 0007/0008, restated for the 0009 mechanism:

- **Golden = 1.0** on the true authority tuple.
- **All wrong bindings fail below pass.**
- **Signoff-green-but-semantically-wrong fails** — a package that PrimeTime signs off GREEN but carries the
  value-swap / PVT-substitution / role-mismatch scores ≤ 0.20 (`EVIDENCE_OK` absent,
  `MISTYPED_BINDING_REJECTED`). *This is the decisive row: it proves the typed oracle, not signoff, rejects
  the exact failure signature.*
- **Evidence-chain fresh-but-wrong-role fails** — `evidence_D_role_mismatch.json` (digest-valid, role-swapped)
  scores below pass; `upstream_evidence_digest` / input-hash binding must reject it.
- **Final-state-only fails** — correct `stage2_summary.json` without the fresh ordered stage1 → below pass.
- **Stage2-only fails** — stage2 built from a stale/typed-wrong stage1 → below pass.
- **Hand-edited evidence fails** — report-body digest mismatch → below pass.
- **Edit-manifest-down / forbidden edit fails** — modifying netlists/library/manifest/schema/decoys/grader/
  truth, or weakening `constraints.sdc` → zeroed by the anti-cheat forbidden-edit check.
- **No hidden leak** — scan all public files: no `handoff_truth`, no `grade_workflow`, no `axis_schema`, no
  netlist/library content, no API key / `.env`, no secret. (Filename + content scan, as in 0007/0008.)
- **Exactly one satisfying assignment** — `enumerate_constraint_graph` proves uniqueness (target 36→1 or
  294→1 depending on axis-domain sizing); `exactly_one=true`, `unique_matches_expected=true`.
- **Human-inferrability check passes** — a *domain-aware* human-resolution argument recovers the tuple from
  public artifacts (e.g. "report_A's `mode=func` is the signoff *corner* because `func` is a functional
  signoff mode; report_B's `corner=slow_1.0V_125C` is a PVT bundle whose process token `slow` is the
  *scenario*"). The gate is **domain reasoning**, not a blind regex solver. (If a blind solver trivially
  recovers it, the variant is too easy — cf. 0008.)
- **No single visible file gives the full tuple or the full value-to-axis mapping.** The tuple is the
  intersection of reports; the mapping is resolved per-source.

---

## 10. Mechanism success criteria (the key section)

**A successful 0009 mechanism is NOT merely "one task DeepSeek fails."** A single-task failure is
indistinguishable from noise at n=3 and proves nothing about a benchmark contribution. Success requires
**reproduction under control**:

- **(R1) Repetition OR (R2) controlled ablation — at least one must hold:**
  - **R1 — repeated failure family across ≥2 variants.** The same *family* of axis-binding failure
    (value-swap, PVT-substitution, role-mismatch, clock-alias) appears in ≥2 of {0009a, 0009d} (the two
    overloaded-label variants). One task failing twice-independently is far stronger than one task failing
    once.
  - **R2 — a clean controlled ablation.** 0009a reproduces the failure family **and** 0009b (canonical
    labels, identical structure/oracle/uniqueness) **saturates**. The delta between a and b, with
    everything else held constant, is the causal evidence that **label/role ambiguity** is the mechanism.
- **Every failure must be byte-confirmed** (from preserved final workspace: `flow_config.json` +
  `evidence_manifest.json` + re-run `EVIDENCE_DETAIL`), and classified as one of:
  - **wrong axis binding** (value from axis X placed in axis Y's slot),
  - **wrong role assignment** (overloaded label bound to the wrong logical axis),
  - **semantic-role mismatch** (digest-valid chain with role-swapped internal fields),
  - and explicitly **NOT**: protocol failure, timeout, budget exhaustion, infra exclusion (429/empty/crash),
    or oracle false-negative.
- **Reliability/protocol failures are reported separately and never folded into the capability metric**
    (the lesson from 0008 trial2: a stale-input-hash chain failure with a correct assignment is
    *reliability*, not axis-binding).
- **Qwen must saturate on the same variants** (it did on 0006: 8/8). Qwen's solvability is the proof the
  task is fair; DeepSeek's reproducible binding failures are the proof it is discriminative. A task both
  models fail is unfair; a task neither fails is saturated.

**If neither R1 nor R2 holds:** the mechanism is *not* reproduced. That is itself a valid (negative) result
— it would mean the 0006 difficulty is even more specific than H3∧H4 (possibly pure H6 wording, or
sample variance), and the honest conclusion is that we do not yet have a reproducible capability mechanism.
**Do not paper over a null reproduction with a positive claim.**

---

## 11. Probe plan (only after acceptance filters pass)

- **Models:** Qwen3.7-Max + DeepSeek-V4-Pro only. **Do not run MiniMax until the mechanism is validated**
  (per the standing budget/model constraint; MiniMax is reserved for confirmed-positive tracks). No Kimi,
  no GLM unless a selected model is unavailable.
- **k = 3 per variant**, 3 separate runner invocations into `trial{1,2,3}` (no `--trials` flag), preserving
  the established protocol. `--max-actions 60 --timeout 1800 --temperature 0.7 --concurrency 1
  --elicit-confidence`.
- **Preservation enabled** (`EDA_BENCH_PRESERVE_FINAL_WORKSPACE=1`); collect post-trial from the runner's
  temp `runs_root` (`/tmp/agentic_eval_*`) into `runs/.../trialN/preserved_capture/<model>/` (gitignored).
  Every non-pass must be byte-classified from preserved artifacts, never inferred.
- **Explicit cost cap** per variant (state the ¥ figure before running; do not exceed without explicit
  authorization). Start with 0009a + 0009b (the controlled pair); extend to 0009c/0009d only if 0009a
  reproduces the failure.
- **Paired clearer-label ablation is mandatory if 0009a works:** the R2 comparison (0009a vs 0009b) is what
  turns "DeepSeek failed a task" into "label ambiguity caused the failure." Run them as a matched pair.
- **Decisive pre-model validation:** the real-PT acceptance matrix (§9) on the golden + signoff-green-but-
  mis-typed + role-mismatch packages must pass *before* spending model budget.

---

## 12. What would count as a real breakthrough

A defensible, mechanism-grounded contribution requires **at least one** of:

- **Repeated frontier split across ≥2 variants** (R1): DeepSeek shows the same axis-binding failure family
  on 0009a *and* 0009d (or another overloaded-label variant), while Qwen saturates on both — i.e. the
  difficulty generalizes beyond one hand-built instance.
- **One positive variant + a clean controlled ablation explaining it** (R2): 0009a reproduces the 0006
  failure family *and* 0009b (canonical labels) saturates, with all else held constant — isolating
  **semantic-role binding under conflicting/overloaded report labels** as the causal variable.
- **Evidence that the task difficulty comes from semantic-role binding under conflicting reports** — i.e.
  the agent must resolve *which physical token binds to which logical axis* by intersecting conflicting
  sources, with no single-file anchor. This is a genuine capability axis (joint constraint inference /
  role binding), distinct from cost stress, protocol stress, or vocabulary hiding.
- **Explicitly NOT sufficient on its own:** a single 0009a trial where DeepSeek fails once; a cost/protocol
  stress signal; a result explainable by "the model didn't read carefully" rather than "the binding is
  genuinely ambiguous under global consistency."

If achieved, the contribution upgrades from "one discriminative task (0006)" to "a reproducible
semantic-role-binding mechanism with a controlled ablation" — which is the bar for a credible
frontier-discrimination claim.

---

## 13. What not to do

- **Do not run more 0008 probes.** 0 axis-binding failures across k=3 establishes the qualitative result;
  more trials only tighten an already-zero axis-binding rate and burn budget on a saturated design.
- **Do not write the final paper yet.** The current state (one positive task + two saturated ablations) is
  preliminary, not top-conference-level. The stage-final outline is parked (left untracked) precisely
  because the thesis it encoded ("0006 + ablations = a complete story") is premature.
- **Do not claim a top-tier contribution from the single 0006 task.** n=1 is a discovery, not a result.
- **Do not generate random variants without a mechanism hypothesis.** Each variant must test a named
  factor (H1–H6); the 0009a–d family exists to isolate H3∧H4, not to enumerate designs.
- **Do not hide too much and make the task unfair.** The fairness gate (domain-expert resolvability,
  unique assignment, no leak) is non-negotiable. If a variant is unsolvable from public artifacts, it is
  broken, not hard.
- **Do not publish a full schema** (0007 proved that removes difficulty) and **do not ship the 0008 anchor
  bundle** (glossary + coverage fact + spec hint + PVT-leak) — that combination collapses binding into a
  solver path even without a schema file.

---

## 14. Recommended next milestone

1. **Write this mechanism design first** (this document) — done on review.
2. **Then implement only the 0009a / 0009b controlled pair**, *not* a large parameterized generator. The
   pair is the minimum experiment that can satisfy R2. A generator is premature until the mechanism is
   confirmed.
3. **Validate the acceptance matrices** (§9) on real PrimeTime for both variants — golden = 1.0 and
   signoff-green-but-mis-typed / role-mismatch ≤ 0.20 — *before* any model run.
4. **Then probe** the matched pair (Qwen + DeepSeek, k=3, preserved, capped), and byte-classify every
   non-pass. Decide R1/R2 from the results.
5. Only if R1 or R2 holds: extend to 0009c/0009d to pin the causal factor, *then* reconsider the paper
   narrative. If neither holds: report the honest null and re-examine H6 (wording) or accept that the 0006
   difficulty is not yet reproducible.

---

*Compliance: design-only. No code, no tasks, no models, no other-worktree changes, no commits, no push —
awaiting review. The stage-final research outline remains parked (untracked, not committed) per the changed
assessment. Grounded in the committed reports and syntheses through HEAD `88a2459` and the actual
`workflow_handoff_0006` / `0008` task artifacts.*
