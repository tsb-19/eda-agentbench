# LEC Failure Attribution: `top`

`impl.v` was produced from the reference `golden.v` by an automated transform, but Formality
reports the two designs are NOT logically equivalent. Find the ROOT CAUSE.

## What you have
- `golden.v` — the reference (correct) design.
- `impl.v` — the implementation under test. It has been STRUCTURALLY REWRITTEN — it is NOT a
  line-by-line copy of the reference, so you cannot simply diff the two files.
- Formality `verify` result below.

## Formality result
Verification FAILED.
  Compare point z1 failed (is not equivalent)
  Compare point z2 failed (is not equivalent)
(every other compare point passed.)

## Your task
The failing compare points are **outputs** — symptoms at the end of the affected logic. Exactly
ONE internal signal in `impl.v` is computed incorrectly and feeds all the failing outputs.
Identify that single root-cause signal. Answer with the wire NAME as declared in `impl.v`, and
state what it computes vs. what it should compute.

## Rules
- Naming the failing compare points (the outputs) is NOT an answer — those are symptoms.
- Name the one internal signal in `impl.v` that is the actual divergence.
