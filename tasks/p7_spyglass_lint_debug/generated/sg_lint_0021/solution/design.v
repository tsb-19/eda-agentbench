module cmb_invsel (
    input  wire [7:0] a,
    input  wire       sel,
    output reg  [7:0] y
);
    always @(*) begin
        if (sel)
            y = a;
        else
            y = ~a;
    end
endmodule
