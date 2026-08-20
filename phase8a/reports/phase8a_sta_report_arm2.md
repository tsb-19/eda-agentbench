# Phase-8A — STA panel at k=[2] on a replacement backend

72 graded episodes (¥58.11, 1 measurement-invalid attempts, 3 replaced). **Unit = task instance (n=12); reps nested; trajectories are NOT n.**

> **Not poolable with Phase-7A.** Phase-7A ran on `llmapi.paratera.com`, which now returns 403 for both model IDs. Phase-8A runs on `tokenrhythm.studio`. Same design, different apparatus, therefore a different measurement. Reported side by side, never combined.

## Condition mean rates over instances (descriptive)
- Base **0.25** | BundleS **0.375** | TypedContract **0.4167**

## Instance-level contrast tallies
- **Primary BundleS vs Base:** improve 5, decline 2, tie 5 (n=12)
- Secondary TC vs Base: {'improve': 4, 'decline': 1, 'tie': 7, 'n': 12}
- Secondary TC vs BundleS: {'improve': 2, 'decline': 1, 'tie': 9, 'n': 12}

## Primary sensitivity
- Exact paired sign test: k+=5 of 7 non-zero instance diffs; two-sided p=0.45312
- Permutation (10000 MC): observed sum=1.5; p=0.3362 (descriptive)

## Per-instance outcomes
| instance | Base | BundleS | TypedContract | B−Base | TC−Base | TC−B |
|---|---|---|---|---|---|---|
| p15_eval_0004 | ✗✓ (0.5) | ✗✗ (0.0) | ✓✗ (0.5) | -0.5 | 0.0 | 0.5 |
| p15_eval_0005 | ✗✗ (0.0) | ✗✗ (0.0) | ✗✗ (0.0) | 0.0 | 0.0 | 0.0 |
| p15_eval_0006 | ✗✗ (0.0) | ✗✗ (0.0) | ✗✗ (0.0) | 0.0 | 0.0 | 0.0 |
| p15_eval_0007 | ✓✓ (1.0) | ✗✗ (0.0) | ✗✗ (0.0) | -1.0 | -1.0 | 0.0 |
| p15_eval_0008 | ✗✗ (0.0) | ✗✗ (0.0) | ✗✗ (0.0) | 0.0 | 0.0 | 0.0 |
| p15_eval_0009 | ✗✗ (0.0) | ✗✗ (0.0) | ✗✗ (0.0) | 0.0 | 0.0 | 0.0 |
| p15_eval_0010 | ✓✓ (1.0) | ✓✓ (1.0) | ✓✓ (1.0) | 0.0 | 0.0 | 0.0 |
| p15_eval_0011 | ✗✗ (0.0) | ✓✓ (1.0) | ✓✓ (1.0) | 1.0 | 1.0 | 0.0 |
| p15_eval_0012 | ✗✗ (0.0) | ✓✗ (0.5) | ✓✓ (1.0) | 0.5 | 1.0 | 0.5 |
| p15_eval_0013 | ✗✓ (0.5) | ✓✓ (1.0) | ✓✓ (1.0) | 0.5 | 0.5 | 0.0 |
| p15_eval_0014 | ✗✗ (0.0) | ✓✗ (0.5) | ✗✗ (0.0) | 0.5 | 0.0 | -0.5 |
| p15_eval_0015 | ✗✗ (0.0) | ✗✓ (0.5) | ✗✓ (0.5) | 0.5 | 0.5 | 0.0 |

## Side by side with Phase-7A (NEVER pooled)

| | backend | k | Base | BundleS | TypedContract |
|---|---|---|---|---|---|
| Phase-7A | llmapi.paratera.com (now 403) | 2 | 0.208 | 0.333 | 0.458 |
| Phase-8A | tokenrhythm.studio | [2] | 0.25 | 0.375 | 0.4167 |

These are two measurements of the same design on different apparatus. The rows are not combined, and neither row is evidence about the other's backend.
