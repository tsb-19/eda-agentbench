module shift_reg (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       din,
    output reg  [7:0] dout
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            dout <= 8'd0;
        else
            dout <= {dout[6:0], din};
    end
endmodule
