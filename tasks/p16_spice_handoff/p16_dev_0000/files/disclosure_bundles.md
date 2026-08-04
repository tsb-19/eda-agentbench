# Disclosure bundle (BundleS: C1+C2+C4+C7, non-answer-bearing)

## C1 canonical labels + disjoint-axis declaration
Typed roles: corner, load_condition, metric — DISJOINT typed axes.

## C2 value-domain definitions
- corner in ['SS_0p9_-40', 'TT_1p2_25', 'FF_1p3_125']
- load_condition in ['light', 'nominal', 'heavy']
- metric in ['gain', 'gbw', 'pm', 'slew', 'vdsat']

## C4 glossary + references
- metric: see char_spec.md
- corner: see mission_profile.md
- load_condition: see application_note.md

## C7 procedural contract
Join the request to its authorities: metric from char_spec, corner from mission_profile, load_condition from application_note; the deck measures a plausible number for any tuple, so correctness is authority-joined, not numeric.
