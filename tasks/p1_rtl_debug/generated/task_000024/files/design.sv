module counter_rst (
    input  wire       clk, rst_n, en,
    output reg  [3:0] cnt
);
    always @(posedge clk or negedge rst_n) begin
        if (rst_n) cnt <= 4'd0;
        else if (en) cnt <= cnt + 1;
    end
endmodule
