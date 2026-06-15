module mod10_counter (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       en,
    output reg  [3:0] mcnt
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            mcnt <= 4'd0;
        else if (en)
            mcnt <= (mcnt == 4'd9) ? 4'd0 : mcnt + 4'd1;
    end
endmodule
