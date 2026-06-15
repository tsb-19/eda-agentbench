#!/usr/bin/env bash
# Grade the real-tool baseline submissions on the EDA host (b04).
#
# Inference already ran locally (scripts/generate_model_submissions.py). This ships
# the committed repo (git archive) + the untracked submissions to b04, grades ONLY
# the real-tool tracks there (VCS/HSPICE/DC/PrimeTime/SpyGlass live only on b04, which
# has no internet — so it never calls a model, it only runs the grader), pulls the
# per-task result JSONs back, and removes the remote workdir.
#
# Usage:
#   scripts/b04_grade.sh <local_submissions_dir> <local_results_dir>
# Env:
#   B04_HOST   ssh target (default: tsb@b04)
#
# Notes (see memory eda-remote-exec-b04): single /tmp workdir, cleaned up; commands
# run under a login shell; "Authorized users only"/lsof lines are benign login noise.
set -euo pipefail

SUBS="${1:?usage: b04_grade.sh <submissions_dir> <results_dir>}"
RESULTS="${2:?usage: b04_grade.sh <submissions_dir> <results_dir>}"
HOST="${B04_HOST:-tsb@b04}"

SUBS="$(cd "$SUBS" && pwd)"
mkdir -p "$RESULTS"; RESULTS="$(cd "$RESULTS" && pwd)"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

WORK="/tmp/eda_baseline_$$"
echo ">> remote workdir: $HOST:$WORK"

# 1. Ship the committed repo (tasks/ + package + scripts) via git archive.
echo ">> shipping repo (git archive HEAD) ..."
git -C "$REPO_ROOT" archive --format=tar HEAD \
  | ssh "$HOST" "mkdir -p $WORK/repo && tar -x -C $WORK/repo"

# 2. Ship the untracked submissions (must include manifest.json).
echo ">> shipping submissions ..."
tar -c -C "$(dirname "$SUBS")" "$(basename "$SUBS")" \
  | ssh "$HOST" "mkdir -p $WORK && tar -x -C $WORK && mv $WORK/$(basename "$SUBS") $WORK/submissions"

# 3. Grade the real-tool tracks on b04 (login shell).
echo ">> grading tool tracks on b04 ..."
ssh "$HOST" "bash -lc 'cd $WORK/repo && python3 scripts/run_model_baseline.py grade \
  --submissions $WORK/submissions --only tool --results $WORK/results'"

# 4. Pull results back and merge into the local results tree.
echo ">> pulling results -> $RESULTS ..."
ssh "$HOST" "tar -c -C $WORK results" | tar -x -C "$RESULTS" --strip-components=1

# 5. Clean up the remote workdir.
echo ">> cleaning $HOST:$WORK"
ssh "$HOST" "rm -rf $WORK"
echo ">> done. Merge complete; render with: \
python3 scripts/run_model_baseline.py leaderboard --results $RESULTS"
