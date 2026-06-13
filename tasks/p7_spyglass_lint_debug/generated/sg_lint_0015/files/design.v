module comb_mux (
    input  wire [3:0] a,
    input  wire [3:0] b,
    input  wire       sel,
    output reg  [3:0] y
);
    always @(*) begin
        if (sel)
            y = a;
    end
endmodule
