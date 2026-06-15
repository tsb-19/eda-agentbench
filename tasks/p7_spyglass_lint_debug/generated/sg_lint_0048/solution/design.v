module cmb_cmp3 (
    input  wire [7:0] a,
    input  wire [7:0] b,
    output reg  [1:0] y
);
    always @(*) begin
        if (a > b)
            y = 2'd2;
        else if (a == b)
            y = 2'd1;
        else
            y = 2'd0;
    end
endmodule
