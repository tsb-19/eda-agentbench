module sq_addk (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] k,
    output reg  [7:0] y
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            y = 8'd0;
        else
            y = y + k;
    end
endmodule
