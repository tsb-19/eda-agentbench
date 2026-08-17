# Phase-7E Submission Freeze (v14 — direct-answer disclosure excluded; measurement theory cited)

**Submission HEAD:** `b281137f`. v14 was assembled over two commits — `5ac63be6` added the
answer-identifiability probe, its regression tests and its report, touching no manuscript file;
`b281137f` is the manuscript. The hashes below are `b281137f`'s. One further commit records the tag
and the documentation updates; it touches no build input and rebuilds to the same PDF byte-for-byte.
**Experiment freeze HEAD:** `a89e084` (immutable). **v14 ran no model calls, no EDA tool and no new
episode, and altered no experimental record.**
**v13 remains an immutable historical snapshot:** source `64b7f0b8…`, PDF `6f64140d…`, 18 pp, tag
`iclr2027-submission-v4`. **v12** likewise: source `82cb22da…`, PDF `bbf948bf…`, 15 pp. v14 is a
*new* freeze, not an amendment of either.
**Previous freezes:** v13 = `c7b3828a`, tagged `iclr2027-submission-v4`. v12 = the commit that added
its section below. v11 = `95128e11`. v10 = `ff9b6b44`. v9 = `7c2f9c4f`. v8 = `83379da4`. v7 =
`5858d843`, tagged `iclr2027-submission-v2`. v5 = `3d3e77b`, tagged `iclr2027-submission-v1`.
**None of those tags moves.**

## Why v14 exists

A mock expert review of v13 identified one alternative explanation that would have materially
weakened the paper's only positive result, and it was answerable without any new measurement: that
BundleS does not help an agent reason but simply narrows the answer to one. v13 flagged this itself
as "the single most informative experiment not yet run." It turned out not to need an experiment —
only deterministic enumeration over already-frozen files — so leaving it open would have meant
shipping a paper whose central positive cell had an unexcluded trivial explanation that the paper
named on its own.

Four smaller items travelled with it, each a correctness or positioning defect rather than polish:

1. **A notation collision.** The frozen task files number the five task constraints C1–C5 and the
   clarity components C1–C7. Constraint C5 *is* the sign-off pair, and component C6 is what asserts
   it — so the two systems collided precisely where the disclosure argument lives. The manuscript now
   says **K1–K5** for task constraints and states the relabel; the frozen stimuli keep their own
   numbering, because rewording an experimental stimulus would change the measurement.
2. **S3's absence had no stated reason.** The paper reported the cell as unmeasured without saying
   why. The reason is methodological, not budgetary, and is now on the record.
3. **The prospective panel's heterogeneity was derivable but unstated.** Per-instance outcomes were
   already published; that six instances are floor-limited and one ceiling-limited was left for the
   reader to work out.
4. **Classical measurement theory was used and uncited.** "Construct validity" appeared with no
   reference attached, and the claim-scope lattice restates facet- and external-validity reasoning
   that predates this field by decades. Not citing it read as ignorance of the tradition.

### What changed

| | v13 | v14 |
|---|---|---|
| Direct answer disclosure | flagged as the most informative test not yet run | **excluded by enumeration**: BundleS leaves 9–147 of 294 candidates, never 1, at S0 and S1 |
| Task constraints | C1–C5, colliding with components C1–C7 | **K1–K5**, with the relabel stated |
| S3 | "not measured" | not measured **and why**: adding it post-outcome would make the ladder outcome-adaptive |
| STA panel | 3 improve / 2 decline / 7 tie | plus **6 floor / 1 ceiling / 5 informative**, leave-two-out (*n*=10) −5.0 pp |
| Measurement theory | uncited | Brennan, Shadish–Cook–Campbell, Messick, plus one recent LLM-benchmark treatment |
| Bibliography | 16 entries | 20 entries |
| Main text | 9 pp | 9 pp (unchanged; additions paid for after the last float) |

### Page cost, and a re-confirmed layout fact

Main text was already exactly 9 pp with zero slack. Every addition had to be paid for **after the
last main-text float**, which is the only region where a cut moves the boundary. This was
re-confirmed the hard way: trimming ~30 words *before* the last float moved the REFERENCES heading
by exactly 0.00 pt, and resizing two main-text tables moved it by 0.00 pt as well — float repacking
absorbs both. Progress came only from the tail. The Discussion was merged into the Conclusion (which
also reclaimed a section heading's vertical space), the Limitations items were tightened, and one
Conclusion sentence was dropped as duplicative of §6 and Table 4's caption. **All eight limitation
claims and both Discussion assertions survive**; the `app:falsif` pointer moved into an appendix,
where space is free.

## SHA-256 hashes (frozen artifacts, v14)
| Artifact | SHA-256 | vs v13 |
|---|---|---|
| Source (main.tex) | `d0fdc5a2d13ffb0b68acd57174730b871499765cfe55ba689ac522d359a6ab65` | changed |
| Final PDF (main.pdf, 20 pp: 9 main + refs + appendix; 301 763 B) | `95664f93161eb3c23a00f971cad0000f4422e5d859cf690f0b8dec5c6cba0b32` | changed |
| Bibliography (references.bib, 20 entries) | `6817858d2c1a5346e77fb79483fe779d9fbed6217284a71a1eeda04e69fb2d8c` | changed |
| Generated ledger table (tables/study1_ledger.tex) | `fdf6c50c2e0c837e96c33c88a1a37bd5a88eb503ed98669de38c4b9fdb99b7c6` | **identical** |
| Generated pilot table (tables/sta_pilot.tex) | `95cb8d73b4de9d368b0b986f22fe1c92810c43ab7b358a22f6723b7bf8aaf32b` | **identical** |
| Generated stat macros (tables/claim_stats.tex) | `40f4b24d1f5b3a2c0c1a57a7fd01125908f4b84f41d7f09343a95d10f3c3b96f` | **additive only** |
| Phase-7E analysis (reports/synthetic_phase7e_answer_identifiability.json) | `9f77ff07ed18f2aa3bf5ff81e9b881f9967daf29abe725f3befd3c7addfa1dea` | new |
| Phase-7E probe (scripts/phase7e_answer_identifiability.py) | `d65bf72ba9b42fc771105a33d1101f88ad35ebc82cd38280b0281243d43c2bb5` | new |
| Claim statistics (scripts/phase7c_claim_statistics.py) | `ebb94c82636a0fa52f2d837b6dabf4836d50b620e1c9dc7b108c63e6ba4a8044` | changed |
| Phase-7D analysis (reports/synthetic_phase7d_semantic_proxy_gap.json) | `e0370a04ba6de10554b8caada29507ec27c0775b8558633d4a2b31c46fb8aa28` | **identical** |
| Claim-evidence matrix (docs/phase7/phase7_synthesis.md) | `9dbecd9fedc65ac19bc5ab1c14589013942f746cf18c2b3900c9627b317f961b` | **identical** |

**On "additive only".** Two of the three generated tables are byte-identical. The third,
`claim_stats.tex`, differs by exactly **four added lines** — `\StatStaFloorN`, `\StatStaCeilingN`,
`\StatStaInformativeN`, `\StatStaLeaveTwoOut` — with **no pre-existing macro modified or removed**
(`git diff` shows four insertions and zero deletions). So the v13 mechanical proof still holds in the
form that matters: **no previously reported derived number moved in v14.** +12.5, [−12.5, 41.7],
−16.7, 58+12=70 and 169/82 are all unchanged, and the panel-anatomy figures are new derivations from
the same frozen records rather than revisions of old ones. The claim-evidence matrix and the Phase-7D
report are untouched, because retroactively editing a frozen custody record would break the chain it
exists to document.

**A precision note carried deliberately.** The leave-two-out figure is **−5.0 pp** at *n*=10 — the
two dominant instances are *dropped*. Zeroing them inside *n*=12 gives −4.2 pp. These are different
operations on the same data and the payload records both, because an earlier draft of this work
quoted the second while describing the first.

**Verification performed for v14:** two independent `make distclean && make` builds give the same PDF
sha256 (byte-reproducible); 3 pdflatex start banners counted rather than assuming a log exists; 0
Overfull boxes, 0 undefined references or citations and 0 multiply-defined labels in the final pass;
the page-limit gate passes with **0 main-text words above the REFERENCES heading** and its negative
control still exits 1 at `--limit 8`; anonymity re-scanned (PDF metadata Title/Author/Subject/
Keywords empty, 0 infra or forge leaks in PDF text); 20 bibitems rendered and all four new citations
present; `scripts/check` passes at the recorded 1065/9/2/1 baseline; and all five `--check` analyses
reproduce their committed outputs.

## Why v13 exists

Two reasons, both external to the manuscript's own argument:

1. **A post-freeze derived analysis turned the grading substrate into a measured result.** The typed
   provenance/authority oracle was always the paper's scoring basis, but its *contribution to
   measurement* had never been quantified. Phase-7D pairs each frozen episode's semantic verdict with
   its family's own pre-existing tool-success field and finds the tool signal **constant** across all
   169 retained trajectories, accepting all **82** semantically wrong bindings. That is a result, not
   infrastructure, and it belongs ahead of the claim-scope framework.
2. **The related-work landscape moved before the v12 freeze and v12 did not reflect it.** arXiv:2605.10448
   (2026-05-11) studies whether stored evidence supports a claimed outcome — published *before* the v12
   freeze and uncited by it. Two further 2026 works (arXiv:2605.11039 argument-level provenance with
   role-specific authority contracts; arXiv:2607.24054 auditing success provenance) sit close enough
   that omitting them would misstate what is novel here. Submitting a v12 whose positioning is known
   to be incomplete is worse than producing a recorded v13.

**No experiment was added, no task semantics changed, no episode re-run, no derived experimental
number moved.** All three generated tables are byte-identical to v12 (verified below), which is the
mechanical proof of that last claim.

### What changed

- **Abstract** now opens with the measured result under four load-bearing qualifiers that must not be
  trimmed for concision — *our* (not agent benchmarks generally), *deliberately tool-green* (a
  property of the construction), *retrospective audit* (not preregistered), *hash-verified pairing*
  (why 169 and not 202). The claim-scope framework follows as the third sentence rather than the first.
- **§1** opens on the problem (a valid tool answer to the wrong question) before the framework.
- **Contributions reordered:** (1) semantically attested evaluation, with the 169/82 result; (2) the
  two never-collapsed binding-failure subtypes; (3) the claim-scope framework and qualification
  standard, now carrying the transfer study; (4) measurement validity, restated as *a verdict must be
  bound to the artifact it judges, and an oracle inherits the custody of its reference standard*.
- **§3** gains the retrospective result, explicitly labelled post-freeze, with the two readings it does
  not license stated inline.
- **§6** gains *"A verdict is only about the artifact it can be shown to describe"* — 9 of 58 historical
  workflow runs excluded because the recorded tool verdict did not attest the final submitted artifact,
  where tuple equality would have caught two of nine. Positioned immediately before the reference-standard
  custody paragraph, so the two read as one principle at two levels.
- **§2 Positioning** bounds the claim against five works and explicitly disclaims priority over the
  general observation that a reported success can be unearned.
- **Conclusion** leads with the discrimination result.
- **§7 gains a harness-scope limitation.** ``Harness'' in this paper means the *task-level information
  structure* (§2), not the agent scaffold. Every episode ran through our own controlled research
  runner, so the 82-of-169 occupancy rate is a property of that scaffold and does not extrapolate to
  production coding agents; what does not depend on the scaffold is that a tool-success field cannot
  discriminate role binding, which is a property of the task and its oracle. Cited to arXiv:2607.22585,
  whose finding is precisely stated: harness choice moved pass rates only 0–8 pp but produced
  scaffold-specific, largely model-independent *failure fingerprints*.
- **Four citations added** (12 → 16), each verified against arXiv before use.

### Page cost, paid by relocation rather than deletion

Main text was at the 9-page limit with **0 headroom**, and the additions cost ~770 words. No claim was
deleted. Four blocks moved to appendices intact, and prose that stated something twice was compressed
to state it once:

| Moved to appendix | From | Now |
|---|---|---|
| the seven "what would change each conclusion" conditions | §7 | App. D |
| full four-tier qualification definitions | §3.1 | App. E |
| three closest concurrent works + transfer-dimension literature | §2 | App. J |
| per-stratum table, exclusions, pairing sensitivity | §3 | App. F |

Compressed in place (no claim removed): §3's lattice paragraph (restated §1), §5's sensitivity-band
explanation (Appendix C re-derives it more strictly), §7's Discussion, and both custody paragraphs.
The harness-scope limitation was paid for the same way: §6's *"why the controls materially affected
interpretation"* paragraph was folded into §7's Discussion, which already carried its point, and four
sentences that restated a fact stated elsewhere were tightened.

**A layout fact worth recording:** removing text *before* the last float does not shorten the tail —
the floats simply repack and absorb the space. Only cuts after the final table (here Table 3) move the
page-9 boundary. Two rounds of word-level trimming earlier in the paper changed the overflow by four
words; folding one paragraph after Table 3 cleared it.

| | v12 | v13 |
|---|---|---|
| main text | 9 pp (p1–p9) | **9 pp (p1–p9)** |
| submission headroom (limit 9) | 0 pp | **0 pp** |
| rebuttal headroom (limit 10) | 1 pp | 1 pp |
| references | p10 | p10 |
| appendix | A–G, p10–p15 | **A–J, p11–p18** |
| total | 15 pp | **18 pp** |
| main-text words | 5805 | 5879 |

Both word counts are measured the same way — every `pdftotext -bbox` word on p1–p9 except the running
head and the line-number ruler — and both PDFs were measured in the same run, so the +74 is a real
delta and not a change of method. (An earlier v13 draft of this table recorded 5741/5795 from a
slightly different furniture filter; the pair above supersedes it.)

## SHA-256 hashes (frozen artifacts, v13)
| Artifact | SHA-256 | vs v12 |
|---|---|---|
| Source (main.tex) | `64b7f0b8ff54417087189399667054bedda49f442e666d6c59dddc19113e1916` | changed |
| Final PDF (main.pdf, 18 pp: 9 main + refs + appendix; 283 476 B) | `6f64140d9ea8f5aa9e95af8a20d112b9cd4cdbe00fbd1e5bccfb21b1778de7c9` | changed |
| Bibliography (references.bib, 16 entries) | `682dc716b6bb29f1c4e7e8d81ef36d8de903a5e09aebf2451398659baaeec1a6` | changed |
| Generated ledger table (tables/study1_ledger.tex) | `fdf6c50c2e0c837e96c33c88a1a37bd5a88eb503ed98669de38c4b9fdb99b7c6` | **identical** |
| Generated stat macros (tables/claim_stats.tex) | `5c0b2577d7fb06be9992cf228767e2d5c317065d8dc51f6d679d6de5e5f36615` | **identical** |
| Generated pilot table (tables/sta_pilot.tex) | `95cb8d73b4de9d368b0b986f22fe1c92810c43ab7b358a22f6723b7bf8aaf32b` | **identical** |
| Phase-7D analysis (reports/synthetic_phase7d_semantic_proxy_gap.json) | `e0370a04ba6de10554b8caada29507ec27c0775b8558633d4a2b31c46fb8aa28` | new |
| Phase-7D generator (scripts/phase7d_semantic_proxy_gap.py) | `b0e4600edc92b4ea7d849087e76c2d3af51c68e02c3c3db6c59a9b2fa17f25ac` | new |
| Claim-evidence matrix (docs/phase7/phase7_synthesis.md) | `9dbecd9fedc65ac19bc5ab1c14589013942f746cf18c2b3900c9627b317f961b` | **identical** |

The three generated tables being byte-identical is the mechanical proof that **no derived experimental
number moved in v13**. The claim-evidence matrix is likewise untouched: it is a frozen Phase-7 record,
and retroactively editing it would break the custody chain it exists to document. The v13 claim is
recorded in `docs/artifact_map.md` instead.

**Verification performed for v13:** two independent `make distclean && make` builds give the same PDF
sha256 (byte-reproducible); 3 pdflatex start banners counted rather than assuming a log exists; 0
Overfull boxes and 0 undefined references or citations in the final pass; anonymity re-scanned (PDF
metadata empty, 0 infra or forge leaks in PDF text, source and generated tables); every number written
into the manuscript re-checked against the committed Phase-7D JSON; `scripts/check`, both Phase-7C
`--check` scripts, the Phase-7D `--check` and the repository link check all clean.

**The page limit is now asserted by code, not by a measurement someone remembered to take.**
`scripts/submission_page_limit_check.py` locates the `REFERENCES` heading and fails if any main-text
word is typeset *above* it on the heading's own page — the exact condition ICLR's 9-page rule is about.
The naive test it replaces ("the heading is on page 10, so the main text is 9 pages") reported 9 pp
during this very revision while 580 main-text words sat above the heading on page 10. The gate is
fail-closed: a missing PDF, a missing `pdftotext`, an unlocatable or duplicated heading, an empty
extraction, or an unrecognised string in the top margin each fail rather than pass quietly. It was
proven non-vacuous against a deliberately overflowing build (caught: 21 words, 10 pp) and
cross-validated against the frozen v12 PDF, which it independently confirms at 9 pp. 16 regression
tests in `tests/test_submission_page_limit.py` require each failure branch to fire.

---

# Phase-7C Submission Freeze (v12 — notation cleanup; framework frozen)

**Submission HEAD:** the commit that adds this file.
**Experiment freeze HEAD:** a89e084 (immutable). **v12 ran no model calls and altered no experimental record.**
**Previous freezes:** v11 = `95128e11` (committed, never tagged). v10 = `ff9b6b44`. v9 = `7c2f9c4f`. v8 = `83379da4`. v7 = `5858d843`, tagged `iclr2027-submission-v2`. v5 = `3d3e77b`, tagged `iclr2027-submission-v1`. **Neither of those two tags moves.**

## Why v12 exists

The fifth reviewer-standard read closed the structural line entirely: **no conceptual, statistical or
evidence-to-claim objection remains at reject level**, and the reviewer stopped hunting for defects.
What remained was **three wording items, all non-decision-critical**, plus an explicit instruction to
freeze afterwards. Two were applied; the third was a deliberate *non*-edit.

**v12 touches `main.tex` only.** Every other frozen artifact — all three generated tables, both
generators, both data reports, `references.bib`, the `Makefile`, both style files, the claim-evidence
matrix — is byte-identical to v11, verified by `git diff --quiet`. **No derived number moved:** a
numeric-token diff of the v11 and v12 rendered PDFs gives 830 tokens on both sides, **identical**.

### 1. `claim` / `evidence-for-a-claim` shorthand made consistent with the v11 E/T split

**Defect.** v11 introduced the evidence support $E$ and the target support $T$, and made the point
that $E$ is what *audits* a claim rather than what the claim asserts. But five sentences elsewhere
still carried the pre-v11 shorthand "indexes **a claim** by the set of configurations **its evidence**
occupies" — which names the claim as the indexed object, exactly the conflation §1 now separates.
Not a new conceptual problem; an inconsistency that the E/T distinction made conspicuous.

| location | v11 | v12 |
|---|---|---|
| Abstract | "index **a harness-effect claim** by the set of (family, instance, model) configurations **its evidence** occupies" | "index **the *evidence* for** a harness-effect claim by the set of (family, instance, model) configurations **it** occupies" |
| §1 Contribution (1) | "indexes **a harness-effect claim** by the set of configurations **its evidence** occupies" | "indexes **the *evidence* for** a harness-effect claim by the set of configurations **it** occupies" |
| §2 Positioning (prior work) | "None of the three indexes **a harness-effect claim** by the scope **its evidence supports**." | "None of the three indexes **the evidence for** a harness-effect claim by the **support it occupies**." |
| §2 Positioning (our contribution) | "locating **a claim** by the set of configurations **its evidence** occupies" | "locating **the *evidence* for a claim** by the set of configurations **it** occupies" |
| §8 Conclusion | "indexes **a claim** by the set of configurations **its evidence** occupies" | "indexes **the evidence supporting a claim** by its **measured configuration support**" |

The reviewer named the Contribution (1) and Conclusion occurrences. The Abstract and the two §2
occurrences are the *same* shorthand and were fixed for the stated reason — full-text notation
consistency — rather than left to read against §1. **0 occurrences of "its evidence occupies" remain.**

### 2. The sensitivity band now says what the resampling actually perturbs

**Defect.** §5 described the band as measuring "how strongly the estimate depends on **which**
instances the panel happens to contain", while Appendix C states the stricter and correct thing: a
with-replacement draw duplicates some instances and omits others, so what is perturbed is the panel's
**empirical weighting**, not its membership list.

| location | v11 | v12 |
|---|---|---|
| §5 S2-F | "how strongly the estimate depends on *which* instances the panel happens to contain" | "how strongly the estimate depends on the panel's *empirical composition*" |

More accurate and two words shorter. **0 occurrences of "happens to contain" remain.**

### 3. A deliberate non-edit, recorded so it is not re-litigated

Appendix C's *"We deliberately do not add a third interval or a hierarchical model to absorb it…"*
was flagged as **correct but the first line to cut** if a future revision needs space — the factual
limitation is fully carried by the two sentences before it. It is **kept in v12** and is hereby the
head of the page-cost queue for any camera-ready trimming. No other reserved cut exists.

### 4. Page budget

The two applied edits are net +5 words across the whole document (8762 → 8767) and cost no line:
main text stays 9 pp, Conclusion still ends on p9, References still begin on p10.

| | v11 | v12 |
|---|---|---|
| main text | 9 pp (p1–p9) | **9 pp (p1–p9)** |
| submission headroom (limit 9) | 0 pp | **0 pp** |
| rebuttal headroom (limit 10) | 1 pp | 1 pp |
| references | p10 | p10 |
| appendix | A–G, p10–p15 | A–G, p10–p15 |
| total | 15 pp | 15 pp |

## SHA-256 hashes (frozen artifacts, v12)

| Artifact | SHA-256 |
|---|---|
| Source (main.tex) | 82cb22da00f74fa751f008060abebc419de29f599a560fc0d49fa07c2c95b473 |
| Final PDF (main.pdf, 15 pp: 9 main + refs + appendix) | bbf948bfc533e3162eef4a299a1215b2664b0d3189bccc51ed65d257aba7a2e1 |
| Generated ledger table (tables/study1_ledger.tex) | fdf6c50c2e0c837e96c33c88a1a37bd5a88eb503ed98669de38c4b9fdb99b7c6 |
| Generated stat macros (tables/claim_stats.tex) | 5c0b2577d7fb06be9992cf228767e2d5c317065d8dc51f6d679d6de5e5f36615 |
| Generated pilot table (tables/sta_pilot.tex) | 95cb8d73b4de9d368b0b986f22fe1c92810c43ab7b358a22f6723b7bf8aaf32b |
| Ledger generator (scripts/phase7c_study1_ledger.py) | 3d7452be5abbe2eb1e39249b4bfa512fcafecf10bd41dbc1aaca3dddc0143615 |
| Statistics generator (scripts/phase7c_claim_statistics.py) | e406a669dc736359a12417acc9943768ec36d1da92c3327544be644b56be2bc0 |
| Ledger data (reports/synthetic_p14_study1_ledger.json) | 2a548fce361487384a11b7ab0a59faed520230d32c18075ab1e2609590038e86 |
| Statistics data (reports/synthetic_p14_claim_statistics.json) | 67dde79c13041f57c9101b1c5064971a4fdf85f2921f94a18643579a38c06832 |
| Bibliography (references.bib, 12 entries) | 7939a80c45fe78d6af4879d4d1279e2cd0e2653be39062e6ca04b6cfb1135f15 |
| Style (iclr2027_conference.sty) | 797deef41724e93761426ac0cbcca46279a91cc650dd1f0ce76a4f08d2098ea6 |
| Bibstyle (iclr2027_conference.bst) | 2d67552db7ed38ccfccb5957b52f95656e25c249724761d3cf5f7922ad1844c5 |
| Claim-evidence matrix (docs/phase7/phase7_synthesis.md) | 9dbecd9fedc65ac19bc5ab1c14589013942f746cf18c2b3900c9627b317f961b |

Byte-identical to v11 (and to v5–v10 where applicable): **every artifact above except `main.tex` and
`main.pdf`**. **No derived experimental number changed in v12.** `references.bib` unchanged — 12
entries, no addition, per the reviewer's explicit advice and ICLR 2027 policy (comparison against
arXiv-only concurrent work is not required and its absence is not a rejection basis).

## Change verification (v11 → v12)
- **No experimental record touched.** No paid call; `git status --porcelain -- tasks/` empty; the
  frozen manifests and evidence tree were read, never written.
- **Change scope proved, not asserted.** `git status --porcelain` lists exactly
  `submission/main.tex` and `submission/main.pdf`. `git diff --quiet HEAD -- submission/tables
  submission/references.bib submission/*.sty submission/*.bst submission/Makefile scripts/ reports/
  docs/` returns clean.
- **Word-level diff of the rendered text** (hyphenated line-breaks rejoined, ICLR margin numbers and
  page headers stripped) yields **18 change regions: 13 belong to the six intended edits and 5 are
  pure reflow** (a hyphenation point or an em-dash line break moving). **No unintended text change.**
- **Numeric-token diff: 830 vs 830, identical.** No number, interval, p-value, count or date moved.
- **Ledger arithmetic re-derived from the rendered PDF** (not from the script): 21 body rows sum to
  41/70 with 24 axis and 5 value, matching the printed totals row exactly; **0** rows violate
  correct+axis+value=$k$.
- **Generator self-checks** reproduce their committed outputs under `--check`
  (`{"ok": true, "sta_delta_pp": 12.5, "sta_band_pp": [-12.5, 41.7], "pilot_delta_pp": -16.7,
  "fisher": {"S0": 0.4, "S1": 0.4, "S2-M": 1.0}, "resolved_snapshot_retained": false}` and
  `{"ok": true, "episodes": 70, "correct": 41, "axis_binding_failure": 24,
  "role_conditioned_value_selection_failure": 5, "cells": 21, "total": 70}`).
- **Citation integrity:** 12 entries, 12 cited, 0 uncited, 0 undefined, 12 rendered.
- **Claim audit:** 0 occurrences of "its evidence occupies", "happens to contain", "cannot encode",
  "not attributable to disclosing", "five points", "coordinate class", "effect is real",
  "unidentified", "external process", or any stray `Level~N`. Both "confidence interval"
  occurrences are explicit denials. All **29** `establish*` occurrences (counted on
  newline-flattened text — see the v11 record for why 29 and not 25) are a negation, an explicit
  denial, the definition of the standard, the *not-licensed* column of Table 1, a cited work's
  title, or the *"What it establishes"* header of the prior-work table — **0 positive uses about our
  own results**.
- **Build:** 0 errors, 0 undefined references, 0 undefined citations, 0 real bibtex warnings
  (`Warning--` count 0). **Overfull hboxes 0**; underfull 34 (cosmetic page-fill slack). Counts read
  from the **final pass only** of a `distclean` build whose log was confirmed to contain 3
  `This is pdfTeX` banners, i.e. the build actually ran.
- **PDF reproducibility:** two consecutive `make distclean && make` runs produce byte-identical PDFs
  (`bbf948bf…`).
- **Anonymity:** 0 hits in PDF text for infra/path/user/credential/repository patterns; PDF metadata
  Title/Author/Subject/Keywords all empty.
- **Repository gate:** `scripts/check` **PASSED 2985/2985**.
- **Tags unmoved:** `iclr2027-submission-v1` → `3d3e77b7…`, `iclr2027-submission-v2` → `5858d843…`.

## ICLR 2027 compliance audit
- Main text ≤9 pages: **PASS** (9 pp, p1–p9; Conclusion ends on p9). **0 pages of headroom at
  submission**, 1 at rebuttal/camera-ready where the limit rises to 10.
- References outside page limit: **PASS** (begin on p10).
- Appendix after references: **PASS** (A–G, p10–p15). Reviewers are not required to read it, which is
  why every load-bearing claim, the E/T distinction, §3.1, the main results, the pilot reversal, the
  measurement incidents and the limitations all sit in p1–p9.
- Double-blind anonymity: **PASS** (0 leaks in PDF text and generated tables).
- PDF metadata anonymous: **PASS**.
- AI-use statement / Ethics statement / Reproducibility statement: **PASS** (all present, outside the
  page limit).
- Citations: **PASS** (12 entries, arXiv-verified, 0 placeholders). No comparison against arXiv-only
  concurrent work is required by ICLR 2027 policy, and its absence cannot be a rejection basis.
- Build: **PASS**. Repository gate: **PASS** (2985/2985).
- Generator self-checks: **PASS** (both `--check` modes reproduce their committed outputs).
- OpenReview upload: **HUMAN STEP** — abstract Sept 18, 2026 AOE; full paper Sept 25, 2026 AOE.

## Known gaps this revision deliberately does not close
Unchanged from v8–v11; each is stated in the manuscript as a limitation rather than silently omitted:
- **Human construct validity (Study B)** — preregistered, unexecuted; no LLM annotator substituted.
- **Bundle-only leakage control** — flagged in §7 as the single most informative experiment not run.
  v11 aligned the two BundleS sentences with this gap; v12 changes nothing here.
- **Backend snapshot provenance** — unrecoverable for episodes already collected.
- **Second independent coder for the Terminal-Bench probe** — single-coder, no agreement statistic.
- **S3 (joint model × family)** — never measured; reported as an empty cell.
- **Trajectory-level Monte-Carlo uncertainty** — not quantified anywhere; stated as a limit on what
  the sensitivity band may be read to mean.

## Freeze status
**The manuscript is frozen at v14**, on branch `iclr2027-artifact`. The v13 freeze (tag
`iclr2027-submission-v4`) and the v12 freeze below both stand as immutable historical snapshots; v14 is
a new freeze, not an amendment.

A v14-specific corollary, stated because it is the boundary this round tested: **a genuine alternative
explanation of a reported result is grounds to reopen a freeze; wanting a better-scoring paper is not.**
The answer-identifiability probe qualified because it could have overturned the paper's own positive
cell — and was run knowing that. The four items that travelled with it qualified because each was a
correctness or attribution defect (a notation collision, an unstated reason, an underivable-from-prose
fact, an uncited tradition), not a rewording. **No further post-hoc analysis should be added before
submission.** The search for new derived results is closed at Phase-7E.

The v13 status text follows.

### v13 freeze status (historical)
**v13 was frozen** on branch `iclr2027-artifact`, tagged `iclr2027-submission-v4`. The v12 freeze below still stands as an immutable historical snapshot; v13
did not amend it.

The reasoning that closed v12 applies unchanged to v13, and is the reason this section is not
rewritten with each revision: the structural audit is over, and **the dominant risk is no longer
unfound defects but over-optimization reintroducing inconsistency.** Further edits should be made
only for a concrete external reason — OpenReview formatting, a reviewer request during rebuttal, or a
verified change in the official requirements — not for further polish. Two v13-specific corollaries:
the manuscript's scientific content is closed, and a *secondhand* report of a changed requirement is
a reason to re-verify against the official site, not a reason to edit (see Deadlines, below, for the
case where doing so would have introduced an error).

Historically, for v12: **the manuscript was frozen at v12**, and that freeze point is published —
branch `master` and tag `iclr2027-submission-v3` are pushed to the origin remote.

## Provenance of the frozen points
- `iclr2027-submission-v1` → `3d3e77b` — v5. **Not moved.**
- `iclr2027-submission-v2` → `5858d843` — v7. **Not moved.**
- `0e82e59` → v6. `83379da4` → v8. `7c2f9c4f` → v9. `ff9b6b44` → v10. `95128e11` → v11. All untagged.
  `ef1a8d49` → **v12, the freeze point**, tagged **`iclr2027-submission-v3`** (lightweight, like its
  two predecessors: the repository is public and an annotated tag would write tagger identity into a
  double-blind submission). That commit records that tag; the manuscript artifacts are unchanged from
  `ef1a8d49` and their hashes above still hold. **`iclr2027-submission-v3` does not move either.**
- `1c01670e` → v13 manuscript reordering. `2295243b` → the page-limit gate. `c7b3828a` → **v13, the
  freeze point**: the manuscript artifacts and every hash in the v13 section above are that commit's.
  The tag **`iclr2027-submission-v4`** is placed one commit later, on the commit that records it —
  the same arrangement as v12, whose tag sits on `cc797ffe` while the manuscript froze at `ef1a8d49`,
  and for the same reason: a commit cannot contain the hash of the commit that records its own tag.
  That recording commit touches no build input; it adds the deadline re-verification below, and its
  rebuilt PDF is byte-identical to `c7b3828a`'s (`6f64140d…`, 283 476 B, 18 pp) — the mechanical proof
  that recording the tag did not alter the manuscript. Lightweight, for the same anonymity reason as
  its three predecessors.

## Deadlines (official ICLR 2027 site)
- Abstract: September 18, 2026 AOE. Full paper: September 25, 2026 AOE.

**Re-verified 2026-08-17** against the three official pages, fetched directly (server `Date:
Mon, 17 Aug 2026 08:34:43 GMT`; cache-busted query string plus `Cache-Control: no-cache`, and the
origin is plain Apache with no CDN `Age`/`X-Cache` header, so this is not a cached copy):

| Source | Text |
|---|---|
| `/Conferences/2027/AuthorGuidelines` | "the abstract submission deadline of **Sep 18, 2026 AOE**" / "The full paper submission deadline is **Sep 25, 2026 AOE**." |
| `/Conferences/2027/CallForPapers` | "Abstract deadline **Sep 18, 2026 AOE**" / "Paper deadline **Sep 25, 2026 AOE**" |
| `/Conferences/2027/Dates` | "Abstract Deadline **Sep 18 '26** (Anywhere on Earth)" / "Paper Deadline **Sep 25 '26** (Anywhere on Earth)" |

The dates have **not** moved. A secondhand report of a shift to Sep 11 / Sep 16 was checked
explicitly and appears on none of the three pages (regex over the full extracted text: no match).
Recorded here so the next recheck does not reopen a settled question from a summarizer's output
rather than from the site.

Two internal cross-checks agree. `docs/phase7/phase7_synthesis.md` — frozen, sha256-recorded above,
written 2026-08-11 — states the same deadlines in UTC: abstract 2026-09-19 11:59 UTC, full paper
2026-09-26 11:59 UTC. AOE is UTC−12, so 2026-09-18 23:59 AOE **is** 2026-09-19 11:59 UTC and
2026-09-25 23:59 AOE **is** 2026-09-26 11:59 UTC: the same two instants recorded six days apart, in
two notations, by two independent readings of the site. The same page also re-confirms the page rule
this build gates on — "At the time of submission, the main text should be 9 pages or fewer."

Re-run the check with no repository state involved:

```bash
curl -sS -L -H 'Cache-Control: no-cache' "https://iclr.cc/Conferences/2027/Dates?cb=$RANDOM" \
  | python3 -c "import sys,re,html; t=html.unescape(re.sub(r'(?s)<[^>]+>',' ',sys.stdin.read())); \
print(re.sub(r'\s+',' ',t)[:0] or [m.strip() for m in re.findall(r'[^ ]*Deadline.{0,40}', re.sub(r'\s+',' ',t))])"
```

`SOURCE_DATE_EPOCH` in the Makefile is pinned to `1790294400` = 2026-09-25T00:00:00Z, the full-paper
deadline date. It is a determinism anchor, not a schedule: only its constancy matters, and it is
therefore *not* a value to chase if a date ever does move — changing it would alter the PDF sha256
recorded above for no reproducibility benefit. It stays correct as things stand.
