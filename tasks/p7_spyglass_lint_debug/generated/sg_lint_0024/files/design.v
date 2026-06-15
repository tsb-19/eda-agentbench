module cmb_masksel (
    input  wire [7:0] a,
    input  wire       sel,
    output reg  [7:0] y
);
    always @(*) begin
        if (sel)
            y = a & 8'h0f;
    end
endmodule
