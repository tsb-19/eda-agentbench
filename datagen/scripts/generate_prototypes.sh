#!/usr/bin/env bash
# Generate SPICE deck debug prototype tasks.
# Idempotent: re-running overwrites existing tasks with identical content.
#
# This module now owns only the spice_deck_debug domain. The rtl_debug and
# timing_report_qa domains were retired (see CLAUDE.md): RTL and timing tasks
# are generated directly by the parent repo's generators/ (tracks p1/p3).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

echo "=== Generating prototype tasks ==="

echo "[1/1] SPICE deck debug tasks..."
python -m generators.spice_deck_debug.generate

echo ""
echo "=== Task generation complete ==="
echo "Tasks written to: $REPO_ROOT/tasks_candidates/"
