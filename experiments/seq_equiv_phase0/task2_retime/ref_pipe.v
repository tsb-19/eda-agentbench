// Reference: one pipeline register placed AFTER the adder.  Latency 1.
//   outp[n] = x[n-1] + y[n-1]
module ref_pipe (
    input  wire       clk,
    input  wire       rst,
    input  wire [7:0] x,
    input  wire [7:0] y,
    output reg  [7:0] outp
);
    always @(posedge clk)
        if (rst) outp <= 8'd0;
        else     outp <= x + y;
endmodule
