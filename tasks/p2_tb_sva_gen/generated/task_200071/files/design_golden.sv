module edge_detect (
    input  wire clk, rst_n, sig,
    output wire rising,
    output wire falling
);
    reg sig_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) sig_d <= 0;
        else        sig_d <= sig;
    assign rising  = sig & ~sig_d;
    assign falling = ~sig & sig_d;
endmodule
