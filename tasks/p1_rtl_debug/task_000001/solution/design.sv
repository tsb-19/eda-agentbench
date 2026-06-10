// 2-to-1 multiplexer (FIXED: uses always @(*) for correct sensitivity)
module mux2 (
    input  wire a,
    input  wire b,
    input  wire sel,
    output reg  y
);
    always @(*) begin
        if (sel)
            y = a;
        else
            y = b;
    end
endmodule
