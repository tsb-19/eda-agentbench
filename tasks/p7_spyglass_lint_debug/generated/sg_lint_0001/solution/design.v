module multi_driven_clean (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] d,
    input  wire       en,
    output reg  [7:0] q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 8'd0;
        else if (en)
            q <= d;
    end
endmodule
