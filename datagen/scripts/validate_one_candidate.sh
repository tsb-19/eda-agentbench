#!/usr/bin/env bash
# Validate a single candidate task using a specified commercial backend.
#
# Pipeline:
#   1. Reads task from tasks_candidates/
#   2. Runs commercial validation
#   3. Stores raw logs under .local_runs/ (git-ignored)
#   4. Copies validated task to tasks_validated/ with validation/ subdirectory
#
# Usage:
#   bash scripts/validate_one_candidate.sh <task_path> <backend>
#
# Examples:
#   bash scripts/validate_one_candidate.sh tasks_candidates/spice_deck_debug_0001 hspice
#   bash scripts/validate_one_candidate.sh tasks_candidates/rtl_debug_0001 vcs
#   bash scripts/validate_one_candidate.sh tasks_candidates/timing_report_qa_0001 pt
#
# Backends: vcs, hspice, spectre, pt
#
# The selected backend's EDA_*_CMD environment variable is checked first.
# If not set, the script tries to discover the tool from PATH.
# If neither works, the script skips gracefully with exit 0.
#
# After validation, the task appears under tasks_validated/ with:
#   validation/validation_record.json
#   validation/normalized_errors.json
#   validation/raw_log.sha256
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

if [ $# -lt 2 ]; then
    echo "Usage: $0 <task_path> <backend>"
    echo ""
    echo "  task_path: path to task directory (e.g., tasks_candidates/spice_deck_debug_0001)"
    echo "  backend:   vcs | hspice | spectre | pt"
    echo ""
    echo "Pipeline:"
    echo "  tasks_candidates/ -> validate -> tasks_validated/ -> package -> tasks_public/"
    echo ""
    echo "Environment variables (optional — PATH discovery is used as fallback):"
    echo "  EDA_VCS_CMD      - path to VCS executable"
    echo "  EDA_HSPICE_CMD   - path to HSPICE executable"
    echo "  EDA_SPECTRE_CMD  - path to Spectre executable"
    echo "  EDA_PT_CMD       - path to PrimeTime executable"
    exit 1
fi

TASK_PATH="$1"
BACKEND="$2"

if [ ! -d "$TASK_PATH" ]; then
    echo "[ERROR] Task directory not found: $TASK_PATH"
    exit 1
fi

TASK_NAME=$(basename "$TASK_PATH")

echo "=== Validating $TASK_NAME with backend: $BACKEND ==="

# Helper: find tool command from env var or PATH
find_tool() {
    local env_var="$1"
    local tool_name="$2"
    local cmd="${!env_var:-}"
    if [ -n "$cmd" ]; then
        echo "$cmd"
        return 0
    fi
    local found
    found=$(which "$tool_name" 2>/dev/null || true)
    if [ -n "$found" ]; then
        echo "$found"
        return 0
    fi
    return 1
}

case "$BACKEND" in
    vcs)
        if ! VCS_CMD=$(find_tool EDA_VCS_CMD vcs); then
            echo "[SKIP] EDA_VCS_CMD not set and vcs not in PATH, skipping"
            exit 0
        fi
        export EDA_VCS_CMD="$VCS_CMD"
        python -m validators.vcs.validate_rtl "$TASK_PATH"
        ;;
    hspice)
        if ! HSPICE_CMD=$(find_tool EDA_HSPICE_CMD hspice); then
            echo "[SKIP] EDA_HSPICE_CMD not set and hspice not in PATH, skipping"
            exit 0
        fi
        export EDA_HSPICE_CMD="$HSPICE_CMD"
        python -m validators.hspice.validate_spice "$TASK_PATH"
        ;;
    spectre)
        if ! SPECTRE_CMD=$(find_tool EDA_SPECTRE_CMD spectre); then
            echo "[SKIP] EDA_SPECTRE_CMD not set and spectre not in PATH, skipping"
            exit 0
        fi
        export EDA_SPECTRE_CMD="$SPECTRE_CMD"
        python -m validators.spectre.validate_spectre "$TASK_PATH"
        ;;
    pt)
        if ! PT_CMD=$(find_tool EDA_PT_CMD pt_shell); then
            echo "[SKIP] EDA_PT_CMD not set and pt_shell not in PATH, skipping"
            exit 0
        fi
        export EDA_PT_CMD="$PT_CMD"
        python -m validators.pt.parse_report "$TASK_PATH"
        ;;
    *)
        echo "[ERROR] Unknown backend: $BACKEND"
        echo "Valid backends: vcs, hspice, spectre, pt"
        exit 1
        ;;
esac

echo ""
echo "=== Pipeline next step ==="
echo "Validated task is at: tasks_validated/$TASK_NAME/"
echo "To package for public release:"
echo "  bash scripts/package_public_task.sh tasks_validated/$TASK_NAME"
