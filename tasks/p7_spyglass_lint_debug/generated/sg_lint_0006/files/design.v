module cmb_min (
    input  wire [7:0] a,
    input  wire [7:0] b,
    output reg  [7:0] y
);
    always @(*) begin
        if (a < b)
            y = a;
    end
endmodule
