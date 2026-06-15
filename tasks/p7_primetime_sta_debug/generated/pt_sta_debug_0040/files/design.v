module updown_counter (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       up,
    output reg  [7:0] cnt
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            cnt <= 8'd0;
        else if (up)
            cnt <= cnt + 8'd1;
        else
            cnt <= cnt - 8'd1;
    end
endmodule
