# Phase-7 Study B — Human-Annotation Ethics & Protocol Freeze

**Status:** FREEZE complete (protocol, consent, rubric, reporting plan). **Label collection
is NOT performed in this phase** — it requires qualified human annotators who are not
available to the automated agent. Per the authorization: if qualified human annotation is
unavailable, Study B stops and is reported as **unexecuted**; it is NEVER replaced with an
LLM-only validation claimed as independent construct validation. No model calls.

## 1. Ethics / IRB assessment (to be confirmed by the institution)

- **Activity:** adult annotators label de-identified LLM-agent outputs (submitted semantic
  bindings + authority evidence) for correctness and failure subtype.
- **Data about annotators:** minimal — only what consent records (no protected health data;
  demographics optional and stored separately/aggregate).
- **Risk:** minimal (reading short technical artifacts; no deception, no sensitive content).
- **Preliminary determination:** this is most likely **IRB-exempt** (e.g., research involving
  adults consenting to a labeling task with no identifiable private information stored) or may
  be classified as non-human-subpects quality work performed by collaborators. **The
  institutional IRB office must confirm exemption or require review before any label is
  collected.** No annotation data is collected until that determination is recorded.
- **Boundary:** annotators are experts/collaborators performing a technical labeling task;
  they are not the research subjects. The objects of study are the agent trajectories.

## 2. Informed-consent language (template; to be localized to the institution)

> You are invited to take part in a labeling task that helps validate an automated grader
> used in an LLM-agent benchmark. **Purpose:** independently judge whether each submitted
> semantic binding is correct. **What you will do:** read a blinded annotation packet
> (authority evidence + a submitted binding) and answer 4 rubric questions per packet
> (correct? provenance-sufficient? failure subtype if incorrect? ambiguous?). **Expected
> time:** about [X] minutes per packet; [Y] minutes total for your assigned subset of 72
> packets (a target load per annotator is recorded before you start). **Compensation:**
> [per institutional policy]. **Storage:** your labels are stored de-identified in the
> project repository; any demographics are stored separately and reported only in aggregate.
> **Release:** the label set (without annotator identifiers) will be released with the
> publication. **Voluntary:** you may stop at any time. **Contact:** [PI / IRB contact].

## 3. Annotator independence

- Target **≥2, preferably 3** independent human annotators.
- At least **two** annotators must **not** have participated in the generator or automated-grader
  design (independence from the construct being validated).
- Annotators must be **technically qualified** to apply the frozen rubric (STA/timing-signoff
  literacy, or trained to criterion on a calibration set).
- Blinding maintained: model identity, Harness condition, automated-grader verdict, score, and
  revealing task IDs are stripped from every packet (verified by leak scan).

## 4. Materials (frozen)

- **72 blinded packets** (`reports/evidence/phase7b_annotation/packets/`) sampled from
  committed trajectories across workflow/STA/SPICE × conditions × models × outcomes.
- **Frozen rubric** (4 independent questions per packet): (1) Is the submitted semantic
  binding correct? (2) Is the evidence/provenance sufficient for that binding? (3) If
  incorrect, which predeclared failure subtype applies? (4) Is the case ambiguous/unjudgeable?
- **Key file** (`key.json`) maps packet→automated-grader label, held separately for
  adjudication only; not shown to annotators.

## 5. Pre-registered analysis (reported whatever the result)

- Raw inter-annotator agreement.
- Agreement coefficient appropriate to the annotator count and label structure:
  Cohen's κ (2 annotators) or Fleiss' κ / Krippendorff's α (≥3).
- **Majority human semantic-correctness label vs automated grader** (construct validity of
  the primary outcome).
- Majority human provenance-sufficiency label vs automated grader.
- Failure-subtype confusion matrix (human majority subtype vs grader subtype).
- Ambiguous/unjudgeable rate.
- All adjudication rules and the **pre-adjudication labels** (no disagreement removed merely
  because it disagrees with the grader).
- If only two annotators are available: no third judge is fabricated with an LLM.

## 6. Stop condition

If qualified human annotation cannot be obtained after the institutional process, Study B is
**stopped and reported as unexecuted** — never silently replaced with an LLM-only annotation.
