// Design under test: the output register of ref_pipe was retimed BACKWARD across the adder
// onto its inputs (reg(x+y) == reg(x)+reg(y)), so the adder output is now combinational.
// Claimed equivalent to ref_pipe.
module dut_pipe (
    input  wire       clk,
    input  wire       rst,
    input  wire [7:0] x,
    input  wire [7:0] y,
    output wire [7:0] outp
);
    reg [7:0] rx;

    always @(posedge clk)
        if (rst) rx <= 8'd0;
        else     rx <= x;

    assign outp = rx + y;
endmodule
