"""P6 DC Constraint Debug task generator — 10 bug categories, deterministic seed."""

from __future__ import annotations

import json
from pathlib import Path

from generators.base import BaseGenerator

# ---------------------------------------------------------------------------
# RTL design templates (small modules for DC synthesis)
# ---------------------------------------------------------------------------

_RTL_COUNTER = """\
module counter (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       en,
    output reg  [7:0] count
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= 8'd0;
        else if (en)
            count <= count + 8'd1;
    end
endmodule
"""

_RTL_FSM = """\
module fsm_ctrl (
    input  wire clk,
    input  wire rst_n,
    input  wire start,
    output reg  busy,
    output reg  done
);
    localparam S_IDLE = 2'd0, S_RUN = 2'd1, S_DONE = 2'd2;
    reg [1:0] state;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            busy  <= 1'b0;
            done  <= 1'b0;
        end else begin
            case (state)
                S_IDLE: begin
                    busy <= 1'b0;
                    done <= 1'b0;
                    if (start) state <= S_RUN;
                end
                S_RUN: begin
                    busy <= 1'b1;
                    done <= 1'b0;
                    state <= S_DONE;
                end
                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
"""

_RTL_ADDER = """\
module adder_pipe (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [15:0] a,
    input  wire [15:0] b,
    output reg  [16:0] sum
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            sum <= 17'd0;
        else
            sum <= {1'b0, a} + {1'b0, b};
    end
endmodule
"""

_RTL_MUX = """\
module mux_reg (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [1:0] sel,
    input  wire [7:0] d0, d1, d2, d3,
    output reg  [7:0] q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 8'd0;
        else begin
            case (sel)
                2'd0: q <= d0;
                2'd1: q <= d1;
                2'd2: q <= d2;
                2'd3: q <= d3;
            endcase
        end
    end
endmodule
"""

RTL_TEMPLATES = [
    {"name": "counter", "rtl": _RTL_COUNTER, "top": "counter",
     "clk": "clk", "ports": ["clk", "rst_n", "en", "count[7:0]"]},
    {"name": "fsm_ctrl", "rtl": _RTL_FSM, "top": "fsm_ctrl",
     "clk": "clk", "ports": ["clk", "rst_n", "start", "busy", "done"]},
    {"name": "adder_pipe", "rtl": _RTL_ADDER, "top": "adder_pipe",
     "clk": "clk", "ports": ["clk", "rst_n", "a[15:0]", "b[15:0]", "sum[16:0]"]},
    {"name": "mux_reg", "rtl": _RTL_MUX, "top": "mux_reg",
     "clk": "clk", "ports": ["clk", "rst_n", "sel[1:0]", "d0[7:0]", "d1[7:0]", "d2[7:0]", "d3[7:0]", "q[7:0]"]},
]


# ---------------------------------------------------------------------------
# Correct SDC templates
# ---------------------------------------------------------------------------

def _correct_sdc(rtl: dict, period_ns: float) -> str:
    """Generate correct SDC for the given RTL template."""
    top = rtl["top"]
    clk = rtl["clk"]
    ports = rtl["ports"]

    input_ports = [p.split("[")[0] for p in ports if p.split("[")[0] not in (clk,)]
    output_ports = []
    for p in ports:
        name = p.split("[")[0]
        if name != clk and name not in input_ports:
            output_ports.append(name)

    # Determine outputs (heuristic: last port is output)
    # For our templates: counter(count), fsm_ctrl(busy,done), adder_pipe(sum), mux_reg(q)
    all_names = [p.split("[")[0] for p in ports]
    inputs = [clk, "rst_n"]
    if "en" in all_names:
        inputs.append("en")
    if "start" in all_names:
        inputs.append("start")
    if "sel" in all_names:
        inputs.append("sel")
    for d in ["d0", "d1", "d2", "d3"]:
        if d in all_names:
            inputs.append(d)
    if "a" in all_names:
        inputs.append("a")
    if "b" in all_names:
        inputs.append("b")

    outputs = [n for n in all_names if n not in inputs]

    lines = [
        f"# SDC constraints for {top}",
        f"create_clock -name {clk} -period {period_ns} [get_ports {{{clk}}}]",
        f"set_clock_uncertainty 0.1 [get_clocks {{{clk}}}]",
        "",
    ]

    for inp in inputs:
        if inp == clk:
            continue
        lines.append(f"set_input_delay 0.5 -clock {clk} [get_ports {{{inp}}}]")

    lines.append("")
    for out in outputs:
        lines.append(f"set_output_delay 0.5 -clock {clk} [get_ports {{{out}}}]")

    lines.append("")
    lines.append(f"set_max_area 0")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Bug categories: each returns (buggy_sdc, bug_name, difficulty, description)
# ---------------------------------------------------------------------------

def _bug_missing_clock(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Missing create_clock definition."""
    sdc = _correct_sdc(rtl, period_ns)
    # Remove the create_clock line
    lines = sdc.split("\n")
    buggy_lines = [l for l in lines if not l.startswith("create_clock")]
    return "\n".join(buggy_lines), "missing_clock", "easy", "Missing create_clock definition"


def _bug_wrong_period(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Wrong clock period (too tight or too loose)."""
    sdc = _correct_sdc(rtl, period_ns)
    # Replace period with 0.1ns (impossibly tight)
    buggy = sdc.replace(f"-period {period_ns}", "-period 0.1")
    return buggy, "wrong_period", "medium", "Clock period set to 0.1ns (impossibly tight)"


def _bug_wrong_port_name(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Wrong port name in constraint (typo)."""
    sdc = _correct_sdc(rtl, period_ns)
    # Change first non-clock port to a wrong name
    lines = sdc.split("\n")
    for i, line in enumerate(lines):
        if "get_ports" in line and "{clk}" not in line:
            lines[i] = line.replace("{rst_n}", "{reset_n}").replace("{en}", "{enable}").replace("{start}", "{go}")
            break
    return "\n".join(lines), "wrong_port_name", "easy", "Wrong port name in constraint (typo)"


def _bug_invalid_get_ports(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Invalid get_ports pattern (wildcard error)."""
    sdc = _correct_sdc(rtl, period_ns)
    # Replace a valid port reference with an invalid wildcard
    lines = sdc.split("\n")
    for i, line in enumerate(lines):
        if "set_input_delay" in line and "rst_n" in line:
            lines[i] = line.replace("[get_ports {rst_n}]", "[get_ports {nonexistent_*}]")
            break
    return "\n".join(lines), "invalid_get_ports", "medium", "Invalid get_ports pattern (nonexistent wildcard)"


def _bug_missing_input_delay(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Missing input delay on a data port."""
    sdc = _correct_sdc(rtl, period_ns)
    lines = sdc.split("\n")
    # Remove first set_input_delay line (not rst_n)
    for i, line in enumerate(lines):
        if "set_input_delay" in line and "rst_n" not in line:
            lines.pop(i)
            break
    return "\n".join(lines), "missing_input_delay", "medium", "Missing input delay on data port"


def _bug_missing_output_delay(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Missing output delay on output port."""
    sdc = _correct_sdc(rtl, period_ns)
    lines = sdc.split("\n")
    # Remove all set_output_delay lines
    buggy_lines = [l for l in lines if not l.startswith("set_output_delay")]
    return "\n".join(buggy_lines), "missing_output_delay", "medium", "Missing output delay on output port"


def _bug_wrong_top_module(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Wrong top module name in SDC (references nonexistent module)."""
    sdc = _correct_sdc(rtl, period_ns)
    # Change port references to use wrong module prefix
    buggy = sdc.replace("[get_ports {clk}]", "[get_ports {wrong_top/clk}]")
    return buggy, "wrong_top_module", "hard", "Wrong top module name in port references"


def _bug_syntax_error(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Syntax error in SDC (missing bracket)."""
    sdc = _correct_sdc(rtl, period_ns)
    lines = sdc.split("\n")
    for i, line in enumerate(lines):
        if "create_clock" in line:
            # Remove closing bracket
            lines[i] = line.replace("]", "")
            break
    return "\n".join(lines), "syntax_error", "easy", "Syntax error: missing closing bracket"


def _bug_unsupported_command(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Unsupported command in DC script."""
    sdc = _correct_sdc(rtl, period_ns)
    # Add an unsupported command
    lines = sdc.split("\n")
    lines.insert(1, "unsupported_command -arg value")
    return "\n".join(lines), "unsupported_command", "medium", "Unsupported command in SDC script"


def _bug_tight_constraint(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Overly tight constraint causing timing violation."""
    sdc = _correct_sdc(rtl, period_ns)
    # Set unreasonably tight input/output delays
    lines = sdc.split("\n")
    for i, line in enumerate(lines):
        if "set_input_delay" in line and "rst_n" not in line:
            lines[i] = line.replace("0.5", str(period_ns * 0.9))
        elif "set_output_delay" in line:
            lines[i] = line.replace("0.5", str(period_ns * 0.9))
    return "\n".join(lines), "tight_constraint", "hard", "Overly tight input/output delays"


# Registry of bug types
BUG_TYPES = [
    _bug_missing_clock,
    _bug_wrong_period,
    _bug_wrong_port_name,
    _bug_invalid_get_ports,
    _bug_missing_input_delay,
    _bug_missing_output_delay,
    _bug_wrong_top_module,
    _bug_syntax_error,
    _bug_unsupported_command,
    _bug_tight_constraint,
]

EXPECTED_BUG_TYPE_NAMES = [
    "missing_clock", "wrong_period", "wrong_port_name", "invalid_get_ports",
    "missing_input_delay", "missing_output_delay", "wrong_top_module",
    "syntax_error", "unsupported_command", "tight_constraint",
]

# DC run script template
RUN_PUBLIC_SH = """\
#!/bin/bash
# DC Constraint Debug — public run script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

DC_CMD="${EDA_DC_CMD:-dc_shell}"

# Check if dc_shell is available
if ! command -v "$DC_CMD" &>/dev/null; then
    echo "SKIP: dc_shell not found (EDA_DC_CMD=$DC_CMD)"
    echo "PUBLIC_RESULT: SKIP"
    exit 0
fi

# Run dc_shell and capture output
DC_OUTPUT=$("$DC_CMD" -f run_public.tcl 2>&1)
DC_EXIT=$?

echo "$DC_OUTPUT"

# Check for DC-level errors in output
DC_ERRORS=$(echo "$DC_OUTPUT" | grep -c "^Error:" || true)
DC_CRASH=$(echo "$DC_OUTPUT" | grep -cPi "\babort\b|segmentation fault|core dumped" || true)

if [ $DC_EXIT -ne 0 ] || [ "$DC_CRASH" -gt 0 ]; then
    echo "PUBLIC_RESULT: FAIL (exit=$DC_EXIT, fatal=$DC_CRASH)"
    exit 1
elif [ "$DC_ERRORS" -gt 0 ]; then
    echo "PUBLIC_RESULT: FAIL ($DC_ERRORS DC errors)"
    exit 1
else
    echo "PUBLIC_RESULT: PASS"
    exit 0
fi
"""

RUN_PUBLIC_TCL = """\
# DC Constraint Debug — public TCL script
# Set library
set target_library "lsi_10k.db"
set link_library "* $target_library gtech.db"

# Track errors
set error_count 0

# Read RTL
analyze -format verilog [list design.v]
elaborate {top}
link

# Read constraints
if {[catch {source -echo -verbose constraints.sdc} err]} {
    echo "ERROR: Failed to read constraints: $err"
    incr error_count
}

# Check design
check_design -summary

# Compile
if {[catch {compile_ultra -no_autoungroup} err]} {
    echo "ERROR: Compile failed: $err"
    incr error_count
}

# Report
report_timing -max_paths 5
report_area

if {$error_count > 0} {
    echo "PUBLIC_RESULT: FAIL ($error_count errors)"
    exit 1
} else {
    echo "PUBLIC_RESULT: PASS"
    exit 0
}
"""

RUN_HIDDEN_SH = """\
#!/bin/bash
# DC Constraint Debug — hidden run script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

DC_CMD="${EDA_DC_CMD:-dc_shell}"

# Check if dc_shell is available
if ! command -v "$DC_CMD" &>/dev/null; then
    echo "SKIP: dc_shell not found (EDA_DC_CMD=$DC_CMD)"
    echo "HIDDEN_RESULT: SKIP"
    exit 0
fi

# Run dc_shell and capture output
DC_OUTPUT=$("$DC_CMD" -f run_hidden.tcl 2>&1)
DC_EXIT=$?

echo "$DC_OUTPUT"

# Check for DC-level errors in output
DC_ERRORS=$(echo "$DC_OUTPUT" | grep -c "^Error:" || true)
DC_CRASH=$(echo "$DC_OUTPUT" | grep -cPi "\babort\b|segmentation fault|core dumped" || true)
DC_TIMING_FAIL=$(echo "$DC_OUTPUT" | grep -c "HIDDEN_RESULT: FAIL" || true)

if [ $DC_EXIT -ne 0 ] || [ "$DC_CRASH" -gt 0 ] || [ "$DC_TIMING_FAIL" -gt 0 ]; then
    echo "HIDDEN_RESULT: FAIL (exit=$DC_EXIT, fatal=$DC_CRASH)"
    exit 1
elif [ "$DC_ERRORS" -gt 0 ]; then
    echo "HIDDEN_RESULT: FAIL ($DC_ERRORS DC errors)"
    exit 1
else
    echo "HIDDEN_RESULT: PASS"
    exit 0
fi
"""

RUN_HIDDEN_TCL = """\
# DC Constraint Debug — hidden TCL script
# Set library
set target_library "lsi_10k.db"
set link_library "* $target_library gtech.db"

# Track errors
set error_count 0

# Read RTL
analyze -format verilog [list design.v]
elaborate {top}
link

# Read constraints
if {[catch {source -echo -verbose constraints.sdc} err]} {
    echo "ERROR: Failed to read constraints: $err"
    incr error_count
}

# Check design (strict)
check_design -summary

# Check timing
check_timing

# Compile
if {[catch {compile_ultra -no_autoungroup} err]} {
    echo "ERROR: Compile failed: $err"
    incr error_count
}

# Verify timing
report_timing -max_paths 10 -delay max
report_timing -max_paths 10 -delay min

# Check for violations
set timing_violations [get_timing_paths -max_paths 1 -slack_lesser_than 0]
if {[sizeof_collection $timing_violations] > 0} {
    echo "HIDDEN_RESULT: FAIL (timing violations found)"
    exit 1
}

if {$error_count > 0} {
    echo "HIDDEN_RESULT: FAIL ($error_count errors)"
    exit 1
} else {
    echo "HIDDEN_RESULT: PASS"
    exit 0
}
"""


class P6DCConstraintDebugGenerator(BaseGenerator):
    """Generates P6 DC Constraint Debug tasks with deterministic seeds."""

    def generate_one(self, task_index: int) -> Path:
        # Round-robin across bug types and RTL templates
        bug_fn = BUG_TYPES[task_index % len(BUG_TYPES)]
        rtl = RTL_TEMPLATES[(task_index // len(BUG_TYPES)) % len(RTL_TEMPLATES)]
        period_ns = self.rng.choice([2.0, 3.0, 5.0, 10.0])

        buggy_sdc, bug_name, difficulty, description = bug_fn(rtl, period_ns)
        correct_sdc = _correct_sdc(rtl, period_ns)

        task_id = f"dc_constraint_{task_index:04d}"
        task_dir = self.output_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (task_dir / "files").mkdir(exist_ok=True)
        (task_dir / "hidden").mkdir(exist_ok=True)
        (task_dir / "solution").mkdir(exist_ok=True)

        # Write RTL
        (task_dir / "files" / "design.v").write_text(rtl["rtl"])

        # Write buggy SDC (editable)
        (task_dir / "files" / "constraints.sdc").write_text(buggy_sdc)

        # Write correct SDC (solution)
        (task_dir / "solution" / "constraints.sdc").write_text(correct_sdc)

        # Write run scripts
        run_pub_sh = RUN_PUBLIC_SH
        run_pub_tcl = RUN_PUBLIC_TCL.replace("{top}", rtl["top"])
        run_hid_sh = RUN_HIDDEN_SH
        run_hid_tcl = RUN_HIDDEN_TCL.replace("{top}", rtl["top"])

        (task_dir / "files" / "run_public.sh").write_text(run_pub_sh)
        (task_dir / "files" / "run_public.tcl").write_text(run_pub_tcl)
        (task_dir / "hidden" / "run_hidden.sh").write_text(run_hid_sh)
        (task_dir / "hidden" / "run_hidden.tcl").write_text(run_hid_tcl)

        # Make scripts executable
        (task_dir / "files" / "run_public.sh").chmod(0o755)
        (task_dir / "hidden" / "run_hidden.sh").chmod(0o755)

        # Write prompt
        prompt = f"""\
# DC Constraint Debug Task: {bug_name.replace('_', ' ').title()}

## Description

The design `{rtl['name']}` has a constraint file (`constraints.sdc`) with a bug.
Fix the constraint file so that Design Compiler synthesis completes successfully.

## Bug Category

{description}

## Files

- `design.v` — RTL design (do not modify)
- `constraints.sdc` — constraint file (you may edit this file)
- `run_public.sh` — public test runner (do not modify)
- `run_public.tcl` — DC TCL script (do not modify)

## Constraints

- Only modify `constraints.sdc`
- Do not modify any other files
- The design has clock `{rtl['clk']}` with period {period_ns}ns

## Hint

Check the SDC file for: missing clock definitions, wrong port names,
syntax errors, or incorrect timing constraints.
"""
        (task_dir / "prompt.md").write_text(prompt)

        # Write metadata
        meta = {
            "task_id": task_id,
            "track": "p6_dc_constraint_debug",
            "tool": ["dc"],
            "difficulty": difficulty,
            "data_type": "template_synthetic",
            "resource_preset": "standard",
            "timeout_sec": 300,
            "max_tool_calls": 30,
            "max_patch_attempts": 8,
            "max_output_tokens": 32000,
            "files": {
                "visible": ["design.v", "constraints.sdc", "run_public.sh", "run_public.tcl"],
                "editable": ["constraints.sdc"],
                "hidden": ["run_hidden.sh", "run_hidden.tcl"],
                "forbidden": ["design.v", "run_public.sh", "run_public.tcl",
                              "run_hidden.sh", "run_hidden.tcl"],
            },
            "run_command": "bash run_public.sh && bash run_hidden.sh",
            "scoring": {
                "weights": {
                    "execution_pass": 0.4,
                    "check_pass": 0.3,
                    "synthesis_pass": 0.2,
                    "explanation": 0.1,
                },
                "evaluator": "dc_constraint_debug.DCConstraintDebugEvaluator",
                "explanation_weight": 0.1,
            },
            "sanitizer": {"enabled": True},
            "generator": {
                "script": "p6_dc_constraint_debug_gen.py",
                "seed": self.seed,
                "bug_type": bug_name,
                "rtl_template": rtl["name"],
                "period_ns": period_ns,
                "task_index": task_index,
            },
            "expected_error_category": bug_name,
            "version": "1.0.0",
        }
        (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")

        return task_dir
