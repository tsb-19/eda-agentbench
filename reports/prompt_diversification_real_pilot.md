# Prompt Diversification Real Provider Pilot Report

## Configuration

- **Model:** mimo-v2.5-pro
- **Provider:** MiMo (OpenAI-compatible endpoint)
- **Variant name:** real_v1
- **Pilot size:** 14 tasks

## Task Selection

| Track | Count | Selection |
|-------|-------|-----------|
| P1 RTL Debug | 10 | 1 task per bug type |
| P4 HSPICE | 2 | First 2 generated tasks |
| P4 Spectre | 2 | First 2 generated tasks |

**Task IDs:** task_000000, task_000100, task_000200, task_000300, task_000400, task_000500, task_000600, task_000700, task_000800, task_000900, hspice_gen_000000, hspice_gen_000001, spectre_gen_000050, spectre_gen_000051

## Results

| Metric | Value |
|--------|-------|
| Tasks attempted | 14 |
| Accepted | 13 |
| Rejected | 1 |
| Acceptance rate | 92.9% |

### Cache Statistics

- Cache entries before: 40 (from mock provider run)
- New entries: 31
- Total entries: 71

## Safety Check Results

### Accepted (13 tasks)

All 13 accepted tasks passed the safety checker with no violations. The rewritten prompts:

- Do not contain bug type labels
- Do not reference hidden test files
- Do not contain local paths
- Do not contain license variables
- Do not contain tool banners

### Rejected (1 task)

| Task | Bug Type | Violation |
|------|----------|-----------|
| task_000000 | sensitivity_list | Contains "sensitivity list" in rewritten prompt |

**Analysis:** The MiMo model preserved the phrase "sensitivity list" in the hint text across all 3 attempts. This is a borderline case — "sensitivity list" is both a bug type label and a legitimate Verilog term. The safety checker correctly rejects it to prevent leakage.

**Mitigation:** For production use, the system prompt should explicitly instruct the model to avoid using the phrase "sensitivity list" and instead describe the concept indirectly (e.g., "signal coverage in combinational blocks").

## Quality Analysis

### Readability

The real provider produces significantly more natural-sounding prompts than the mock provider:

| Aspect | Mock Provider | Real Provider (MiMo) |
|--------|--------------|---------------------|
| Title variation | Strips bug type, adds EDA context | Rewrites entirely ("RTL Bug Hunt: Boundary Condition Error") |
| Description | Preserves structure, minor word swaps | Full paraphrase with maintained meaning |
| Hint | Generic replacement | Context-aware rewrite |
| File descriptions | Simple word substitution | Natural rephrasing |

### Representative Samples

**task_000200 (reset_polarity):**
- Canonical: "RTL Debug Task: Reset Polarity" / "Check the reset polarity."
- Real: "RTL Debug Task: Reset Signal Issue" / Natural description with context

**task_000400 (comparison_boundary):**
- Canonical: "RTL Debug Task: Comparison Boundary" / "Check the boundary conditions."
- Real: "RTL Bug Hunt: Boundary Condition Error" / "Your mission is to identify and resolve the issue"

**hspice_gen_000000:**
- Canonical: "Fix RC Low-Pass Filter Rise Time"
- Real: "Correct the RC Filter's Rise Delay" / Technical accuracy preserved

**spectre_gen_000050:**
- Canonical: "Fix RC Low-Pass Filter Rise Time"
- Real: "Correct Excessive Delay in RC Low-Pass Filter" / Clear, professional

### Information Preservation

- All technical values (R, C, voltage thresholds, timing ranges) preserved in accepted variants
- File references (design.sv, circuit.sp, circuit.scs) maintained
- Constraints and instructions kept intact
- No information was added or removed

### Ambiguity Introduced

- Minimal ambiguity in accepted variants
- Some title changes are more generic ("Design Issue") but body text preserves specificity
- Hints are rewritten to be equivalent in guidance value

### Hint Leakage Risk

- 1/14 tasks (7.1%) had hint leakage (sensitivity_list term)
- All other tasks successfully abstracted bug type references
- P4 tasks had zero leakage (no bug type labels in prompts)

## Comparison: Mock vs Real Provider

| Dimension | Mock | Real (MiMo) |
|-----------|------|-------------|
| Safety pass rate | 100% (60/60) | 92.9% (13/14) |
| Naturalness | Low (template-based) | High (free-form rewrite) |
| Diversity | Limited (word substitution) | Rich (structural variation) |
| Cost | Zero | ~$0.01 per task |
| Speed | Instant | ~2-5 seconds per task |
| Deterministic | Yes | No (temperature > 0) |

## Recommendations

1. **For production:** Use real provider with enhanced system prompt that explicitly lists forbidden phrases
2. **For testing:** Continue using mock provider (deterministic, no cost)
3. **Safety improvement:** Add "sensitivity list" to the list of phrases the model should avoid in the system prompt
4. **Scale-up:** Safe to proceed with 100+ tasks using the real provider
5. **Cache:** Effective for reducing API calls on repeated runs

## Files Generated

- 13 accepted variants: `prompt_variants/real_v1.md` + `real_v1_meta.json`
- 1 rejected variant (stored but marked as failed): `task_000000/prompt_variants/real_v1.md`
- Cache: `.cache/llm/` (71 entries)
