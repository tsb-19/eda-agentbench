module sq_par (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] d,
    output reg  p
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            p <= 1'b0;
        else
            p <= ^d;
    end
endmodule
