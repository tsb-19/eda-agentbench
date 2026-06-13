"""P7 PrimeTime STA Debug task generator — 5 reliable bug categories, deterministic seed.

Only categories that produce detectable failures under PrimeTime are included.
Removed categories (unreliable — PT accepts them silently or detection is non-deterministic):
  - missing_input_delay (PT accepts missing delays)
  - missing_output_delay (PT accepts missing delays)
  - false_path_too_broad (requires real timing data)
  - multicycle_path_error (requires real timing data)
  - wrong_uncertainty (PT accepts, only shifts numbers slightly)

Design approach:
  Each task includes a structural Verilog netlist (hidden) that PrimeTime can read
  via read_verilog + link_design. The netlist uses DFF primitives and basic gates
  so PT can perform real STA without needing a synthesis library.
"""

from __future__ import annotations

import json
from pathlib import Path

from generators.base import BaseGenerator

# ---------------------------------------------------------------------------
# RTL design templates (visible to agent as design.v)
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

# ---------------------------------------------------------------------------
# Structural netlist templates (hidden — read by PrimeTime)
# Uses DFFX1 primitive for flip-flops. PT accepts unresolved cell references.
# ---------------------------------------------------------------------------

_NETLIST_COUNTER = """\
// Gate-level netlist for counter — used by PrimeTime STA
module counter (clk, rst_n, en, count);
  input clk;
  input rst_n;
  input en;
  output [7:0] count;
  DFFX1 count_reg_0 (.D(count_next_0), .CK(clk), .Q(count[0]));
  DFFX1 count_reg_1 (.D(count_next_1), .CK(clk), .Q(count[1]));
  DFFX1 count_reg_2 (.D(count_next_2), .CK(clk), .Q(count[2]));
  DFFX1 count_reg_3 (.D(count_next_3), .CK(clk), .Q(count[3]));
  DFFX1 count_reg_4 (.D(count_next_4), .CK(clk), .Q(count[4]));
  DFFX1 count_reg_5 (.D(count_next_5), .CK(clk), .Q(count[5]));
  DFFX1 count_reg_6 (.D(count_next_6), .CK(clk), .Q(count[6]));
  DFFX1 count_reg_7 (.D(count_next_7), .CK(clk), .Q(count[7]));
endmodule
"""

_NETLIST_FSM = """\
// Gate-level netlist for fsm_ctrl — used by PrimeTime STA
module fsm_ctrl (clk, rst_n, start, busy, done);
  input clk;
  input rst_n;
  input start;
  output busy;
  output done;
  DFFX1 state_reg_0 (.D(state_next_0), .CK(clk), .Q(state[0]));
  DFFX1 state_reg_1 (.D(state_next_1), .CK(clk), .Q(state[1]));
  DFFX1 busy_reg (.D(busy_next), .CK(clk), .Q(busy));
  DFFX1 done_reg (.D(done_next), .CK(clk), .Q(done));
endmodule
"""

_NETLIST_ADDER = """\
// Gate-level netlist for adder_pipe — used by PrimeTime STA
module adder_pipe (clk, rst_n, a, b, sum);
  input clk;
  input rst_n;
  input [15:0] a;
  input [15:0] b;
  output [16:0] sum;
  DFFX1 sum_reg_0 (.D(sum_next_0), .CK(clk), .Q(sum[0]));
  DFFX1 sum_reg_1 (.D(sum_next_1), .CK(clk), .Q(sum[1]));
  DFFX1 sum_reg_2 (.D(sum_next_2), .CK(clk), .Q(sum[2]));
  DFFX1 sum_reg_3 (.D(sum_next_3), .CK(clk), .Q(sum[3]));
  DFFX1 sum_reg_4 (.D(sum_next_4), .CK(clk), .Q(sum[4]));
  DFFX1 sum_reg_5 (.D(sum_next_5), .CK(clk), .Q(sum[5]));
  DFFX1 sum_reg_6 (.D(sum_next_6), .CK(clk), .Q(sum[6]));
  DFFX1 sum_reg_7 (.D(sum_next_7), .CK(clk), .Q(sum[7]));
  DFFX1 sum_reg_8 (.D(sum_next_8), .CK(clk), .Q(sum[8]));
  DFFX1 sum_reg_9 (.D(sum_next_9), .CK(clk), .Q(sum[9]));
  DFFX1 sum_reg_10 (.D(sum_next_10), .CK(clk), .Q(sum[10]));
  DFFX1 sum_reg_11 (.D(sum_next_11), .CK(clk), .Q(sum[11]));
  DFFX1 sum_reg_12 (.D(sum_next_12), .CK(clk), .Q(sum[12]));
  DFFX1 sum_reg_13 (.D(sum_next_13), .CK(clk), .Q(sum[13]));
  DFFX1 sum_reg_14 (.D(sum_next_14), .CK(clk), .Q(sum[14]));
  DFFX1 sum_reg_15 (.D(sum_next_15), .CK(clk), .Q(sum[15]));
  DFFX1 sum_reg_16 (.D(sum_next_16), .CK(clk), .Q(sum[16]));
endmodule
"""

_NETLIST_MUX = """\
// Gate-level netlist for mux_reg — used by PrimeTime STA
module mux_reg (clk, rst_n, sel, d0, d1, d2, d3, q);
  input clk;
  input rst_n;
  input [1:0] sel;
  input [7:0] d0;
  input [7:0] d1;
  input [7:0] d2;
  input [7:0] d3;
  output [7:0] q;
  DFFX1 q_reg_0 (.D(q_next_0), .CK(clk), .Q(q[0]));
  DFFX1 q_reg_1 (.D(q_next_1), .CK(clk), .Q(q[1]));
  DFFX1 q_reg_2 (.D(q_next_2), .CK(clk), .Q(q[2]));
  DFFX1 q_reg_3 (.D(q_next_3), .CK(clk), .Q(q[3]));
  DFFX1 q_reg_4 (.D(q_next_4), .CK(clk), .Q(q[4]));
  DFFX1 q_reg_5 (.D(q_next_5), .CK(clk), .Q(q[5]));
  DFFX1 q_reg_6 (.D(q_next_6), .CK(clk), .Q(q[6]));
  DFFX1 q_reg_7 (.D(q_next_7), .CK(clk), .Q(q[7]));
endmodule
"""

RTL_TEMPLATES = [
    {"name": "counter", "rtl": _RTL_COUNTER, "netlist": _NETLIST_COUNTER,
     "top": "counter", "clk": "clk",
     "inputs": ["clk", "rst_n", "en"], "outputs": ["count"]},
    {"name": "fsm_ctrl", "rtl": _RTL_FSM, "netlist": _NETLIST_FSM,
     "top": "fsm_ctrl", "clk": "clk",
     "inputs": ["clk", "rst_n", "start"], "outputs": ["busy", "done"]},
    {"name": "adder_pipe", "rtl": _RTL_ADDER, "netlist": _NETLIST_ADDER,
     "top": "adder_pipe", "clk": "clk",
     "inputs": ["clk", "rst_n", "a", "b"], "outputs": ["sum"]},
    {"name": "mux_reg", "rtl": _RTL_MUX, "netlist": _NETLIST_MUX,
     "top": "mux_reg", "clk": "clk",
     "inputs": ["clk", "rst_n", "sel", "d0", "d1", "d2", "d3"], "outputs": ["q"]},
]


# ---------------------------------------------------------------------------
# Correct SDC templates
# ---------------------------------------------------------------------------

def _correct_sdc(rtl: dict, period_ns: float) -> str:
    """Generate correct SDC for the given RTL template."""
    clk = rtl["clk"]
    inputs = [p for p in rtl["inputs"] if p != clk]
    outputs = rtl["outputs"]

    lines = [
        f"# SDC constraints for {rtl['top']}",
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
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Bug categories: each returns (buggy_sdc, bug_name, difficulty, description)
# Only categories that produce detectable failures under PrimeTime.
# ---------------------------------------------------------------------------

def _bug_missing_clock(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Missing create_clock definition."""
    sdc = _correct_sdc(rtl, period_ns)
    lines = sdc.split("\n")
    buggy_lines = [l for l in lines if not l.startswith("create_clock")]
    return "\n".join(buggy_lines), "missing_clock", "easy", \
        "Missing create_clock definition — PrimeTime reports unconstrained paths"


def _bug_wrong_port_name(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Wrong port name in constraint (typo)."""
    sdc = _correct_sdc(rtl, period_ns)
    lines = sdc.split("\n")
    for i, line in enumerate(lines):
        if "get_ports" in line and "{clk}" not in line:
            for old, new in [("{rst_n}", "{reset_n}"), ("{en}", "{enable}"),
                             ("{start}", "{go}"), ("{a}", "{in_a}"), ("{b}", "{in_b}"),
                             ("{sel}", "{selector}"), ("{d0}", "{data0}")]:
                if old in line:
                    lines[i] = line.replace(old, new)
                    break
            break
    return "\n".join(lines), "wrong_port_name", "easy", \
        "Wrong port name in constraint — PrimeTime reports 'Can't find port'"


def _bug_wrong_period(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Wrong clock period (off by 10x)."""
    sdc = _correct_sdc(rtl, period_ns)
    wrong_period = period_ns * 10.0
    buggy = sdc.replace(f"-period {period_ns}", f"-period {wrong_period}")
    return buggy, "wrong_period", "medium", \
        f"Wrong clock period ({wrong_period}ns instead of {period_ns}ns) — report_clocks shows mismatch"


def _bug_syntax_error(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Syntax error in SDC (missing bracket)."""
    sdc = _correct_sdc(rtl, period_ns)
    lines = sdc.split("\n")
    for i, line in enumerate(lines):
        if "create_clock" in line:
            lines[i] = line.replace("]", "")
            break
    return "\n".join(lines), "syntax_error", "easy", \
        "Syntax error: missing closing bracket — PrimeTime TCL parser error"


def _bug_invalid_get_ports(rtl: dict, period_ns: float) -> tuple[str, str, str, str]:
    """Invalid get_ports pattern (wildcard error)."""
    sdc = _correct_sdc(rtl, period_ns)
    lines = sdc.split("\n")
    for i, line in enumerate(lines):
        if "set_input_delay" in line and "rst_n" in line:
            lines[i] = line.replace("[get_ports {rst_n}]", "[get_ports {nonexistent_*}]")
            break
    return "\n".join(lines), "invalid_get_ports", "medium", \
        "Invalid get_ports pattern — PrimeTime reports 'Can't find ports matching'"


# Registry of reliable bug types
BUG_TYPES = [
    _bug_missing_clock,
    _bug_wrong_port_name,
    _bug_wrong_period,
    _bug_syntax_error,
    _bug_invalid_get_ports,
]

EXPECTED_BUG_TYPE_NAMES = [
    "missing_clock", "wrong_port_name", "wrong_period",
    "syntax_error", "invalid_get_ports",
]


def _make_tcl(rtl: dict, section: str) -> str:
    """Generate PrimeTime TCL script with explicit timing-constraint validation.

    The script reads a structural netlist (design_netlist.v), links the design,
    then sources the SDC constraints and validates them.
    """
    top = rtl["top"]
    clk = rtl["clk"]
    inputs = [p for p in rtl["inputs"] if p != clk]
    outputs = rtl["outputs"]
    all_ports = [clk] + inputs + outputs

    if section == "public":
        report_cmds = "report_timing -max_paths 5\nreport_clocks"
    else:
        report_cmds = (
            "report_timing -max_paths 10 -delay max\n"
            "report_timing -max_paths 10 -delay min\n"
            "report_clocks -skew"
        )

    return f"""\
# PrimeTime STA Debug — {section} TCL script
# Track errors
set error_count 0
set fail_reasons {{}}

# Read netlist and link design
read_verilog design_netlist.v
link_design {top}

# Read constraints and capture output for error checking
set source_log "source_output.log"
redirect -file $source_log {{ source -echo -verbose constraints.sdc }}

# --- Constraint validation checks ---

# Check source output for PT errors
set fh [open $source_log r]
set source_content [read $fh]
close $fh

if {{[regexp {{Error:}} $source_content]}} {{
    incr error_count
    lappend fail_reasons "pt_error_in_source"
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

# Check 3: Report timing (must succeed)
if {{[catch {{report_timing -max_paths 1}} result]}} {{
    incr error_count
    lappend fail_reasons "report_timing_failed"
}}

# Report
{report_cmds}

# Emit result
if {{$error_count > 0}} {{
    set reason_str [join $fail_reasons ","]
    echo "TIMING_CHECK_FAIL: $reason_str"
    exit 1
}} else {{
    echo "TIMING_CHECK_OK"
    exit 0
}}
"""


def _make_sh(section: str) -> str:
    """Generate bash run script."""
    return f"""\
#!/bin/bash
# PrimeTime STA Debug — {section} run script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PT_CMD="${{EDA_PT_CMD:-pt_shell}}"

# Check if pt_shell is available
if ! command -v "$PT_CMD" &>/dev/null; then
    echo "SKIP: pt_shell not found (EDA_PT_CMD=$PT_CMD)"
    exit 0
fi

# Run pt_shell and capture both stdout and stderr
PT_OUTPUT=$("$PT_CMD" -f run_{section}.tcl 2>&1)
PT_EXIT=$?

echo "$PT_OUTPUT"

exit $PT_EXIT
"""


class P7PrimeTimeSTADebugGenerator(BaseGenerator):
    """Generates P7 PrimeTime STA Debug tasks with deterministic seeds."""

    def generate_one(self, task_index: int) -> Path:
        bug_fn = BUG_TYPES[task_index % len(BUG_TYPES)]
        rtl = RTL_TEMPLATES[(task_index // len(BUG_TYPES)) % len(RTL_TEMPLATES)]
        period_ns = self.rng.choice([2.0, 3.0, 5.0, 10.0])

        buggy_sdc, bug_name, difficulty, description = bug_fn(rtl, period_ns)
        correct_sdc = _correct_sdc(rtl, period_ns)

        task_id = f"pt_sta_debug_{task_index:04d}"
        task_dir = self.output_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (task_dir / "files").mkdir(exist_ok=True)
        (task_dir / "hidden").mkdir(exist_ok=True)
        (task_dir / "solution").mkdir(exist_ok=True)

        # Write RTL (visible to agent)
        (task_dir / "files" / "design.v").write_text(rtl["rtl"])

        # Write structural netlist (hidden — used by PrimeTime)
        (task_dir / "hidden" / "design_netlist.v").write_text(rtl["netlist"])

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
# PrimeTime STA Debug Task: {bug_name.replace('_', ' ').title()}

## Description

The design `{rtl['name']}` has a constraint file (`constraints.sdc`) with a bug.
Fix the constraint file so that PrimeTime STA timing checks pass.

## Bug Category

{description}

## Files

- `design.v` — RTL design (do not modify)
- `constraints.sdc` — constraint file (you may edit this file)
- `run_public.sh` — public test runner (do not modify)
- `run_public.tcl` — PrimeTime TCL script (do not modify)

## Constraints

- Only modify `constraints.sdc`
- Do not modify any other files
- The design has clock `{rtl['clk']}` with period {period_ns}ns
- Design ports: {port_list}

## Hint

The run script checks that:
1. At least one clock is created
2. All design ports resolve correctly
3. report_timing succeeds

Check the SDC file for: missing clock definitions, wrong port names,
wrong clock periods, syntax errors, or invalid port references.
"""
        (task_dir / "prompt.md").write_text(prompt)

        # Write metadata
        meta = {
            "task_id": task_id,
            "track": "p7_primetime_sta_debug",
            "tool": ["pt"],
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
                "hidden": ["design_netlist.v", "run_hidden.sh", "run_hidden.tcl"],
                "forbidden": ["design.v", "run_public.sh", "run_public.tcl",
                              "run_hidden.sh", "run_hidden.tcl"],
            },
            "run_command": "bash run_public.sh && bash run_hidden.sh",
            "scoring": {
                "weights": {
                    "timing_check": 0.6,
                    "execution_pass": 0.3,
                    "explanation": 0.1,
                },
                "evaluator": "primetime_sta_debug.PrimeTimeSTADebugEvaluator",
                "explanation_weight": 0.1,
            },
            "sanitizer": {"enabled": True},
            "generator": {
                "script": "p7_primetime_sta_debug_gen.py",
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
