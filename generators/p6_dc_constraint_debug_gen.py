"""P6 DC Constraint Debug task generator — 6 reliable bug categories, deterministic seed.

Only categories that produce detectable failures under DC are included.
Removed categories (unreliable — DC accepts them silently):
  - wrong_period (DC accepts any period value)
  - missing_input_delay (DC accepts missing delays)
  - missing_output_delay (DC accepts missing delays)
  - tight_constraint (DC accepts overly tight constraints)
"""

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

_RTL_SHIFT = """\
module shift_reg (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       din,
    output reg  [7:0] dout
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            dout <= 8'd0;
        else
            dout <= {dout[6:0], din};
    end
endmodule
"""

_RTL_CMP = """\
module comparator_reg (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] a,
    input  wire [7:0] b,
    output reg        gt,
    output reg        eq
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            gt <= 1'b0;
            eq <= 1'b0;
        end else begin
            gt <= (a > b);
            eq <= (a == b);
        end
    end
endmodule
"""

_RTL_DECODER = """\
module decoder_reg (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [1:0] sel,
    output reg  [3:0] onehot
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            onehot <= 4'd0;
        else
            onehot <= (4'd1 << sel);
    end
endmodule
"""

_RTL_ALU = """\
module alu_reg (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [1:0] op,
    input  wire [7:0] a,
    input  wire [7:0] b,
    output reg  [7:0] result
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            result <= 8'd0;
        else begin
            case (op)
                2'd0: result <= a + b;
                2'd1: result <= a - b;
                2'd2: result <= a & b;
                2'd3: result <= a | b;
            endcase
        end
    end
endmodule
"""

_RTL_ACC = """\
module accumulator (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        en,
    input  wire [7:0]  data,
    output reg  [15:0] acc
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            acc <= 16'd0;
        else if (en)
            acc <= acc + {8'd0, data};
    end
endmodule
"""

_RTL_UPDOWN = """\
module updown_counter (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       up,
    output reg  [7:0] cnt
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            cnt <= 8'd0;
        else if (up)
            cnt <= cnt + 8'd1;
        else
            cnt <= cnt - 8'd1;
    end
endmodule
"""

RTL_TEMPLATES = [
    {"name": "counter", "rtl": _RTL_COUNTER, "top": "counter",
     "clk": "clk", "inputs": ["clk", "rst_n", "en"], "outputs": ["count"]},
    {"name": "fsm_ctrl", "rtl": _RTL_FSM, "top": "fsm_ctrl",
     "clk": "clk", "inputs": ["clk", "rst_n", "start"], "outputs": ["busy", "done"]},
    {"name": "adder_pipe", "rtl": _RTL_ADDER, "top": "adder_pipe",
     "clk": "clk", "inputs": ["clk", "rst_n", "a", "b"], "outputs": ["sum"]},
    {"name": "mux_reg", "rtl": _RTL_MUX, "top": "mux_reg",
     "clk": "clk", "inputs": ["clk", "rst_n", "sel", "d0", "d1", "d2", "d3"], "outputs": ["q"]},
    {"name": "shift_reg", "rtl": _RTL_SHIFT, "top": "shift_reg",
     "clk": "clk", "inputs": ["clk", "rst_n", "din"], "outputs": ["dout"]},
    {"name": "comparator_reg", "rtl": _RTL_CMP, "top": "comparator_reg",
     "clk": "clk", "inputs": ["clk", "rst_n", "a", "b"], "outputs": ["gt", "eq"]},
    {"name": "decoder_reg", "rtl": _RTL_DECODER, "top": "decoder_reg",
     "clk": "clk", "inputs": ["clk", "rst_n", "sel"], "outputs": ["onehot"]},
    {"name": "alu_reg", "rtl": _RTL_ALU, "top": "alu_reg",
     "clk": "clk", "inputs": ["clk", "rst_n", "op", "a", "b"], "outputs": ["result"]},
    {"name": "accumulator", "rtl": _RTL_ACC, "top": "accumulator",
     "clk": "clk", "inputs": ["clk", "rst_n", "en", "data"], "outputs": ["acc"]},
    {"name": "updown_counter", "rtl": _RTL_UPDOWN, "top": "updown_counter",
     "clk": "clk", "inputs": ["clk", "rst_n", "up"], "outputs": ["cnt"]},
]


# ---------------------------------------------------------------------------
# Correct SDC templates
# ---------------------------------------------------------------------------

def _correct_sdc(rtl: dict, period_ns: float) -> str:
    """Generate correct SDC for the given RTL template."""
    top = rtl["top"]
    clk = rtl["clk"]
    inputs = [p for p in rtl["inputs"] if p != clk]
    outputs = rtl["outputs"]

    lines = [
        f"# SDC constraints for {top}",
        f"create_clock -name {clk} -period {period_ns} [get_ports {{{clk}}}]",
        f"set_clock_uncertainty 0.1 [get_clocks {{{clk}}}]",
        "",
    ]

    for inp in inputs:
        lines.append(f"set_input_delay 0.5 -clock {clk} [get_ports {{{inp}}}]")

    lines.append("")
    for out in outputs:
        lines.append(f"set_output_delay 0.5 -clock {clk} [get_ports {{{out}}}]")

    lines.append("")
    lines.append("set_max_area 0")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Bug categories: each returns (buggy_sdc, bug_name, difficulty, description)
# Only categories that produce detectable failures under DC.
# ---------------------------------------------------------------------------

def _bug_missing_clock(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Missing create_clock definition."""
    sdc = _correct_sdc(rtl, period_ns)
    lines = sdc.split("\n")
    buggy_lines = [l for l in lines if not l.startswith("create_clock")]
    return "\n".join(buggy_lines), "missing_clock", "easy", \
        "Missing create_clock definition — DC reports 'Can't find clock'"


def _first_nonclk_port(rtl: dict) -> str | None:
    """First non-clock port (prefer inputs, then outputs) — used to inject port bugs.

    Keeps the port-name bugs template-agnostic so any RTL template works.
    """
    clk = rtl["clk"]
    cands = [p for p in rtl["inputs"] if p != clk] + list(rtl["outputs"])
    return cands[0] if cands else None


def _bug_wrong_port_name(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Wrong port name in constraint (typo) — template-agnostic."""
    sdc = _correct_sdc(rtl, period_ns)
    port = _first_nonclk_port(rtl)
    if port is not None:
        sdc = sdc.replace(f"[get_ports {{{port}}}]", f"[get_ports {{{port}_typo}}]", 1)
    return sdc, "wrong_port_name", "easy", \
        "Wrong port name in constraint — DC reports 'Can't find port'"


def _bug_invalid_get_ports(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Invalid get_ports pattern (wildcard matches nothing) — template-agnostic."""
    sdc = _correct_sdc(rtl, period_ns)
    port = _first_nonclk_port(rtl)
    if port is not None:
        sdc = sdc.replace(f"[get_ports {{{port}}}]", "[get_ports {nonexistent_*}]", 1)
    return sdc, "invalid_get_ports", "medium", \
        "Invalid get_ports pattern — DC reports 'Can't find ports matching'"


def _bug_wrong_top_module(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Wrong top module name in SDC (references nonexistent module)."""
    sdc = _correct_sdc(rtl, period_ns)
    buggy = sdc.replace("[get_ports {clk}]", "[get_ports {wrong_top/clk}]")
    return buggy, "wrong_top_module", "hard", \
        "Wrong top module name in port references — DC reports 'Can't find port'"


def _bug_syntax_error(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Syntax error in SDC (missing bracket)."""
    sdc = _correct_sdc(rtl, period_ns)
    lines = sdc.split("\n")
    for i, line in enumerate(lines):
        if "create_clock" in line:
            lines[i] = line.replace("]", "")
            break
    return "\n".join(lines), "syntax_error", "easy", \
        "Syntax error: missing closing bracket — DC exits nonzero"


def _bug_unsupported_command(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Unsupported command in DC script."""
    sdc = _correct_sdc(rtl, period_ns)
    lines = sdc.split("\n")
    lines.insert(1, "unsupported_command -arg value")
    return "\n".join(lines), "unsupported_command", "medium", \
        "Unsupported command in SDC script — DC reports 'unknown command'"


# Registry of reliable bug types
BUG_TYPES = [
    _bug_missing_clock,
    _bug_wrong_port_name,
    _bug_invalid_get_ports,
    _bug_wrong_top_module,
    _bug_syntax_error,
    _bug_unsupported_command,
]

EXPECTED_BUG_TYPE_NAMES = [
    "missing_clock", "wrong_port_name", "invalid_get_ports",
    "wrong_top_module", "syntax_error", "unsupported_command",
]


def _make_tcl(rtl: dict, section: str) -> str:
    """Generate TCL script with explicit constraint validation."""
    top = rtl["top"]
    clk = rtl["clk"]
    inputs = [p for p in rtl["inputs"] if p != clk]
    outputs = rtl["outputs"]
    all_ports = [clk] + inputs + outputs

    if section == "public":
        report_cmds = "report_timing -max_paths 5\nreport_area"
    else:
        report_cmds = (
            "report_timing -max_paths 10 -delay max\n"
            "report_timing -max_paths 10 -delay min"
        )

    return f"""\
# DC Constraint Debug — {section} TCL script
# Set library
set target_library "lsi_10k.db"
set link_library "* $target_library gtech.db"

# Track errors
set error_count 0
set fail_reasons {{}}

# Read RTL
analyze -format verilog [list design.v]
elaborate {top}
link

# Read constraints and capture output for error checking
set source_log "source_output.log"
redirect -file $source_log {{ source -echo -verbose constraints.sdc }}

# --- Constraint validation checks ---

# Check source output for DC errors
set fh [open $source_log r]
set source_content [read $fh]
close $fh

if {{[regexp {{Error:}} $source_content]}} {{
    incr error_count
    lappend fail_reasons "dc_error_in_source"
}}

if {{[regexp {{Can't find}} $source_content]}} {{
    incr error_count
    lappend fail_reasons "port_or_clock_not_found"
}}

if {{[regexp -nocase {{unknown command}} $source_content]}} {{
    incr error_count
    lappend fail_reasons "unsupported_command"
}}

# Check 1: Clocks must exist
set all_clks [all_clocks]
if {{[sizeof_collection $all_clks] == 0}} {{
    incr error_count
    lappend fail_reasons "no_clocks_created"
}}

# Check 2: All ports must resolve
foreach port {{{" ".join(all_ports)}}} {{
    if {{[catch {{get_ports $port}} result]}} {{
        incr error_count
        lappend fail_reasons "port_not_found:$port"
    }}
}}

# Compile
if {{[catch {{compile_ultra -no_autoungroup}} result]}} {{
    incr error_count
    lappend fail_reasons "compile_failed"
}}

# Report
{report_cmds}

# Emit result
if {{$error_count > 0}} {{
    set reason_str [join $fail_reasons ","]
    echo "CONSTRAINTS_FAIL: $reason_str"
    exit 1
}} else {{
    echo "CONSTRAINTS_OK"
    exit 0
}}
"""


def _make_sh(section: str) -> str:
    """Generate bash run script."""
    return f"""\
#!/bin/bash
# DC Constraint Debug — {section} run script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

DC_CMD="${{EDA_DC_CMD:-dc_shell}}"

# Check if dc_shell is available
if ! command -v "$DC_CMD" &>/dev/null; then
    echo "SKIP: dc_shell not found (EDA_DC_CMD=$DC_CMD)"
    exit 0
fi

# Run dc_shell and capture both stdout and stderr
DC_OUTPUT=$("$DC_CMD" -f run_{section}.tcl 2>&1)
DC_EXIT=$?

echo "$DC_OUTPUT"

exit $DC_EXIT
"""


class P6DCConstraintDebugGenerator(BaseGenerator):
    """Generates P6 DC Constraint Debug tasks with deterministic seeds."""

    def generate_one(self, task_index: int) -> Path:
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
        (task_dir / "files" / "run_public.sh").write_text(_make_sh("public"))
        (task_dir / "files" / "run_public.tcl").write_text(_make_tcl(rtl, "public"))
        (task_dir / "hidden" / "run_hidden.sh").write_text(_make_sh("hidden"))
        (task_dir / "hidden" / "run_hidden.tcl").write_text(_make_tcl(rtl, "hidden"))

        # Make scripts executable
        (task_dir / "files" / "run_public.sh").chmod(0o755)
        (task_dir / "hidden" / "run_hidden.sh").chmod(0o755)

        # Build port list string for prompt
        port_list = ", ".join(rtl["inputs"] + rtl["outputs"])

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
- Design ports: {port_list}

## Hint

The run script checks that:
1. At least one clock is created
2. All design ports resolve correctly
3. compile_ultra succeeds

Check the SDC file for: missing clock definitions, wrong port names,
syntax errors, or invalid port references.
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
                    "constraint_pass": 0.6,
                    "execution_pass": 0.3,
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
            "version": "2.0.0",
        }
        (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")

        return task_dir
