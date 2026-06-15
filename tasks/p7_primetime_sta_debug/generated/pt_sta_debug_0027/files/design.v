module decoder_reg (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [1:0] sel,
    output reg  [3:0] onehot
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            onehot <= 4'd0;
        else
            onehot <= (4'd1 << sel);
    end
endmodule
