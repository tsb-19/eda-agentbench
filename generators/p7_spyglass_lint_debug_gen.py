"""P7 SpyGlass Lint Debug task generator — reliable bug categories, deterministic seed.

Only categories that produce detectable violations under SpyGlass Lint
(lint/lint_rtl goal, default policies) are included.  Each category has
a correct and buggy RTL version.

Bug categories (retained — verified to produce Errors/Warnings):
  - latch_inference: incomplete if-else in combinational block → latch
  - multi_driven: same signal assigned in two always blocks
  - blocking_in_seq: blocking assignment in sequential always block

Rejected/deferred categories (SpyGlass default lint does NOT flag these):
  - width_mismatch: SpyGlass accepts without warning
  - unused_signal: SpyGlass accepts without warning
  - undriven_signal: SpyGlass accepts without warning
  - missing_default: SpyGlass accepts without warning
  - implicit_net: SpyGlass accepts without warning
  - combinational_loop: not reliably flagged
  - unreachable_case_item: depends on synthesis context
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from generators.base import BaseGenerator


# ---------------------------------------------------------------------------
# RTL templates — each returns (correct_rtl, buggy_rtl, description, difficulty)
# ---------------------------------------------------------------------------

def _bug_latch_inference(rng) -> tuple[str, str, str, str, str]:
    """Incomplete if-else in combinational block creates a latch."""
    width = rng.choice([4, 8])
    correct = f"""\
module comb_mux (
    input  wire [{width-1}:0] a,
    input  wire [{width-1}:0] b,
    input  wire       sel,
    output reg  [{width-1}:0] y
);
    always @(*) begin
        if (sel)
            y = a;
        else
            y = b;
    end
endmodule
"""
    buggy = f"""\
module comb_mux (
    input  wire [{width-1}:0] a,
    input  wire [{width-1}:0] b,
    input  wire       sel,
    output reg  [{width-1}:0] y
);
    always @(*) begin
        if (sel)
            y = a;
    end
endmodule
"""
    return correct, buggy, "latch_inference", "easy", \
        "Incomplete if-else in combinational always block — creates inferred latch"


def _bug_width_mismatch(rng) -> tuple[str, str, str, str, str]:
    """Assign wider expression to narrower signal."""
    wide = rng.choice([8, 16])
    narrow = wide // 2
    correct = f"""\
module width_check (
    input  wire [{wide-1}:0] a,
    input  wire [{wide-1}:0] b,
    output wire [{wide-1}:0] sum
);
    assign sum = a + b;
endmodule
"""
    buggy = f"""\
module width_check (
    input  wire [{wide-1}:0] a,
    input  wire [{wide-1}:0] b,
    output wire [{narrow-1}:0] sum
);
    assign sum = a + b;
endmodule
"""
    return correct, buggy, "width_mismatch", "easy", \
        "Output width narrower than input — width mismatch on addition result"


def _bug_unused_signal(rng) -> tuple[str, str, str, str, str]:
    """Declare a signal that is never read."""
    correct = """\
module unused_clean (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] d,
    output reg  [7:0] q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 8'd0;
        else
            q <= d;
    end
endmodule
"""
    buggy = """\
module unused_clean (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] d,
    output reg  [7:0] q
);
    wire [7:0] unused_w;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 8'd0;
        else
            q <= d;
    end
endmodule
"""
    return correct, buggy, "unused_signal", "easy", \
        "Declared wire 'unused_w' is never used — unused signal warning"


def _bug_undriven_signal(rng) -> tuple[str, str, str, str, str]:
    """Declare output but never assign it."""
    correct = """\
module undriven_clean (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] d,
    output reg  [7:0] q,
    output reg  [7:0] status
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            q <= 8'd0;
            status <= 8'd0;
        end else begin
            q <= d;
            status <= d;
        end
    end
endmodule
"""
    buggy = """\
module undriven_clean (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] d,
    output reg  [7:0] q,
    output reg  [7:0] status
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 8'd0;
        else
            q <= d;
    end
endmodule
"""
    return correct, buggy, "undriven_signal", "easy", \
        "Output 'status' is declared but never driven — undriven signal warning"


def _bug_multi_driven(rng) -> tuple[str, str, str, str, str]:
    """Same signal assigned in two always blocks."""
    correct = """\
module multi_driven_clean (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] d,
    input  wire       en,
    output reg  [7:0] q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 8'd0;
        else if (en)
            q <= d;
    end
endmodule
"""
    buggy = """\
module multi_driven_clean (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] d,
    input  wire       en,
    output reg  [7:0] q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 8'd0;
        else if (en)
            q <= d;
    end

    always @(posedge clk) begin
        if (!en)
            q <= 8'hFF;
    end
endmodule
"""
    return correct, buggy, "multi_driven", "medium", \
        "Signal 'q' driven by two always blocks — multi-driven net error"


def _bug_missing_default(rng) -> tuple[str, str, str, str, str]:
    """case statement without default creates potential latch."""
    n_states = rng.choice([3, 4])
    correct_lines = []
    buggy_lines = []
    for i in range(n_states):
        correct_lines.append(f"            {i}: q <= {i};")
        buggy_lines.append(f"            {i}: q <= {i};")
    correct_lines.append("            default: q <= 0;")
    # buggy has no default

    correct = f"""\
module fsm_case (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [1:0] state,
    output reg  [7:0] q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 8'd0;
        else begin
            case (state)
{chr(10).join(correct_lines)}
            endcase
        end
    end
endmodule
"""
    buggy = f"""\
module fsm_case (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [1:0] state,
    output reg  [7:0] q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 8'd0;
        else begin
            case (state)
{chr(10).join(buggy_lines)}
            endcase
        end
    end
endmodule
"""
    return correct, buggy, "missing_default", "medium", \
        "case statement without default — potential latch or incomplete coverage"


def _bug_implicit_net(rng) -> tuple[str, str, str, str, str]:
    """Use undeclared wire (implicit net declaration)."""
    correct = """\
module implicit_net_clean (
    input  wire a,
    input  wire b,
    output wire y
);
    wire intermediate;
    assign intermediate = a & b;
    assign y = intermediate;
endmodule
"""
    buggy = """\
module implicit_net_clean (
    input  wire a,
    input  wire b,
    output wire y
);
    assign intermediate = a & b;
    assign y = intermediate;
endmodule
"""
    return correct, buggy, "implicit_net", "easy", \
        "Signal 'intermediate' used without declaration — implicit net warning"


def _bug_blocking_in_seq(rng) -> tuple[str, str, str, str, str]:
    """Blocking assignment in sequential always block."""
    correct = """\
module seq_blocking_clean (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] d,
    output reg  [7:0] q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 8'd0;
        else
            q <= d;
    end
endmodule
"""
    buggy = """\
module seq_blocking_clean (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] d,
    output reg  [7:0] q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q = 8'd0;
        else
            q = d;
    end
endmodule
"""
    return correct, buggy, "blocking_in_seq", "medium", \
        "Blocking assignment (=) in sequential always block — use non-blocking (<=)"


# Registry of bug generators — only categories with reliable SpyGlass detection
BUG_GENERATORS = [
    _bug_latch_inference,
    _bug_multi_driven,
    _bug_blocking_in_seq,
]

EXPECTED_BUG_TYPE_NAMES = [
    "latch_inference", "multi_driven", "blocking_in_seq",
]


def _make_spyglass_prj(task_dir_name: str) -> str:
    """Generate SpyGlass project file content."""
    return f"""\
# SpyGlass Lint Debug project file
# Auto-generated — do not edit
set_option enableSV09 yes
set_option enableSV yes
read_file -type verilog design.v
current_goal lint/lint_rtl
"""


def _make_spyglass_tcl(section: str, top_module: str) -> str:
    """Generate TCL script for SpyGlass sg_shell."""
    return f"""\
# SpyGlass Lint Debug — {section} TCL script
# Auto-generated — do not edit

# Read design and set top
read_file -type verilog design.v
set_option top {top_module}

# Run lint goal
current_goal lint/lint_rtl
run_goal

exit
"""


def _make_sh(section: str) -> str:
    """Generate bash run script."""
    return f"""\
#!/bin/bash
# SpyGlass Lint Debug — {section} run script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

SG_CMD="${{EDA_SG_CMD:-sg_shell}}"

# Check if sg_shell is available
if ! command -v "$SG_CMD" &>/dev/null; then
    echo "SKIP: sg_shell not found (EDA_SG_CMD=$SG_CMD)"
    exit 0
fi

# Run sg_shell with TCL script
SG_OUTPUT=$("$SG_CMD" -tcl run_{section}.tcl 2>&1)
SG_EXIT=$?

echo "$SG_OUTPUT"

# Parse the Goal Violation Summary from SpyGlass output
# Format:
#   Goal Violation Summary:
#       Waived   Messages:                      0 Errors,      0 Warnings,      0 Infos
#       Reported Messages:         0 Fatals,    1 Errors,      1 Warnings,      3 Infos
VIOLATION_COUNT=0

REPORTED_LINE=$(echo "$SG_OUTPUT" | grep "Reported Messages:" | tail -1)
if [ -n "$REPORTED_LINE" ]; then
    FATALS=$(echo "$REPORTED_LINE" | grep -oP '\\d+(?=\\s+Fatal)' || echo "0")
    ERRORS=$(echo "$REPORTED_LINE" | grep -oP '\\d+(?=\\s+Error)' || echo "0")
    WARNINGS=$(echo "$REPORTED_LINE" | grep -oP '\\d+(?=\\s+Warning)' || echo "0")
    VIOLATION_COUNT=$((FATALS + ERRORS + WARNINGS))
fi

echo "Lint violations: $VIOLATION_COUNT"

if [ "$SG_EXIT" -ne 0 ] && [ "$VIOLATION_COUNT" -eq 0 ]; then
    # sg_shell exited nonzero but no violations found — treat as crash
    echo "LINT_FAIL"
    exit 1
fi

if [ "$VIOLATION_COUNT" -gt 0 ]; then
    echo "LINT_FAIL"
    exit 1
else
    echo "LINT_PASS"
    exit 0
fi
"""


class P7SpyGlassLintDebugGenerator(BaseGenerator):
    """Generates P7 SpyGlass Lint Debug tasks with deterministic seeds."""

    def generate_one(self, task_index: int) -> Path:
        bug_fn = BUG_GENERATORS[task_index % len(BUG_GENERATORS)]
        # Use rng for any randomization within the bug function
        correct_rtl, buggy_rtl, bug_name, difficulty, description = bug_fn(self.rng)

        # Extract top module name from RTL
        m = re.search(r"module\s+(\w+)", correct_rtl)
        top_module = m.group(1) if m else "top"

        task_id = f"sg_lint_{task_index:04d}"
        task_dir = self.output_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (task_dir / "files").mkdir(exist_ok=True)
        (task_dir / "hidden").mkdir(exist_ok=True)
        (task_dir / "solution").mkdir(exist_ok=True)

        # Write buggy RTL (editable)
        (task_dir / "files" / "design.v").write_text(buggy_rtl)

        # Write correct RTL (solution)
        (task_dir / "solution" / "design.v").write_text(correct_rtl)

        # Write SpyGlass project file (visible, not editable)
        (task_dir / "files" / "spyglass.prj").write_text(_make_spyglass_prj(task_id))

        # Write run scripts
        (task_dir / "files" / "run_public.sh").write_text(_make_sh("public"))
        (task_dir / "files" / "run_public.tcl").write_text(_make_spyglass_tcl("public", top_module))
        (task_dir / "hidden" / "run_hidden.sh").write_text(_make_sh("hidden"))
        (task_dir / "hidden" / "run_hidden.tcl").write_text(_make_spyglass_tcl("hidden", top_module))

        # Make scripts executable
        (task_dir / "files" / "run_public.sh").chmod(0o755)
        (task_dir / "hidden" / "run_hidden.sh").chmod(0o755)

        # Write prompt
        prompt = f"""\
# SpyGlass Lint Debug Task: {bug_name.replace('_', ' ').title()}

## Description

The RTL design `design.v` has a lint issue that SpyGlass Lint detects.
Fix the design file so that the lint check passes with zero violations.

## Bug Category

{description}

## Files

- `design.v` — RTL design (you may edit this file)
- `spyglass.prj` — SpyGlass project file (do not modify)
- `run_public.sh` — public test runner (do not modify)
- `run_public.tcl` — SpyGlass TCL script (do not modify)

## Constraints

- Only modify `design.v`
- Do not modify any other files
- The lint check must pass with zero violations

## Hint

Run `bash run_public.sh` to check if your fix passes the lint check.
The script will report `LINT_PASS` if all violations are resolved.
"""
        (task_dir / "prompt.md").write_text(prompt)

        # Write metadata
        meta = {
            "task_id": task_id,
            "track": "p7_spyglass_lint_debug",
            "tool": ["spyglass"],
            "difficulty": difficulty,
            "data_type": "template_synthetic",
            "resource_preset": "standard",
            "timeout_sec": 300,
            "max_tool_calls": 30,
            "max_patch_attempts": 8,
            "max_output_tokens": 32000,
            "files": {
                "visible": ["design.v", "spyglass.prj", "run_public.sh", "run_public.tcl"],
                "editable": ["design.v"],
                "hidden": ["run_hidden.sh", "run_hidden.tcl"],
                "forbidden": ["spyglass.prj", "run_public.sh", "run_public.tcl",
                              "run_hidden.sh", "run_hidden.tcl"],
            },
            "run_command": "bash run_public.sh && bash run_hidden.sh",
            "scoring": {
                "weights": {
                    "lint_pass": 0.9,
                    "explanation": 0.1,
                },
                "evaluator": "spyglass_lint_debug.SpyGlassLintDebugEvaluator",
                "explanation_weight": 0.1,
            },
            "sanitizer": {"enabled": True},
            "generator": {
                "script": "p7_spyglass_lint_debug_gen.py",
                "seed": self.seed,
                "bug_type": bug_name,
                "top_module": top_module,
                "task_index": task_index,
            },
            "expected_error_category": bug_name,
            "version": "1.0.0",
        }
        (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")

        return task_dir
