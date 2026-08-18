# Phase-8A — STA panel at k=[6] on a replacement backend

216 graded episodes (¥122.8175, 2 measurement-invalid attempts, 4 replaced). **Unit = task instance (n=12); reps nested; trajectories are NOT n.**

> **Not poolable with Phase-7A.** Phase-7A ran on `llmapi.paratera.com`, which now returns 403 for both model IDs. Phase-8A runs on `tokenrhythm.studio`. Same design, different apparatus, therefore a different measurement. Reported side by side, never combined.

## Condition mean rates over instances (descriptive)
- Base **0.2778** | BundleS **0.25** | TypedContract **0.3611**

## Instance-level contrast tallies
- **Primary BundleS vs Base:** improve 2, decline 3, tie 7 (n=12)
- Secondary TC vs Base: {'improve': 5, 'decline': 3, 'tie': 4, 'n': 12}
- Secondary TC vs BundleS: {'improve': 4, 'decline': 1, 'tie': 7, 'n': 12}

## Primary sensitivity
- Exact paired sign test: k+=2 of 5 non-zero instance diffs; two-sided p=1.0
- Permutation (10000 MC): observed sum=-0.3333; p=0.7176 (descriptive)

## Per-instance outcomes
| instance | Base | BundleS | TypedContract | B−Base | TC−Base | TC−B |
|---|---|---|---|---|---|---|
| p15_eval_0004 | ✓✓✓✓✓✓ (1.0) | ✗✗✗✗✗✗ (0.0) | ✗✗✗✗✗✗ (0.0) | -1.0 | -1.0 | 0.0 |
| p15_eval_0005 | ✗✗✗✗✗✗ (0.0) | ✗✗✗✗✗✗ (0.0) | ✗✗✗✗✗✗ (0.0) | 0.0 | 0.0 | 0.0 |
| p15_eval_0006 | ✗✗✗✗✗✗ (0.0) | ✗✗✗✗✗✗ (0.0) | ✗✗✗✗✗✗ (0.0) | 0.0 | 0.0 | 0.0 |
| p15_eval_0007 | ✓✓✓✗✓✓ (0.8333) | ✗✗✗✗✗✗ (0.0) | ✗✗✗✗✗✗ (0.0) | -0.8333 | -0.8333 | 0.0 |
| p15_eval_0008 | ✗✗✗✗✗✗ (0.0) | ✗✗✗✗✗✗ (0.0) | ✗✗✗✗✗✗ (0.0) | 0.0 | 0.0 | 0.0 |
| p15_eval_0009 | ✗✗✗✗✗✗ (0.0) | ✗✗✗✗✗✗ (0.0) | ✗✗✗✗✗✗ (0.0) | 0.0 | 0.0 | 0.0 |
| p15_eval_0010 | ✓✓✓✓✓✓ (1.0) | ✓✓✓✓✓✓ (1.0) | ✓✓✗✓✓✓ (0.8333) | 0.0 | -0.1667 | -0.1667 |
| p15_eval_0011 | ✗✗✗✗✗✗ (0.0) | ✓✓✓✓✓✓ (1.0) | ✓✓✓✓✓✓ (1.0) | 1.0 | 1.0 | 0.0 |
| p15_eval_0012 | ✗✗✗✗✗✗ (0.0) | ✓✓✗✓✓✗ (0.6667) | ✓✓✓✓✓✓ (1.0) | 0.6667 | 1.0 | 0.3333 |
| p15_eval_0013 | ✗✗✓✓✗✓ (0.5) | ✗✗✓✗✗✓ (0.3333) | ✓✓✓✓✓✓ (1.0) | -0.1667 | 0.5 | 0.6667 |
| p15_eval_0014 | ✗✗✗✗✗✗ (0.0) | ✗✗✗✗✗✗ (0.0) | ✗✗✗✗✓✗ (0.1667) | 0.0 | 0.1667 | 0.1667 |
| p15_eval_0015 | ✗✗✗✗✗✗ (0.0) | ✗✗✗✗✗✗ (0.0) | ✓✗✗✗✗✓ (0.3333) | 0.0 | 0.3333 | 0.3333 |

## Side by side with Phase-7A (NEVER pooled)

| | backend | k | Base | BundleS | TypedContract |
|---|---|---|---|---|---|
| Phase-7A | llmapi.paratera.com (now 403) | 2 | 0.208 | 0.333 | 0.458 |
| Phase-8A | tokenrhythm.studio | [6] | 0.2778 | 0.25 | 0.3611 |

These are two measurements of the same design on different apparatus. The rows are not combined, and neither row is evidence about the other's backend.
