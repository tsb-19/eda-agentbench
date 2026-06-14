#!/usr/bin/env bash
# Package a validated task for public release under tasks_public/.
#
# Default flow (requires validated task):
#   bash scripts/package_public_task.sh tasks_validated/spice_deck_debug_0001
#
# Override for unvalidated tasks (explicit opt-in):
#   bash scripts/package_public_task.sh tasks_candidates/spice_deck_debug_0001 --allow-unvalidated
#
# The task must have:
#   - public_release_safe: true in metadata.json
#   - validation_status: validated_static or validated_commercial
#     (unless --allow-unvalidated is passed)
#
# The script:
#   1. Copies the task directory to tasks_public/
#   2. Strips raw data: .log, .lis, .trn, .dsn, .raw, .st0, .sw0 files
#   3. Strips validation_record.json (internal detail)
#   4. Keeps validation/normalized_errors.json and validation/raw_log.sha256
#   5. Verifies no proprietary data is present
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

ALLOW_UNVALIDATED=false
TASK_PATH=""

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --allow-unvalidated)
            ALLOW_UNVALIDATED=true
            ;;
        *)
            TASK_PATH="$arg"
            ;;
    esac
done

if [ -z "$TASK_PATH" ]; then
    echo "Usage: $0 <task_path> [--allow-unvalidated]"
    echo ""
    echo "  task_path: path to task directory"
    echo "             Default: must be under tasks_validated/"
    echo "             With --allow-unvalidated: may be under tasks_candidates/"
    echo ""
    echo "Pipeline:"
    echo "  tasks_candidates/ -> validate -> tasks_validated/ -> package -> tasks_public/"
    echo ""
    echo "Examples:"
    echo "  $0 tasks_validated/spice_deck_debug_0001"
    echo "  $0 tasks_candidates/spice_deck_debug_0001 --allow-unvalidated"
    exit 1
fi

if [ ! -d "$TASK_PATH" ]; then
    echo "[ERROR] Task directory not found: $TASK_PATH"
    exit 1
fi

TASK_NAME=$(basename "$TASK_PATH")
META_FILE="$TASK_PATH/metadata.json"

if [ ! -f "$META_FILE" ]; then
    echo "[ERROR] metadata.json not found in $TASK_PATH"
    exit 1
fi

# Enforce validated-only by default
if [ "$ALLOW_UNVALIDATED" = false ]; then
    # Resolve to check if it's under tasks_validated/
    RESOLVED_PATH=$(cd "$TASK_PATH" 2>/dev/null && pwd || echo "$TASK_PATH")
    VALIDATED_ROOT=$(cd "$REPO_ROOT/tasks_validated" 2>/dev/null && pwd || echo "NONE")
    case "$RESOLVED_PATH" in
        "$VALIDATED_ROOT"/*)
            # OK — task is from the validated directory
            ;;
        *)
            echo "[ERROR] Task must be under tasks_validated/ to package for public release."
            echo ""
            echo "  Validated flow:"
            echo "    bash scripts/validate_one_candidate.sh tasks_candidates/$TASK_NAME <backend>"
            echo "    bash scripts/package_public_task.sh tasks_validated/$TASK_NAME"
            echo ""
            echo "  To override (explicit opt-in):"
            echo "    bash scripts/package_public_task.sh $TASK_PATH --allow-unvalidated"
            exit 1
            ;;
    esac
fi

# Check public_release_safe
PUBLIC_SAFE=$(python -c "import json; print(json.load(open('$META_FILE'))['public_release_safe'])")
if [ "$PUBLIC_SAFE" != "True" ]; then
    echo "[ERROR] Task $TASK_NAME is not marked public_release_safe=true"
    exit 1
fi

# Check validation_status
VALIDATION_STATUS=$(python3 -c "import json; print(json.load(open('$META_FILE'))['validation_status'])")
DOMAIN=$(python3 -c "import json; print(json.load(open('$META_FILE'))['domain'])")

# Valid statuses for packaging
VALID_STATUSES="validated_static commercial_smoke_passed debug_contrast_verified oracle_parser_verified"

# For debug tasks, require debug_contrast_verified
if [ "$DOMAIN" = "rtl_debug" ] || [ "$DOMAIN" = "spice_deck_debug" ]; then
    REQUIRED_STATUS="debug_contrast_verified"
else
    REQUIRED_STATUS=""
fi

if echo "$VALID_STATUSES" | grep -qw "$VALIDATION_STATUS"; then
    # Status is in the valid set
    if [ -n "$REQUIRED_STATUS" ] && [ "$VALIDATION_STATUS" != "$REQUIRED_STATUS" ]; then
        if [ "$ALLOW_UNVALIDATED" = true ]; then
            echo "[WARN] Debug task $TASK_NAME has validation_status=$VALIDATION_STATUS (expected $REQUIRED_STATUS)"
            echo "       Packaging anyway (--allow-unvalidated was set)."
        else
            echo "[ERROR] Debug task $TASK_NAME has validation_status=$VALIDATION_STATUS"
            echo "        Debug tasks require $REQUIRED_STATUS."
            echo "        Run debug contrast validation first."
            exit 1
        fi
    fi
else
    if [ "$ALLOW_UNVALIDATED" = true ]; then
        echo "[WARN] Task $TASK_NAME has validation_status=$VALIDATION_STATUS"
        echo "       Packaging anyway (--allow-unvalidated was set)."
    else
        echo "[ERROR] Task $TASK_NAME has validation_status=$VALIDATION_STATUS"
        echo "        Valid statuses: $VALID_STATUSES"
        exit 1
    fi
fi

# Ensure tasks_public directory exists
mkdir -p tasks_public

# Copy task to tasks_public/
DEST="tasks_public/$TASK_NAME"
if [ -d "$DEST" ]; then
    echo "[WARN] Overwriting existing $DEST"
    rm -rf "$DEST"
fi

echo "Packaging $TASK_NAME for public release..."
cp -r "$TASK_PATH" "$DEST"

# Remove raw simulator output files
echo "Removing raw simulator output files..."
find "$DEST" -type f \( \
    -name "*.log" -o \
    -name "*.lis" -o \
    -name "*.trn" -o \
    -name "*.dsn" -o \
    -name "*.raw" -o \
    -name "*.st0" -o \
    -name "*.sw0" -o \
    -name "*.ac0" -o \
    -name "*.ic0" \
\) -delete 2>/dev/null || true

# Keep validation_record.json (it contains only normalized data, no raw logs)
# Remove any stray raw log files that might be in validation/
find "$DEST/validation" -name "*.log" -type f -delete 2>/dev/null || true

# Remove hidden/ and oracle/ (golden solutions) unless allow_public_oracle is set
ALLOW_ORACLE=$(python3 -c "import json; print(json.load(open('$META_FILE')).get('allow_public_oracle', False))" 2>/dev/null || echo "False")
if [ "$ALLOW_ORACLE" != "True" ]; then
    rm -rf "$DEST/hidden" 2>/dev/null || true
    rm -rf "$DEST/oracle" 2>/dev/null || true
fi

# === Safety checks ===
echo "Running safety checks..."

# Check 1: No absolute paths
ABS_PATH_HITS=$(grep -rn '/home/\|/data1/\|/tmp/\|/EDA/\|/tools/\|/usr/local/' "$DEST" 2>/dev/null || true)
if [ -n "$ABS_PATH_HITS" ]; then
    echo "[ERROR] Absolute paths found in public package:"
    echo "$ABS_PATH_HITS"
    echo "Removing contaminated package..."
    rm -rf "$DEST"
    exit 1
fi

# Check 2: No raw simulator output files remain
RAW_HITS=$(find "$DEST" -type f \( -name "*.log" -o -name "*.lis" -o -name "*.trn" -o -name "*.dsn" -o -name "*.raw" \) 2>/dev/null || true)
if [ -n "$RAW_HITS" ]; then
    echo "[ERROR] Raw simulator output files found in public package:"
    echo "$RAW_HITS"
    echo "Removing contaminated package..."
    rm -rf "$DEST"
    exit 1
fi

# Check 3: No license variables
LIC_HITS=$(grep -ri 'LM_LICENSE_FILE\|SNPSLMD_LICENSE_FILE\|CDS_LIC_FILE\|license_file\|license_path\|license_server\|flexlm' "$DEST" 2>/dev/null || true)
if [ -n "$LIC_HITS" ]; then
    echo "[ERROR] License variable references found in public package:"
    echo "$LIC_HITS"
    echo "Removing contaminated package..."
    rm -rf "$DEST"
    exit 1
fi

# Check 4: No hostnames or usernames
HOST_HITS=$(grep -ri 'hostname\|host_name\|/home/[a-z]' "$DEST" 2>/dev/null || true)
if [ -n "$HOST_HITS" ]; then
    echo "[ERROR] Hostname/username references found in public package:"
    echo "$HOST_HITS"
    echo "Removing contaminated package..."
    rm -rf "$DEST"
    exit 1
fi

# Check 5: task_id in metadata matches directory name
META_TASK_ID=$(python -c "import json; print(json.load(open('$DEST/metadata.json'))['task_id'])")
if [ "$META_TASK_ID" != "$TASK_NAME" ]; then
    echo "[ERROR] metadata task_id '$META_TASK_ID' does not match directory name '$TASK_NAME'"
    rm -rf "$DEST"
    exit 1
fi

# Check 6: public_release_safe is true in the copy
DEST_SAFE=$(python -c "import json; print(json.load(open('$DEST/metadata.json'))['public_release_safe'])")
if [ "$DEST_SAFE" != "True" ]; then
    echo "[ERROR] public_release_safe is not true in the public package"
    rm -rf "$DEST"
    exit 1
fi

echo ""
echo "=== Public package created ==="
echo "  Location: $DEST"
echo "  Status:   $VALIDATION_STATUS"
echo "  Safe:     $PUBLIC_SAFE"
echo ""
echo "Safety checks passed:"
echo "  - No absolute paths"
echo "  - No raw simulator output files"
echo "  - No license variable references"
echo "  - No hostname/username references"
echo "  - task_id matches directory name"
echo "  - public_release_safe=true"
