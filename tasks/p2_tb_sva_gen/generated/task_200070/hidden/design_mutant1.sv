module edge_detect (
    input  wire clk, rst_n, sig,
    output reg  rising,
    output reg  falling
);
    reg sig_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin sig_d <= 0; rising <= 0; falling <= 0; end
        else begin
            sig_d <= sig;
            rising  <= sig & ~sig_d;
            falling <= ~sig & sig_d;
        end
endmodule
