module toggle_ff (
    input  wire clk,
    input  wire rst_n,
    input  wire en,
    output reg  tff
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            tff <= 1'b0;
        else if (en)
            tff <= ~tff;
    end
endmodule
