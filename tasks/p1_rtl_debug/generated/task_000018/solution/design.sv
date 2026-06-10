module pipe2 (
    input  wire       clk, rst_n,
    input  wire [7:0] din,
    output reg  [7:0] dout
);
    reg [7:0] stage1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin stage1 <= 8'd0; dout <= 8'd0; end
        else begin stage1 <= din; dout <= stage1; end
    end
endmodule
