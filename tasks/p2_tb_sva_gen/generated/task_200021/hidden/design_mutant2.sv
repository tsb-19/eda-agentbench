module pulse_detect (
    input  wire clk, rst_n, sig,
    output reg  pulse
);
    reg sig_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sig_d <= 0;
            pulse <= 0;
        end else begin
            pulse <= ~sig & sig_d;
            sig_d <= sig;
        end
    end
endmodule
