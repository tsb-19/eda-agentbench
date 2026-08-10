# Phase-7A Study A — 72-Episode Instance-Level Report (prospective, n=12 instances)

72/72 episodes collected (¥43.5628, 0 invalid, 1 validity-only replacement). **Unit = task instance (n=12); 2 reps nested; 72 trajectories are NOT n=72.** Pilot 0001-0003 excluded from primary.

## Condition mean rates over instances (descriptive)
- Base: **0.208**  | BundleS: **0.333**  | TypedContract: **0.458**

## Instance-level contrast tallies (improve / decline / tie of the 12 instances)
- **Primary BundleS vs Base:** improve 3, decline 2, tie 7
- Secondary TypedContract vs Base: {'improve': 5, 'decline': 2, 'tie': 5, 'n': 12}
- Secondary TypedContract vs BundleS: {'improve': 2, 'decline': 0, 'tie': 10, 'n': 12}

## Primary sensitivity (BundleS vs Base)
- Exact paired sign test: k+=3 of 5 non-zero instance diffs; two-sided p=1.0
- Per-instance permutation (10000 MC): observed Σ(BundleS−Base)=1.5; two-sided p=0.3133 (descriptive sensitivity; NOT a population-rate p-value)

## Per-instance outcomes (✓=correct typed binding)
| instance | Base | BundleS | TypedContract | B−Base | TC−Base | TC−B | agree |
|---|---|---|---|---|---|---|---|
| p15_eval_0004 | ✗✓ (0.5) | ✗✗ (0.0) | ✗✗ (0.0) | -0.5 | -0.5 | 0.0 | dis/agr/agr |
| p15_eval_0005 | ✗✗ (0.0) | ✗✗ (0.0) | ✗✗ (0.0) | 0.0 | 0.0 | 0.0 | agr/agr/agr |
| p15_eval_0006 | ✗✗ (0.0) | ✗✗ (0.0) | ✗✗ (0.0) | 0.0 | 0.0 | 0.0 | agr/agr/agr |
| p15_eval_0007 | ✓✗ (0.5) | ✗✗ (0.0) | ✗✗ (0.0) | -0.5 | -0.5 | 0.0 | dis/agr/agr |
| p15_eval_0008 | ✗✗ (0.0) | ✗✗ (0.0) | ✗✗ (0.0) | 0.0 | 0.0 | 0.0 | agr/agr/agr |
| p15_eval_0009 | ✗✗ (0.0) | ✗✗ (0.0) | ✗✗ (0.0) | 0.0 | 0.0 | 0.0 | agr/agr/agr |
| p15_eval_0010 | ✗✓ (0.5) | ✓✓ (1.0) | ✓✓ (1.0) | 0.5 | 0.5 | 0.0 | dis/agr/agr |
| p15_eval_0011 | ✗✗ (0.0) | ✓✓ (1.0) | ✓✓ (1.0) | 1.0 | 1.0 | 0.0 | agr/agr/agr |
| p15_eval_0012 | ✗✗ (0.0) | ✓✓ (1.0) | ✓✓ (1.0) | 1.0 | 1.0 | 0.0 | agr/agr/agr |
| p15_eval_0013 | ✓✓ (1.0) | ✓✓ (1.0) | ✓✓ (1.0) | 0.0 | 0.0 | 0.0 | agr/agr/agr |
| p15_eval_0014 | ✗✗ (0.0) | ✗✗ (0.0) | ✓✗ (0.5) | 0.0 | 0.5 | 0.5 | agr/agr/dis |
| p15_eval_0015 | ✗✗ (0.0) | ✗✗ (0.0) | ✓✓ (1.0) | 0.0 | 1.0 | 1.0 | agr/agr/agr |
