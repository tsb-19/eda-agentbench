module en_counter (
    input  wire       clk, rst_n,
    input  wire       en,
    input  wire       load,
    input  wire [3:0] din,
    output reg  [3:0] cnt
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            cnt <= 4'd0;
        else if (load)
            cnt <= din;
        else if (en)
            cnt <= cnt + 1;
    end
endmodule
