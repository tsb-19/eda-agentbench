module sq_toggle (
    input  wire       clk,
    input  wire       rst_n,
    input  wire en,
    output reg  t
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            t = 1'b0;
        else if (en)
            t = ~t;
    end
endmodule
