#!/bin/bash
# PrimeTime STA Debug — public run script (two-phase, forge-resistant)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PT_CMD="${EDA_PT_CMD:-pt_shell}"
APPLIED="applied_public.sdc"
REQ_IN="rst_n start"
REQ_OUT="busy done"

if ! command -v "$PT_CMD" &>/dev/null; then
    echo "SKIP: pt_shell not found (EDA_PT_CMD=$PT_CMD)"
    exit 0
fi

# --- Phase 1: apply agent constraints (agent Tcl sandboxed via read_sdc) ---
rm -f "$APPLIED"
PT_OUTPUT=$("$PT_CMD" -f run_public.tcl 2>&1)
# Prefix raw tool output so an agent-injected "TIMING_CHECK_OK" cannot match ^TIMING_CHECK_OK
echo "$PT_OUTPUT" | sed 's/^/[apply] /'

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
if echo "$PT_OUTPUT" | grep -Eq "unknown command|Can't find|cannot find"; then
    ok=0; reasons="$reasons,tool_error"
fi

if [ "$ok" = 1 ]; then
    echo "TIMING_CHECK_OK"
    exit 0
else
    echo "TIMING_CHECK_FAIL: ${reasons#,}"
    exit 1
fi
