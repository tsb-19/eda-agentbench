module acc_stage (
    input  wire clk_main,
    input  wire rst_n,
    input  wire en,
    input  wire din,
    output reg  dout
);
    // Two-stage registered datapath stage on clock clk_main. The behavioural RTL is the
    // human-facing design context; PrimeTime times the gate-level model in design_netlist.v
    // (a scalar-delay abstraction against tiny.db). Note the clock port is clk_main.
    reg cap;
    always @(posedge clk_main or negedge rst_n) begin
        if (!rst_n) begin
            cap  <= 1'b0;
            dout <= 1'b0;
        end else if (en) begin
            cap  <= din;   // input capture  (din -> cap)
            dout <= cap;    // registered output (cap -> dout)
        end
    end
endmodule
