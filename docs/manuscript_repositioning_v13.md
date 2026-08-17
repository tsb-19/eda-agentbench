**English | [中文](manuscript_repositioning_v13.zh.md)**

# Manuscript repositioning proposal — move the measured result ahead of the framework

## Status: proposal only. This file changes no manuscript.

`submission/` is frozen at manuscript v12 by hard constraint 3 in `CLAUDE.md`, and it currently
rebuilds byte-identically (`bbf948bf…`, 268 459 bytes, 15 pp, verified after `make distclean`).
Applying any text below to `submission/main.tex` would break that byte-reproducibility and
invalidate the hashes recorded in `submission/FREEZE_HASHES.md`. That is a deliberate decision for
the authors to take explicitly; it is **not** taken here. This document exists so the wording can be
reviewed and argued about while v12 stays intact.

## What the repositioning rests on

One post-freeze analysis, re-derived from records committed at or before the experiment freeze — no
model call, no EDA tool run, no new episode. Source:
`scripts/phase7d_semantic_proxy_gap.py --check` → `reports/synthetic_phase7d_semantic_proxy_gap.json`.

| Stratum | n | semantically correct | semantically wrong | tool-proxy accept | false-accept | tool signal constant |
|---|---|---|---|---|---|---|
| workflow program-primary | 49 | 33 | 16 | 49 | 16/16 | yes |
| STA prospective (7A) | 72 | 24 | 48 | 72 | 48/48 | yes |
| STA phase-5C | 12 | 5 | 7 | 12 | 7/7 | yes |
| STA phase-5D | 18 | 7 | 11 | 18 | 11/11 | yes |
| SPICE phase-5D | 18 | 18 | 0 | 18 | — (negative control) | yes |

169 trajectories retained of 202 considered; 33 excluded rather than imputed. The tool-success
signal accepted **169/169**, including all **82** semantically wrong bindings. The result holds
stratum by stratum, so it never depends on pooling a heterogeneous universe.

## The change, in one line

v12's abstract opens *"We introduce a claim-scope framework for harness interventions in LLM
agents."* The framework is real and stays, but it is a way of qualifying claims — a reader meets a
method of description before meeting any result. The measured finding above is concrete, verifiable,
memorable, and directly about benchmark design, so it should come first.

## Proposed abstract opening

Replace the first sentence with two, then keep v12's remaining sentences unchanged:

> In our tool-green semantic-binding benchmarks, professional tool success is insufficient to
> determine task correctness: across 169 frozen trajectories with pairing-verified tool outcomes,
> family-specific tool-success signals accepted every run, including all 82 semantically incorrect
> bindings. We therefore evaluate task success with typed provenance/authority oracles that attest
> whether submitted values occupy the correct semantic roles, rather than with tool success alone.

The opening clause **"In our tool-green semantic-binding benchmarks"** is load-bearing and must not
be trimmed for concision. Without it the sentence reads as a general claim about agent evaluation,
which these data do not support (see *What must not be claimed*).

## Proposed introduction chain

1. **Problem.** A tool can sign off on a configuration whose values are bound to the wrong typed
   semantic roles, so tool success cannot decide task correctness.
2. **Solution, already built.** Typed provenance/authority oracles that check whether each
   submitted value is the target of an edge from a sufficiently trusted authority — not tool exit
   status. This is not a proposal; it is the grading substrate the whole program ran on.
3. **Quantification.** On 169 pairing-verified frozen trajectories the tool signal is constant, so
   every unit of measured discrimination comes from the oracle. SPICE-5D shows the oracle does not
   manufacture disagreement: where the agent bound every role correctly, oracle and tool agree
   18/18.
4. **Only then the scientific question.** With a measurement that can see the failure, how far does
   a harness clarity intervention actually transfer?
5. **Answer.** Observed for Qwen within-instance and once replicated on a pre-frozen held-out
   instance; not established across models, not established across families, never measured jointly.
6. **Two orders of authority.** A tool verdict must be bound to the artifact it claims to judge, and
   an oracle's authority inherits the custody of its hidden reference.

## Proposed contribution order

1. **Semantic-aware evaluation of tool-grounded agents.** Separate tool execution success from
   semantic task correctness in three executable EDA families, and quantify that the tool-success
   proxy has no discrimination on 169 pairing-verified trajectories, including all 82 real agent
   misbindings.
2. **The semantic-binding failure itself.** Two never-collapsed subtypes — role-axis binding error,
   and correct role with wrong value selection — exhibited as real, tool-green agent trajectories.
3. **Scope of the harness effect.** Studied on top of that measurement: Qwen local and within-family
   positive; DeepSeek not established; the prospective STA panel not established and directionally
   reversed against its pilot; SPICE at a non-discriminative ceiling. This is where the claim-scope
   framework does its work.
4. **Authority of the measurement.** Verdict-to-artifact pairing and reference-standard custody, as
   empirical demonstrations rather than as a list of incidents.

## Where the 9-of-58 pairing exclusions go

Measurement validity, one sentence, not the abstract:

> Hash-based pairing excluded 9 of 58 historical workflow episodes whose recorded tool verdict did
> not attest the final submitted artifact; tuple equality alone would have missed seven of the nine.

Frame it as the principle, not as a defect count: **a verdict may only be compared with another
verdict when both are bound, in the provenance chain, to the same object.** A workflow agent can run
the evidence chain on configuration A, obtain a green tool result, then submit configuration B; the
green result does not transfer. This is the same class of problem as reference-standard custody, one
level down. Do **not** write it as "nine of our episodes were mis-scored" — the frozen grader already
flagged them independently via `stage_chain == 0.0`; what is new is that a *post-hoc paired analysis*
must re-verify pairing rather than assume it.

## Prior work that must be cited before this framing ships

Two are already in `submission/references.bib`; three are not and are close enough that a reviewer
would expect them.

| Status | Work | Why it bounds our claim |
|---|---|---|
| cited (`abc`) | arXiv:2507.02825 — *Establishing Best Practices for Building Rigorous Agentic Benchmarks* | task validity / outcome validity / reporting as a checklist |
| cited (`protocolval`) | arXiv:2607.22368 — *Do Agent Benchmarks Measure Capability? Protocol Validity in the Age of Agentic AI* | formalizes whether the target capability is still necessary for success; Mislead gap quantifies score inflation |
| **missing** | arXiv:2605.10448 (2026-05-11), Gao & Zhou — *Can Agent Benchmarks Support Their Scores? Evidence-Supported Bounds for Interactive-Agent Evaluation* | its motivating example is a surface outcome check ("clicked Save") that does not establish the intended state change; adds an evidence layer with Pass / Fail / Unknown and evidence-supported score bounds over five public benchmarks |
| **missing** | arXiv:2605.11039 (2026-05-11), Fan et al. — *The Granularity Mismatch in Agent Security: Argument-Level Provenance…* (PACT) | assigns semantic roles to tool arguments, tracks provenance, and checks role-specific authority contracts — conceptually adjacent, but for runtime security enforcement, not benchmark scoring |
| **missing** | arXiv:2607.24054 (2026-07-27), Luo & Peng — *Success Is Not Self-Explanatory: Auditing Success Provenance in Agent Evaluation* | audits whether a correct outcome came from permitted information, via paired CLEAN / GOLD / SHAM interventions |

arXiv:2605.10448 predates the v12 freeze and is the closest of the three; its absence from v12 is a
real exposure, independent of whether this repositioning is adopted.

The defensible boundary statement, given all five:

> We do not claim to be first to observe that outcome success can be unearned. We study a specific
> value-to-role misbinding inside executable professional workflows: the agent submits a
> configuration a real commercial tool fully accepts, while the correct evidence is bound to the
> wrong typed semantic role. We identify these with provenance-attested semantic scoring, and
> measure that the tool-success proxy loses all discrimination on real agent trajectories.

## What must not be claimed

- Not *"agent benchmarks have a 100 % semantic false-accept rate."* These families are
  **constructed** so a wrong binding stays tool-green. A rate of 1.0 shows the construction working
  as specified and quantifies its cost to measurement.
- Not a population rate. Strata span stages, conditions, models and run windows and are not one
  sampling frame; report them separately.
- Not two findings. Because the tool signal is constant,
  `Δ = S_tool − S_semantic ≡ 1 − S_semantic`. Δ belongs in an appendix.
- Not a theorem. That the oracle rejects every wrong binding when the constraints admit exactly one
  satisfying assignment is a **construction property** of the generator (294 → 1), not a proof.
  Presenting it as a theorem invites the correct objection that it is circular.

What *is* non-trivial is behavioural rather than definitional: the tool-green-but-wrong region is
not merely reachable in the generator's candidate space — real agents entered it 82 times.

## The decision this document needs

Two ways forward, and the choice is the authors':

1. **Leave v12 frozen.** This text waits for the next submission. Byte-reproducibility and
   `FREEZE_HASHES.md` stay valid. The 2605.10448 exposure stays too.
2. **Amend deliberately.** Apply the abstract/introduction/contribution changes plus the three
   missing citations, and re-derive `FREEZE_HASHES.md` in the same commit, stating plainly in
   `docs/provenance.md` that v12-as-submitted and v12-as-in-tree now differ.

Whichever is chosen, no experiment is added and no frozen task semantics change. Every number above
is already committed and re-derivable by
`python3 scripts/phase7d_semantic_proxy_gap.py --check`.
