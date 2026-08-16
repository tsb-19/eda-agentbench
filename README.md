**English | [中文](README.zh.md)**

# Auditing Generalization Claims for LLM Agent Harnesses — reproducibility artifact

This branch is the artifact for one paper: ***Auditing Generalization Claims for LLM Agent
Harnesses: Semantic Binding and Measurement Validity*** (ICLR 2027 submission, manuscript v12,
frozen). The paper is in [`submission/`](submission/); build it with `cd submission && make`.

> Looking for **EDA-AgentBench**, the 2892-task commercial-EDA benchmark? That is on `master`.
> This branch keeps only what the paper covers — see [`docs/REMOVED.md`](docs/REMOVED.md).

## What the paper claims

When a harness intervention changes agent behaviour, what may you claim? "How general" is not one
axis but three — over task **instances**, over model **backends**, over task **families** — and
widening one is a move *incomparable* to widening another, not a further rung on a ladder. The
paper therefore indexes the *evidence* for a claim by the set of (family, instance, model)
configurations at which it was measured, ordered by inclusion.

Applied to its own results, on a tool-grounded **semantic-handoff** task:

| Support | What was measured | Verdict |
|---|---|---|
| **S0** local (Qwen3.7-Max, workflow family, dev instance) | Base 1/3 → BundleS 3/3, zero axis-binding failures under BundleS | **observed** |
| **S1** + held-out instance (widens instance scope) | same direction on a pre-frozen instance | **replicated once** |
| **S2-M** + DeepSeek-V4-Pro (widens model scope) | 3/4 = 3/4 | **not established** — and not absence either |
| **S2-F** + STA family, 12 prospective instances | +12.5 pp, sensitivity band −12.5 to 41.7; the 3-instance pilot ran the *other* way (−16.7 pp) | **estimated; band spans zero** |
| **S2-F** + SPICE family | 1.00 = 1.00 = 1.00 | **ceiling; uninformative** |
| **S3** different model *and* different family | nothing | **not measured** — reported as untested, not as failed |

A wrong binding still produces a green tool sign-off (*tool-green*), so only a typed
provenance/authority oracle rejects it. That is why the paper's failures survive a benchmark that
scores by tool exit status.

The second, orthogonal contribution is a four-layer **Harness Effect Audit Protocol** — capability,
sampling, execution, artifact integrity. Each layer caught a concrete threat that would have
changed the scientific conclusion; two of them (transport censoring, an action-surface false
positive) would have produced confident wrong numbers in *any* analysis of the uncorrected logs.

## Start here

| If you want to… | Read |
|---|---|
| find the evidence for a specific claim, table or figure | **[`docs/artifact_map.md`](docs/artifact_map.md)** — every paper object mapped to the files that produce it |
| understand the evidence base | [`reports/README.md`](reports/README.md) |
| reproduce the numbers | [`docs/reproducibility.md`](docs/reproducibility.md) |
| know what the task families are | [`docs/datacard.md`](docs/datacard.md) |
| know how correctness is decided | [`docs/scoring.md`](docs/scoring.md) |
| know which commit produced what | [`docs/provenance.md`](docs/provenance.md) |
| know what this branch dropped and why | [`docs/REMOVED.md`](docs/REMOVED.md) |
| see it as a one-page overview | [`docs/overview.html`](docs/overview.html) |
| see the gate output for this branch | [`VERIFICATION.md`](VERIFICATION.md) |

## Layout

```
submission/        the frozen manuscript: main.tex, main.pdf (15 pp), generated tables, freeze hashes
tasks/             the three semantic-handoff families
  p14_workflow_handoff/   27 instances — Study I (PVT axes, PrimeTime)
  p15_sta_handoff/        Family A — Study II S2-F (provenance DAG, PrimeTime)
  p16_spice_handoff/      Family B — Study II S2-F (request-authority join, HSPICE)
  p13_trajectory_handoff/ NOT a studied family — the asset substrate the p14 generator reads
generators/        the three family generators and their typed graders
eda_agentbench/    the harness: task loader, agentic runner, two-phase workspace, anti-cheat
scripts/           the audit infrastructure and the per-phase freeze/fairness/analysis scripts
reports/           the evidence base; reports/evidence/ is frozen custody records
docs/              documentation, bilingual (EN + zh)
```

## Reproduce the paper without any EDA tool

Every derived number — each table, interval, sensitivity band and *p*-value — recomputes from the
frozen per-episode records with no commercial tool, no network and no model call:

```bash
pip install -e ".[test]"

scripts/check                                          # tests + task structure + 1065 custody pins
python3 scripts/phase7c_study1_ledger.py    --check    # Study I ledger: 58 + 12 = 70 episodes
python3 scripts/phase7c_claim_statistics.py --check    # 12.5 / [-12.5, 41.7] / -16.7
python3 scripts/slim_link_check.py                     # no dangling repository references

cd submission && make distclean && make                # 15 pp; byte-reproducible PDF
```

`--check` recomputes from `reports/evidence/` and diffs against the committed output, exiting
non-zero on any drift. No table in the paper is a transcribed number: `main.tex` `\input`s what
these scripts emit.

## Running the task families

Grading a handoff instance needs the real tool — PrimeTime for p14/p15, HSPICE for p16 — because a
wrong binding is only detectable *after* the tool signs it off green. With the tools reachable:

```bash
eda-bench detect-tools
eda-bench evaluate-task tasks/p14_workflow_handoff/workflow_handoff_0009 \
    --submission tasks/p14_workflow_handoff/workflow_handoff_0009/solution
eda-bench run-agent tasks/p14_workflow_handoff/workflow_handoff_0009 --agent-cmd "<your agent>"
```

The agentic path is a two-phase workspace model: the agent sees visible+editable files only,
never `hidden/`; grading happens in a second workspace that overlays the hidden truth. See
[`docs/agentic_runner.md`](docs/agentic_runner.md).

## What is deliberately not here

- **The paid episodes cannot be re-run.** The experimental program is permanently closed at the
  frozen experiment HEAD; all reported numbers are re-derived from committed ledgers at or before
  it. See [`docs/provenance.md`](docs/provenance.md).
- **No S3 evidence.** Different model *and* different family was never measured. Its absence is
  the claim, not an omission.
- **No human construct validation.** The blinded human study was preregistered and never executed
  — no LLM was substituted for the missing annotators.
- **This branch is not anonymised.** ~212 frozen custody files contain a username, host name or
  absolute path, and rewriting them would break the custody chain the paper asserts. A double-blind
  supplement needs a separate sanitising export, not a git edit. See
  [`docs/REMOVED.md`](docs/REMOVED.md).
- **Two generators drifted after their freeze.** `frozen_membership_verify.py` reports exactly 2
  mismatches and 9 missing pinned files, all pre-existing and explained in
  `docs/frozen_membership_baseline.json`. They are carried forward rather than quietly cleaned up,
  because a clean sheet would hide real drift.

## Commercial tools

The families target commercial Synopsys tools; no open-source EDA tool substitutes. Probes look
under `/EDA/soft2/synopsys/` and `/EDA/soft2/cadence/` by default; set `EDA_TOOL_ROOT` to replace
the leading `/EDA` for a different install prefix. Nothing is hardcoded in task definitions. See
[`docs/commercial_tool_policy.md`](docs/commercial_tool_policy.md).

## License

Apache-2.0
