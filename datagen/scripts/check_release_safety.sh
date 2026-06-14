#!/usr/bin/env bash
# Release safety scanner.
#
# Scans a target directory (or the whole repo) for content that must not be published.
#
# Usage:
#   bash scripts/check_release_safety.sh [target_dir]
#
# If target_dir is omitted, scans the entire repository.
# Exit code 0 = safe, exit code 1 = violations found.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

TARGET="${1:-$REPO_ROOT}"

cd "$REPO_ROOT"

PASS=0
FAIL=0
WARNINGS=0

check() {
    local desc="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        echo "[PASS] $desc"
        PASS=$((PASS + 1))
    else
        echo "[FAIL] $desc"
        FAIL=$((FAIL + 1))
    fi
}

warn() {
    local desc="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        echo "[WARN] $desc"
        WARNINGS=$((WARNINGS + 1))
    fi
}

echo "=== Release Safety Scan ==="
echo "Target: $TARGET"
echo ""

# 1. Check for hidden/oracle directories
echo "--- Checking for hidden/oracle directories ---"
check "No hidden/ directories" bash -c "
! find '$TARGET' -type d -name 'hidden' 2>/dev/null | grep -q .
"
check "No oracle/ directories" bash -c "
! find '$TARGET' -type d -name 'oracle' 2>/dev/null | grep -q .
"

# 2. Check for tasks_eval_private/
echo ""
echo "--- Checking for private bundle leakage ---"
check "No tasks_eval_private/ in target" bash -c "
! find '$TARGET' -type d -name 'tasks_eval_private' 2>/dev/null | grep -q .
"

# 3. Check for .local_runs/
echo ""
echo "--- Checking for raw commercial logs ---"
check "No .local_runs/ in target" bash -c "
! find '$TARGET' -type d -name '.local_runs' 2>/dev/null | grep -q .
"

# 4. Check for raw simulator output files
echo ""
echo "--- Checking for raw simulator output files ---"
RAW_EXTS="log lis trn dsn raw st0 sw0 ac0 ic0"
for ext in $RAW_EXTS; do
    hits=$(find "$TARGET" -type f -name "*.$ext" 2>/dev/null || true)
    if [ -n "$hits" ]; then
        echo "[FAIL] Found *.$ext files:"
        echo "$hits" | head -5
        FAIL=$((FAIL + 1))
    else
        echo "[PASS] No *.$ext files"
        PASS=$((PASS + 1))
    fi
done

# 5. Check for absolute paths
echo ""
echo "--- Checking for absolute paths ---"
ABS_PATTERNS="/EDA/ /home/ /data1/ /tmp/ /tools/ /usr/local/"
for pattern in $ABS_PATTERNS; do
    hits=$(grep -rn "$pattern" "$TARGET" --include='*.json' --include='*.md' --include='*.sp' --include='*.v' --include='*.py' --include='*.sh' 2>/dev/null | grep -v "check_release_safety" | grep -v "release_checklist" || true)
    if [ -n "$hits" ]; then
        echo "[FAIL] Found '$pattern' references:"
        echo "$hits" | head -3
        FAIL=$((FAIL + 1))
    else
        echo "[PASS] No '$pattern' references"
        PASS=$((PASS + 1))
    fi
done

# 6. Check for license variables
echo ""
echo "--- Checking for license variables ---"
LIC_VARS="LM_LICENSE_FILE SNPSLMD_LICENSE_FILE CDS_LIC_FILE"
for var in $LIC_VARS; do
    hits=$(grep -rn "$var" "$TARGET" --include='*.json' --include='*.md' --include='*.sp' --include='*.v' --include='*.py' --include='*.sh' --include='*.log' 2>/dev/null || true)
    if [ -n "$hits" ]; then
        echo "[FAIL] Found '$var' references:"
        echo "$hits" | head -3
        FAIL=$((FAIL + 1))
    else
        echo "[PASS] No '$var' references"
        PASS=$((PASS + 1))
    fi
done

# 7. Check for hostnames/usernames
echo ""
echo "--- Checking for hostname/username leakage ---"
check "No hostname references" bash -c "
! grep -rn 'hostname\|host_name' '$TARGET' --include='*.json' --include='*.sp' --include='*.v' 2>/dev/null | grep -v 'check_release_safety\|release_checklist' | grep -q .
"
check "No /home/username paths" bash -c "
! grep -rn '/home/[a-z]' '$TARGET' --include='*.json' --include='*.md' --include='*.sp' --include='*.v' --include='*.sh' 2>/dev/null | grep -v 'check_release_safety\|release_checklist' | grep -q .
"

# 8. If target is tasks_public/, verify task_id and public_release_safe
echo ""
echo "--- Public package metadata checks ---"
if echo "$TARGET" | grep -q "tasks_public"; then
    for task_dir in "$TARGET"/*/; do
        [ -d "$task_dir" ] || continue
        task_name=$(basename "$task_dir")
        meta_file="$task_dir/metadata.json"
        if [ ! -f "$meta_file" ]; then
            echo "[FAIL] $task_name: missing metadata.json"
            FAIL=$((FAIL + 1))
            continue
        fi
        check "$task_name public_release_safe=true" python3 -c "
import json
m = json.load(open('$meta_file'))
assert m.get('public_release_safe') is True
"
    done
fi

echo ""
echo "=== Safety Scan Summary ==="
echo "PASSED:   $PASS"
echo "FAILED:   $FAIL"
echo "WARNINGS: $WARNINGS"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo "[ERROR] Release safety violations found. Fix before publishing."
    exit 1
fi

echo ""
echo "All release safety checks passed."
