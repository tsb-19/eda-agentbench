"""P2 Testbench/SVA Generation task generator — 5 design templates, mutation-based grading."""

from __future__ import annotations

import json
from pathlib import Path

from generators.base import BaseGenerator

# ---------------------------------------------------------------------------
# Design templates
# Each returns: {name, difficulty, module_name, golden, mutants, solution_tb,
#                ports, description, mutant_description}
# mutants is a list of {name, code, bug_description}
# ---------------------------------------------------------------------------

def _template_mux2():
    return {
        "name": "mux2",
        "difficulty": "easy",
        "module_name": "mux2",
        "golden": """\
module mux2 (
    input  wire a, b, sel,
    output wire y
);
    assign y = sel ? a : b;
endmodule
""",
        "mutants": [
            {
                "name": "select_swapped",
                "code": """\
module mux2 (
    input  wire a, b, sel,
    output wire y
);
    assign y = sel ? b : a;
endmodule
""",
                "bug_description": "select lines swapped: sel=1 gives b instead of a",
            },
            {
                "name": "stuck_at_zero",
                "code": """\
module mux2 (
    input  wire a, b, sel,
    output wire y
);
    assign y = 1'b0;
endmodule
""",
                "bug_description": "output stuck at 0",
            },
        ],
        "solution_tb": """\
module tb;
    reg a, b, sel;
    wire y;
    mux2 uut (.a(a), .b(b), .sel(sel), .y(y));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        a=0; b=1; sel=0; #10;
        if (y===1'b1) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: sel=0 expected y=1, got %b", y); end
        a=1; b=0; sel=1; #10;
        if (y===1'b1) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: sel=1 expected y=1, got %b", y); end
        a=0; b=0; sel=0; #10;
        if (y===1'b0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: both 0 expected y=0, got %b", y); end
        a=1; b=1; sel=1; #10;
        if (y===1'b1) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: both 1 expected y=1, got %b", y); end
        a=1; b=0; sel=0; #10;
        if (y===1'b0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: sel=0 expected y=b=0, got %b", y); end
        a=0; b=1; sel=1; #10;
        if (y===1'b0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: sel=1 expected y=a=0, got %b", y); end
        if (fail === 0) $display("ALL_TESTS_PASS: %0d/%0d", pass, pass+fail);
        else $display("TEST_FAIL: %0d/%0d", pass, pass+fail);
        $finish;
    end
endmodule
""",
        "ports": "input a, b, sel; output y",
        "description": "2-to-1 multiplexer: y = sel ? a : b",
        "mutant_description": "select logic or output stuck-at",
    }


def _template_counter():
    return {
        "name": "counter",
        "difficulty": "easy",
        "module_name": "counter4",
        "golden": """\
module counter4 (
    input  wire       clk, rst_n,
    input  wire       en,
    output reg  [3:0] cnt
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) cnt <= 4'd0;
        else if (en) cnt <= cnt + 1;
    end
endmodule
""",
        "mutants": [
            {
                "name": "enable_inverted",
                "code": """\
module counter4 (
    input  wire       clk, rst_n,
    input  wire       en,
    output reg  [3:0] cnt
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) cnt <= 4'd0;
        else if (!en) cnt <= cnt + 1;
    end
endmodule
""",
                "bug_description": "enable polarity inverted: counts when en=0",
            },
            {
                "name": "off_by_one",
                "code": """\
module counter4 (
    input  wire       clk, rst_n,
    input  wire       en,
    output reg  [3:0] cnt
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) cnt <= 4'd0;
        else if (en) cnt <= cnt + 2;
    end
endmodule
""",
                "bug_description": "increments by 2 instead of 1",
            },
        ],
        "solution_tb": """\
module tb;
    reg clk, rst_n, en;
    wire [3:0] cnt;
    counter4 uut (.clk(clk), .rst_n(rst_n), .en(en), .cnt(cnt));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        clk = 0; rst_n = 0; en = 0; #20;
        rst_n = 1; en = 1;
        @(posedge clk); #1;
        if (cnt === 4'd1) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: expected 1, got %0d", cnt); end
        @(posedge clk); #1;
        if (cnt === 4'd2) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: expected 2, got %0d", cnt); end
        @(posedge clk); #1;
        if (cnt === 4'd3) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: expected 3, got %0d", cnt); end
        en = 0; @(posedge clk); #1;
        if (cnt === 4'd3) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: hold expected 3, got %0d", cnt); end
        @(posedge clk); #1;
        if (cnt === 4'd3) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: still hold expected 3, got %0d", cnt); end
        en = 1; @(posedge clk); #1;
        if (cnt === 4'd4) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: resume expected 4, got %0d", cnt); end
        rst_n = 0; #10;
        if (cnt === 4'd0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: reset expected 0, got %0d", cnt); end
        if (fail === 0) $display("ALL_TESTS_PASS: %0d/%0d", pass, pass+fail);
        else $display("TEST_FAIL: %0d/%0d", pass, pass+fail);
        $finish;
    end
endmodule
""",
        "ports": "input clk, rst_n, en; output [3:0] cnt",
        "description": "4-bit counter with enable and active-low synchronous reset",
        "mutant_description": "enable polarity or increment value",
    }


def _template_fsm():
    return {
        "name": "fsm",
        "difficulty": "medium",
        "module_name": "fsm_simple",
        "golden": """\
module fsm_simple (
    input  wire clk, rst_n, go, finish,
    output reg  busy, completed
);
    localparam S_IDLE=0, S_RUN=1, S_DONE=2;
    reg [1:0] state, next;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) state <= S_IDLE;
        else        state <= next;
    always @(*) begin
        next = state;
        busy = 0;
        completed = 0;
        case (state)
            S_IDLE: begin if (go) next = S_RUN; end
            S_RUN:  begin busy = 1; if (finish) next = S_DONE; end
            S_DONE: begin completed = 1; next = S_IDLE; end
        endcase
    end
endmodule
""",
        "mutants": [
            {
                "name": "wrong_transition",
                "code": """\
module fsm_simple (
    input  wire clk, rst_n, go, finish,
    output reg  busy, completed
);
    localparam S_IDLE=0, S_RUN=1, S_DONE=2;
    reg [1:0] state, next;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) state <= S_IDLE;
        else        state <= next;
    always @(*) begin
        next = state;
        busy = 0;
        completed = 0;
        case (state)
            S_IDLE: begin if (go) next = S_RUN; end
            S_RUN:  begin busy = 1; if (finish) next = S_IDLE; end
            S_DONE: begin completed = 1; next = S_IDLE; end
        endcase
    end
endmodule
""",
                "bug_description": "S_RUN+finish goes to S_IDLE instead of S_DONE",
            },
            {
                "name": "missing_busy",
                "code": """\
module fsm_simple (
    input  wire clk, rst_n, go, finish,
    output reg  busy, completed
);
    localparam S_IDLE=0, S_RUN=1, S_DONE=2;
    reg [1:0] state, next;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) state <= S_IDLE;
        else        state <= next;
    always @(*) begin
        next = state;
        busy = 0;
        completed = 0;
        case (state)
            S_IDLE: begin if (go) next = S_RUN; end
            S_RUN:  begin if (finish) next = S_DONE; end
            S_DONE: begin completed = 1; next = S_IDLE; end
        endcase
    end
endmodule
""",
                "bug_description": "busy not asserted in S_RUN state",
            },
        ],
        "solution_tb": """\
module tb;
    reg clk, rst_n, go, finish;
    wire busy, completed;
    fsm_simple uut (.clk(clk), .rst_n(rst_n), .go(go), .finish(finish),
                    .busy(busy), .completed(completed));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        clk = 0; rst_n = 0; go = 0; finish = 0; #20;
        rst_n = 1;
        if (busy === 0 && completed === 0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: idle"); end
        go = 1; @(posedge clk); #1; go = 0;
        if (busy === 1) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: busy expected 1, got %b", busy); end
        if (completed === 0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: completed should be 0 in RUN"); end
        finish = 1; @(posedge clk); #1; finish = 0;
        if (completed === 1) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: completed expected 1, got %b", completed); end
        if (busy === 0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: busy should be 0 in DONE"); end
        @(posedge clk); #1;
        if (completed === 0 && busy === 0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: should be idle"); end
        if (fail === 0) $display("ALL_TESTS_PASS: %0d/%0d", pass, pass+fail);
        else $display("TEST_FAIL: %0d/%0d", pass, pass+fail);
        $finish;
    end
endmodule
""",
        "ports": "input clk, rst_n, go, finish; output busy, completed",
        "description": "3-state FSM: IDLE->RUN->DONE with busy and completed outputs",
        "mutant_description": "wrong transition or missing output assertion",
    }


def _template_handshake():
    return {
        "name": "handshake",
        "difficulty": "medium",
        "module_name": "handshake_reg",
        "golden": """\
module handshake_reg (
    input  wire       clk, rst_n,
    input  wire       valid_in,
    input  wire       ready_in,
    input  wire [7:0] data_in,
    output reg        valid_out,
    output reg        ready_out,
    output reg [7:0]  data_out
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_out <= 0;
            ready_out <= 1;
            data_out  <= 8'd0;
        end else begin
            if (valid_in && ready_out) begin
                data_out  <= data_in;
                valid_out <= 1;
                ready_out <= 0;
            end else if (ready_in && valid_out) begin
                valid_out <= 0;
                ready_out <= 1;
            end
        end
    end
endmodule
""",
        "mutants": [
            {
                "name": "ready_inverted",
                "code": """\
module handshake_reg (
    input  wire       clk, rst_n,
    input  wire       valid_in,
    input  wire       ready_in,
    input  wire [7:0] data_in,
    output reg        valid_out,
    output reg        ready_out,
    output reg [7:0]  data_out
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_out <= 0;
            ready_out <= 0;
            data_out  <= 8'd0;
        end else begin
            if (valid_in && ready_out) begin
                data_out  <= data_in;
                valid_out <= 1;
                ready_out <= 0;
            end else if (ready_in && valid_out) begin
                valid_out <= 0;
                ready_out <= 1;
            end
        end
    end
endmodule
""",
                "bug_description": "ready_out initialized to 0 instead of 1 (can never accept first transfer)",
            },
            {
                "name": "data_not_captured",
                "code": """\
module handshake_reg (
    input  wire       clk, rst_n,
    input  wire       valid_in,
    input  wire       ready_in,
    input  wire [7:0] data_in,
    output reg        valid_out,
    output reg        ready_out,
    output reg [7:0]  data_out
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_out <= 0;
            ready_out <= 1;
            data_out  <= 8'd0;
        end else begin
            if (valid_in && ready_out) begin
                valid_out <= 1;
                ready_out <= 0;
            end else if (ready_in && valid_out) begin
                valid_out <= 0;
                ready_out <= 1;
            end
        end
    end
endmodule
""",
                "bug_description": "data_in not captured into data_out on handshake",
            },
        ],
        "solution_tb": """\
module tb;
    reg clk, rst_n, valid_in, ready_in;
    reg [7:0] data_in;
    wire valid_out, ready_out;
    wire [7:0] data_out;
    handshake_reg uut (.clk(clk), .rst_n(rst_n), .valid_in(valid_in),
        .ready_in(ready_in), .data_in(data_in),
        .valid_out(valid_out), .ready_out(ready_out), .data_out(data_out));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        clk = 0; rst_n = 0; valid_in = 0; ready_in = 0; data_in = 0; #20;
        rst_n = 1; #1;
        if (ready_out === 1 && valid_out === 0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: initial state"); end
        data_in = 8'hA5; valid_in = 1; @(posedge clk); #1; valid_in = 0;
        if (valid_out === 1 && data_out === 8'hA5) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: capture expected A5, got %h", data_out); end
        if (ready_out === 0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: ready should be 0"); end
        ready_in = 1; @(posedge clk); #1; ready_in = 0;
        if (valid_out === 0 && ready_out === 1) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: ready handshake"); end
        data_in = 8'h3C; valid_in = 1; @(posedge clk); #1; valid_in = 0;
        if (valid_out === 1 && data_out === 8'h3C) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: second capture expected 3C, got %h", data_out); end
        if (fail === 0) $display("ALL_TESTS_PASS: %0d/%0d", pass, pass+fail);
        else $display("TEST_FAIL: %0d/%0d", pass, pass+fail);
        $finish;
    end
endmodule
""",
        "ports": "input clk, rst_n, valid_in, ready_in, [7:0] data_in; output valid_out, ready_out, [7:0] data_out",
        "description": "valid/ready handshake register with 8-bit data path",
        "mutant_description": "ready polarity or data capture failure",
    }


def _template_priority_encoder():
    return {
        "name": "priority_encoder",
        "difficulty": "easy",
        "module_name": "priority_enc",
        "golden": """\
module priority_enc (
    input  wire [3:0] req,
    output reg  [1:0] grant
);
    always @(*) begin
        if      (req[0]) grant = 2'd0;
        else if (req[1]) grant = 2'd1;
        else if (req[2]) grant = 2'd2;
        else if (req[3]) grant = 2'd3;
        else             grant = 2'd0;
    end
endmodule
""",
        "mutants": [
            {
                "name": "reversed_priority",
                "code": """\
module priority_enc (
    input  wire [3:0] req,
    output reg  [1:0] grant
);
    always @(*) begin
        if      (req[3]) grant = 2'd3;
        else if (req[2]) grant = 2'd2;
        else if (req[1]) grant = 2'd1;
        else if (req[0]) grant = 2'd0;
        else             grant = 2'd0;
    end
endmodule
""",
                "bug_description": "priority reversed: highest bit has priority instead of lowest",
            },
            {
                "name": "wrong_encoding",
                "code": """\
module priority_enc (
    input  wire [3:0] req,
    output reg  [1:0] grant
);
    always @(*) begin
        if      (req[0]) grant = 2'd1;
        else if (req[1]) grant = 2'd0;
        else if (req[2]) grant = 2'd3;
        else if (req[3]) grant = 2'd2;
        else             grant = 2'd0;
    end
endmodule
""",
                "bug_description": "grant encoding wrong: bits 0,1 swapped",
            },
        ],
        "solution_tb": """\
module tb;
    reg [3:0] req;
    wire [1:0] grant;
    priority_enc uut (.req(req), .grant(grant));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        req = 4'b0001; #10;
        if (grant === 2'd0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: req[0] expected grant=0, got %0d", grant); end
        req = 4'b0010; #10;
        if (grant === 2'd1) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: req[1] expected grant=1, got %0d", grant); end
        req = 4'b0100; #10;
        if (grant === 2'd2) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: req[2] expected grant=2, got %0d", grant); end
        req = 4'b1000; #10;
        if (grant === 2'd3) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: req[3] expected grant=3, got %0d", grant); end
        req = 4'b0011; #10;
        if (grant === 2'd0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: priority 0 over 1, got %0d", grant); end
        req = 4'b1100; #10;
        if (grant === 2'd2) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: priority 2 over 3, got %0d", grant); end
        req = 4'b1111; #10;
        if (grant === 2'd0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: all req priority 0, got %0d", grant); end
        req = 4'b0000; #10;
        if (grant === 2'd0) begin pass=pass+1; end else begin fail=fail+1; $display("FAIL: no req, got %0d", grant); end
        if (fail === 0) $display("ALL_TESTS_PASS: %0d/%0d", pass, pass+fail);
        else $display("TEST_FAIL: %0d/%0d", pass, pass+fail);
        $finish;
    end
endmodule
""",
        "ports": "input [3:0] req; output [1:0] grant",
        "description": "4-to-2 priority encoder: lowest bit has highest priority",
        "mutant_description": "priority order or grant encoding",
    }


# Registry of all design templates
DESIGN_TEMPLATES = [
    _template_mux2,
    _template_counter,
    _template_fsm,
    _template_handshake,
    _template_priority_encoder,
]

EXPECTED_TEMPLATE_NAMES = [fn()["name"] for fn in DESIGN_TEMPLATES]

RUN_PUBLIC_SCRIPT = """\
#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "=== Golden Design ==="
vcs -full64 -sverilog design_golden.sv tb.sv -o simv_golden -quiet 2>&1
./simv_golden 2>&1
"""

RUN_HIDDEN_SCRIPT = """\
#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "=== Mutant 1 ==="
vcs -full64 -sverilog design_mutant1.sv tb.sv -o simv_mutant1 -quiet 2>&1
./simv_mutant1 2>&1
echo "=== Mutant 2 ==="
vcs -full64 -sverilog design_mutant2.sv tb.sv -o simv_mutant2 -quiet 2>&1
./simv_mutant2 2>&1
"""


class P2TBGenerator(BaseGenerator):
    """Generates P2 Testbench/SVA Generation tasks with deterministic seeds."""

    # Task IDs start at 200001 to avoid collision with smoke task (200000)
    TASK_ID_OFFSET = 200001

    def generate_one(self, task_index: int) -> Path:
        template_fn = DESIGN_TEMPLATES[(task_index // 4) % len(DESIGN_TEMPLATES)]
        template = template_fn()

        # Pick mutant based on task_index % 2 (each template has 2 mutants)
        mutant_idx = task_index % 2
        mutant = template["mutants"][mutant_idx]

        task_num = self.TASK_ID_OFFSET + task_index
        task_id = f"task_{task_num:06d}"
        task_dir = self.output_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (task_dir / "files").mkdir(exist_ok=True)
        (task_dir / "hidden").mkdir(exist_ok=True)
        (task_dir / "solution").mkdir(exist_ok=True)

        # Write golden design (visible to agent)
        (task_dir / "files" / "design_golden.sv").write_text(template["golden"])

        # Write initial empty testbench (visible, editable — agent replaces this)
        (task_dir / "files" / "tb.sv").write_text(
            "// Agent: replace this file with your testbench\n"
            "module tb;\n    initial begin\n        $finish;\n    end\nendmodule\n"
        )

        # Write mutant design (hidden, used for grading)
        (task_dir / "hidden" / "design_mutant1.sv").write_text(mutant["code"])

        # Write a second mutant (rotate to next mutant)
        mutant2 = template["mutants"][(mutant_idx + 1) % len(template["mutants"])]
        (task_dir / "hidden" / "design_mutant2.sv").write_text(mutant2["code"])

        # Write run scripts
        (task_dir / "files" / "run_public.sh").write_text(RUN_PUBLIC_SCRIPT)
        (task_dir / "files" / "run_public.sh").chmod(0o755)
        (task_dir / "hidden" / "run_hidden.sh").write_text(RUN_HIDDEN_SCRIPT)
        (task_dir / "hidden" / "run_hidden.sh").chmod(0o755)

        # Write solution testbench
        (task_dir / "solution" / "tb.sv").write_text(template["solution_tb"])

        # Write prompt
        prompt = f"""\
# Testbench Generation Task: {template['name'].replace('_', ' ').title()}

## Description

Write a SystemVerilog testbench for the `{template['module_name']}` module.

{template['description']}.

Ports: {template['ports']}

## Files

- `design_golden.sv` — the correct design (do not modify)
- `tb.sv` — the testbench (you must create this file)

## Requirements

Your testbench should:

1. Instantiate the design module
2. Thoroughly test the expected behavior
3. Report pass/fail status using `$display("ALL_TESTS_PASS: ...")` on success
4. Use `$display("TEST_FAIL: ...")` on any failure
5. Call `$finish` when done

## Constraints

- Only submit `tb.sv`
- Do not modify `design_golden.sv`
"""
        (task_dir / "prompt.md").write_text(prompt)

        # Write metadata
        n_mutants = 2
        mutant_weight = round(0.4 / n_mutants, 4)
        meta = {
            "task_id": task_id,
            "track": "p2_rtl_gen",
            "tool": ["vcs"],
            "difficulty": template["difficulty"],
            "data_type": "mutation_synthetic",
            "resource_preset": "fast",
            "timeout_sec": 120,
            "max_tool_calls": 10,
            "max_patch_attempts": 3,
            "max_output_tokens": 16000,
            "files": {
                "visible": ["design_golden.sv", "run_public.sh", "tb.sv"],
                "editable": ["tb.sv"],
                "hidden": ["design_mutant1.sv", "design_mutant2.sv", "run_hidden.sh"],
                "forbidden": ["design_golden.sv", "design_mutant1.sv", "design_mutant2.sv",
                              "run_public.sh", "run_hidden.sh"],
            },
            "run_command": "bash run_public.sh && bash run_hidden.sh",
            "scoring": {
                "weights": {
                    "compile": 0.2,
                    "golden_pass": 0.4,
                    "mutant_1": mutant_weight,
                    "mutant_2": mutant_weight,
                },
                "evaluator": "rtl_gen.RTLGenEvaluator",
                "explanation_weight": 0.0,
            },
            "sanitizer": {"enabled": True},
            "generator": {
                "script": "p2_tb_sva_gen.py",
                "seed": self.seed,
                "template": template["name"],
                "mutant_name": mutant["name"],
                "mutant2_name": mutant2["name"],
                "mutant_description": mutant["bug_description"],
                "task_index": task_index,
            },
            "version": "1.0.0",
        }
        (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")

        return task_dir
