module mux_reg (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [1:0] sel,
    input  wire [7:0] d0, d1, d2, d3,
    output reg  [7:0] q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 8'd0;
        else begin
            case (sel)
                2'd0: q <= d0;
                2'd1: q <= d1;
                2'd2: q <= d2;
                2'd3: q <= d3;
            endcase
        end
    end
endmodule
