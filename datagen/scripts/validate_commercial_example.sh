#!/usr/bin/env bash
# Example commercial validation script.
# Demonstrates how to run commercial EDA tool validation.
# Requires EDA_*_CMD environment variables to be set.
# Skips gracefully if tools are not available.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

echo "=== Commercial Validation Example ==="
echo ""

# Check which tools are available
echo "Checking available EDA tools:"
echo "  EDA_VCS_CMD=${EDA_VCS_CMD:-[not set]}"
echo "  EDA_HSPICE_CMD=${EDA_HSPICE_CMD:-[not set]}"
echo "  EDA_SPECTRE_CMD=${EDA_SPECTRE_CMD:-[not set]}"
echo "  EDA_PT_CMD=${EDA_PT_CMD:-[not set]}"
echo ""

# Ensure tasks exist
if [ ! -d tasks_candidates ]; then
    echo "No tasks_candidates/ directory. Run generate_prototypes.sh first."
    exit 1
fi

# Run validation for each tool that is available
VALIDATED=0
SKIPPED=0

# VCS validation for RTL tasks
if [ -n "${EDA_VCS_CMD:-}" ]; then
    echo "--- VCS Validation ---"
    for task_dir in tasks_candidates/rtl_debug_*/; do
        echo "Validating $(basename "$task_dir")..."
        python -m validators.vcs.validate_rtl "$task_dir" || true
        VALIDATED=$((VALIDATED + 1))
    done
else
    echo "[SKIP] EDA_VCS_CMD not set, skipping VCS validation"
    SKIPPED=$((SKIPPED + 1))
fi

# HSPICE validation for SPICE tasks
if [ -n "${EDA_HSPICE_CMD:-}" ]; then
    echo "--- HSPICE Validation ---"
    for task_dir in tasks_candidates/spice_deck_debug_*/; do
        echo "Validating $(basename "$task_dir")..."
        python -m validators.hspice.validate_spice "$task_dir" || true
        VALIDATED=$((VALIDATED + 1))
    done
else
    echo "[SKIP] EDA_HSPICE_CMD not set, skipping HSPICE validation"
    SKIPPED=$((SKIPPED + 1))
fi

# Spectre validation for SPICE tasks
if [ -n "${EDA_SPECTRE_CMD:-}" ]; then
    echo "--- Spectre Validation ---"
    for task_dir in tasks_candidates/spice_deck_debug_*/; do
        echo "Validating $(basename "$task_dir")..."
        python -m validators.spectre.validate_spectre "$task_dir" || true
        VALIDATED=$((VALIDATED + 1))
    done
else
    echo "[SKIP] EDA_SPECTRE_CMD not set, skipping Spectre validation"
    SKIPPED=$((SKIPPED + 1))
fi

# PrimeTime validation for timing tasks
if [ -n "${EDA_PT_CMD:-}" ]; then
    echo "--- PrimeTime Validation ---"
    for task_dir in tasks_candidates/timing_report_qa_*/; do
        echo "Validating $(basename "$task_dir")..."
        python -m validators.pt.parse_report "$task_dir" || true
        VALIDATED=$((VALIDATED + 1))
    done
else
    echo "[SKIP] EDA_PT_CMD not set, skipping PrimeTime validation"
    SKIPPED=$((SKIPPED + 1))
fi

echo ""
echo "=== Commercial Validation Summary ==="
echo "Validated: $VALIDATED"
echo "Skipped:   $SKIPPED (tool not available)"

if [ -d .local_runs ]; then
    echo ""
    echo "Raw logs stored in: .local_runs/ (git-ignored)"
    echo "Validation records: .local_runs/*/validation_record.json"
fi
