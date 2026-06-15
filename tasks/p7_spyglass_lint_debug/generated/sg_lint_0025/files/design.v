module sq_sat (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       en,
    output reg  [7:0] c
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            c <= 8'd0;
        else if (en && c != 8'hff)
            c <= c + 8'd1;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            c <= {8{1'b0}};
    end
endmodule
