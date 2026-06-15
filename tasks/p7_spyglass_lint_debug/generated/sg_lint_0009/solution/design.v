module cmb_gate (
    input  wire [3:0] d,
    input  wire       en,
    output reg  [3:0] q
);
    always @(*) begin
        if (en)
            q = d;
        else
            q = 4'd0;
    end
endmodule
