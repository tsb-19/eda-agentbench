module cmb_selconst (
    input  wire [7:0] a,
    input  wire       sel,
    output reg  [7:0] y
);
    always @(*) begin
        if (sel)
            y = a;
        else
            y = 8'haa;
    end
endmodule
