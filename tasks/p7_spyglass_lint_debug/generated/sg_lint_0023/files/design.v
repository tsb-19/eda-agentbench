module sq_decr (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       en,
    output reg  [7:0] c
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            c = 8'hff;
        else if (en)
            c = c - 8'd1;
    end
endmodule
