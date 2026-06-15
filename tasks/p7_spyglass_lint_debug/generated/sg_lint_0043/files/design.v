module sq_rotate (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       en,
    output reg  [7:0] r
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            r <= 8'd1;
        else if (en)
            r <= {r[6:0], r[7]};
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            r <= {8{1'b0}};
    end
endmodule
