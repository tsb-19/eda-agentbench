module counter_mod (
    input  wire       clk, rst_n,
    output reg  [3:0] cnt,
    output reg        wrap
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin cnt <= 4'd0; wrap <= 0; end
        else if (cnt == 4'd9) begin cnt <= 4'd0; wrap <= 1; end
        else begin cnt <= cnt + 1; wrap <= 0; end
    end
endmodule
