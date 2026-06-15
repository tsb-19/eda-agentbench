module sq_load (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       ld,
    input  wire [7:0] d,
    output reg  [7:0] r
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            r = 8'd0;
        else if (ld)
            r = d;
    end
endmodule
