module sq_xoracc (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] x,
    output reg  [7:0] a
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            a = 8'd0;
        else
            a = a ^ x;
    end
endmodule
