**English | [中文](baseline_eval.zh.md)**

# Model Baseline Evaluation

How to run real LLMs against EDA-AgentBench and produce a model-vs-model leaderboard.

The benchmark itself is tool-grounded and offline: `evaluate-dataset` only runs the
`solution`/`buggy` calibration modes. This baseline harness adds the missing bridge —
**model → submission → score** — as two standalone scripts, with no changes to the
evaluator core.

## Why inference and grading are separate

Commercial EDA tools (VCS, HSPICE, Design Compiler, PrimeTime, SpyGlass) live **only on
the EDA host `b04`, which has no internet**. LLM inference needs internet. So the two
cannot share a process, and the agentic runner (which calls the agent *and* the tool in
one run) can't span them for tool tracks. The harness splits the work:

1. **Inference (here, has internet)** — `generate_model_submissions.py` calls each model
   once per task and writes a submission directory. The model is **never** invoked again.
2. **Grading (no internet)** — `run_model_baseline.py grade` just runs the grader:
   - report-QA tracks (P3, P6 Synthesis QA, P8) have no tool → graded **locally**;
   - the 7 real-tool tracks → graded **on b04** (`scripts/b04_grade.sh`).

This is a **single-shot** baseline: the model sees the prompt + files once and returns
the edited file(s); it does not iterate on tool feedback. Agentic iterative evaluation is
a separate, later track.

## Prerequisites

1. Copy the model spec template and fill in **which** models to compare (keys come from
   the environment / `.env`, never the file):

   ```bash
   cp configs/baseline_models.example.json configs/baseline_models.json
   # edit: name, api_key_env, api_base, model_id, temperature, max_tokens
   ```

   `configs/baseline_models.json` and `.env` are git-ignored. Each spec resolves its key
   from `api_key_env`; if a key is missing the harness **errors** rather than silently
   using the mock provider (override with `--allow-mock` for a wiring-only dry run).

2. Export the keys (or put them in `.env`):

   ```bash
   export MIMO_API_KEY=...      # or OPENAI_API_KEY=..., etc.
   ```

## Steps

### 1. Generate submissions (local, uses the API)

```bash
STAMP=$(date +%Y%m%d_%H%M%S)
python3 scripts/generate_model_submissions.py tasks \
    --models configs/baseline_models.json \
    --sample-per-track 15 --seed 42 \
    --out runs/baseline/$STAMP/submissions
```

Produces `runs/baseline/$STAMP/submissions/<model>/<track>/<task_id>/<editable file>`
plus a per-task `transcript.json` (raw response + token usage) and a top-level
`manifest.json` (sampled tasks + a `needs_b04` flag per track). Sampling **exactly
mirrors** `evaluate-dataset --sample-per-track N --seed S`, so a given `(seed, N)` always
selects the same tasks.

### 2. Grade the report-QA tracks locally

```bash
python3 scripts/run_model_baseline.py grade \
    --submissions runs/baseline/$STAMP/submissions --only local \
    --results runs/baseline/$STAMP/results
```

### 3. Grade the real-tool tracks on b04

```bash
scripts/b04_grade.sh runs/baseline/$STAMP/submissions runs/baseline/$STAMP/results
# ships repo (git archive) + submissions to b04, grades --only tool, pulls results back,
# removes the remote /tmp workdir. Override host with B04_HOST=tsb@b04.
```

Local and b04 results merge into the same `results/` tree (one JSON per
`model/track/task`).

### 4. Render the leaderboard

```bash
python3 scripts/run_model_baseline.py leaderboard \
    --results runs/baseline/$STAMP/results --stamp $STAMP
# writes reports/model_baseline_$STAMP.{md,csv}
```

The report gives, per model: average `total_score` and pass-rate **by track**, a macro
average, the **per-track model spread** (which tracks discriminate models best), and an
explicit list of any inference/parse errors (recorded as scored, not silently dropped).

## Reading the results

- **PASS** = `total_score >= 0.5` (the benchmark threshold).
- A track where every model scores ~1.0 is **saturated** (too easy); a track with a wide
  spread **discriminates**; a track where all score ~0 is **too hard or mis-prompted**.
- Parse failures (model didn't follow the `<<<FILE: ...>>>` contract) fall back to
  treating the whole reply as the file; the count is reported so you can spot a model with
  poor format adherence vs. genuine task failure.

## Grader integrity sanity check

To confirm the grading path itself is sound, grade the reference `solution/` set through
the same harness — it must score 1.0 everywhere:

```bash
python3 -m eda_agentbench evaluate-dataset tasks \
    --sample-per-track 15 --seed 42 --submission-mode solution
```

## Reproducibility & cost

- Same `--seed` / `--sample-per-track` → identical task set (asserted in
  `tests/test_model_baseline.py`). Use `temperature: 0.0` in the specs for stable replies.
- Cost ≈ `sample_per_track × 10 tracks × N models` inference calls (~150/model at 15).
  b04 grading is `7 tool tracks × sample × N` grader runs in one cleaned `/tmp` workdir.
- Start with `--track p3_timing_report_qa --allow-mock` (no key, no cost) to verify wiring.
