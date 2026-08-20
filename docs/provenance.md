**English | [中文](provenance.zh.md)**

# Provenance — which commit produced what, and what is frozen

A measurement is reproducible only if you can say exactly which state of the repository produced
it. This document resolves the paper's claims to explicit commits and states what may no longer
change. It replaces the benchmark-era status document and absorbs the Phase-6C freeze attestation.

## Two explicit HEADs

| | Commit | Meaning |
|---|---|---|
| **Experiment freeze HEAD** | `a89e084` | *"report(phase5d): TypedContract extension complete 36/36"*. **No experiment, paid model call, or task/model asset beyond this commit contributes to the paper.** Every reported number is re-derived from committed ledgers at or before it. |
| **Submission HEAD (v12)** | `cc797ffe` (tag `iclr2027-submission-v3`) | manuscript v12. Ahead of `a89e084` by documentation and submission work only — no new experimental result. **Retained as an immutable historical snapshot; not rewritten by v13.** |
| **Submission HEAD (v13)** | `c7b3828a`, tag `iclr2027-submission-v4` | manuscript v13. Promotes the Phase-7D retrospective result ahead of the claim-scope framework, adds four citations and states harness scope as a limitation. **No paid model call, no new episode, no task-semantics change, no derived experimental number moved** — all three generated tables stay byte-identical to v12. |
| **Submission HEAD (v14)** | `f12faba4` | manuscript v14. Adds the Phase-7E answer-identifiability result (Appendix F), relabels the task constraints K1--K5 to split them from the clarity components C1--C7, records why S3 is unmeasured, discloses the prospective panel's floor/ceiling anatomy, and cites classical generalizability and validity theory. **No paid model call, no new episode, no EDA tool run, no task-semantics change**; all three generated tables and every previously reported number are unchanged. **Retained as an immutable historical snapshot, recoverable byte-for-byte; v15 does not rewrite it.** |
| **Submission HEAD (v17)** | *(this revision)* | manuscript v17 — **current**. **Measures the joint model x family cell (S3)** by analysing 72 already-collected `deepseek-v4-pro` episodes on the same twelve frozen STA instances at k=2: +12.5 pp, 5 improving to 2 declining, sign test *p*=0.453, band −16.7 to +41.7 → **not established**, explicitly not "no effect". The arm's *execution* is not preregistered (it ran after the cost gate returned `ARM2_NOT_RUN`) and the manuscript says so; what governs the analysis is a plan committed before any of its outcomes was read, with the ordering checkable against git history and the report refusing to build without the plan. No control was relaxed: the report withholds aggregates iff a planned instance is missing, and this arm ran 12 of 12. Programme spend returns to one figure, ¥183.9329 of ¥200. The cost-gate narrative leaves the paper for `docs/`. **No paid model call, no new episode, no EDA tool run, no task-semantics change** — the 72 episodes already existed. Every generated table carrying a Study I, k=2 or k=6 number is byte-identical to v15. |
| Submission HEAD (v16) | `c8503f22` | manuscript v16 — **never pushed, never tagged, superseded by v17 before publication**. It disclosed the same 72 episodes and left them unanalysed. v17 reverses that judgement: a cell that is scientifically necessary, already collected and complete should be analysed, and an internal budget rule is not a reason to leave a hole in the evidence matrix. Recoverable in full from `c8503f22` and `591c9a99`. |
| Submission HEAD (v15) | `07f5bf7f` | manuscript v15. Makes the separately preregistered k=6 STA batch the primary S2-F evidence, keeps the k=2 batch as the earlier study reported alongside it, and never pools them. Records S3 as **not executed** (a preregistered arm refused by a preregistered cost gate), discloses the serving-endpoint change without treating it as an experimental factor, and states the Phase-8A process defects as three accounting requirements in the methods appendix. **No paid model call in this revision, no new episode, no EDA tool run, no task-semantics change**; all four v14-generated artifacts stay byte-identical, so no previously reported number moved. A review pass before freezing then named the k=6 panel as primary in the introduction as well as the abstract, corrected an unsupported inference in §6 about panel size, and fixed two phantom dangling references that `scripts/slim_link_check.py` had been reporting unread. A final wording pass then bounded two sentences to their evidence: the cross-batch concordance in §7 is now "largely did not" move, tagged `not a backend comparison` as well as post hoc and unpooled, and §5's heterogeneity claim reads *not wholly* an artifact of low repetition rather than *not plausibly*. |

`iclr2027-artifact`, this branch, is cut from `cc797ffe` and contains no experimental change at
all: only deletions, documentation, and the two verifier scripts. See
[`REMOVED.md`](REMOVED.md).

### Manuscript lineage

| Tag | Commit | Manuscript |
|---|---|---|
| `iclr2027-submission-v1` | `3d3e77b7` | v5 |
| `iclr2027-submission-v2` | `5858d843` | v7 — closed the Study I episode accounting (58 program-primary vs the 70-episode descriptive ledger) |
| `iclr2027-submission-v3` | `cc797ffe` | v12. Evidence-support claim lattice, symmetric claim qualification, estimand-aligned uncertainty |
| `iclr2027-submission-v4` | tags the commit recording `c7b3828a` | **v13.** The Phase-7D retrospective audit becomes the leading result: the tool-success signal is constant across 169 pairing-verified frozen trajectories and accepts all 82 semantically wrong bindings, so the typed provenance/authority oracle carries the entire measurement. Interpretation and positioning only. |
| `iclr2027-submission-v5` | tags the commit recording `f12faba4` | **v14.** Direct-answer disclosure excluded by deterministic enumeration; K1--K5 / C1--C7 separated; S3's absence given its methodological reason; panel anatomy disclosed; classical measurement theory cited. Interpretation, positioning and one zero-call derived analysis. |
| `iclr2027-submission-v6` | tags the commit recording `07f5bf7f` | **v15.** The k=6 STA batch becomes the primary S2-F evidence; the k=2 batch is retained and never pooled with it; S3 becomes *not executed* rather than *not measured*; the endpoint change is disclosed and is not an experimental factor. |
| *(untagged; held for review)* | *(this revision)* | **v17 — current.** S3 is measured and reported as *not established*. The arm's execution is not preregistered and the paper says so; its analysis plan predates its outcomes and is enforced mechanically. Nothing is pooled across the three STA batches. |
| *(untagged; superseded)* | `c8503f22` | v16. Disclosed the 72 S3 trajectories and left them unanalysed. Never published; superseded by v17. |

### Why the v12 freeze was reopened

A freeze exists so a version can be returned to exactly, not so that nothing may follow it. Two
things made v13 the more defensible option. First, the Phase-7D audit turned the paper's own
grading substrate into a measured result — the typed oracle was always the scoring basis, but its
contribution to measurement had never been quantified. Second, `arXiv:2605.10448` was public
before the v12 freeze and uncited by it, so submitting v12 would have meant shipping a positioning
known to be incomplete. v12's source and PDF hashes remain recorded and its PDF still rebuilds
byte-identically from its own commit; v13 is a new freeze, not an amendment.

**Phase-7D is labelled retrospective and post-freeze everywhere it appears**, in the manuscript and
in [`artifact_map.md`](artifact_map.md). It is not presented as a preregistered analysis, because it
is not one.

## Experiments are permanently closed

All paid model calls ended at `a89e084`. Nothing in this repository can or should reopen them:
there is no path from a checkout to a new episode, the frozen task semantics may not be altered,
and the manuscript's numbers are fixed. Attempting to "refresh" a result would change what the
paper reports without the preregistration that licensed the original measurement.

**Program accounting** (Appendix E and the reproducibility statement): 58 + 24 + 36 + 72 paid
primary episodes; committed-ledger cost ¥745.29. The descriptive Study I ledger reports **70**
workflow episodes — those 58 plus the 12 earlier controlled-pair episodes, which predate that
accounting and sit outside its cost ledger. The two counts are different on purpose and the
paper says so; `scripts/phase7c_study1_ledger.py` asserts both against the frozen program
manifest and aborts on mismatch.

## What is frozen, and what enforces it

| Object | Frozen by | Enforced by |
|---|---|---|
| membership code and task files — 1020 task files, 36 scripts, 6 generator files, 3 package modules; no test and no document carries a hash | **1065 `path → sha256` pins** in the pre-run manifests under `reports/evidence/` | `scripts/frozen_membership_verify.py`, run by `scripts/check` |
| `docs/phase7/phase7_synthesis.md` | sha256 recorded in `submission/FREEZE_HASHES.md` (`9dbecd9f…`) | that file; the doc must not move or change |
| `docs/synthetic_p14_phase4w_clarity_bundle_ablation_design.md` | cited **by path** as the pre-declared interpretation table in `reports/evidence/p14_phase4w_fairness/MANIFEST.json` | the manifest is frozen, so the path must stay valid |
| the three task families | per-episode custody byte-matching; canonical-hash verification before and after each episode | `scripts/canonical_integrity.py` (`FAILED_INTEGRITY` stop), `scripts/chain_executor.py` |
| `tasks/p14_workflow_handoff/workflow_handoff_0009/solution/flow_config.json` | tripwire test | `test_canonical_golden_fingerprint_intact` in `tests/test_fullpath_check.py` |
| `submission/main.pdf` | `SOURCE_DATE_EPOCH` pinned in the Makefile | rebuild is byte-identical; sha256 in `FREEZE_HASHES.md` |

### The three findings the custody gate carries forward

`frozen_membership_verify.py` reports non-zero counts, and that is correct rather than a defect to
be tidied. `docs/frozen_membership_baseline.json` records the state as of `cc797ffe`:

- **9 missing** — `circuit_built.sp` under nine p16 instances. HSPICE build products, gitignored;
  the manifests pinned them at run time, the repository never tracked them.
- **2 mismatch** — `generators/p15_sta_handoff_gen.py` and `p16_spice_handoff_gen.py` were edited
  after the phase-5B/5C freeze. **The reported numbers derive from the pinned versions.** The
  drift is pre-existing and is stated rather than erased.
- **1 multi-sha** — `scripts/phase5c_run.py` is legitimately versioned across phases, so several
  hashes are pinned for it and "differs from one of them" is not drift.

The gate asserts *reproduces this baseline*, not *reports nothing*. A verifier tuned until it
prints zero would hide the next real mutation.

## Exploratory versus confirmatory

Appendix E states this in the paper; the short version, because it governs how any result here may
be read:

- **Exploratory** — discovery of the tool-green axis-binding failure; the transport repair; the
  workflow controlled pair; construction of the clarity bundle. **BundleS was selected during this
  stage, so its development-instance cell (S0) is exploratory by construction.** Also exploratory:
  the cross-model arm and the entire component decomposition (C1; Schema vs Contract; C2-only,
  C4-only, C24 and the C24 bridge).
- **Freeze point 1** — BundleS fixed as C1+C2+C4+C7 with C6 withheld, and the held-out instance
  frozen, *before* the held-out evaluation ran. S1 is therefore the only cell described as
  replicating anything.
- **Freeze point 2** — for the prospective STA study the instance panel, its size (*n*=12), the
  conditions, the randomization schedule and the analysis were all committed *before any paid call
  of that phase*. Sample size was not adapted; no analysis was chosen after seeing outcomes.
- **Confirmatory** — the prospective STA panel is the study's only preregistered confirmatory test
  of transfer, and it did not establish an effect.

Preregistration: [`phase7/phase7a_preregistration.md`](phase7/phase7a_preregistration.md). Phase
matrix and freeze points: `reports/synthetic_p14_phase4z_freeze_manifest.json`.

## One preregistered study was never executed

The blinded human construct-validity study (Study B) is preregistered in
[`phase7/phase7b_annotation_freeze.md`](phase7/phase7b_annotation_freeze.md), with packets
generated by `scripts/phase7a_annotation_packets.py`. It was **not** executed: qualified
independent annotators were unavailable, and **no LLM annotator was substituted**. The paper
therefore claims a formal construct, not agreement with expert human judgement.

## One episode was replaced, for validity only

`reports/evidence/phase7a_state.json` records `replaced: 1`. The discarded artifact is preserved
under `reports/evidence/phase7a_discarded/` with a note recording its original path and run
timestamp — it had never been in git, and deleting the raw run trees without rescuing it would
have destroyed the only record of the single validity-only replacement the paper discloses.

## Verifying this branch

```bash
scripts/check                                          # tests + task structure + the 1065 custody pins
python3 scripts/slim_link_check.py                     # no dangling repository references
python3 scripts/phase7c_study1_ledger.py --check       # 58 + 12 = 70
python3 scripts/phase7c_claim_statistics.py --check     # 12.5 / [-12.5, 41.7] / -16.7
python3 scripts/phase7d_semantic_proxy_gap.py --check   # 169 included / 82 tool-green wrong
python3 scripts/phase7e_answer_identifiability.py --check  # 294 universe; BundleS 9-147, never 1
cd submission && make distclean && make                # 22 pp (main text 9), sha256 unchanged
python3 scripts/submission_page_limit_check.py         # main text ends on p9 (ICLR limit 9)
```

`make clean` deliberately keeps `main.pdf`; use `distclean` before any build whose log you intend
to measure. A v9 page-count measurement was once taken off a stale PDF because `make` was a no-op,
which is why the gate counts pdflatex start banners rather than trusting that a log exists.

`VERIFICATION.md` at the repository root records the output of every gate for this branch.
