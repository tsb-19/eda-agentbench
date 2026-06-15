module sq_reg (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] d,
    output reg  [7:0] q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 8'd0;
        else
            q <= d;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= {8{1'b0}};
    end
endmodule
