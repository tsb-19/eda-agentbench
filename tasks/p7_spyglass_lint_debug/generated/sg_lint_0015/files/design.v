module cmb_andor (
    input  wire [7:0] a,
    input  wire [7:0] b,
    input  wire       op,
    output reg  [7:0] y
);
    always @(*) begin
        if (op)
            y = a & b;
    end
endmodule
