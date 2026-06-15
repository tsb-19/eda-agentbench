#!/bin/bash
# DC Constraint Debug — hidden run script (two-phase, forge-resistant)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

DC_CMD="${EDA_DC_CMD:-dc_shell}"
APPLIED="applied_hidden.sdc"
REQ_IN="rst_n op a b"
REQ_OUT="result"

if ! command -v "$DC_CMD" &>/dev/null; then
    echo "SKIP: dc_shell not found (EDA_DC_CMD=$DC_CMD)"
    exit 0
fi

# --- Phase 1: apply agent constraints (agent Tcl sandboxed via read_sdc) ---
rm -f "$APPLIED"
APPLY_OUT=$("$DC_CMD" -f run_hidden.tcl 2>&1)
# Prefix raw tool output so an agent-injected "CONSTRAINTS_OK" cannot match ^CONSTRAINTS_OK
echo "$APPLY_OUT" | sed 's/^/[apply] /'

# --- Phase 2: verdict from the laundered applied SDC (no agent-controlled code here) ---
ok=1
reasons=""
if [ ! -s "$APPLIED" ]; then
    ok=0; reasons="no_applied_sdc"
else
    grep -q "create_clock" "$APPLIED" || { ok=0; reasons="$reasons,no_clock"; }
    for p in $REQ_IN; do
        grep -Eq "set_input_delay.*\b$p\b" "$APPLIED" || { ok=0; reasons="$reasons,no_input_delay:$p"; }
    done
    for p in $REQ_OUT; do
        grep -Eq "set_output_delay.*\b$p\b" "$APPLIED" || { ok=0; reasons="$reasons,no_output_delay:$p"; }
    done
fi
# Tool-native errors the agent cannot remove (e.g. unsupported command, bad port)
if echo "$APPLY_OUT" | grep -Eq "unknown command|Can't find|cannot find"; then
    ok=0; reasons="$reasons,tool_error"
fi

if [ "$ok" = 1 ]; then
    echo "CONSTRAINTS_OK"
    exit 0
else
    echo "CONSTRAINTS_FAIL: ${reasons#,}"
    exit 1
fi
