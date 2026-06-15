module cmb_mux2 (
    input  wire [7:0] a,
    input  wire [7:0] b,
    input  wire       sel,
    output reg  [7:0] y
);
    always @(*) begin
        if (sel)
            y = a;
        else
            y = b;
    end
endmodule
