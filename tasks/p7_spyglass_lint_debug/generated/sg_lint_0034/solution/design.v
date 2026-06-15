module sq_gray (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] bin,
    output reg  [7:0] g
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            g <= 8'd0;
        else
            g <= (bin >> 1) ^ bin;
    end
endmodule
