"""P1 RTL Debug task generator — 10 bug types, deterministic seed."""

from __future__ import annotations

import json
from pathlib import Path

from generators.base import BaseGenerator

# ---------------------------------------------------------------------------
# Bug type templates
# Each returns: {name, correct, buggy, tb_public, tb_hidden, prompt_hint, difficulty}
# ---------------------------------------------------------------------------

def _bug_sensitivity_list():
    return {
        "name": "sensitivity_list",
        "difficulty": "easy",
        "correct": """\
module mux2 (
    input  wire a, b, sel,
    output reg  y
);
    always @(*) begin
        if (sel) y = a;
        else     y = b;
    end
endmodule
""",
        "buggy": """\
module mux2 (
    input  wire a, b, sel,
    output reg  y
);
    always @(a or sel) begin
        if (sel) y = a;
        else     y = b;
    end
endmodule
""",
        "tb_public": """\
module tb_public;
    reg a, b, sel;
    wire y;
    mux2 uut (.a(a), .b(b), .sel(sel), .y(y));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        a=0; b=1; sel=0; #10;
        if (y===1'b1) begin $display("PASS: t1 sel=0 y=b"); pass=pass+1; end
        else begin $display("FAIL: t1 sel=0 expected 1 got %b", y); fail=fail+1; end
        a=1; b=0; sel=1; #10;
        if (y===1'b1) begin $display("PASS: t2 sel=1 y=a"); pass=pass+1; end
        else begin $display("FAIL: t2 sel=1 expected 1 got %b", y); fail=fail+1; end
        a=0; b=1; sel=0; #10;
        b=0; #10;
        if (y===1'b0) begin $display("PASS: t3 b changed"); pass=pass+1; end
        else begin $display("FAIL: t3 expected 0 got %b", y); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "tb_hidden": """\
module tb_hidden;
    reg a, b, sel;
    wire y;
    mux2 uut (.a(a), .b(b), .sel(sel), .y(y));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        a=1; b=0; sel=1; #10;
        a=0; #10;
        if (y===1'b0) begin $display("PASS: t4 sel=1 a changed"); pass=pass+1; end
        else begin $display("FAIL: t4 expected 0 got %b", y); fail=fail+1; end
        a=0; b=0; sel=0; #10;
        b=1; #10;
        if (y===1'b1) begin $display("PASS: t5a b toggled up"); pass=pass+1; end
        else begin $display("FAIL: t5a expected 1 got %b", y); fail=fail+1; end
        b=0; #10;
        if (y===1'b0) begin $display("PASS: t5b b toggled down"); pass=pass+1; end
        else begin $display("FAIL: t5b expected 0 got %b", y); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "prompt_hint": "Pay attention to the sensitivity list. When does the always block re-evaluate?",
    }


def _bug_blocking_nonblocking():
    return {
        "name": "blocking_nonblocking",
        "difficulty": "medium",
        "correct": """\
module pipe2 (
    input  wire       clk, rst_n,
    input  wire [7:0] din,
    output reg  [7:0] dout
);
    reg [7:0] stage1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin stage1 <= 8'd0; dout <= 8'd0; end
        else begin stage1 <= din; dout <= stage1; end
    end
endmodule
""",
        "buggy": """\
module pipe2 (
    input  wire       clk, rst_n,
    input  wire [7:0] din,
    output reg  [7:0] dout
);
    reg [7:0] stage1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin stage1 = 8'd0; dout = 8'd0; end
        else begin stage1 = din; dout = stage1; end
    end
endmodule
""",
        "tb_public": """\
module tb_public;
    reg clk=0, rst_n;
    reg [7:0] din;
    wire [7:0] dout;
    pipe2 uut (.clk(clk), .rst_n(rst_n), .din(din), .dout(dout));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 0; din = 8'hAA; #20;
        rst_n = 1;
        din = 8'h11; @(posedge clk); #1;
        din = 8'h22; @(posedge clk); #1;
        if (dout === 8'h11) begin $display("PASS: t1 pipeline latency"); pass=pass+1; end
        else begin $display("FAIL: t1 expected 11 got %h", dout); fail=fail+1; end
        din = 8'h33; @(posedge clk); #1;
        if (dout === 8'h22) begin $display("PASS: t2 pipeline shift"); pass=pass+1; end
        else begin $display("FAIL: t2 expected 22 got %h", dout); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "tb_hidden": """\
module tb_hidden;
    reg clk=0, rst_n;
    reg [7:0] din;
    wire [7:0] dout;
    pipe2 uut (.clk(clk), .rst_n(rst_n), .din(din), .dout(dout));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 0; din = 0; #20;
        rst_n = 1;
        din = 8'hA5; @(posedge clk); #1;
        din = 8'h5A; @(posedge clk); #1;
        din = 8'hFF; @(posedge clk); #1;
        if (dout === 8'h5A) begin $display("PASS: t3 third cycle"); pass=pass+1; end
        else begin $display("FAIL: t3 expected 5a got %h", dout); fail=fail+1; end
        rst_n = 0; #10; rst_n = 1; #10;
        din = 8'h42; @(posedge clk); #1;
        din = 8'h00; @(posedge clk); #1;
        if (dout === 8'h42) begin $display("PASS: t4 after reset"); pass=pass+1; end
        else begin $display("FAIL: t4 expected 42 got %h", dout); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "prompt_hint": "Think about blocking (=) vs nonblocking (<=) assignments in sequential logic.",
    }


def _bug_reset_polarity():
    return {
        "name": "reset_polarity",
        "difficulty": "easy",
        "correct": """\
module counter_rst (
    input  wire       clk, rst_n, en,
    output reg  [3:0] cnt
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) cnt <= 4'd0;
        else if (en) cnt <= cnt + 1;
    end
endmodule
""",
        "buggy": """\
module counter_rst (
    input  wire       clk, rst_n, en,
    output reg  [3:0] cnt
);
    always @(posedge clk or negedge rst_n) begin
        if (rst_n) cnt <= 4'd0;
        else if (en) cnt <= cnt + 1;
    end
endmodule
""",
        "tb_public": """\
module tb_public;
    reg clk=0, rst_n, en;
    wire [3:0] cnt;
    counter_rst uut (.clk(clk), .rst_n(rst_n), .en(en), .cnt(cnt));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 0; en = 0; #20;
        if (cnt === 4'd0) begin $display("PASS: t1 reset clears"); pass=pass+1; end
        else begin $display("FAIL: t1 expected 0 got %0d", cnt); fail=fail+1; end
        rst_n = 1; en = 1; @(posedge clk); #1;
        @(posedge clk); #1;
        @(posedge clk); #1;
        if (cnt === 4'd3) begin $display("PASS: t2 counts up"); pass=pass+1; end
        else begin $display("FAIL: t2 expected 3 got %0d", cnt); fail=fail+1; end
        rst_n = 0; #10;
        if (cnt === 4'd0) begin $display("PASS: t3 reset again"); pass=pass+1; end
        else begin $display("FAIL: t3 expected 0 got %0d", cnt); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "tb_hidden": """\
module tb_hidden;
    reg clk=0, rst_n, en;
    wire [3:0] cnt;
    counter_rst uut (.clk(clk), .rst_n(rst_n), .en(en), .cnt(cnt));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 1; en = 0; #20;
        rst_n = 0; #10; rst_n = 1; en = 1; #1;
        @(posedge clk); #1;
        @(posedge clk); #1;
        if (cnt === 4'd2) begin $display("PASS: t4 count after release"); pass=pass+1; end
        else begin $display("FAIL: t4 expected 2 got %0d", cnt); fail=fail+1; end
        en = 0; @(posedge clk); #1;
        if (cnt === 4'd2) begin $display("PASS: t5 hold when !en"); pass=pass+1; end
        else begin $display("FAIL: t5 expected 2 got %0d", cnt); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "prompt_hint": "Check the reset polarity. Is the reset active-high or active-low?",
    }


def _bug_width_truncation():
    return {
        "name": "width_truncation",
        "difficulty": "medium",
        "correct": """\
module adder_wide (
    input  wire [7:0] a, b,
    output wire [8:0] sum
);
    assign sum = {1'b0, a} + {1'b0, b};
endmodule
""",
        "buggy": """\
module adder_wide (
    input  wire [7:0] a, b,
    output wire [8:0] sum
);
    wire [7:0] s8;
    assign s8 = a + b;
    assign sum = {1'b0, s8};
endmodule
""",
        "tb_public": """\
module tb_public;
    reg [7:0] a, b;
    wire [8:0] sum;
    adder_wide uut (.a(a), .b(b), .sum(sum));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        a = 8'd10; b = 8'd20; #10;
        if (sum === 9'd30) begin $display("PASS: t1 simple add"); pass=pass+1; end
        else begin $display("FAIL: t1 expected 30 got %0d", sum); fail=fail+1; end
        a = 8'd200; b = 8'd100; #10;
        if (sum === 9'd300) begin $display("PASS: t2 overflow"); pass=pass+1; end
        else begin $display("FAIL: t2 expected 300 got %0d", sum); fail=fail+1; end
        a = 8'd255; b = 8'd255; #10;
        if (sum === 9'd510) begin $display("PASS: t3 max"); pass=pass+1; end
        else begin $display("FAIL: t3 expected 510 got %0d", sum); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "tb_hidden": """\
module tb_hidden;
    reg [7:0] a, b;
    wire [8:0] sum;
    adder_wide uut (.a(a), .b(b), .sum(sum));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        a = 8'd128; b = 8'd128; #10;
        if (sum === 9'd256) begin $display("PASS: t4 128+128"); pass=pass+1; end
        else begin $display("FAIL: t4 expected 256 got %0d", sum); fail=fail+1; end
        a = 8'd0; b = 8'd0; #10;
        if (sum === 9'd0) begin $display("PASS: t5 zero"); pass=pass+1; end
        else begin $display("FAIL: t5 expected 0 got %0d", sum); fail=fail+1; end
        a = 8'd255; b = 8'd1; #10;
        if (sum === 9'd256) begin $display("PASS: t6 255+1"); pass=pass+1; end
        else begin $display("FAIL: t6 expected 256 got %0d", sum); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "prompt_hint": "Watch out for intermediate width truncation before extending to the output width.",
    }


def _bug_comparison_boundary():
    return {
        "name": "comparison_boundary",
        "difficulty": "easy",
        "correct": """\
module range_check (
    input  wire [3:0] val,
    output reg        in_range
);
    always @(*) begin
        in_range = (val >= 4'd3) && (val <= 4'd12);
    end
endmodule
""",
        "buggy": """\
module range_check (
    input  wire [3:0] val,
    output reg        in_range
);
    always @(*) begin
        in_range = (val > 4'd3) && (val < 4'd12);
    end
endmodule
""",
        "tb_public": """\
module tb_public;
    reg [3:0] val;
    wire in_range;
    range_check uut (.val(val), .in_range(in_range));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        val = 4'd0; #10;
        if (in_range === 1'b0) begin $display("PASS: t1 val=0 out"); pass=pass+1; end
        else begin $display("FAIL: t1 val=0 expected 0 got %b", in_range); fail=fail+1; end
        val = 4'd3; #10;
        if (in_range === 1'b1) begin $display("PASS: t2 val=3 in"); pass=pass+1; end
        else begin $display("FAIL: t2 val=3 expected 1 got %b", in_range); fail=fail+1; end
        val = 4'd12; #10;
        if (in_range === 1'b1) begin $display("PASS: t3 val=12 in"); pass=pass+1; end
        else begin $display("FAIL: t3 val=12 expected 1 got %b", in_range); fail=fail+1; end
        val = 4'd15; #10;
        if (in_range === 1'b0) begin $display("PASS: t4 val=15 out"); pass=pass+1; end
        else begin $display("FAIL: t4 val=15 expected 0 got %b", in_range); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "tb_hidden": """\
module tb_hidden;
    reg [3:0] val;
    wire in_range;
    range_check uut (.val(val), .in_range(in_range));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        val = 4'd5; #10;
        if (in_range === 1'b1) begin $display("PASS: t5 val=5 in"); pass=pass+1; end
        else begin $display("FAIL: t5 val=5 expected 1 got %b", in_range); fail=fail+1; end
        val = 4'd10; #10;
        if (in_range === 1'b1) begin $display("PASS: t6 val=10 in"); pass=pass+1; end
        else begin $display("FAIL: t6 val=10 expected 1 got %b", in_range); fail=fail+1; end
        val = 4'd1; #10;
        if (in_range === 1'b0) begin $display("PASS: t7 val=1 out"); pass=pass+1; end
        else begin $display("FAIL: t7 val=1 expected 0 got %b", in_range); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "prompt_hint": "Check the boundary conditions. Should the comparison be inclusive (>=, <=) or exclusive (>, <)?",
    }


def _bug_mux_select():
    return {
        "name": "wrong_mux_select",
        "difficulty": "easy",
        "correct": """\
module mux4 (
    input  wire [1:0] sel,
    input  wire [7:0] d0, d1, d2, d3,
    output reg  [7:0] y
);
    always @(*) begin
        case (sel)
            2'b00: y = d0;
            2'b01: y = d1;
            2'b10: y = d2;
            2'b11: y = d3;
        endcase
    end
endmodule
""",
        "buggy": """\
module mux4 (
    input  wire [1:0] sel,
    input  wire [7:0] d0, d1, d2, d3,
    output reg  [7:0] y
);
    always @(*) begin
        case (sel)
            2'b00: y = d0;
            2'b01: y = d1;
            2'b10: y = d3;
            2'b11: y = d2;
        endcase
    end
endmodule
""",
        "tb_public": """\
module tb_public;
    reg [1:0] sel;
    reg [7:0] d0, d1, d2, d3;
    wire [7:0] y;
    mux4 uut (.sel(sel), .d0(d0), .d1(d1), .d2(d2), .d3(d3), .y(y));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        d0=8'hAA; d1=8'hBB; d2=8'hCC; d3=8'hDD;
        sel = 2'b00; #10;
        if (y === 8'hAA) begin $display("PASS: t1 sel=0"); pass=pass+1; end
        else begin $display("FAIL: t1 expected AA got %h", y); fail=fail+1; end
        sel = 2'b01; #10;
        if (y === 8'hBB) begin $display("PASS: t2 sel=1"); pass=pass+1; end
        else begin $display("FAIL: t2 expected BB got %h", y); fail=fail+1; end
        sel = 2'b10; #10;
        if (y === 8'hCC) begin $display("PASS: t3 sel=2"); pass=pass+1; end
        else begin $display("FAIL: t3 expected CC got %h", y); fail=fail+1; end
        sel = 2'b11; #10;
        if (y === 8'hDD) begin $display("PASS: t4 sel=3"); pass=pass+1; end
        else begin $display("FAIL: t4 expected DD got %h", y); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "tb_hidden": """\
module tb_hidden;
    reg [1:0] sel;
    reg [7:0] d0, d1, d2, d3;
    wire [7:0] y;
    mux4 uut (.sel(sel), .d0(d0), .d1(d1), .d2(d2), .d3(d3), .y(y));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        d0=8'h00; d1=8'h11; d2=8'h22; d3=8'h33;
        sel = 2'b10; #10;
        if (y === 8'h22) begin $display("PASS: t5 sel=2 alt"); pass=pass+1; end
        else begin $display("FAIL: t5 expected 22 got %h", y); fail=fail+1; end
        sel = 2'b11; #10;
        if (y === 8'h33) begin $display("PASS: t6 sel=3 alt"); pass=pass+1; end
        else begin $display("FAIL: t6 expected 33 got %h", y); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "prompt_hint": "Check that each mux input is correctly mapped to its select value.",
    }


def _bug_priority_order():
    return {
        "name": "priority_order",
        "difficulty": "medium",
        "correct": """\
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
        "buggy": """\
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
        "tb_public": """\
module tb_public;
    reg [3:0] req;
    wire [1:0] grant;
    priority_enc uut (.req(req), .grant(grant));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        req = 4'b0001; #10;
        if (grant === 2'd0) begin $display("PASS: t1 req[0]"); pass=pass+1; end
        else begin $display("FAIL: t1 expected 0 got %0d", grant); fail=fail+1; end
        req = 4'b0010; #10;
        if (grant === 2'd1) begin $display("PASS: t2 req[1]"); pass=pass+1; end
        else begin $display("FAIL: t2 expected 1 got %0d", grant); fail=fail+1; end
        req = 4'b0100; #10;
        if (grant === 2'd2) begin $display("PASS: t3 req[2]"); pass=pass+1; end
        else begin $display("FAIL: t3 expected 2 got %0d", grant); fail=fail+1; end
        req = 4'b1000; #10;
        if (grant === 2'd3) begin $display("PASS: t4 req[3]"); pass=pass+1; end
        else begin $display("FAIL: t4 expected 3 got %0d", grant); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "tb_hidden": """\
module tb_hidden;
    reg [3:0] req;
    wire [1:0] grant;
    priority_enc uut (.req(req), .grant(grant));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        req = 4'b0011; #10;
        if (grant === 2'd0) begin $display("PASS: t5 priority 0 over 1"); pass=pass+1; end
        else begin $display("FAIL: t5 expected 0 got %0d", grant); fail=fail+1; end
        req = 4'b1100; #10;
        if (grant === 2'd2) begin $display("PASS: t6 priority 2 over 3"); pass=pass+1; end
        else begin $display("FAIL: t6 expected 2 got %0d", grant); fail=fail+1; end
        req = 4'b1111; #10;
        if (grant === 2'd0) begin $display("PASS: t7 all req priority 0"); pass=pass+1; end
        else begin $display("FAIL: t7 expected 0 got %0d", grant); fail=fail+1; end
        req = 4'b0000; #10;
        if (grant === 2'd0) begin $display("PASS: t8 no req"); pass=pass+1; end
        else begin $display("FAIL: t8 expected 0 got %0d", grant); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "prompt_hint": "Check the priority order. Which request should be granted when multiple are active?",
    }


def _bug_fsm_transition():
    return {
        "name": "fsm_transition_error",
        "difficulty": "hard",
        "correct": """\
module fsm_simple (
    input  wire clk, rst_n, go, finish,
    output reg  busy,
    output reg  completed
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
        "buggy": """\
module fsm_simple (
    input  wire clk, rst_n, go, finish,
    output reg  busy,
    output reg  completed
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
        "tb_public": """\
module tb_public;
    reg clk=0, rst_n, go, finish;
    wire busy, completed;
    fsm_simple uut (.clk(clk), .rst_n(rst_n), .go(go), .finish(finish),
                    .busy(busy), .completed(completed));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 0; go = 0; finish = 0; #20;
        rst_n = 1;
        if (busy === 0 && completed === 0) begin $display("PASS: t1 idle"); pass=pass+1; end
        else begin $display("FAIL: t1 expected idle"); fail=fail+1; end
        go = 1; @(posedge clk); #1; go = 0;
        if (busy === 1) begin $display("PASS: t2 run busy"); pass=pass+1; end
        else begin $display("FAIL: t2 expected 1 got %b", busy); fail=fail+1; end
        // Assert finish: at next posedge, state→S_DONE, completed pulses
        finish = 1; @(posedge clk); #1; finish = 0;
        if (completed === 1) begin $display("PASS: t3 completed pulses"); pass=pass+1; end
        else begin $display("FAIL: t3 expected 1 got %b", completed); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "tb_hidden": """\
module tb_hidden;
    reg clk=0, rst_n, go, finish;
    wire busy, completed;
    fsm_simple uut (.clk(clk), .rst_n(rst_n), .go(go), .finish(finish),
                    .busy(busy), .completed(completed));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 0; #20; rst_n = 1;
        // First run
        go = 1; @(posedge clk); #1; go = 0;
        finish = 1; @(posedge clk); #1; finish = 0;
        // completed should be 1 right now (in S_DONE)
        if (completed === 1) begin $display("PASS: t4 first completed"); pass=pass+1; end
        else begin $display("FAIL: t4 expected 1 got %b", completed); fail=fail+1; end
        @(posedge clk); #1;
        // Back to idle
        if (completed === 0 && busy === 0) begin $display("PASS: t5 back to idle"); pass=pass+1; end
        else begin $display("FAIL: t5 expected idle"); fail=fail+1; end
        // Second run
        go = 1; @(posedge clk); #1; go = 0;
        finish = 1; @(posedge clk); #1; finish = 0;
        if (completed === 1) begin $display("PASS: t6 second completed"); pass=pass+1; end
        else begin $display("FAIL: t6 expected 1 got %b", completed); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "prompt_hint": "Check the FSM transitions. Does the completed signal pulse after the operation finishes?",
    }


def _bug_counter_off_by_one():
    return {
        "name": "counter_off_by_one",
        "difficulty": "easy",
        "correct": """\
module counter_mod (
    input  wire       clk, rst_n,
    output reg  [3:0] cnt,
    output reg        wrap
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin cnt <= 4'd0; wrap <= 0; end
        else if (cnt == 4'd9) begin cnt <= 4'd0; wrap <= 1; end
        else begin cnt <= cnt + 1; wrap <= 0; end
    end
endmodule
""",
        "buggy": """\
module counter_mod (
    input  wire       clk, rst_n,
    output reg  [3:0] cnt,
    output reg        wrap
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin cnt <= 4'd0; wrap <= 0; end
        else if (cnt == 4'd10) begin cnt <= 4'd0; wrap <= 1; end
        else begin cnt <= cnt + 1; wrap <= 0; end
    end
endmodule
""",
        "tb_public": """\
module tb_public;
    reg clk=0, rst_n;
    wire [3:0] cnt;
    wire wrap;
    counter_mod uut (.clk(clk), .rst_n(rst_n), .cnt(cnt), .wrap(wrap));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 0; #20; rst_n = 1;
        repeat(9) @(posedge clk); #1;
        if (cnt === 4'd9) begin $display("PASS: t1 cnt=9"); pass=pass+1; end
        else begin $display("FAIL: t1 expected 9 got %0d", cnt); fail=fail+1; end
        @(posedge clk); #1;
        if (cnt === 4'd0 && wrap === 1) begin $display("PASS: t2 wraps at 10"); pass=pass+1; end
        else begin $display("FAIL: t2 expected cnt=0 wrap=1 got cnt=%0d wrap=%b", cnt, wrap); fail=fail+1; end
        @(posedge clk); #1;
        if (cnt === 4'd1 && wrap === 0) begin $display("PASS: t3 continues"); pass=pass+1; end
        else begin $display("FAIL: t3 expected cnt=1 wrap=0 got cnt=%0d wrap=%b", cnt, wrap); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "tb_hidden": """\
module tb_hidden;
    reg clk=0, rst_n;
    wire [3:0] cnt;
    wire wrap;
    counter_mod uut (.clk(clk), .rst_n(rst_n), .cnt(cnt), .wrap(wrap));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 0; #20; rst_n = 1;
        repeat(19) @(posedge clk); #1;
        @(posedge clk); #1;
        if (cnt === 4'd0 && wrap === 1) begin $display("PASS: t4 second wrap"); pass=pass+1; end
        else begin $display("FAIL: t4 expected wrap cnt=%0d wrap=%b", cnt, wrap); fail=fail+1; end
        rst_n = 0; #10; rst_n = 1; @(posedge clk); #1;
        if (cnt === 4'd1) begin $display("PASS: t5 after reset"); pass=pass+1; end
        else begin $display("FAIL: t5 expected 1 got %0d", cnt); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "prompt_hint": "Check the counter wrap value. Does it count to the right modulus?",
    }


def _bug_enable_condition():
    return {
        "name": "enable_condition",
        "difficulty": "medium",
        "correct": """\
module en_counter (
    input  wire       clk, rst_n,
    input  wire       en,
    input  wire       load,
    input  wire [3:0] din,
    output reg  [3:0] cnt
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            cnt <= 4'd0;
        else if (load)
            cnt <= din;
        else if (en)
            cnt <= cnt + 1;
    end
endmodule
""",
        "buggy": """\
module en_counter (
    input  wire       clk, rst_n,
    input  wire       en,
    input  wire       load,
    input  wire [3:0] din,
    output reg  [3:0] cnt
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            cnt <= 4'd0;
        else if (load)
            cnt <= din;
        else if (!en)
            cnt <= cnt + 1;
    end
endmodule
""",
        "tb_public": """\
module tb_public;
    reg clk=0, rst_n, en, load;
    reg [3:0] din;
    wire [3:0] cnt;
    en_counter uut (.clk(clk), .rst_n(rst_n), .en(en), .load(load), .din(din), .cnt(cnt));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 0; en = 0; load = 0; din = 0; #20;
        rst_n = 1;
        en = 1; @(posedge clk); #1;
        @(posedge clk); #1;
        @(posedge clk); #1;
        if (cnt === 4'd3) begin $display("PASS: t1 counts with en"); pass=pass+1; end
        else begin $display("FAIL: t1 expected 3 got %0d", cnt); fail=fail+1; end
        en = 0; @(posedge clk); #1;
        @(posedge clk); #1;
        if (cnt === 4'd3) begin $display("PASS: t2 holds when !en"); pass=pass+1; end
        else begin $display("FAIL: t2 expected 3 got %0d", cnt); fail=fail+1; end
        load = 1; din = 4'd7; @(posedge clk); #1;
        load = 0;
        if (cnt === 4'd7) begin $display("PASS: t3 load works"); pass=pass+1; end
        else begin $display("FAIL: t3 expected 7 got %0d", cnt); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "tb_hidden": """\
module tb_hidden;
    reg clk=0, rst_n, en, load;
    reg [3:0] din;
    wire [3:0] cnt;
    en_counter uut (.clk(clk), .rst_n(rst_n), .en(en), .load(load), .din(din), .cnt(cnt));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 0; en = 0; load = 0; din = 0; #20; rst_n = 1;
        // Count with en=1
        en = 1; @(posedge clk); #1;
        @(posedge clk); #1;
        if (cnt === 4'd2) begin $display("PASS: t4 counted 2"); pass=pass+1; end
        else begin $display("FAIL: t4 expected 2 got %0d", cnt); fail=fail+1; end
        // Stop counting
        en = 0; @(posedge clk); #1;
        if (cnt === 4'd2) begin $display("PASS: t5 held at 2"); pass=pass+1; end
        else begin $display("FAIL: t5 expected 2 got %0d", cnt); fail=fail+1; end
        // Load value
        load = 1; din = 4'd9; @(posedge clk); #1;
        load = 0;
        if (cnt === 4'd9) begin $display("PASS: t6 loaded 9"); pass=pass+1; end
        else begin $display("FAIL: t6 expected 9 got %0d", cnt); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "prompt_hint": "Check the enable condition. Does the counter increment when en is high or low?",
    }


# Registry of all bug types
BUG_TYPES = [
    _bug_sensitivity_list,
    _bug_blocking_nonblocking,
    _bug_reset_polarity,
    _bug_width_truncation,
    _bug_comparison_boundary,
    _bug_mux_select,
    _bug_priority_order,
    _bug_fsm_transition,
    _bug_counter_off_by_one,
    _bug_enable_condition,
]

EXPECTED_BUG_TYPES = [fn()["name"] for fn in BUG_TYPES]

RUN_SCRIPT = """\
#!/bin/bash
set -e
cd "$(dirname "$0")"
vcs -full64 -sverilog design.sv {tb} -o {simv} -quiet
./{simv}
"""


class P1RTLDebugGenerator(BaseGenerator):
    """Generates P1 RTL Debug tasks with deterministic seeds."""

    def generate_one(self, task_index: int) -> Path:
        # Round-robin: ensures balanced distribution across bug types
        bug_fn = BUG_TYPES[(task_index // 10) % len(BUG_TYPES)]
        bug = bug_fn()

        task_id = f"task_{task_index:06d}"
        task_dir = self.output_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (task_dir / "files").mkdir(exist_ok=True)
        (task_dir / "hidden").mkdir(exist_ok=True)
        (task_dir / "solution").mkdir(exist_ok=True)

        # Write designs
        (task_dir / "files" / "design.sv").write_text(bug["buggy"])
        (task_dir / "solution" / "design.sv").write_text(bug["correct"])

        # Write testbenches
        (task_dir / "files" / "tb_public.sv").write_text(bug["tb_public"])
        (task_dir / "hidden" / "tb_hidden.sv").write_text(bug["tb_hidden"])

        # Write run scripts
        (task_dir / "files" / "run_public.sh").write_text(
            RUN_SCRIPT.format(tb="tb_public.sv", simv="simv_public"))
        (task_dir / "hidden" / "run_hidden.sh").write_text(
            RUN_SCRIPT.format(tb="tb_hidden.sv", simv="simv_hidden"))

        # Make scripts executable
        (task_dir / "files" / "run_public.sh").chmod(0o755)
        (task_dir / "hidden" / "run_hidden.sh").chmod(0o755)

        # Write prompt
        prompt = f"""\
# RTL Debug Task: {bug['name'].replace('_', ' ').title()}

## Description

The module below has a bug. Find and fix the bug in `design.sv` so that it passes all test cases.

## Files

- `design.sv` — the buggy design (you may edit this file)
- `tb_public.sv` — public testbench (do not modify)
- `run_public.sh` — public test runner (do not modify)

## Constraints

- Only modify `design.sv`
- Do not modify any other files

## Hint

{bug['prompt_hint']}
"""
        (task_dir / "prompt.md").write_text(prompt)

        # Write metadata
        meta = {
            "task_id": task_id,
            "track": "p1_rtl_debug",
            "tool": ["vcs"],
            "difficulty": bug["difficulty"],
            "data_type": "mutation_synthetic",
            "resource_preset": "fast",
            "timeout_sec": 120,
            "max_tool_calls": 10,
            "max_patch_attempts": 3,
            "max_output_tokens": 16000,
            "files": {
                "visible": ["design.sv", "tb_public.sv", "run_public.sh"],
                "editable": ["design.sv"],
                "hidden": ["tb_hidden.sv", "run_hidden.sh"],
                "forbidden": ["tb_public.sv", "tb_hidden.sv", "run_public.sh", "run_hidden.sh"],
            },
            "run_command": "bash run_public.sh && bash run_hidden.sh",
            "scoring": {
                "weights": {
                    "compile": 0.1,
                    "public_test": 0.3,
                    "hidden_test": 0.5,
                    "explanation": 0.1,
                },
                "explanation_weight": 0.1,
            },
            "sanitizer": {"enabled": True},
            "generator": {
                "script": "p1_rtl_debug_gen.py",
                "seed": self.seed,
                "bug_type": bug["name"],
                "task_index": task_index,
            },
            "version": "1.0.0",
        }
        (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")

        return task_dir
