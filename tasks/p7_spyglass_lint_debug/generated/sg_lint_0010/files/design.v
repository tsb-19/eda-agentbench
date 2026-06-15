module sq_shift (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       din,
    output reg  [7:0] q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 8'd0;
        else
            q <= {q[6:0], din};
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= {8{1'b0}};
    end
endmodule
