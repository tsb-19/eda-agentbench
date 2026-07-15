# Phase-4W — clarity-bundle component ablation design (DESIGN ONLY, no paid calls)

**Status: DESIGN ONLY.** Pre-registered ablation plan. **No generators are implemented, no tasks are
changed, and no model calls are made in this phase.** Stop for review before any of those.

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
estimates the paid-call and token budget. **No paid calls are performed.**

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
here to the analysis axes requested for Phase-4W:

| ID | Candidate component | Where it lives | Analysis axis |
|----|---------------------|----------------|---------------|
| **C1** | Canonical field labels **+** the "disjoint typed axes" type declaration | `spec.md` Terminology; report field names; `glossary.md` | (1) explicit semantic type / field-to-role mapping |
| **C2** | PVT-descriptor definition ("`<process>_<voltage>_<temperature>` … never a valid scenario/corner value") | `spec.md`, `glossary.md` | (4) stale-decoy disambiguation (neutralizes report_C) |
| **C3** | Clock coverage fact (`intended_clock_coverage: {clk_main:1,…}`) | `public_check_summary.json` | (2) authority/ownership (clock) |
| **C4** | Glossary — partial terminology examples ("INCOMPLETE; NOT a schema") | `glossary.md` | (1) semantic type (examples) |
| **C5** | Pairwise-conflict symptom list | `public_check_summary.json` | (4) stale-decoy disambiguation (symptoms) |
| **C6** | Signoff-pair assertion: "setup signoff is taken at the **slow scenario** in the **functional corner**" | `spec.md` | (2) authority/ownership — **near-answer** |
| **C7** | Handoff-contract wording (prompt/spec/manifests reworded "resolve the role" → "infer via canonical labels + glossary + coverage fact") | `prompt.md`, `spec.md`, `_comment`s | (3) handoff contract wording |

Controls address the remaining axes directly:
- **(5) field/source ordering** → order-swapped controls (§8).
- **(6) lexical priors on `func`/`slow`/`typ`** → lexical-anonymization controls (§8).

**C6 is the highest-risk component:** it nearly states the golden tuple's scenario/corner (`slow`/
`func`) directly. If C6 alone drives the effect, the Phase-4V2 result is "the answer was published,"
not "clarity aids role-resolution inference." PC1 (§7) exists to test exactly this.

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
- **V7 = 0009 + C6**: add ONLY the signoff-pair assertion to 0009. If this alone flips 0009 to pass,
  C6 is sufficient (answer-publishing). **Mirror of PC1.**
- **V8 = 0009 + C1**: add ONLY canonical labels + disjoint-axes declaration (no glossary/coverage/
  PVT/signoff-pair). Tests labeling/type sufficiency.

### C. Lexical-anonymization controls — isolates lexical priors (axis 6)
Replace the concrete value tokens `slow`/`func`/`typ`/`fast` (and the PVT string) with neutral,
non-lexical tokens (e.g. `scn_A`/`scn_B`, `crn_X`/`crn_Y`, `pvt_K`) **consistently** across every
report, `spec.md`, `glossary.md`, `flow_config.json`, and the mutant — preserving the structural
typing and the unique-assignment intersection, removing the semantic prior.
- **V9 = 0010-anon**: full bundle, anonymized values. If V9 still passes, the effect is **structural**
  (typing/labels), not lexical. If V9 fails toward 0009, lexical priors on `slow`/`func` carry weight.
- **V10 = 0009-anon**: ambiguous baseline, anonymized. Controls that anonymization itself does not
  interact with ambiguity.

### D. Order-swapped controls — isolates field/source ordering (axis 5)
- **V11 = 0010-shuf**: 0010 with report file order shuffled and the `flow_config.json` field order
  swapped (corner before scenario).
- **V12 = 0009-shuf**: same shuffle on 0009. Controls ordering × ambiguity.

### E. Held-out controlled pair — generalization (a second pair, different hidden truth)
- **V13 = 0011 (ambiguous)** / **V14 = 0012 (clear)**: a NEW controlled pair generated by the same
  mechanism and same oracle, with a **different** hidden truth (different netlist family, different
  scenario+corner values, different decoy structure). If the clarity-bundle effect replicates on
  0011/0012 (0011 fails, 0012 passes), that is the generalization evidence 0009/0010 alone cannot
  provide. Pre-registered as the generalization contrast (PC5).

## 7. Predeclared primary contrasts (no fishing)

Only these contrasts are interpreted; everything else is exploratory and labeled as such. For each,
the hypothesis and the decisive pattern are stated up front (baselines: 0009 = 1/3, 0010 = 3/3
artifact-correct on Qwen).

| # | Contrast | Question | Decisive if |
|---|----------|----------|-------------|
| **PC1** | 0010 vs **V1** (0010−C6) | Does the **near-answer** (signoff-pair assertion) carry the effect? | V1 clusters with 0009 (≈1/3) ⇒ C6 causal (answer-publishing); V1 clusters with 0010 (≈3/3) ⇒ inference-aids suffice |
| **PC2** | 0009 vs **V8** (0009+C1); and 0010 vs **V3** (0010−labels) | Do **canonical labels + type declaration** alone carry the effect? | V8≈3/3 ⇒ labeling sufficient; V3≈1/3 ⇒ labels necessary |
| **PC3** | 0010 vs **V4** (0010−PVT-def) | Does **decoy disambiguation** carry the effect (report_C)? | V4<0010 ⇒ PVT-def protects against the report_C decoy |
| **PC4** | 0010 vs **V9** (anonymized) | **Structural typing vs lexical priors** on slow/func/typ? | V9≈3/3 ⇒ structural; V9≈1/3 ⇒ lexical priors carry it |
| **PC5** | 0009/0010 vs **0011/0012** (held-out) | Does the effect **generalize** to a different hidden truth? | 0011 fails & 0012 passes ⇒ generalizes; otherwise ⇒ pair-specific |

PC1 and PC4 are the two highest-information contrasts: PC1 separates "answer published" from
"inference aided"; PC4 separates "structural" from "lexical." They are run first (§10).

## 8. Controls detail

- **Lexical anonymization (V9/V10):** the value-rename map is applied programmatically to all
  visible files at once and checked for consistency (every occurrence renamed; the golden truth's
  roles preserved). The mutant and decoys are renamed identically so the *structural* conflict is
  unchanged; only the lexical prior is removed. A fairness-gate golden run must still score 1.0.
- **Order swap (V11/V12):** only presentation order changes (file listing order; field key order in
  `flow_config.json`). No semantic content change. Fairness-gate golden run must still score 1.0.

## 9. Held-out pair generation contract (V13/V14) — design only, not generated here

0011/0012 reuse the same generator, oracle, and grading as 0009/0010 but with a different hidden
truth: a different netlist family (still a small acc-style stage), different scenario/corner values
drawn from a disjoint value set, and a re-rolled decoy structure (role-swap / stale / PVT /
internal-swap slots shuffled). The clarity bundle for 0012 is the SAME component set as 0010; 0011
ships none. Generation is deferred to the implementation phase (after review); only the contract is
fixed here.

## 10. Stopping rules, evidence requirements, fairness gate

- **k per variant:** k=3 valid episodes (Qwen, streaming). Validity rule unchanged: infrastructure
  timeout / gateway error / worker failure ⇒ measurement-invalid, re-run until 3 valid; stop at 3.
- **Decisiveness:** a variant is decisive for its contrast if its k=3 artifact-correct count clusters
  with one baseline (within 1 of 0/3-equivalent or 3/3-equivalent). A variant landing in between
  (e.g., 2/3) is escalated to k=5 for that variant only (pre-registered), then frozen.
- **Run order:** PC1 (V1) and PC4 (V9) first — 6 episodes — review, then PC2/PC3, then PC5 (held-out
  pair, which requires generation). No variant runs before its contrast's predecessors are reviewed
  unless budget allows a batch.
- **Per-episode evidence (6-dim, as in Phase-4V2):** transport-valid / gradeable / artifact-grader-
  pass / typed-binding-pass / protocol-complete-FINISH / termination-reason, plus confidence,
  anti-cheat, reasoning tokens, cost, wall. Artifact correctness (not FINISH) is the primary measure.
- **Fairness gate (mandatory, before any model run on a variant):** the variant's golden solution
  must grade 1.0 through the identical path (real PT via b04 shim + typed-binding oracle). A variant
  whose golden does not grade 1.0 is broken and is not run on any model (the measurement-validity
  discipline; cf. the grading-fairness-gate).
- **Anti-cheat:** oracle isolation, forbidden-edit, hash, tcl-injection, hidden-shadow checked per
  episode, as in 0009/0010.

## 11. Budget estimate (NO paid calls performed)

Observed per-episode cost (Qwen, streaming, 12/36 CNY per M in/out): 0009-type ≈ ¥11–14 (longer
reasoning, 60–77K reasoning tokens); 0010-type ≈ ¥8–12 (≈34–48K reasoning tokens). Use **¥11/episode**
as a planning average; ≈0.8M tokens/episode.

| Batch | Variants | Episodes | Est. cost |
|-------|----------|----------|-----------|
| Run-1 (highest-information) | V1 (PC1), V9 (PC4) | 2 × 3 = 6 | ≈¥66 |
| Run-2 (labeling + decoy) | V8, V3 (PC2); V4 (PC3) | 4 × 3 = 12 | ≈¥132 |
| Run-3 (remaining removals + controls) | V2, V5, V6, V7, V10, V11, V12 | 7 × 3 = 21 | ≈¥230 |
| Run-4 (held-out pair) | V13, V14 (PC5) | 2 × 3 = 6 | ≈¥66 |
| Optional: DeepSeek cross-model on decisive contrasts | 2–3 variants | 6–9 | ≈¥75 |
| **Total (Qwen core)** | | **45** | **≈¥495** |
| **Total (with optional DeepSeek)** | | **≈51–54** | **≈¥540** |

Token budget: ≈45–54 episodes × ≈0.8M ≈ **36–43M tokens**. Against the ¥1000 project budget this is
large, so the design is **staged**: Run-1 first (≈¥66), review the PC1/PC4 verdicts, then decide
whether Run-2/3/4 proceed. The near-answer question (PC1) can terminate much of the agenda early: if
V1 shows the effect is answer-publishing, the remaining inference-aid ablations are deprioritized.

## 12. What this phase does NOT do (compliance)

- No generators are implemented; no task directories (0009/0010 or any V*) are created or modified.
- No model calls are made.
- No code, grader, prompt-template, scoring, or config changes.
- 0009 and 0010 are untouched.
- All variants are pre-registered here before any run; contrasts are fixed (no fishing).
- Stop for review before implementing generators, changing tasks, or making model calls.

## 13. Decision gates after review

- **Gate A:** approve the component factoring (§4) and the primary contrasts (§7).
- **Gate B:** approve Run-1 (V1, V9) as the first paid batch, or re-scope.
- **Gate C (after Run-1):** decide whether the agenda proceeds to Run-2/3/4 or terminates early
  (e.g., if PC1 shows answer-publishing, the design is reframed around "what is the minimal
  non-answer-publishing clarity that still aids inference").
