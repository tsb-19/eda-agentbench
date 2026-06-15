module sq_updown (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       up,
    output reg  [7:0] c
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            c <= 8'd0;
        else if (up)
            c <= c + 8'd1;
        else
            c <= c - 8'd1;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            c <= {8{1'b0}};
    end
endmodule
