# Phase-4W — clarity-bundle component ablation design (Gate A: screening design; Gate B: Run-1 = symmetric C6)

**Status: design + Run-1 authorization.** Gate A conditionally approved (this is a **sequential
mechanistic screening design**, not a factorial experiment). Gate B approves only the minimal
symmetric-C6 Run-1 (`V1 = 0010−C6`, `V9 = 0009+C6`), k=3 each, plus freezing the held-out 0011/0012
pair. The rest of the matrix is **not** authorized yet.

## 1. Purpose and scope

Phase-4V2 established that, on the constructed pair `workflow_handoff_0009` (ambiguous) vs `0010`
(clear control), the **complete** visible clarity bundle suppresses the scenario/corner wrong-axis
binding failure for both evaluated models (DeepSeek 0/3→3/3, Qwen 1/3→3/3, k=3 per cell). The accepted
conclusion is deliberately bounded: it is a **replication of the clarity-bundle effect on this one
controlled task pair**, not a component isolation and not a generalization claim.

Phase-4W asks the next two questions:
1. **Component isolation:** which part(s) of the clarity bundle carry the effect?
2. **Generalization:** does the effect replicate on a held-out controlled pair with a different
   hidden truth?

This document factors the 0009→0010 clarity bundle into explicit candidate components, defines
one-variable and factorial ablation variants (plus lexical-anonymization and order-swapped controls
and a held-out pair), predeclares the primary contrasts / stopping rules / evidence requirements, and
estimates the paid-call and token budget. **No paid calls are performed beyond Gate-B Run-1.**

## 1a. Screening framing — NOT a factorial experiment (Gate A)

The C1–C7 components are a **mechanistic hypothesis map and sequential screening design**, not
orthogonal causal factors. Several components are semantically overlapping and may interact (e.g. the
canonical labels C1 and the glossary C4 both carry the disjoint-typed-axes idea; the signoff-pair
assertion C6 and the coverage fact C3 are both authority-bearing). Therefore:

- **`0010−X` estimates local necessity of X around the CLEAR endpoint** (does removing X from the
  full bundle move the clear endpoint toward the ambiguous one?).
- **`0009+X` estimates local sufficiency of X around the AMBIGUOUS endpoint** (does adding X alone to
  the bare ambiguous task move it toward the clear one?).
- **Neither, alone, estimates a general main effect for X.** A component can be locally necessary at
  one endpoint and not the other, or its effect can depend on what else is present.
- **The full Phase-4W program is sequential mechanistic screening, not a complete seven-factor
  factorial experiment.** Variants are run in information-priority order; each result can terminate or
  reframe the remaining agenda. No variant is interpreted as a context-free main effect.

Component-level interpretation rule (Gate A): if an effect is carried by an **answer-bearing**
component (C6 is the prime case), it is reported as an **answer-disclosure effect**, not as isolated
evidence for a semantic-role mechanism. A semantic-role-mechanism claim requires the effect to
reproduce on **non-answer-bearing** controls.

## 2. Background — the controlled pair and what is already known

- Golden tuple (frozen, both tasks): `netlist_v2.v / clk_main / scenario=slow / corner=func`.
- 0009 and 0010 share byte-identical hidden truth, grader (`hidden/grade_workflow.py`), flow, mutant
  (a value-swap on the signoff axes: shipped `flow_config.json` = `scenario=func / corner=typ`), and
  the four decoys (report_A role-swap, report_B stale-netlist, report_C PVT-in-corner, evidence_D
  internal role-swap). They differ ONLY in the visible clarity bundle.
- Baselines (Qwen, streaming, k=3): 0009 = 1/3 artifact-correct (2 wrong-axis: `func/slow`,
  `func/typ`); 0010 = 3/3 artifact-correct (0 wrong-axis). 0010 = 3/3 artifact/typed-binding but only
  1/3 protocol-complete FINISH (2 action-cap) — role clarity suppressed the binding error, not
  termination inefficiency.
- Prior ablation lesson (`synthetic_p14_axis_binding_ablation_synthesis.md`, task 0007): **publishing
  the full axis schema made binding a LOOKUP, not INFERENCE, and saturated both models.** This is the
  central design risk for Phase-4W: some clarity-bundle components may publish the answer rather than
  aid inference. The design must distinguish those.

## 3. Source-level diff (0009 → 0010)

Files added in 0010 (absent in 0009):
- `files/glossary.md` — terminology examples (scenario/corner/PVT/disjoint-axes/clock).
- `files/public_check_summary.json` — intended-clock coverage fact + a pairwise-conflict symptom list.

Files changed (0009 → 0010), content-only (hidden/grader/flow/netlists/library identical):
- `prompt.md`, `files/spec.md`, `files/flow_config.json` (_comment), `files/handoff_manifest.json`
  (_comment + terminology/recovery_note), `files/evidence_manifest.json` (_comment),
  `files/evidence_D_role_mismatch.json` (field names), `files/prev_signoff.log`,
  `files/report_A_role_swap.rpt`, `files/report_B_role_stale.rpt`, `files/report_C_role_pvt.rpt`,
  `metadata.json` (variant/authority_source/editable+read-only file lists/expected_error_category).
- Net effect in the reports: the field labels `op_point=` / `mode=` (0009) become canonical
  `scenario=` / `corner=` (0010) everywhere a value is carried.

## 4. Semantic diff — the clarity bundle factored into candidate components

The "clarity bundle" is not one thing. It is at least seven separable candidate components, mapped
here to the analysis axes requested for Phase-4W. **Each is classified (Gate A, before any run)** as
one or more of: **answer-bearing** (nearly publishes the golden binding) · **schema-bearing** (declares
the typed-axis structure / type rules) · **authority-bearing** (states which source/value is
authoritative) · **decoy-filtering** (exists to reject a specific decoy) · **format-only** (label/
wording/ordering with no new semantic content).

| ID | Candidate component | Where it lives | Analysis axis | Classification |
|----|---------------------|----------------|---------------|----------------|
| **C1** | Canonical field labels **+** the "disjoint typed axes" type declaration | `spec.md` Terminology; report field names; `glossary.md` | (1) explicit semantic type / field-to-role mapping | schema-bearing + format-only |
| **C2** | PVT-descriptor definition ("`<process>_<voltage>_<temperature>` … never a valid scenario/corner value") | `spec.md`, `glossary.md` | (4) stale-decoy disambiguation (neutralizes report_C) | decoy-filtering + schema-bearing |
| **C3** | Clock coverage fact (`intended_clock_coverage: {clk_main:1,…}`) | `public_check_summary.json` | (2) authority/ownership (clock) | authority-bearing |
| **C4** | Glossary — partial terminology examples ("INCOMPLETE; NOT a schema") | `glossary.md` | (1) semantic type (examples) | schema-bearing + format-only |
| **C5** | Pairwise-conflict symptom list | `public_check_summary.json` | (4) stale-decoy disambiguation (symptoms) | decoy-filtering + format-only |
| **C6** | Signoff-pair assertion: "setup signoff is taken at the **slow scenario** in the **functional corner**" | `spec.md` | (2) authority/ownership — near-answer | **answer-bearing** (nearly publishes the golden binding) |
| **C7** | Handoff-contract wording (prompt/spec/manifests reworded "resolve the role" → "infer via canonical labels + glossary + coverage fact") | `prompt.md`, `spec.md`, `_comment`s | (3) handoff contract wording | format-only |

Controls address the remaining axes directly:
- **(5) field/source ordering** → order-swapped controls (§8).
- **(6) lexical priors on `func`/`slow`/`typ`** → lexical-anonymization controls (§8).

**C6 is classified answer-bearing** (Gate A): it nearly states the golden tuple's scenario/corner
(`slow`/`func`) directly. Per the §1a interpretation rule, if C6 drives an effect, that effect is
reported as an **answer-disclosure effect**, NOT as isolated evidence for a semantic-role mechanism.
Run-1 (§7a) tests exactly this.

## 5. Frozen invariants (every variant preserves these)

For every ablation variant, the following are **byte-identical to 0009/0010** (only `files/` visible
content changes; the hidden layer is untouched and reused):
- hidden truth (`hidden/handoff_truth.json`: netlist_v2 / clk_main / slow / func);
- grader (`hidden/grade_workflow.py` — the typed-binding oracle; 294→1 uniqueness);
- evidence flow (two ordered stages; `gen_evidence_stage{1,2}`; `run_evidence_stage{1,2}.sh`);
- the mutant (shipped `flow_config.json` value-swap `scenario=func/corner=typ`);
- the four decoys (report_A/B/C, evidence_D) — unless a variant explicitly targets one;
- scoring weights, anti-cheat checks, budgets (max-actions 60, episode timeout 1800 s, temperature
  0.7, streaming transport, request inactivity 120 s, hard deadline 300 s, max chat retries 1).

## 6. Ablation variant families

Notation: a variant is "0010 − X" (remove component X from the full bundle) or "0009 + X" (add only
component X to the ambiguous baseline). Each variant is a new task dir with the frozen invariants
above; variants are generated, not hand-edited into 0009/0010 (0009/0010 are never modified).

### A. One-variable removals from the full bundle (0010 − X) — tests necessity
- **V1 = 0010 − C6**: drop the "slow scenario / functional corner" signoff-pair assertion from
  `spec.md` (replace with a neutral "infer the signoff pair from the constraints"). **Highest
  priority (PC1).**
- **V2 = 0010 − C1(type-decl)**: keep canonical labels but remove the "disjoint typed axes"
  declaration.
- **V3 = 0010 − C1(labels)**: revert canonical `scenario`/`corner` labels back to `op_point`/`mode`
  in the reports, keep all other bundle components (glossary, coverage, PVT-def, signoff-pair,
  symptoms).
- **V4 = 0010 − C2**: drop the PVT-descriptor definition (report_C decoy regains plausibility).
- **V5 = 0010 − C3**: drop the clock coverage fact from `public_check_summary.json`.
- **V6 = 0010 − (C4+C5)**: drop glossary + pairwise-conflict list, keep labels/types/PVT/coverage/signoff-pair.

### B. One-variable additions to the ambiguous baseline (0009 + X) — tests sufficiency
- **V9 = 0009 + C6** *(Gate-B Run-1 label; was "V7" in an earlier draft)*: add ONLY the signoff-pair
  assertion to 0009. If this alone flips 0009 to pass, C6 is sufficient (answer-publishing). **Run-1
  variant (mirror of V1).**
- **V8 = 0009 + C1**: add ONLY canonical labels + disjoint-axes declaration (no glossary/coverage/
  PVT/signoff-pair). Tests labeling/type sufficiency. *(Not Run-1.)*

### C. Lexical-anonymization controls — isolates lexical priors (axis 6) — DEFERRED (not Run-1)
Replace the concrete value tokens `slow`/`func`/`typ`/`fast` (and the PVT string) with neutral,
non-lexical tokens (e.g. `scn_A`/`scn_B`, `crn_X`/`crn_Y`, `pvt_K`) **consistently** across every
report, `spec.md`, `glossary.md`, `flow_config.json`, and the mutant — preserving the structural
typing and the unique-assignment intersection, removing the semantic prior.
- **V-LEX1 = 0010-anon** *(deferred; was "V9" in an earlier draft — Gate B reassigns the V9 label to
  the 0009+C6 sufficiency variant above)*: full bundle, anonymized values.
- **V-LEX2 = 0009-anon**: ambiguous baseline, anonymized. Controls that anonymization itself does not
  interact with ambiguity.

### D. Order-swapped controls — isolates field/source ordering (axis 5)
- **V11 = 0010-shuf**: 0010 with report file order shuffled and the `flow_config.json` field order
  swapped (corner before scenario).
- **V12 = 0009-shuf**: same shuffle on 0009. Controls ordering × ambiguity.

### E. Held-out controlled pair — generalization (a second pair, different hidden truth) — frozen before Run-1
- **0011 (ambiguous)** / **0012 (clear)**: a NEW controlled pair (real task IDs) generated from the
  same acc_stage project + generator + oracle, with a **different** hidden truth (a different golden
  scenario/corner binding from the axis_schema, re-rolled mutant + decoys). If the clarity-bundle
  effect replicates on 0011/0012 (0011 fails, 0012 passes), that is the generalization evidence
  0009/0010 alone cannot provide. Pre-registered as PC5; **generated + fairness-gated + committed
  frozen before Run-1** (§9), not run on any model in Run-1.

## 7. Predeclared primary contrasts (no fishing)

Only these contrasts are interpreted; everything else is exploratory and labeled as such. For each,
the hypothesis and the decisive pattern are stated up front (baselines: 0009 = 1/3, 0010 = 3/3
artifact-correct on Qwen).

| # | Contrast | Question | Decisive if |
|---|----------|----------|-------------|
| **PC1** (Run-1) | **symmetric C6**: `V1 = 0010−C6` (necessity) **and** `V9 = 0009+C6` (sufficiency) | Does the **answer-bearing** signoff-pair assertion carry the effect? (See §7a for the 4-cell interpretation.) | V1 degrades & V9 recovers ⇒ C6 dominant local driver (answer-disclosure effect unless non-answer controls reproduce); see §7a for all cells |
| **PC2** | 0009 vs **V8** (0009+C1); and 0010 vs **V3** (0010−labels) | Do **canonical labels + type declaration** alone carry the effect? | V8≈3/3 ⇒ labeling sufficient; V3≈1/3 ⇒ labels necessary |
| **PC3** | 0010 vs **V4** (0010−PVT-def) | Does **decoy disambiguation** carry the effect (report_C)? | V4<0010 ⇒ PVT-def protects against the report_C decoy |
| **PC4** | 0010 vs **V-LEX1** (anonymized) | **Structural typing vs lexical priors** on slow/func/typ? | V-LEX1≈3/3 ⇒ structural; V-LEX1≈1/3 ⇒ lexical priors carry it |
| **PC5** | 0009/0010 vs **0011/0012** (held-out) | Does the effect **generalize** to a different hidden truth? | 0011 fails & 0012 passes ⇒ generalizes; otherwise ⇒ pair-specific |

## 7a. Run-1 (Gate B) — symmetric C6 ablation: `V1 = 0010−C6`, `V9 = 0009+C6`

Gate B authorizes ONLY this minimal pair, k=3 valid each, Qwen streaming, frozen Phase-4V2
model–harness configuration. No other variant, no DeepSeek, no automatic Run-2, no k=5 escalation.

**Endpoint framing (Gate A):** V1 estimates **local necessity of C6 at the clear endpoint**;
V9 estimates **local sufficiency of C6 at the ambiguous endpoint**. Neither is a general main effect.

**Predeclared C6 interpretation table (decided before execution; `degrade` = V1 artifact-correct count
drops toward the 0009 baseline 1/3; `recover` = V9 artifact-correct count rises toward the 0010
baseline 3/3; `strong` = V1 stays ≈3/3; `no recover` = V9 stays ≈1/3):**

| V1 (0010−C6) | V9 (0009+C6) | Interpretation |
|---|---|---|
| degrade | recover | C6 is the **dominant local driver** — but per §1a this is an **answer-disclosure effect**, NOT semantic-role-mechanism evidence, unless later non-answer-bearing controls (PC2/PC3/PC4) reproduce it. |
| strong | no recover | C6 is **not the primary driver**; the effect lives in other bundle components. |
| degrade | no recover | C6 is **locally necessary but insufficient** ⇒ interaction with other bundle components. |
| strong | recover | C6 is **sufficient on 0009 but redundant within 0010** (the rest of the bundle already suffices at the clear endpoint). |
| — | — | **High within-condition instability** (e.g. both conditions 2/3, or run-to-run disagreement at k=3) ⇒ report **recurrence/instability only**, no mechanistic claim, return for review. |

**Primary outcomes:** typed-binding correctness; artifact/grader correctness (these coincide for this
oracle family at the episode level — both ⟺ score 1.00 — but are reported as separate dimensions).
**Independent report dimensions per episode:** transport validity; gradeability; FINISH/protocol
completion; action-cap or task-wall termination; submitted binding; score breakdown; actions; reasoning
tokens; cost; confidence; retries; transport events.

**Execution order (predeclared, balanced interleaved):** the 6 episodes (V1×3, V9×3) are run in a
single balanced interleaved stream, **not** one variant fully before the other, using the predeclared
seed **`phase4w_run1_seed=20260715`** → order `V1,V9,V1,V9,V1,V9` (deterministic interleaving under
the seed; recorded in the manifest). Independence caveat unchanged (no controllable sampling seed at
the provider; identical exposed config, naturally differing transcripts).

**Stopping:** k=3 valid per variant (infra-invalid ⇒ re-run until 3 valid). **No automatic k=5
escalation.** Stop after both reach k=3 valid; return for review with the interpretation-table cell.

PC1 (the symmetric C6 ablation) is the highest-information contrast — it separates "answer published"
from "inference aided" — and is the **only** contrast authorized for Run-1 (Gate B). PC4 (lexical,
via V-LEX1) and the rest are deferred to later runs pending review.

## 8. Controls detail (deferred controls — not Run-1)

- **Lexical anonymization (V-LEX1/V-LEX2):** the value-rename map is applied programmatically to all
  visible files at once and checked for consistency (every occurrence renamed; the golden truth's
  roles preserved). The mutant and decoys are renamed identically so the *structural* conflict is
  unchanged; only the lexical prior is removed. A fairness-gate golden run must still score 1.0.
- **Order swap (V11/V12):** only presentation order changes (file listing order; field key order in
  `flow_config.json`). No semantic content change. Fairness-gate golden run must still score 1.0.

## 9. Held-out pair generation contract (0011/0012) — frozen before Run-1 (Gate B prerequisite)

0011 (ambiguous) / 0012 (clear) reuse the same acc_stage project, netlist, library, generator,
oracle, and grading as 0009/0010. The **different hidden truth** is a **different golden
(scenario, corner) binding** drawn from the axis_schema value set (distinct from 0009/0010's
`slow`/`func`), with the mutant value-swap and the four decoys re-rolled consistently for the new
binding (role-swap / stale / PVT / internal-swap slots preserved in structure, re-instantiated with
the new values). The clarity bundle for 0012 is the SAME component set as 0010; 0011 ships none.
**This pair is generated, fairness-gated, and committed FROZEN before any Run-1 paid call** (so it
cannot be tuned after observing Run-1); it is not run on any model in Run-1 (PC5 is a later run).
fixed here.

## 10. Stopping rules, evidence requirements, fairness gate

- **k per variant:** k=3 valid episodes (Qwen, streaming). Validity rule unchanged: infrastructure
  timeout / gateway error / worker failure ⇒ measurement-invalid, re-run until 3 valid; stop at 3.
- **Decisiveness (Run-1):** a condition is read against the §7a interpretation table by whether its
  k=3 artifact-correct count clusters with the 0009 baseline (≈1/3) or the 0010 baseline (≈3/3). A
  condition landing in between (e.g., 2/3) is **high within-condition instability** → per §7a, report
  recurrence/instability only, no mechanistic claim, return for review. **No automatic k=5
  escalation** (Gate B).
- **Run order (Run-1):** V1 and V9 interleaved `V1,V9,V1,V9,V1,V9` under seed `phase4w_run1_seed`
  (§7a). No other variant runs in Run-1.
- **Per-episode evidence (6-dim, as in Phase-4V2):** transport-valid / gradeable / artifact-grader-
  pass / typed-binding-pass / protocol-complete-FINISH / termination-reason, plus confidence,
  anti-cheat, reasoning tokens, cost, wall. Artifact correctness (not FINISH) is the primary measure.
- **Fairness gate (mandatory, before any model run on a variant):** the variant's golden solution
  must grade 1.0 through the identical path (real PT via b04 shim + typed-binding oracle). A variant
  whose golden does not grade 1.0 is broken and is not run on any model (the measurement-validity
  discipline; cf. the grading-fairness-gate). **Static fairness gates also reject the wrong-axis and
  stale-decoy solutions** and confirm hidden truth / flow / mutant / grader / scoring / budgets /
  action surface are unchanged between paired variants (exact source + semantic diffs recorded).
- **Anti-cheat:** oracle isolation, forbidden-edit, hash, tcl-injection, hidden-shadow checked per
  episode, as in 0009/0010.

## 11. Budget estimate (NO paid calls performed beyond Gate-B Run-1)

Observed per-episode cost (Qwen, streaming, 12/36 CNY per M in/out): 0009-type ≈ ¥11–14 (longer
reasoning, 60–77K reasoning tokens); 0010-type ≈ ¥8–12 (≈34–48K reasoning tokens). Use **¥11/episode**
as a planning average; ≈0.8M tokens/episode.

| Batch | Variants | Episodes | Est. cost |
|-------|----------|----------|-----------|
| **Run-1 (Gate B, authorized)** | **V1 (0010−C6), V9 (0009+C6) — symmetric C6** | **2 × 3 = 6** | **≈¥66** |
| Run-2 (labeling + decoy; deferred) | V8, V3 (PC2); V4 (PC3) | 4 × 3 = 12 | ≈¥132 |
| Run-3 (remaining removals + controls; deferred) | V2, V5, V6, V-LEX1, V-LEX2, V11, V12 | 7 × 3 = 21 | ≈¥231 |
| Run-4 (held-out pair; deferred) | 0011, 0012 (PC5) | 2 × 3 = 6 | ≈¥66 |
| Optional: DeepSeek cross-model on decisive contrasts | 2–3 variants | 6–9 | ≈¥75 |
| **Total program (Qwen core, all runs)** | | **45** | **≈¥495** |
| **Total (with optional DeepSeek)** | | **≈51–54** | **≈¥540** |

Token budget: ≈45–54 episodes × ≈0.8M ≈ **36–43M tokens**. The program is **staged**: Run-1 first
(≈¥66), review the PC1 (symmetric C6) verdict, then decide whether Run-2/3/4 proceed. The
near-answer question (PC1) can terminate much of the agenda early: if V1 shows the effect is
answer-publishing, the remaining inference-aid ablations are deprioritized.

## 12. Run-1 compliance (what Run-1 does NOT do)

- No variants beyond V1 (0010−C6) and V9 (0009+C6); the rest of the matrix is not implemented or run.
- No DeepSeek calls; no other paid variants; no automatic Run-2; no k=5 escalation; no push.
- No changes to 0009/0010 or to any code/grader/prompt-template/scoring/config — V1/V9 are NEW task
  dirs generated from the frozen 0009/0010 source with only the C6 assertion added/removed; the hidden
  truth / grader / flow / mutant / decoys / budgets / action surface are byte-identical across the pair.
- The held-out 0011/0012 pair is generated + fairness-gated + committed FROZEN before any Run-1 paid
  call and is not tuned after; it is not run on any model in Run-1.
- Interleaved execution under a predeclared seed; the C6 interpretation table is fixed before execution.

## 13. Decision gates

- **Gate A — conditionally approved** (this revision): screening framing (§1a), component
  classifications (§4), C6 = answer-bearing. Holds as a mechanistic hypothesis map, not a factorial.
- **Gate B — approved (Run-1 only):** V1 = 0010−C6, V9 = 0009+C6, k=3 each, interleaved; held-out pair
  frozen first. Returns for review with the §7a interpretation-table cell.
- **Gate C (after Run-1):** decide whether the agenda proceeds (Run-2/3/4) or reframes (e.g., if PC1
  is an answer-disclosure effect, reframe around "what is the minimal non-answer-publishing clarity
  that still aids inference" and prioritize non-answer controls PC2/PC3/PC4).
