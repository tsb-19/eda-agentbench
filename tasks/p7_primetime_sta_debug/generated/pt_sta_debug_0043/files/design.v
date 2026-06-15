module parity_reg (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] data,
    output reg        par
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            par <= 1'b0;
        else
            par <= ^data;
    end
endmodule
