**English | [中文](scoring.zh.md)**

# Scoring Rules

## Score Structure

Each evaluation produces a `score.json`:

```json
{
  "schema_version": "1.0.0",
  "task_id": "task_000001",
  "track": "p1_rtl_debug",
  "mode": "submission",
  "total_score": 0.78,
  "max_possible": 1.0,
  "objective_score": 0.69,
  "explanation_score": 0.09,
  "passed": true,
  "passing_threshold": 0.5,
  "components": [...],
  "anti_cheat": {...},
  "resource_usage": {...}
}
```

## Score Components

### total_score

Sum of all weighted component scores. Range: [0.0, 1.0].

### objective_score

Sum of all non-explanation component scores. This is the primary metric.

### explanation_score

Score from the `explanation` component. Only meaningful in agentic mode with LLM evaluation. In submission mode, defaults to 1.0.

### Pass Threshold

`passed = total_score >= 0.5`

This is a binary flag. It does NOT define "correct" vs "buggy" -- see below.

## P1 RTL Debug Scoring

Components:

| Component | Weight | What It Measures |
|-----------|--------|------------------|
| compile | 0.2 | Design compiles with VCS without errors |
| public_test | 0.3 | Public testbench passes all cases |
| hidden_test | 0.4 | Hidden testbench passes all cases |
| explanation | 0.1 | Agent's explanation of the fix (LLM-judged, defaults 1.0) |

**Evaluation logic:**

- `compile`: checks VCS exit code and log for errors
- `public_test`: parses public test log for PASS/FAIL counts
- `hidden_test`: parses hidden test log for PASS/FAIL counts
- `explanation`: reserved for LLM evaluation; in submission mode returns 1.0

## P4 SPICE Sim Scoring

Components:

| Component | Weight | What It Measures |
|-----------|--------|------------------|
| tool_run | 0.3 | EDA tool (HSPICE/Spectre) ran without fatal errors |
| output_generated | 0.2 | Simulation produced output (waveform/measures) |
| public_metric | 0.2 | Public measurement within spec range |
| hidden_metric | 0.2 | Hidden measurement within spec range |
| explanation | 0.1 | Agent's explanation (defaults 1.0) |

**Evaluation logic:**

- `tool_run`: checks for tool completion without errors (HSPICE: `.lis` parsing; Spectre: `spectre ended`)
- `output_generated`: checks for measurement values in output (HSPICE: `.lis`; Spectre: `metrics.json`)
- `public_metric`: checks if the public measurement (e.g., `tdrise`) falls within `[min, max]`
- `hidden_metric`: checks if the hidden measurement (e.g., `tdfall`) falls within `[min, max]`

**Metric extraction:**

- HSPICE: parses `.lis` file for `.measure` results with engineering suffixes (e.g., `1.234n`)
- Spectre: reads `metrics.json` written by the run script, which parses `-format nutascii` waveform output

## Buggy Baseline Semantics

**The correct criterion for a buggy baseline is `total_score < 1.0`.**

Do not confuse with the pass threshold (0.5). A buggy design might still score above 0.5 if it partially works. The key property is:

- Solution must score **exactly 1.00**
- Buggy baseline must score **strictly less than 1.00**

The dataset evaluation tracks `buggy_lower_than_solution_count`: the number of tasks where buggy mode scored less than solution mode. For a well-designed benchmark, this should equal the total task count.

## Explanation Score in Submission Mode

In submission/workspace mode (v0), the agent does not generate explanations during evaluation. The `explanation` component defaults to `raw_score = 1.0`, contributing its full weight to the total.

This means:

- A perfect solution in submission mode scores 1.00
- The explanation component does not penalize submission-mode evaluations
- In future agentic mode, explanation scoring will be LLM-judged

## Custom Weights

Tasks can override the default weights via `metadata.scoring.weights`. The only constraint is that weights must sum to 1.0. Components not listed in weights are not evaluated.
