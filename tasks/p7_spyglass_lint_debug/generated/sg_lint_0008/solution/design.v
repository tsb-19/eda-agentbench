module sq_acc (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0]  x,
    output reg  [15:0] s
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            s <= 16'd0;
        else
            s <= s + {8'd0, x};
    end
endmodule
