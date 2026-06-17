"""Curated *subtle* RTL bugs for the P1 hardening pilot.

Same dict shape as ``generators.p1_rtl_debug_gen.BUG_TYPES``
({name, difficulty, correct, buggy, tb_public, tb_hidden, prompt_hint}), but
engineered for discrimination rather than recall:

  * The bug is a *corner-case* defect — the buggy module is functionally correct
    on the common case and only diverges on boundary / sign / wrap inputs.
  * ``tb_public`` exercises ONLY the common case, so the buggy module PASSES it.
    The model is therefore not handed the failing corner; it must reason about it.
  * ``tb_hidden`` is a deep suite of corner vectors (sign crossings, exact
    boundaries, overflow/wrap, back-to-back events). An incomplete fix — one that
    patches the common case or only one end of a range — passes a *fraction* of
    these, so the existing fractional PASS:/FAIL: evaluator yields a continuous
    score instead of 0/1.

Held constant vs the easy ``BUG_TYPES`` so the only changed variable is bug
subtlety: one bug per module, brief prompt hint, same scoring weights, same
multi-module bundling (see scripts/prototype_p1_subtle.py). Each module is
pre-flighted with iverilog before any commercial-tool run.
"""

from __future__ import annotations


def _bug_signed_max():
    return {
        "name": "signed_max",
        "difficulty": "hard",
        "correct": """\
module signed_max (
    input  wire signed [7:0] a, b,
    output wire signed [7:0] y
);
    assign y = (a > b) ? a : b;
endmodule
""",
        # Compares magnitudes as unsigned -> wrong whenever the operands' signs differ.
        "buggy": """\
module signed_max (
    input  wire signed [7:0] a, b,
    output wire signed [7:0] y
);
    assign y = ($unsigned(a) > $unsigned(b)) ? a : b;
endmodule
""",
        # Public: same-sign operands only -> unsigned compare agrees with signed.
        "tb_public": """\
module tb_public;
    reg signed [7:0] a, b;
    wire signed [7:0] y;
    signed_max uut (.a(a), .b(b), .y(y));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        a = 8'sd10;  b = 8'sd20;  #10;
        if (y === 8'sd20) begin $display("PASS: p1 max(10,20)"); pass=pass+1; end
        else begin $display("FAIL: p1 expected 20 got %0d", y); fail=fail+1; end
        a = 8'sd50;  b = 8'sd30;  #10;
        if (y === 8'sd50) begin $display("PASS: p2 max(50,30)"); pass=pass+1; end
        else begin $display("FAIL: p2 expected 50 got %0d", y); fail=fail+1; end
        a = -8'sd40; b = -8'sd80; #10;
        if (y === -8'sd40) begin $display("PASS: p3 max(-40,-80)"); pass=pass+1; end
        else begin $display("FAIL: p3 expected -40 got %0d", y); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        # Hidden: sign-crossing corners where unsigned-compare picks the wrong operand.
        "tb_hidden": """\
module tb_hidden;
    reg signed [7:0] a, b;
    wire signed [7:0] y;
    signed_max uut (.a(a), .b(b), .y(y));
    integer pass, fail;
    task chk(input signed [7:0] ea, eb, ey, input [127:0] tag);
        begin
            a = ea; b = eb; #10;
            if (y === ey) begin $display("PASS: %0s", tag); pass=pass+1; end
            else begin $display("FAIL: %0s expected %0d got %0d", tag, ey, y); fail=fail+1; end
        end
    endtask
    initial begin
        pass = 0; fail = 0;
        chk(-8'sd1,   8'sd1,   8'sd1,   "h1 max(-1,1)");
        chk( 8'sd1,  -8'sd1,   8'sd1,   "h2 max(1,-1)");
        chk(-8'sd128, 8'sd127, 8'sd127, "h3 max(-128,127)");
        chk( 8'sd127,-8'sd128, 8'sd127, "h4 max(127,-128)");
        chk(-8'sd100, 8'sd50,  8'sd50,  "h5 max(-100,50)");
        chk( 8'sd0,  -8'sd1,   8'sd0,   "h6 max(0,-1)");
        chk(-8'sd5,  -8'sd10, -8'sd5,   "h7 max(-5,-10) same-sign");
        chk( 8'sd100, 8'sd100, 8'sd100, "h8 max(100,100) equal");
        chk(-8'sd128,-8'sd1,  -8'sd1,   "h9 max(-128,-1)");
        chk( 8'sd3,   8'sd7,   8'sd7,   "h10 max(3,7)");
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "prompt_hint": "The inputs and output are signed. Make sure the comparison respects the sign.",
    }


def _bug_arith_shift():
    return {
        "name": "arith_shift",
        "difficulty": "hard",
        "correct": """\
module arith_shift (
    input  wire signed [7:0] a,
    input  wire       [2:0] sh,
    output wire signed [7:0] y
);
    assign y = a >>> sh;
endmodule
""",
        # Logical shift (`>>`) zero-fills, so negative inputs lose their sign.
        "buggy": """\
module arith_shift (
    input  wire signed [7:0] a,
    input  wire       [2:0] sh,
    output wire signed [7:0] y
);
    assign y = a >> sh;
endmodule
""",
        # Public: non-negative inputs -> logical and arithmetic shift agree.
        "tb_public": """\
module tb_public;
    reg  signed [7:0] a;
    reg        [2:0] sh;
    wire signed [7:0] y;
    arith_shift uut (.a(a), .sh(sh), .y(y));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        a = 8'sd64; sh = 3'd1; #10;
        if (y === 8'sd32) begin $display("PASS: p1 64>>>1"); pass=pass+1; end
        else begin $display("FAIL: p1 expected 32 got %0d", y); fail=fail+1; end
        a = 8'sd16; sh = 3'd2; #10;
        if (y === 8'sd4) begin $display("PASS: p2 16>>>2"); pass=pass+1; end
        else begin $display("FAIL: p2 expected 4 got %0d", y); fail=fail+1; end
        a = 8'sd100; sh = 3'd0; #10;
        if (y === 8'sd100) begin $display("PASS: p3 100>>>0"); pass=pass+1; end
        else begin $display("FAIL: p3 expected 100 got %0d", y); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        # Hidden: negative inputs with nonzero shift -> sign must be preserved.
        "tb_hidden": """\
module tb_hidden;
    reg  signed [7:0] a;
    reg        [2:0] sh;
    wire signed [7:0] y;
    arith_shift uut (.a(a), .sh(sh), .y(y));
    integer pass, fail;
    task chk(input signed [7:0] ea, input [2:0] esh, input signed [7:0] ey, input [127:0] tag);
        begin
            a = ea; sh = esh; #10;
            if (y === ey) begin $display("PASS: %0s", tag); pass=pass+1; end
            else begin $display("FAIL: %0s expected %0d got %0d", tag, ey, y); fail=fail+1; end
        end
    endtask
    initial begin
        pass = 0; fail = 0;
        chk(-8'sd8,   3'd1, -8'sd4,   "h1 -8>>>1");
        chk(-8'sd64,  3'd2, -8'sd16,  "h2 -64>>>2");
        chk(-8'sd1,   3'd1, -8'sd1,   "h3 -1>>>1");
        chk(-8'sd128, 3'd3, -8'sd16,  "h4 -128>>>3");
        chk(-8'sd2,   3'd1, -8'sd1,   "h5 -2>>>1");
        chk(-8'sd16,  3'd4, -8'sd1,   "h6 -16>>>4");
        chk(-8'sd100, 3'd0, -8'sd100, "h7 -100>>>0");
        chk( 8'sd32,  3'd2,  8'sd8,   "h8 32>>>2 (pos)");
        chk(-8'sd96,  3'd5, -8'sd3,   "h9 -96>>>5");
        chk(-8'sd7,   3'd1, -8'sd4,   "h10 -7>>>1 (floor)");
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "prompt_hint": "The input is signed. Shifting it right should preserve its arithmetic value.",
    }


def _bug_round_shift():
    return {
        "name": "round_shift",
        "difficulty": "hard",
        "correct": """\
module round_shift (
    input  wire [9:0] a,
    output wire [8:0] y
);
    // divide by 4, rounding to nearest (round half up); +2 done at 11 bits so the
    // bias add cannot overflow the 10-bit input before the shift.
    assign y = (a + 11'd2) >> 2;
endmodule
""",
        # Truncating divide: drops the fraction instead of rounding.
        "buggy": """\
module round_shift (
    input  wire [9:0] a,
    output wire [8:0] y
);
    assign y = a >> 2;
endmodule
""",
        # Public: exact multiples of 4 -> rounding and truncation agree.
        "tb_public": """\
module tb_public;
    reg  [9:0] a;
    wire [8:0] y;
    round_shift uut (.a(a), .y(y));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        a = 10'd0;   #10;
        if (y === 9'd0)   begin $display("PASS: p1 0/4"); pass=pass+1; end
        else begin $display("FAIL: p1 expected 0 got %0d", y); fail=fail+1; end
        a = 10'd16;  #10;
        if (y === 9'd4)   begin $display("PASS: p2 16/4"); pass=pass+1; end
        else begin $display("FAIL: p2 expected 4 got %0d", y); fail=fail+1; end
        a = 10'd400; #10;
        if (y === 9'd100) begin $display("PASS: p3 400/4"); pass=pass+1; end
        else begin $display("FAIL: p3 expected 100 got %0d", y); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        # Hidden: non-multiples where the rounded result differs from truncation.
        "tb_hidden": """\
module tb_hidden;
    reg  [9:0] a;
    wire [8:0] y;
    round_shift uut (.a(a), .y(y));
    integer pass, fail;
    task chk(input [9:0] ea, input [8:0] ey, input [127:0] tag);
        begin
            a = ea; #10;
            if (y === ey) begin $display("PASS: %0s", tag); pass=pass+1; end
            else begin $display("FAIL: %0s expected %0d got %0d", tag, ey, y); fail=fail+1; end
        end
    endtask
    initial begin
        pass = 0; fail = 0;
        chk(10'd2,    9'd1,   "h1 2/4=0.5->1");
        chk(10'd3,    9'd1,   "h2 3/4=0.75->1");
        chk(10'd6,    9'd2,   "h3 6/4=1.5->2");
        chk(10'd7,    9'd2,   "h4 7/4=1.75->2");
        chk(10'd10,   9'd3,   "h5 10/4=2.5->3");
        chk(10'd1022, 9'd256, "h6 1022/4=255.5->256");
        chk(10'd1023, 9'd256, "h7 1023/4=255.75->256");
        chk(10'd1,    9'd0,   "h8 1/4=0.25->0");
        chk(10'd5,    9'd1,   "h9 5/4=1.25->1");
        chk(10'd4,    9'd1,   "h10 4/4=1");
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "prompt_hint": "Scale the input down by 4, rounding to the nearest integer (round half up).",
    }


def _bug_sat_clip():
    return {
        "name": "sat_clip",
        "difficulty": "hard",
        "correct": """\
module sat_clip (
    input  wire signed [9:0] a,
    output reg  signed [7:0] y
);
    always @(*) begin
        if      (a >  10'sd127) y =  8'sd127;
        else if (a < -10'sd128) y = -8'sd128;
        else                    y =  a[7:0];
    end
endmodule
""",
        # Plain truncation: wraps out-of-range values instead of clamping them.
        "buggy": """\
module sat_clip (
    input  wire signed [9:0] a,
    output reg  signed [7:0] y
);
    always @(*) begin
        y = a[7:0];
    end
endmodule
""",
        # Public: values already inside [-128,127] -> truncation == clamp.
        "tb_public": """\
module tb_public;
    reg  signed [9:0] a;
    wire signed [7:0] y;
    sat_clip uut (.a(a), .y(y));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        a = 10'sd100;  #10;
        if (y === 8'sd100)  begin $display("PASS: p1 clip(100)"); pass=pass+1; end
        else begin $display("FAIL: p1 expected 100 got %0d", y); fail=fail+1; end
        a = -10'sd50;  #10;
        if (y === -8'sd50)  begin $display("PASS: p2 clip(-50)"); pass=pass+1; end
        else begin $display("FAIL: p2 expected -50 got %0d", y); fail=fail+1; end
        a = 10'sd0;    #10;
        if (y === 8'sd0)    begin $display("PASS: p3 clip(0)"); pass=pass+1; end
        else begin $display("FAIL: p3 expected 0 got %0d", y); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        # Hidden: out-of-range high and low, plus the exact saturation boundaries.
        "tb_hidden": """\
module tb_hidden;
    reg  signed [9:0] a;
    wire signed [7:0] y;
    sat_clip uut (.a(a), .y(y));
    integer pass, fail;
    task chk(input signed [9:0] ea, input signed [7:0] ey, input [127:0] tag);
        begin
            a = ea; #10;
            if (y === ey) begin $display("PASS: %0s", tag); pass=pass+1; end
            else begin $display("FAIL: %0s expected %0d got %0d", tag, ey, y); fail=fail+1; end
        end
    endtask
    initial begin
        pass = 0; fail = 0;
        chk(10'sd128,  8'sd127,  "h1 128->127");
        chk(10'sd200,  8'sd127,  "h2 200->127");
        chk(10'sd511,  8'sd127,  "h3 511->127");
        chk(-10'sd129, -8'sd128, "h4 -129->-128");
        chk(-10'sd300, -8'sd128, "h5 -300->-128");
        chk(-10'sd512, -8'sd128, "h6 -512->-128");
        chk(10'sd127,  8'sd127,  "h7 127 boundary");
        chk(-10'sd128, -8'sd128, "h8 -128 boundary");
        chk(10'sd50,   8'sd50,   "h9 50 in-range");
        chk(-10'sd80,  -8'sd80,  "h10 -80 in-range");
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "prompt_hint": "Clip the wider input into the output's representable range instead of letting it wrap.",
    }


def _bug_edge_detect():
    return {
        "name": "edge_detect",
        "difficulty": "hard",
        "correct": """\
module edge_detect (
    input  wire clk, rst_n,
    input  wire level,
    output reg  pulse
);
    reg level_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin level_d <= 1'b0; pulse <= 1'b0; end
        else begin
            level_d <= level;
            pulse   <= level & ~level_d;
        end
    end
endmodule
""",
        # XOR fires on BOTH edges -> spurious pulse on the falling edge too.
        "buggy": """\
module edge_detect (
    input  wire clk, rst_n,
    input  wire level,
    output reg  pulse
);
    reg level_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin level_d <= 1'b0; pulse <= 1'b0; end
        else begin
            level_d <= level;
            pulse   <= level ^ level_d;
        end
    end
endmodule
""",
        # Public: a single rising edge then hold-high (both designs agree here).
        "tb_public": """\
module tb_public;
    reg clk=0, rst_n, level;
    wire pulse;
    edge_detect uut (.clk(clk), .rst_n(rst_n), .level(level), .pulse(pulse));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 0; level = 0; @(posedge clk); #1; rst_n = 1;
        @(posedge clk); #1;            // level still 0
        level = 1; @(posedge clk); #1; // rising edge sampled
        if (pulse === 1'b1) begin $display("PASS: p1 rising pulse"); pass=pass+1; end
        else begin $display("FAIL: p1 expected pulse got %b", pulse); fail=fail+1; end
        @(posedge clk); #1;            // level held high
        if (pulse === 1'b0) begin $display("PASS: p2 no repeat while high"); pass=pass+1; end
        else begin $display("FAIL: p2 expected 0 got %b", pulse); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        # Hidden: falling edges (must NOT pulse) and back-to-back rising edges.
        "tb_hidden": """\
module tb_hidden;
    reg clk=0, rst_n, level;
    wire pulse;
    edge_detect uut (.clk(clk), .rst_n(rst_n), .level(level), .pulse(pulse));
    always #5 clk = ~clk;
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        rst_n = 0; level = 0; @(posedge clk); #1; rst_n = 1;
        @(posedge clk); #1;
        // rising edge
        level = 1; @(posedge clk); #1;
        if (pulse === 1'b1) begin $display("PASS: h1 rising"); pass=pass+1; end
        else begin $display("FAIL: h1 expected 1 got %b", pulse); fail=fail+1; end
        // hold high
        @(posedge clk); #1;
        if (pulse === 1'b0) begin $display("PASS: h2 hold high no pulse"); pass=pass+1; end
        else begin $display("FAIL: h2 expected 0 got %b", pulse); fail=fail+1; end
        // FALLING edge -> must NOT pulse
        level = 0; @(posedge clk); #1;
        if (pulse === 1'b0) begin $display("PASS: h3 falling no pulse"); pass=pass+1; end
        else begin $display("FAIL: h3 expected 0 got %b", pulse); fail=fail+1; end
        // hold low
        @(posedge clk); #1;
        if (pulse === 1'b0) begin $display("PASS: h4 hold low no pulse"); pass=pass+1; end
        else begin $display("FAIL: h4 expected 0 got %b", pulse); fail=fail+1; end
        // second rising
        level = 1; @(posedge clk); #1;
        if (pulse === 1'b1) begin $display("PASS: h5 second rising"); pass=pass+1; end
        else begin $display("FAIL: h5 expected 1 got %b", pulse); fail=fail+1; end
        // second falling -> must NOT pulse
        level = 0; @(posedge clk); #1;
        if (pulse === 1'b0) begin $display("PASS: h6 second falling no pulse"); pass=pass+1; end
        else begin $display("FAIL: h6 expected 0 got %b", pulse); fail=fail+1; end
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "prompt_hint": "Emit a one-clock pulse when the level signal asserts. Think about which edge.",
    }


def _bug_rotl():
    return {
        "name": "rotate_left",
        "difficulty": "hard",
        "correct": """\
module rotl8 (
    input  wire [7:0] a,
    input  wire [2:0] sh,
    output wire [7:0] y
);
    assign y = (sh == 3'd0) ? a : ((a << sh) | (a >> (4'd8 - sh)));
endmodule
""",
        # Plain left shift drops the bits that should wrap around to the bottom.
        "buggy": """\
module rotl8 (
    input  wire [7:0] a,
    input  wire [2:0] sh,
    output wire [7:0] y
);
    assign y = a << sh;
endmodule
""",
        # Public: low-magnitude inputs / shifts where no set bit wraps.
        "tb_public": """\
module tb_public;
    reg  [7:0] a;
    reg  [2:0] sh;
    wire [7:0] y;
    rotl8 uut (.a(a), .sh(sh), .y(y));
    integer pass, fail;
    initial begin
        pass = 0; fail = 0;
        a = 8'h01; sh = 3'd1; #10;
        if (y === 8'h02) begin $display("PASS: p1 01<<1"); pass=pass+1; end
        else begin $display("FAIL: p1 expected 02 got %h", y); fail=fail+1; end
        a = 8'h03; sh = 3'd2; #10;
        if (y === 8'h0C) begin $display("PASS: p2 03 rotl2"); pass=pass+1; end
        else begin $display("FAIL: p2 expected 0C got %h", y); fail=fail+1; end
        a = 8'hA5; sh = 3'd0; #10;
        if (y === 8'hA5) begin $display("PASS: p3 rotl0"); pass=pass+1; end
        else begin $display("FAIL: p3 expected A5 got %h", y); fail=fail+1; end
        $display("PUBLIC_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        # Hidden: high bits set / larger shifts where bits must wrap to the bottom.
        "tb_hidden": """\
module tb_hidden;
    reg  [7:0] a;
    reg  [2:0] sh;
    wire [7:0] y;
    rotl8 uut (.a(a), .sh(sh), .y(y));
    integer pass, fail;
    task chk(input [7:0] ea, input [2:0] esh, input [7:0] ey, input [127:0] tag);
        begin
            a = ea; sh = esh; #10;
            if (y === ey) begin $display("PASS: %0s", tag); pass=pass+1; end
            else begin $display("FAIL: %0s expected %h got %h", tag, ey, y); fail=fail+1; end
        end
    endtask
    initial begin
        pass = 0; fail = 0;
        chk(8'h81, 3'd1, 8'h03, "h1 81 rotl1");
        chk(8'hFF, 3'd4, 8'hFF, "h2 FF rotl4");
        chk(8'hC0, 3'd2, 8'h03, "h3 C0 rotl2");
        chk(8'h80, 3'd1, 8'h01, "h4 80 rotl1");
        chk(8'hA5, 3'd3, 8'h2D, "h5 A5 rotl3");
        chk(8'h0F, 3'd4, 8'hF0, "h6 0F rotl4");
        chk(8'hF0, 3'd4, 8'h0F, "h7 F0 rotl4");
        chk(8'h12, 3'd7, 8'h09, "h8 12 rotl7");
        chk(8'h01, 3'd0, 8'h01, "h9 rotl0");
        chk(8'hAA, 3'd1, 8'h55, "h10 AA rotl1");
        $display("HIDDEN_RESULT: %0d PASS, %0d FAIL", pass, fail);
        $finish;
    end
endmodule
""",
        "prompt_hint": "Rotate the bits left by sh; bits shifted off the top wrap around to the bottom.",
    }


# Registry — same shape/contract as p1_rtl_debug_gen.BUG_TYPES.
SUBTLE_BUG_TYPES = [
    _bug_signed_max,
    _bug_arith_shift,
    _bug_round_shift,
    _bug_sat_clip,
    _bug_edge_detect,
    _bug_rotl,
]

EXPECTED_SUBTLE_BUG_TYPES = [fn()["name"] for fn in SUBTLE_BUG_TYPES]
