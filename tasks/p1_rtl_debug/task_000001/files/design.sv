// 2-to-1 multiplexer (BUGGY: missing 'b' in sensitivity list)
module mux2 (
    input  wire a,
    input  wire b,
    input  wire sel,
    output reg  y
);
    always @(a or sel) begin
        if (sel)
            y = a;
        else
            y = b;
    end
endmodule
