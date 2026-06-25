# Phase-2 agentic reliability pilot — run matrix & cost

Status: **PROPOSED — awaiting approval before any b04 spend.** Built on the completed Phase-1
reliability/calibration layer (`eda_agentbench/reliability.py`, `scripts/reliability_report.py`,
`--elicit-confidence` + `--temperature` on the agentic harness). No new tasks; read-only reuse of
existing P5/P6/P7 debug tracks.

## Why these tracks (scope §2–3: mid-difficulty / agentic, where flipping was seen — not easy QA)

The single-shot easy-QA Phase-0 understated the consistency gap (≤0.08). The run-to-run flipping we
actually observed was on the **agentic, tool-feedback debug tracks** (k=1 within-cell stdev 0.118 on
the damping re-baseline, #92; mid-tier flips on P5/P6/P7 diagnosis, #100/#101). So the pilot targets
the four genuine **diagnosis-under-tools** tracks — symptom → root-cause → fix → re-run — which is
exactly where instability and overconfidence are expected to surface.

| Track | Tool | Tasks avail. | Difficulty strata | Role |
|---|---|---|---|---|
| `p6_dc_constraint_debug` | DC | 61 | easy 31 / med 20 / hard 10 | best-stratified diagnosis |
| `p7_primetime_sta_debug` | PrimeTime | 53 | easy 40 / med 13 | STA exception/constraint diagnosis |
| `p7_spyglass_lint_debug` | SpyGlass | 50 | med 32 / easy 18 | lint diagnosis (mostly medium) |
| `p5_spice_deck_debug` | HSPICE | 100 | easy 100 | SPICE deck repair |

Excluded by default: `p4_spice_sim` (the damping/sizing subset already **collapsed to frontier-perfect**,
#92 — least likely to show frontier instability). Available as an optional **known-floor control**
(+45 episodes ≈ +¥25) if you want a calibration anchor that the metrics should score frontier≈1.0 /
mid-tier lower.

## Matrix (scope §3–5)

- **Models (5):** Qwen3.7-Max, DeepSeek-V4-Pro, GLM-5.1, Kimi-K2.6, MiniMax-M3
- **Tasks/track:** 3, **stratified by difficulty** (deterministic, `--seed 42` → identical task set
  every trial; the only run-to-run variation is sampling at temperature)
- **k = 3** (3 independent passes; **extend to k=5 only if the signal is promising**, scope §4)
- **temperature = 0.7** (configured temps are UNSET → forced >0 so identical inputs vary, the whole point)
- **`--elicit-confidence` ON**; concurrency 2 (b04 seats); per-episode timeout 1200 s

Episodes = 4 tracks × 3 tasks × 5 models × k = **180** (default).

## Cost estimate

Anchor: damping re-baseline (#92) = ¥118 / 225 episodes = **¥0.52/episode** (5 same models, k=3, real
tool, with tool-iteration). Cross-checked against observed per-episode tokens (median 30.6k in / 2.7k
out → ¥0.33; mean 48k / 6k → ¥0.57). Budget at **¥0.55/episode** (conservative, ≈ mean).

| Variant | tracks × tasks × models × k | episodes | est. cost | % of ¥1000 |
|---|---|---|---|---|
| **Lean** | 4 × 2 × 5 × 3 | 120 | **≈ ¥66** | 7% |
| **Default (recommended)** | 4 × 3 × 5 × 3 | 180 | **≈ ¥99** | 10% |
| + P4 known-floor control | 5 × 3 × 5 × 3 | 225 | ≈ ¥124 | 12% |
| k=5 extension (only if promising) | +2 passes (default) | +120 | +¥66 | — |

Wall-clock: ~4–8 h at concurrency 2 (real-tool episodes are slow); **chunkable per track/trial** so it
can be run and checkpointed in pieces.

## Metrics reported (scope §6–7) — all emitted by `scripts/reliability_report.py`

pass@1 · pass@k (any-of-k) · pass^k (all-of-k) · reliability gap (pass@1−pass^k) · flip-rate · trust ·
overconfident-wrong (count + rate) · abstain/low-confidence rate · format compliance · **protocol
tally** (NOCOMMIT / BUDGET_EXHAUSTED / TOOL_MISUSE / ANTI_CHEAT / **HTTP_429 / EMPTY**) · cost (mean
tokens / tool-calls / retries / wall-time). **Infra (429/empty) is excluded from capability** and shown
only in the protocol column (infra-filter discipline, #79/#102).

## Exact commands (NOT yet run)

```bash
source /data1/tongsb/eda-remote-shim/env.sh           # EDA tools on PATH (b04) + gateway/.env
cd /data1/tongsb/eda-agentbench
TRACKS="p6_dc_constraint_debug p7_primetime_sta_debug p7_spyglass_lint_debug p5_spice_deck_debug p4_spice_sim"
for k in 1 2 3; do
  for tr in $TRACKS; do
    python3 scripts/run_agentic_baseline.py tasks \
      --models configs/baseline_models.json --track $tr \
      --sample-per-track 3 --seed 42 --max-actions 12 --timeout 1200 \
      --concurrency 2 --elicit-confidence --temperature 0.7 \
      --results runs/reliability_phase2/trial$k/results
  done
done
# aggregate the 3 trial trees into the reliability/calibration leaderboard:
python3 scripts/reliability_report.py \
  runs/reliability_phase2/trial1/results \
  runs/reliability_phase2/trial2/results \
  runs/reliability_phase2/trial3/results \
  --md reports/reliability_phase2.md --json reports/reliability_phase2.json
```

## Fairness / sanity before trusting numbers (held discipline)

- Same `--seed` → identical task set across trials (verify task IDs match across trial trees).
- A frontier model that solves a track should show pass^k≈pass@1 (low gap) and trust≈1.0; spread should
  come from flip-rate / overconfident-wrong on mid-tier — re-confirm against the known #92/#101 pattern.
- Spot-check that any `overconfident_wrong` episode is a real confident-wrong transcript (not a parse
  artifact) before reporting it.

## Guardrails

Do not scale beyond this pilot. Do not build new tasks. Do not commit until the full diff + this matrix
are reviewed. k=5 only after k=3 shows a promising signal. Infra artifacts tracked, never counted as
capability.
