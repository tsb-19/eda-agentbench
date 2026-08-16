**English | [中文](provenance.zh.md)**

# Provenance — which commit produced what, and what is frozen

A measurement is reproducible only if you can say exactly which state of the repository produced
it. This document resolves the paper's claims to explicit commits and states what may no longer
change. It replaces the benchmark-era status document and absorbs the Phase-6C freeze attestation.

## Two explicit HEADs

| | Commit | Meaning |
|---|---|---|
| **Experiment freeze HEAD** | `a89e084` | *"report(phase5d): TypedContract extension complete 36/36"*. **No experiment, paid model call, or task/model asset beyond this commit contributes to the paper.** Every reported number is re-derived from committed ledgers at or before it. |
| **Submission HEAD** | `cc797ffe` (tag `iclr2027-submission-v3`) | manuscript v12, frozen. Ahead of `a89e084` by documentation and submission work only — no new experimental result. |

`iclr2027-artifact`, this branch, is cut from `cc797ffe` and contains no experimental change at
all: only deletions, documentation, and the two verifier scripts. See
[`REMOVED.md`](REMOVED.md).

### Manuscript lineage

| Tag | Commit | Manuscript |
|---|---|---|
| `iclr2027-submission-v1` | `3d3e77b7` | v5 |
| `iclr2027-submission-v2` | `5858d843` | v7 — closed the Study I episode accounting (58 program-primary vs the 70-episode descriptive ledger) |
| `iclr2027-submission-v3` | `cc797ffe` | **v12 — final.** Evidence-support claim lattice, symmetric claim qualification, estimand-aligned uncertainty |

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
cd submission && make distclean && make                # 15 pp, sha256 unchanged
```

`make clean` deliberately keeps `main.pdf`; use `distclean` before any build whose log you intend
to measure. A v9 page-count measurement was once taken off a stale PDF because `make` was a no-op,
which is why the gate counts pdflatex start banners rather than trusting that a log exists.

`VERIFICATION.md` at the repository root records the output of every gate for this branch.
