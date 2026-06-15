module cmb_eqmux (
    input  wire [7:0] a,
    input  wire [7:0] b,
    input  wire [7:0] c,
    input  wire [7:0] d,
    output reg  [7:0] y
);
    always @(*) begin
        if (a == b)
            y = c;
        else
            y = d;
    end
endmodule
