# Phase-5D Collection Report — pre-specified secondary TypedContract extension with a protocol-repaired SPICE replication

**Status: complete 36/36.** Branch `synthetic-phase0a`. Model: Qwen3.7-Max (SSE streaming). Machine-readable: `reports/synthetic_phase5d_collection_report.json`; state: `reports/evidence/phase5d_state.json`; evidence + custody: `reports/evidence/phase5d_episodes/`. **Phase-5C remains the frozen primary external-validity result; Phase-5D is a labeled secondary extension.** No push.

## 1. Collection status
- **36/36 primary episodes (Base, BundleS, TypedContract × 3 instances × 2 families × 2 reps); 0 invalid, 0 replaced, 0 aborted.** All measurement-valid (terminal_transport_valid ∧ gradeable); no terminal-invalid replacements.
- **Cost ¥11.7524** (remaining ledger ≈ **¥306.00**). Far under the recomputed ¥50.76 ceiling (per-slot ¥0.94 conservative, from the Phase-5C slot-cost distribution). No `incomplete_collection_budget_stop`.
- **SPICE protocol-repair validated: 0 anti-cheat forbidden-modification trips** across all 18 SPICE episodes (Phase-5C had 12/12 false-positive trips; the immutable-core/derived-deck repair eliminated them). SPICE artifact scores are now interpretable.
- Condition order balanced: per family the 6 (instance×rep) blocks used all 6 permutations of the 3 conditions exactly once → every condition twice at each position (Latin balance, verified).

## 2. Instance-level + family rates (PRIMARY = semantic-binding correctness; instance = unit; reps nested)

| Family | Base | BundleS | TypedContract |
|---|---|---|---|
| **A (STA)** | 0.50 | 0.33 | 0.33 |
| **B (SPICE, repaired)** | 1.00 | 1.00 | 1.00 |

Instance-level (Base / BundleS / TypedContract): STA 0001 = 0.5/0.0/0.0 (decline); STA 0002 = 1.0/1.0/1.0 (ceiling); STA 0003 = 0.0/0.0/0.0 (floor); SPICE 0001–0003 = 1.0/1.0/1.0 (ceiling).

## 3. Predeclared contrasts (descriptive instance-level directions; NOT a pooled-trajectory headline test)

| Contrast | improve | decline | tie | n |
|---|---|---|---|---|
| **TypedContract vs Base** | 0 | 1 | 5 | 6 |
| **TypedContract vs BundleS** | 0 | 0 | 6 | 6 |
| **BundleS vs Base (same-window replication)** | 0 | 1 | 5 | 6 |

**No contrast shows a TypedContract (or BundleS) benefit.** TypedContract is indistinguishable from BundleS (6/6 tie) and does not improve over Base (0 improve, 1 decline). BundleS vs Base same-window replicates the Phase-5C STA null (0 improve). On the families tested: machine-readable TypedContract adds no measurable benefit over Base, and none over BundleS.

## 4. Interpretation (consistent with Phase-5C; not categorical)
- **STA (clean primary evidence):** neither BundleS nor TypedContract improves semantic binding for Qwen (Base 0.50 ≥ BundleS ≈ TypedContract 0.33). The non-answer disclosures (prose or typed-schema) do not help on this family; one instance declines, one is at ceiling, one at floor. Dominant subtype `coverage_cell_mismatch`.
- **SPICE (repaired, clean artifact data now):** at ceiling on semantic binding across all three conditions (Base already 1.00) — non-discriminative; a TypedContract/BundleS benefit cannot be expressed. The repaired SPICE artifact data (mean 0.5) is now interpretable: the agent binds the tuple correctly but does not produce the provenance-attestation/measurement-report artifacts (evidence_provenance and protocol_completion unscored), a real agent-behavior observation (not an anti-cheat artifact).
- **Composite:** the Phase-5D TypedContract extension does not establish a benefit for the typed-contract representation over Base or over BundleS. Combined with Phase-5C, **cross-family transfer of the p14 BundleS/TypedContract benefit remains not established** across the two tested families (STA null; SPICE non-discriminative at ceiling). This is a lack of external-validity evidence, not a categorical "does not generalize" claim.

## 5. Per-episode data + sanitized evidence + custody
All 36 episodes (family/instance/condition/rep+position, semantic-binding correctness, family subtype, artifact total_score, anti-cheat flag, provenance/protocol components, termination, terminal_transport_valid, recovered_degradation, tokens, cost) are in the machine-readable companion. All episodes `terminal_transport_valid = true`; recovered degradation present in some (does not trigger replacement). Per-episode evidence (`<editable>.submitted.json`, `result.json`, `agentlog.sanitized.json`, `SHA256SUMS`) under `reports/evidence/phase5d_episodes/<trial>/`. Integrity: Phase-5D pre-run custody manifest (`reports/evidence/phase5d_freeze/phase5d_freeze.json`) anchored at the run commit; canonical `tasks/` never written (agent + grading on /tmp copies). No credential markers in any committed evidence (verified for Phase-5C; same pipeline).

## 6. Relation to Phase-5C + the program
Phase-5C (frozen primary) showed cross-family transfer not established (STA null; SPICE ceiling + anti-cheat false positive). Phase-5D (this secondary extension) repaired the SPICE action surface (eliminating the false positive; SPICE artifact data now clean) and added the TypedContract condition: it confirms the null — neither BundleS nor the machine-readable TypedContract provides a measurable benefit on these two families. The p14 effect remains p14-scoped; external-validity evidence across the tested families is lacking. No DeepSeek, no new instances, no P14, no held-out-family-2, no extra reps, no wording changes were introduced.
